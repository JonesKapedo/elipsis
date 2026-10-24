"""Marketplace governance: request privacy, bid review, award, and handoff gate."""
from __future__ import annotations

import os
import tempfile
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

os.environ["ELIPSIS_DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp(prefix='elipsis-market-')}/test.db"
os.environ.setdefault("ELIPSIS_HOST", "127.0.0.1")

from sqlalchemy import select  # noqa: E402

from elipsis_api import models, security  # noqa: E402
from elipsis_api.database import Base, SessionLocal, engine  # noqa: E402
from elipsis_api.main import app  # noqa: E402

Base.metadata.create_all(bind=engine)


def _email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


def _make_user(email: str, password: str, user_type: str = "client", pro: bool = False,
               is_admin: bool = False):
    with SessionLocal() as db:
        existing = db.scalar(select(models.User).where(models.User.email == email))
        if existing is not None:
            return existing.id
        user = models.User(
            email=email,
            name=email.split("@")[0],
            role="bidder" if user_type == "bidder" else "client",
            user_type=user_type,
            password_hash=security.hash_password(password),
            is_admin=is_admin,
        )
        db.add(user)
        db.flush()
        if pro:
            db.add(models.UserPref(user_id=user.id, pro_until="active"))
        db.commit()
        return user.id


def _make_bidder(email: str, password: str) -> int:
    user_id = _make_user(email, password, user_type="bidder")
    with SessionLocal() as db:
        bidder = models.BidderCompany(
            user_id=user_id,
            company_name="Verified Automation Ltd",
            contact_email=email,
            verification_status="approved",
            verification_submitted_at=datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="seconds"),
            verified_at=datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="seconds"),
            subscription_status="active",
            subscription_tier="monthly",
            subscription_expires_at=(
                datetime.now(UTC).replace(tzinfo=None) + timedelta(days=30)
            ).isoformat(timespec="seconds"),
            partner_tier="standard",
            rating=0,
            completed_jobs=0,
        )
        db.add(bidder)
        db.commit()
    return user_id


def _login(client: TestClient, email: str, password: str) -> None:
    response = client.post(
        "/login", data={"email": email, "password": password},
        headers={"x-forwarded-for": f"203.0.113.{uuid.uuid4().int % 200 + 20}"},
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text


def _demo_assessment(client: TestClient) -> tuple[int, int]:
    created = client.post("/demo", follow_redirects=False)
    assert created.status_code == 303
    assessment_id = int(created.headers["location"].split("/")[2])
    with SessionLocal() as db:
        assessment = db.get(models.Assessment, assessment_id)
        return assessment_id, assessment.organization_id


@pytest.fixture()
def marketplace_on(monkeypatch):
    from elipsis_api.routers import marketplace, marketplace_ui
    monkeypatch.setattr(marketplace, "MARKETPLACE_ENABLED", True)
    monkeypatch.setattr(marketplace_ui, "MARKETPLACE_ENABLED", True)


def test_request_is_private_until_approved_and_award_opens_conversation(marketplace_on):
    client_email = _email("client")
    other_email = _email("other")
    bidder_email = _email("bidder")
    _make_user(client_email, "client-password", pro=True)
    _make_user(other_email, "other-password", pro=True)
    _make_user("admin@elipsis.local", "elipsis", user_type="admin", is_admin=True)
    _make_bidder(bidder_email, "bidder-password")

    with TestClient(app) as client:
        _login(client, client_email, "client-password")
        assessment_id, org_id = _demo_assessment(client)
        with SessionLocal() as db:
            org = db.get(models.Organization, org_id)
            org.contact_name = "Demo Operations Lead"
            org.contact_email = "hello@guided-demo.test"
            org.contact_phone = "+254700000000"
            db.commit()
        created = client.post("/api/v1/marketplace/requests", json={
            "organization_id": org_id,
            "assessment_id": assessment_id,
            "title": "Automate dispatch reconciliation",
            "description": "Daily dispatch reports are reconciled by hand.",
            "expectations": "Cut reconciliation time by 70%.",
            "specifications": "Integrate with the existing TMS.",
        })
        assert created.status_code == 201, created.text
        request_id = created.json()["id"]
        assert created.json()["status"] == "pending_review"

    with TestClient(app) as other:
        _login(other, other_email, "other-password")
        assert other.get(f"/api/v1/marketplace/requests/{request_id}").status_code == 404
        listing = other.get("/api/v1/marketplace/requests").json()
        assert all(row["id"] != request_id for row in listing["requests"])
        assert other.get(f"/admin/requests/{request_id}").status_code == 404

    with TestClient(app) as admin:
        _login(admin, "admin@elipsis.local", "elipsis")
        approved = admin.post(f"/api/v1/admin/requests/{request_id}/approve")
        assert approved.status_code == 200, approved.text
        desk = admin.get(f"/admin/requests/{request_id}")
        assert desk.status_code == 200
        assert "Automate dispatch reconciliation" in desk.text

    with TestClient(app) as bidder:
        _login(bidder, bidder_email, "bidder-password")
        detail = bidder.get(f"/api/v1/marketplace/requests/{request_id}")
        assert detail.status_code == 200, detail.text
        assert detail.json()["organization"]["name"] == "Guided Demo Co"
        assert detail.json()["organization"]["contact_email"] is None
        bid = bidder.post(f"/api/v1/marketplace/requests/{request_id}/bid", json={
            "proposal": "We will map the current reconciliation and automate it in two phases.",
            "estimated_cost": 18000,
            "timeline": "6 weeks",
        })
        assert bid.status_code == 201, bid.text
        bid_id = bid.json()["id"]
        assert bid.json()["status"] == "pending_review"

    with TestClient(app) as client:
        _login(client, client_email, "client-password")
        assert client.get(f"/api/v1/marketplace/requests/{request_id}").json()["bids"] == []

    with TestClient(app) as admin:
        _login(admin, "admin@elipsis.local", "elipsis")
        desk = admin.get(f"/admin/requests/{request_id}")
        assert desk.status_code == 200
        assert "Verified Automation Ltd" in desk.text
        assert admin.post(f"/api/v1/admin/bids/{bid_id}/approve").status_code == 200
        bidders = admin.get("/admin/bidders")
        assert bidders.status_code == 200
        assert "Verified Automation Ltd" in bidders.text

    with TestClient(app) as client:
        _login(client, client_email, "client-password")
        visible = client.get(f"/api/v1/marketplace/requests/{request_id}").json()
        assert len(visible["bids"]) == 1
        assert visible["bids"][0]["id"] == bid_id
        assert visible["organization"]["contact_email"] == "hello@guided-demo.test"
        assert visible["can_choose_partner"] is True
        preferred = client.post(
            f"/api/v1/marketplace/requests/{request_id}/preferred",
            json={"bid_id": bid_id},
        )
        assert preferred.status_code == 200, preferred.text
        assert preferred.json()["preferred_bid_id"] == bid_id
        preferred_ui = client.post(
            f"/marketplace/{request_id}/preferred",
            data={"bid_id": bid_id},
            follow_redirects=False,
        )
        assert preferred_ui.status_code == 303
        desk = client.get(f"/marketplace/{request_id}")
        assert desk.status_code == 200
        assert "Your preference" in desk.text

    with TestClient(app) as admin:
        _login(admin, "admin@elipsis.local", "elipsis")
        desk = admin.get(f"/admin/requests/{request_id}")
        assert desk.status_code == 200
        assert "Client preference" in desk.text
        awarded = admin.post(
            f"/api/v1/admin/requests/{request_id}/award?bid_id={bid_id}")
        assert awarded.status_code == 200, awarded.text
        assert awarded.json()["status"] == "awarded"
        assert awarded.json()["conversation_id"]

    with TestClient(app) as client:
        _login(client, client_email, "client-password")
        awarded_detail = client.get(f"/api/v1/marketplace/requests/{request_id}").json()
        assert awarded_detail["status"] == "awarded"
        assert awarded_detail["organization"]["contact_email"] is not None


def test_bidder_subscription_requires_full_plan_amount(marketplace_on, monkeypatch):
    email = _email("planner")
    _make_user(email, "planner-password", user_type="bidder")
    from elipsis_api import paystack

    with TestClient(app) as client:
        _login(client, email, "planner-password")
        created = client.put(
            "/api/v1/bidder/shop", params={"company_name": "Plan Test Ltd"})
        assert created.status_code == 200, created.text
        assert created.json()["verification_status"] == "submitted"

        monkeypatch.setattr(paystack, "verify", lambda ref: {
            "status": "success", "reference": ref, "dummy": False,
            "amount": 100, "currency": "USD",
        })
        short = client.post("/api/v1/bidder/subscription/activate", params={
            "tier": "monthly", "payment_reference": f"short-{uuid.uuid4().hex}"})
        assert short.status_code == 402

        monkeypatch.setattr(paystack, "verify", lambda ref: {
            "status": "success", "reference": ref, "dummy": False,
            "amount": 3900, "currency": "USD",
        })
        paid = client.post("/api/v1/bidder/subscription/activate", params={
            "tier": "monthly", "payment_reference": f"full-{uuid.uuid4().hex}"})
        assert paid.status_code == 200, paid.text
        shop = client.get("/api/v1/bidder/shop").json()
        assert shop["verification_status"] == "submitted"
        assert shop["can_bid"] is False


def test_full_assessment_purchase_conversation_switch_handoff_and_directory(
        marketplace_on, monkeypatch):
    from urllib.parse import parse_qs, urlparse

    client_email = _email("buyer")
    bidder_one_email = _email("partner-one")
    bidder_two_email = _email("partner-two")
    _make_user(client_email, "buyer-password")
    _make_user("admin@elipsis.local", "elipsis", user_type="admin", is_admin=True)
    _make_bidder(bidder_one_email, "partner-one-password")
    _make_bidder(bidder_two_email, "partner-two-password")

    with TestClient(app) as client:
        _login(client, client_email, "buyer-password")
        assessment_id, org_id = _demo_assessment(client)
        free = client.get(f"/assessment/{assessment_id}/results")
        assert free.status_code == 200
        assert "Unlock Full Assessment" in free.text
        assert "Implementation roadmap" not in free.text

        checkout = client.post(f"/assessment/{assessment_id}/checkout",
                               follow_redirects=False)
        assert checkout.status_code == 303
        assert "/pay/dummy/ASM_" in checkout.headers["location"]
        reference = checkout.headers["location"].rsplit("/", 1)[-1]
        paid = client.get(f"/pay/return/{reference}", follow_redirects=False)
        assert paid.status_code == 303
        assert f"/assessment/{assessment_id}/results" in paid.headers["location"]
        unlocked = client.get(f"/assessment/{assessment_id}/results")
        assert "Implementation roadmap" in unlocked.text
        assert "Unlock Full Assessment" not in unlocked.text
        with SessionLocal() as db:
            purchase = db.scalar(select(models.AssessmentPurchase).where(
                models.AssessmentPurchase.assessment_id == assessment_id))
            assert purchase is not None and purchase.active is True

        created = client.post("/api/v1/marketplace/requests", json={
            "organization_id": org_id, "assessment_id": assessment_id,
            "title": "Switch and handoff flow",
            "description": "Two approved partners should be available.",
            "expectations": "A working dispatch workflow.",
            "specifications": "Integrate with the current TMS."})
        assert created.status_code == 201, created.text
        request_id = created.json()["id"]

    with TestClient(app) as admin:
        _login(admin, "admin@elipsis.local", "elipsis")
        assert admin.post(f"/api/v1/admin/requests/{request_id}/approve").status_code == 200

    bid_ids = []
    for email, password in ((bidder_one_email, "partner-one-password"),
                            (bidder_two_email, "partner-two-password")):
        with TestClient(app) as bidder:
            _login(bidder, email, password)
            bid = bidder.post(f"/api/v1/marketplace/requests/{request_id}/bid", json={
                "proposal": f"Proposal from {email}",
                "estimated_cost": 12000,
                "timeline": "5 weeks"})
            assert bid.status_code == 201, bid.text
            bid_ids.append(bid.json()["id"])

    with TestClient(app) as admin:
        _login(admin, "admin@elipsis.local", "elipsis")
        for bid_id in bid_ids:
            assert admin.post(f"/api/v1/admin/bids/{bid_id}/approve").status_code == 200
        award = admin.post(f"/api/v1/admin/requests/{request_id}/award?bid_id={bid_ids[0]}")
        assert award.status_code == 200, award.text
        conversation_id = award.json()["conversation_id"]

    with TestClient(app) as client:
        _login(client, client_email, "buyer-password")
        sent = client.post(f"/marketplace/conversations/{conversation_id}/messages",
                           data={"body": "Can we start Monday?"},
                           follow_redirects=False)
        assert sent.status_code == 303
        thread = client.get(f"/marketplace/conversations/{conversation_id}")
        assert thread.status_code == 200
        assert "Can we start Monday?" in thread.text
        invited = client.post(
            f"/marketplace/conversations/{conversation_id}/involve-admin",
            data={"reason": "Need a scope clarification"},
            follow_redirects=False)
        assert invited.status_code == 303

    with TestClient(app) as bidder:
        _login(bidder, bidder_one_email, "partner-one-password")
        thread = bidder.get(f"/marketplace/conversations/{conversation_id}")
        assert "Can we start Monday?" in thread.text

    with TestClient(app) as admin:
        _login(admin, "admin@elipsis.local", "elipsis")
        assert admin.get(f"/marketplace/conversations/{conversation_id}").status_code == 200

    with TestClient(app) as client:
        _login(client, client_email, "buyer-password")
        switched = client.post(f"/marketplace/{request_id}/switch",
                               data={"bid_id": bid_ids[1]}, follow_redirects=False)
        assert switched.status_code == 303, switched.text
        assert "/marketplace/conversations/" in switched.headers["location"]
        with SessionLocal() as db:
            req = db.get(models.PhysicalAssessmentRequest, request_id)
            assert req.awarded_bid_id == bid_ids[1]
            assert req.switches_used == 1
            old = db.get(models.BidSubmission, bid_ids[0])
            assert old.status == "not_selected"
            old_conv = db.get(models.MarketplaceConversation, conversation_id)
            assert old_conv.status == "closed"
            req.switches_granted = req.switches_used
            db.commit()

        topup = client.post(f"/marketplace/{request_id}/topup", follow_redirects=False)
        assert topup.status_code == 303
        assert "/pay/dummy/SWT_" in topup.headers["location"]
        topup_ref = topup.headers["location"].rsplit("/", 1)[-1]
        assert client.get(f"/pay/return/{topup_ref}", follow_redirects=False).status_code == 303
        with SessionLocal() as db:
            req = db.get(models.PhysicalAssessmentRequest, request_id)
            assert req.switches_granted == req.switches_used + 3

        monkeypatch.setenv("ELIPSIS_HANDOFF_SECRET", "test-handoff-signing-secret")
        monkeypatch.setenv("ELIPSIS_HANDOFF_FETCH_SECRET", "test-handoff-fetch-secret")
        handoff = client.post(f"/marketplace/{request_id}/handoff", follow_redirects=False)
        assert handoff.status_code == 303
        token = parse_qs(urlparse(handoff.headers["location"]).query)["handoff"][0]
        fetched = client.get(
            f"/api/v1/marketplace/handoffs/{token}",
            headers={"x-elipsis-handoff-secret": "test-handoff-fetch-secret"})
        assert fetched.status_code == 200, fetched.text
        payload = fetched.json()
        assert payload["reference"].startswith("ELP-")
        assert payload["company_name"]
        assert "raw_answers" not in payload
        assert "assessment_id" not in payload
        assert client.get(
            f"/api/v1/marketplace/handoffs/{token}",
            headers={"x-elipsis-handoff-secret": "test-handoff-fetch-secret"}
        ).status_code == 410

        directory = client.get("/marketplace/companies")
        assert directory.status_code == 200
        assert "Great Turbinez" in directory.text
        profile = client.get("/marketplace/companies/great-turbinez")
        assert profile.status_code == 200
        assert "Trusted implementation partner" in profile.text

        notes = client.get("/notifications")
        assert notes.status_code == 200
        assert "Your implementation partner is confirmed" in notes.text

    with TestClient(app) as admin_view:
        _login(admin_view, "admin@elipsis.local", "elipsis")
        assert admin_view.get("/admin/conversations").status_code == 200
        handoffs_page = admin_view.get("/admin/handoffs")
        assert handoffs_page.status_code == 200
        assert "Partner handoffs" in handoffs_page.text


def test_bidder_partner_console_and_subscription_checkout(marketplace_on):
    email = _email("partner")
    user_id = _make_user(email, "partner-password", user_type="bidder")
    with SessionLocal() as db:
        bidder = models.BidderCompany(
            user_id=user_id, company_name="Inactive Verified Partner",
            contact_email=email, verification_status="approved",
            subscription_status="inactive", partner_tier="standard")
        db.add(bidder)
        db.commit()
        bidder_id = bidder.id
    with TestClient(app) as client:
        _login(client, email, "partner-password")
        page = client.get("/marketplace/partner")
        assert page.status_code == 200, page.text
        checkout = client.post(
            "/marketplace/partner/subscribe", data={"tier": "monthly"},
            follow_redirects=False)
        assert checkout.status_code == 303, checkout.text
        location = checkout.headers["location"]
        assert "/pay/dummy/BID_" in location
        reference = location.rsplit("/", 1)[-1]
        paid = client.get(f"/pay/return/{reference}?simulate=success",
                          follow_redirects=False)
        assert paid.status_code == 303
        assert paid.headers["location"].startswith("/marketplace/partner")
        with SessionLocal() as db:
            bidder = db.get(models.BidderCompany, bidder_id)
            assert bidder.subscription_status == "active"
            assert bidder.subscription_tier == "monthly"
            payment = db.scalar(select(models.Payment).where(
                models.Payment.reference == reference))
            assert payment.status == "success"
            assert payment.purpose == "bidder_plan"


def test_paystack_recurring_plan_webhooks(monkeypatch):
    from elipsis_api.routers import studio

    monkeypatch.setenv("PAYSTACK_PLAN_PREMIUM_MONTHLY", "PLN_PREM_MONTHLY")
    monkeypatch.setenv("PAYSTACK_PLAN_BIDDER_MONTHLY", "PLN_BIDDER_MONTHLY")
    monkeypatch.setattr(studio.paystack, "verify_webhook", lambda raw, sig: True)

    email = _email("renewing")
    user_id = _make_user(email, "renewing-password")
    bidder_email = _email("renewing-partner")
    bidder_user_id = _make_bidder(bidder_email, "partner-password")
    with SessionLocal() as db:
        bidder = db.scalar(select(models.BidderCompany).where(
            models.BidderCompany.user_id == bidder_user_id))
        before_expiry = bidder.subscription_expires_at
        bidder_id = bidder.id

    with TestClient(app) as client:
        renewal = client.post("/paystack/webhook", json={
            "event": "charge.success",
            "data": {
                "reference": "RENEW_PREM_1", "amount": 2900, "currency": "USD",
                "plan": {"plan_code": "PLN_PREM_MONTHLY"},
                "customer": {"email": email}}})
        assert renewal.status_code == 200, renewal.text
        assert renewal.json()["status"] == "ok"

        created = client.post("/paystack/webhook", json={
            "event": "subscription.create",
            "data": {
                "subscription_code": "SUB_PREM_1", "email_token": "tok",
                "next_payment_date": "2026-12-01T00:00:00.000Z",
                "plan": {"plan_code": "PLN_PREM_MONTHLY"},
                "customer": {"email": email}}})
        assert created.status_code == 200, created.text

        bidder_renewal = client.post("/paystack/webhook", json={
            "event": "charge.success",
            "data": {
                "reference": "RENEW_BIDDER_1", "amount": 3900, "currency": "USD",
                "plan": {"plan_code": "PLN_BIDDER_MONTHLY"},
                "customer": {"email": bidder_email}}})
        assert bidder_renewal.status_code == 200, bidder_renewal.text

        disabled = client.post("/paystack/webhook", json={
            "event": "subscription.disable",
            "data": {"subscription_code": "SUB_PREM_1",
                     "status": "cancelled",
                     "customer": {"email": email}}})
        assert disabled.status_code == 200, disabled.text

    with SessionLocal() as db:
        pref = db.get(models.UserPref, user_id)
        assert pref.pro_until and pref.pro_until != "active"
        charge = db.scalar(select(models.Payment).where(
            models.Payment.reference == "RENEW_PREM_1"))
        assert charge is not None and charge.status == "success"
        subscription = db.scalar(select(models.BillingSubscription).where(
            models.BillingSubscription.provider_subscription_code == "SUB_PREM_1"))
        assert subscription is not None and subscription.status == "cancelled"
        bidder = db.get(models.BidderCompany, bidder_id)
        assert bidder.subscription_expires_at > before_expiry
        bidder_charge = db.scalar(select(models.Payment).where(
            models.Payment.reference == "RENEW_BIDDER_1"))
        assert bidder_charge is not None and bidder_charge.related_id == bidder_id
