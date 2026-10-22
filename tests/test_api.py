"""End-to-end API: create -> answer every segment live -> submit -> report.

Runs against a throwaway SQLite file so it never touches the dev database.
"""
import os
import tempfile

import pytest

_TMP = tempfile.mkdtemp(prefix="elipsis-test-")
os.environ["ELIPSIS_DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ.setdefault("ELIPSIS_HOST", "127.0.0.1")

import constants as C  # noqa: E402
import elipsis_questions as EQ  # noqa: E402


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from elipsis_api.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def signed_in(client):
    r = client.post("/login", data={"email": "admin@elipsis.local", "password": "elipsis"},
                    follow_redirects=False)
    assert r.status_code == 303, "demo sign-in failed"
    return client


def test_health(client):
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok"
    assert body["brand"] == C.BRAND_NAME
    assert body["index"] == C.INDEX_NAME


def test_questionnaire_exposes_per_question_options(client):
    questions = client.get("/api/v1/questionnaire").json()
    assert len(questions) == 63
    for q in questions:
        assert q["scale"] in C.SCALES, f"{q['code']} has no valid scale"
        assert len(q["options"]) == 6, f"{q['code']} did not ship its options"
        assert q["options"][0]["score"] == 0
        assert q["options"][-1]["score"] == 5


def test_dashboard_requires_sign_in(client):
    assert client.get("/dashboard", follow_redirects=False).status_code == 303


def test_full_assessment_round_trip(signed_in):
    client = signed_in
    created = client.post("/api/v1/assessments", json={
        "organization": {"name": "Test Co", "industry": "Logistics",
                         "employee_count": 80, "country": "Kenya"},
        "department": "Operations", "respondent": "Tester"})
    assert created.status_code == 201
    assessment_id = created.json()["id"]

    questions = client.get("/api/v1/questionnaire").json()
    by_subdomain = {}
    for q in questions:
        by_subdomain.setdefault(q["subdomain"], []).append(q)

    segments = [s["subdomain"] for s in EQ.segments()]
    assert set(segments) == set(by_subdomain)

    # Answer one segment at a time, exactly as the browser does.
    for index, subdomain in enumerate(segments):
        payload = {
            "segment": subdomain,
            "answers": [{"question_id": q["id"], "score": (index % 5) + 1,
                         "evidence": "document"} for q in by_subdomain[subdomain]],
        }
        live = client.post(f"/assessment/{assessment_id}/live", json=payload)
        assert live.status_code == 200
        body = live.json()
        assert body["total"] == 63
        assert len(body["metrics"]) == 36

    submitted = client.post(f"/api/v1/assessments/{assessment_id}/submit", json={
        "answers": [{"question_id": q["id"], "score": 3, "evidence": "document"}
                    for q in questions]})
    assert submitted.status_code == 200
    result = submitted.json()

    assert 0 <= result["readiness_index"] <= 100
    assert len(result["metrics"]) == 36
    assert len(result["metric_rows"]) == 36
    assert len(result["pillars"]) == 7
    assert len(result["subdomains"]) == 21
    assert result["answered"] == 63
    assert result["total"] == 63
    assert len(result["roadmap"]) == 3
    assert sum(p["count"] for p in result["roadmap"]) == len(result["recommendations"])
    assert result["confidence_band"]
    assert result["maturity_band"] != "Unknown"

    # The HTML surfaces render with the new payload.
    assert client.get(f"/assessment/{assessment_id}/results").status_code == 200
    assert client.get(f"/assessment/{assessment_id}/report").status_code == 200
    assert client.get("/dashboard").status_code == 200
    assessments_page = client.get("/assessments")
    assert assessments_page.status_code == 200
    assert "Know which operating unit is holding" in assessments_page.text
    assert "Lane signal" in assessments_page.text


def test_step_pages_render_every_segment(signed_in):
    client = signed_in
    created = client.post("/api/v1/assessments", json={
        "organization": {"name": "Steps Co"}, "department": "Operations"})
    assessment_id = created.json()["id"]
    for number in (1, 5, 11, 21):
        page = client.get(f"/assessment/{assessment_id}/step/{number}")
        assert page.status_code == 200
        assert "Why this matters" in page.text
    # Out-of-range steps clamp instead of erroring.
    assert client.get(f"/assessment/{assessment_id}/step/999").status_code == 200


def test_login_page_is_logistics_specific():
    from fastapi.testclient import TestClient

    from elipsis_api.main import app
    with TestClient(app) as fresh:
        page = fresh.get("/login")
    assert page.status_code == 200
    assert "Every delayed load has a cost. See it." in page.text
    assert "FOR LOGISTICS OPERATORS" in page.text
    assert "Origin port" in page.text and "Global operations" in page.text
    assert "Create a free operations account" in page.text


def test_pricing_is_global_and_utility_priced():
    from fastapi.testclient import TestClient

    from elipsis_api.main import app
    with TestClient(app) as fresh:
        page = fresh.get("/pricing")
    assert page.status_code == 200
    assert "$490" in page.text and "$1,500" in page.text
    assert "Why this pricing holds up" in page.text
    assert "List prices are in USD" in page.text
    assert "Kenya" not in page.text


def test_bad_login_is_rejected(client):
    r = client.post("/login", data={"email": "admin@elipsis.local", "password": "wrong"},
                    follow_redirects=False)
    assert r.status_code == 401


def test_value_workstreams_round_trip(signed_in):
    client = signed_in
    created = client.post("/api/v1/assessments", json={
        "organization": {"name": "Value Logistics", "industry": "Logistics",
                         "employee_count": 40, "country": "Kenya"},
        "department": "Operations", "respondent": "Value Tester"})
    assert created.status_code == 201
    assessment_id = created.json()["id"]
    questions = client.get("/api/v1/questionnaire").json()
    submitted = client.post(f"/api/v1/assessments/{assessment_id}/submit", json={
        "answers": [{"question_id": q["id"], "score": 3, "evidence": "document"}
                    for q in questions]})
    assert submitted.status_code == 200

    for path in ("assumptions", "evidence", "plan", "summary", "report"):
        assert client.get(f"/assessment/{assessment_id}/{path}").status_code == 200
    assert client.get(f"/assessment/{assessment_id}/export.xlsx").status_code == 200

    saved = client.post(f"/assessment/{assessment_id}/assumptions", data={
        "staff": 40, "hourly_rate": 600, "working_hours_per_month": 173.33,
        "max_savings_share": 12, "annual_revenue": "50000000",
        "note": "Validated with finance"}, follow_redirects=False)
    assert saved.status_code == 303

    uploaded = client.post(
        f"/assessment/{assessment_id}/evidence/{questions[0]['id']}",
        files={"file": ("proof.pdf", b"%PDF-1.4 test", "application/pdf")},
        follow_redirects=False)
    assert uploaded.status_code == 303

    shared = client.post(f"/assessment/{assessment_id}/share?days=7",
                         follow_redirects=False)
    assert shared.status_code == 303
    token = shared.headers["location"].split("shared=")[-1]
    assert client.get(f"/share/{token}").status_code == 200

    for path in ("/privacy", "/terms", "/security", "/partners", "/case-study"):
        assert client.get(path).status_code == 200


def test_workspace_intelligence_round_trip(signed_in):
    import re

    client = signed_in
    created = client.post("/api/v1/assessments", json={
        "organization": {"name": "Workspace Logistics", "industry": "Logistics",
                         "employee_count": 65, "country": "Kenya"},
        "department": "Operations", "respondent": "Workspace Tester"})
    assert created.status_code == 201
    assessment_id = created.json()["id"]
    org_id = created.json()["organization_id"]
    questions = client.get("/api/v1/questionnaire").json()
    submitted = client.post(f"/api/v1/assessments/{assessment_id}/submit", json={
        "answers": [{"question_id": q["id"], "score": 2, "evidence": "document"}
                    for q in questions]})
    assert submitted.status_code == 200

    assert client.get("/actions").status_code == 200
    assert client.get("/trends").status_code == 200
    assert client.get("/audit").status_code == 200
    assert client.get(f"/company/{org_id}/team").status_code == 200

    from fastapi.testclient import TestClient

    from elipsis_api.main import app
    with TestClient(app) as teammate:
        registered = teammate.post("/api/v1/auth/register", json={
            "email": "teammate@example.com", "password": "StrongPass123!",
            "name": "Team Mate"})
        assert registered.status_code in (200, 201)
    added = client.post(f"/company/{org_id}/team", data={
        "email": "teammate@example.com"}, follow_redirects=False)
    assert added.status_code == 303
    assert "teammate@example.com" in client.get(f"/company/{org_id}/team").text
    teammate_id = registered.json().get("user", {}).get("id") or registered.json().get("id")
    if teammate_id:
        removed = client.post(f"/company/{org_id}/team/{teammate_id}/remove",
                              follow_redirects=False)
        assert removed.status_code == 303

    scenario = client.post(f"/assessment/{assessment_id}/scenario", json={
        "staff": 80, "hourly_rate": 650, "working_hours_per_month": 170,
        "max_savings_share": 15, "annual_revenue": "60000000"})
    assert scenario.status_code == 200
    assert scenario.json()["financial"]["annual_savings"] > 0

    review = client.post(f"/assessment/{assessment_id}/review", data={
        "review_due_at": "2026-12-01", "review_note": "Dispatch cycle time"},
        follow_redirects=False)
    assert review.status_code == 303
    results = client.get(f"/assessment/{assessment_id}/results")
    assert "2026-12-01" in results.text

    plan = client.get(f"/assessment/{assessment_id}/plan").text
    item_ids = [int(x) for x in re.findall(rf"/assessment/{assessment_id}/plan/(\d+)", plan)]
    assert item_ids
    updated = client.post(f"/actions/{item_ids[0]}", data={
        "owner": "Ops lead", "due_date": "2026-11-15",
        "status": "in_progress", "notes": "Kickoff booked", "next": "/actions"},
        follow_redirects=False)
    assert updated.status_code == 303

    shared = client.post(f"/assessment/{assessment_id}/share?days=7&label=Board",
                         follow_redirects=False)
    assert shared.status_code == 303
    token = shared.headers["location"].split("shared=")[-1]
    assert client.get(f"/share/{token}").status_code == 200
    assert client.get(f"/share/{token}").status_code == 200
    results = client.get(f"/assessment/{assessment_id}/results")
    assert "Board" in results.text
    revoked = client.post(f"/assessment/{assessment_id}/shares/{token}/revoke",
                          follow_redirects=False)
    assert revoked.status_code == 303
    assert client.get(f"/share/{token}").status_code == 404

    audit = client.get("/audit")
    assert audit.status_code == 200
    assert "plan.update" in audit.text
    assert "share.create" in audit.text


def test_workspace_search_and_brand_surface(signed_in):
    client = signed_in
    page = client.get("/search?q=Workspace")
    assert page.status_code == 200
    assert "Workspace Logistics" in page.text
    assert "90-day actions" in page.text

    short = client.get("/search?q=a")
    assert short.status_code == 200
    assert "at least two characters" in short.text

    missing = client.get("/search?q=zzzz-no-such-record")
    assert missing.status_code == 200
    assert "No matches" in missing.text

    landing = client.get("/")
    assert landing.status_code == 200
    assert 'property="og:image"' in landing.text
    assert "/static/brand/elipsis-logo" in landing.text
    assert "/static/premium.css" in landing.text
    assert "/static/app.js" in landing.text

    robots = client.get("/robots.txt")
    assert robots.status_code == 200
    assert "Sitemap:" in robots.text
    assert "Disallow: /dashboard" in robots.text
    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200
    assert "<urlset" in sitemap.text
    assert "/methodology" in sitemap.text

    dashboard = client.get("/dashboard")
    assert 'id="cmdk"' in dashboard.text
    assert 'id="cmd-trigger"' in dashboard.text
    assert 'data-admin=' in dashboard.text


def test_growth_certification_imports_and_webhooks(signed_in):
    import re

    client = signed_in
    created = client.post("/api/v1/assessments", json={
        "organization": {"name": "Growth Logistics", "industry": "Logistics",
                         "employee_count": 55, "country": "Kenya"},
        "department": "Operations", "respondent": "Growth Tester"})
    assert created.status_code == 201
    assessment_id = created.json()["id"]
    org_id = created.json()["organization_id"]
    questions = client.get("/api/v1/questionnaire").json()
    submitted = client.post(f"/api/v1/assessments/{assessment_id}/submit", json={
        "answers": [{"question_id": q["id"], "score": 2, "evidence": "document"}
                    for q in questions]})
    assert submitted.status_code == 200

    narrative = client.get(f"/assessment/{assessment_id}/narrative")
    assert narrative.status_code == 200
    assert "Board narrative" in narrative.text or "What to do next" in narrative.text

    badge = client.get(f"/assessment/{assessment_id}/badge")
    assert badge.status_code == 200
    token = re.search(r"/verify/([^\"<]+)", badge.text).group(1).removesuffix(".svg")
    assert client.get(f"/verify/{token}").status_code == 200
    svg = client.get(f"/verify/{token}.svg")
    assert svg.status_code == 200
    assert "image/svg+xml" in svg.headers["content-type"]
    assert client.get("/verify/not-a-token").status_code == 404
    assert client.get("/benchmarks").status_code == 200

    notifications = client.get("/notifications")
    assert notifications.status_code == 200
    digest = client.post("/notifications/digest", data={"frequency": "daily"},
                         follow_redirects=False)
    assert digest.status_code == 303
    sent = client.post("/notifications/digest/send", follow_redirects=False)
    assert sent.status_code == 303

    saved = client.post("/views", data={"name": "Growth open", "query": "status=open"},
                        follow_redirects=False)
    assert saved.status_code == 303
    actions = client.get("/actions")
    assert "Growth open" in actions.text
    view_id = int(re.search(r'/views/(\d+)"', actions.text).group(1))
    assert client.get(f"/views/{view_id}", follow_redirects=False).status_code == 303

    plan = client.get(f"/assessment/{assessment_id}/plan").text
    item_ids = [int(x) for x in re.findall(rf"/assessment/{assessment_id}/plan/(\d+)", plan)]
    assert item_ids
    bulk = client.post("/actions/bulk", data={
        "item_ids": [str(item_ids[0])], "status": "in_progress",
        "owner": "Growth owner", "due_date": "2026-12-01"},
        follow_redirects=False)
    assert bulk.status_code == 303

    invite = client.get(f"/assessment/{assessment_id}/invite")
    assert invite.status_code == 200
    made_invite = client.post(f"/assessment/{assessment_id}/invite", data={
        "days": "14", "min_respondents": "2", "phone": "0712 345 678"},
        follow_redirects=False)
    assert made_invite.status_code == 303
    token = made_invite.headers["location"].split("token=")[1].split("&")[0]
    invite = client.get(f"/assessment/{assessment_id}/invite?token={token}&phone=0712345678")
    assert invite.status_code == 200
    assert "wa.me" in invite.text

    nudge = client.get(f"/actions/{item_ids[0]}/nudge")
    assert nudge.status_code == 200
    saved_phone = client.post(f"/actions/{item_ids[0]}/nudge", data={
        "phone": "0712 345 678"}, follow_redirects=False)
    assert saved_phone.status_code == 303
    assert "254712345678" in saved_phone.headers["location"]

    partner = client.get("/partner")
    assert partner.status_code == 200
    branded = client.post("/partner/brand", data={
        "name": "Growth Partner", "footer": "Prepared for the board",
        "accent": "#123456"}, follow_redirects=False)
    assert branded.status_code == 303
    assert "Growth Partner" in client.get("/partner").text

    template = client.get(f"/assessment/{assessment_id}/import/template.csv")
    assert template.status_code == 200
    csv_body = "code,score,evidence\n" + "\n".join(
        f"{q['code']},4,none" for q in questions[:5])
    imported = client.post(
        f"/assessment/{assessment_id}/import",
        files={"file": ("answers.csv", csv_body, "text/csv")},
        follow_redirects=False)
    assert imported.status_code == 303
    assert "import=5" in imported.headers["location"]

    denied = client.post("/settings/webhooks", data={
        "organization_id": org_id, "url": "http://127.0.0.1/hook",
        "events": ["action.updated"]}, follow_redirects=False)
    assert denied.status_code == 303
    assert "webhook=invalid" in denied.headers["location"]
    made = client.post("/settings/webhooks", data={
        "organization_id": org_id, "url": "https://93.184.216.34/hook",
        "events": ["action.updated", "assessment.completed"]},
        follow_redirects=False)
    assert made.status_code == 303
    assert "webhook=saved" in made.headers["location"]
    settings = client.get("/settings")
    assert settings.status_code == 200
    assert "93.184.216.34" in settings.text
    hook_id = int(re.search(r"/settings/webhooks/(\d+)/test", settings.text).group(1))
    deleted = client.post(f"/settings/webhooks/{hook_id}/delete",
                          follow_redirects=False)
    assert deleted.status_code == 303


def test_security_and_cache_headers(signed_in):
    page = signed_in.get("/dashboard")
    assert page.headers["X-Content-Type-Options"] == "nosniff"
    assert page.headers["X-Frame-Options"] == "DENY"
    assert page.headers["Cache-Control"] == "no-store"
    assert "base-uri" in page.headers["Content-Security-Policy"]
    assert page.headers["Cross-Origin-Opener-Policy"] == "same-origin"

    asset = signed_in.get("/static/app.js")
    assert asset.status_code == 200
    assert "max-age=86400" in asset.headers["Cache-Control"]


def test_guided_demo_generates_a_readable_result(signed_in):
    client = signed_in
    created = client.post("/demo", follow_redirects=False)
    assert created.status_code == 303
    location = created.headers["location"]
    assert location.startswith("/assessment/") and location.endswith("/results")
    page = client.get(location)
    assert page.status_code == 200
    assert "Guided Demo Co" in page.text
    assert "Logistics reading" in page.text


def test_setup_persists_logistics_organisation_fields():
    import uuid

    from fastapi.testclient import TestClient

    from elipsis_api.main import app
    client = TestClient(app)
    with client:
        signup = client.post("/signup", data={
            "name": "Setup Tester",
            "email": f"setup-{uuid.uuid4().hex}@example.com",
            "password": "testpass123",
            "password2": "testpass123",
            "user_type": "client",
            "accept_terms": "1",
        }, follow_redirects=False)
        assert signup.status_code == 303
        saved = client.post("/setup", data={
            "name": "Mombasa Line Haul",
            "industry": "Logistics",
            "sub_industry": "Freight forwarding",
            "employee_count": "140",
            "revenue_band": "USD 1M–10M",
            "country": "Kenya",
            "city": "Mombasa",
            "default_department": "Operations",
            "contact_name": "Ops lead",
            "primary_services": "Cross-border line haul",
        }, follow_redirects=False)
        assert saved.status_code == 303
        assert saved.headers["location"].startswith("/start?org=")
        org_id = int(saved.headers["location"].split("org=")[1])

        from elipsis_api import models
        from elipsis_api.database import SessionLocal
        with SessionLocal() as db:
            org = db.get(models.Organization, org_id)
            assert org is not None
            assert org.name == "Mombasa Line Haul"
            assert org.industry == "Logistics"
            assert org.sub_industry == "Freight forwarding"
            assert org.employee_count == 140
            assert org.revenue_band == "USD 1M–10M"
            assert org.city == "Mombasa"
            assert org.country == "Kenya"
            assert org.contact_name == "Ops lead"
            assert org.primary_services == "Cross-border line haul"

        dashboard = client.get(f"/dashboard?org={org_id}")
        assert dashboard.status_code == 200
        assert "Mombasa Line Haul at a glance" in dashboard.text
        assert "Freight forwarding" in dashboard.text
        assert "Mid-sized operator" in dashboard.text
        assert "USD 1M–10M" in dashboard.text

        diagnostics = client.get(f"/assessments?org={org_id}")
        assert diagnostics.status_code == 200
        assert "holding Mombasa Line Haul back" in diagnostics.text

        start_page = client.get(f"/start?org={org_id}")
        assert start_page.status_code == 200
        assert "Start Mombasa Line Haul's diagnostic" in start_page.text
        assert "Freight forwarding" in start_page.text
        assert "I will answer" in start_page.text

        started = client.post("/start", data={
            "organization_id": str(org_id),
            "department": "Operations",
            "respondent": "Ops lead",
            "method": "self",
        }, follow_redirects=False)
        assert started.status_code == 303
        assert started.headers["location"].startswith("/assessment/")

def test_start_requires_a_saved_company(signed_in):
    client = signed_in
    response = client.post("/start", data={
        "organization_id": "",
        "department": "Operations",
        "method": "self",
    }, follow_redirects=False)
    assert response.status_code in (303, 400)
    if response.status_code == 303:
        assert response.headers["location"].startswith("/setup")


def test_provider_signup_is_invitation_only():
    from fastapi.testclient import TestClient

    from elipsis_api.main import app
    with TestClient(app) as fresh:
        page = fresh.post("/signup", data={
            "name": "Provider Test",
            "email": "provider-test@example.com",
            "password": "testpass123",
            "password2": "testpass123",
            "user_type": "bidder",
            "accept_terms": "1",
        })
    assert page.status_code == 400
    assert "invitation-only" in page.text


def test_logout_then_login_returns_to_the_app():
    from fastapi.testclient import TestClient

    from elipsis_api.main import app
    with TestClient(app) as fresh:
        signed = fresh.post("/login", data={
            "email": "admin@elipsis.local",
            "password": "elipsis",
        }, follow_redirects=False)
        assert signed.status_code == 303
        fresh.get("/logout", follow_redirects=False)
        again = fresh.post("/login", data={
            "email": "admin@elipsis.local",
            "password": "elipsis",
        }, follow_redirects=False)
    assert again.status_code == 303
    assert again.headers["location"].startswith("/dashboard")

def test_compare_page_uses_the_selected_organisation(signed_in):
    client = signed_in
    created = client.post("/demo", follow_redirects=False)
    assessment_id = int(created.headers["location"].split("/")[2])

    from elipsis_api import models
    from elipsis_api.database import SessionLocal
    with SessionLocal() as db:
        assessment = db.get(models.Assessment, assessment_id)
        org_id = assessment.organization_id

    page = client.get(f"/compare/{org_id}")
    assert page.status_code == 200
    assert "Guided Demo Co" in page.text
    assert "Unit rankings" in page.text
    assert "Choose an organisation" not in page.text


def test_operations_ecosystem_round_trip(signed_in):
    import re

    client = signed_in
    created = client.post("/api/v1/assessments", json={
        "organization": {"name": "Operations Ecosystem", "industry": "Logistics",
                         "employee_count": 72, "country": "Kenya", "city": "Mombasa"},
        "department": "Operations", "respondent": "Ops Tester"})
    assert created.status_code == 201
    assessment_id = created.json()["id"]
    org_id = created.json()["organization_id"]
    questions = client.get("/api/v1/questionnaire").json()
    submitted = client.post(f"/api/v1/assessments/{assessment_id}/submit", json={
        "answers": [{"question_id": q["id"], "score": 3, "evidence": "document"}
                    for q in questions]})
    assert submitted.status_code == 200

    home = client.get(f"/operations?org={org_id}")
    assert home.status_code == 200
    assert "Connect the numbers behind the score" in home.text

    loaded = client.post("/operations/sample", data={"organization_id": org_id},
                         follow_redirects=False)
    assert loaded.status_code == 303
    home = client.get(f"/operations?org={org_id}")
    assert "On-time delivery" in home.text
    assert "Late port release" in home.text

    summary = client.get(f"/api/v1/operations?org_id={org_id}").json()
    assert summary["measured"] == 8
    assert summary["incidents"]["open"] >= 2
    assert summary["documents"]["expiring"] >= 1

    recorded = client.post("/operations/metrics", data={
        "organization_id": org_id, "metric_key": "on_time_delivery",
        "value": "96.4", "period_end": "2026-10-31",
        "note": "Weekly dispatch review"}, follow_redirects=False)
    assert recorded.status_code == 303
    metrics = client.get(f"/api/v1/operations/metrics?org_id={org_id}").json()["metrics"]
    on_time = next(item for item in metrics if item["metric_key"] == "on_time_delivery")
    assert on_time["value"] == 96.4
    assert on_time["status"] == "good"

    incident = client.post("/operations/incidents", data={
        "organization_id": org_id, "title": "Customer status calls",
        "lane": "customer", "severity": "high", "occurred_on": "2026-10-20",
        "shipment_ref": "NBO-9001", "customer_impact": "Three calls on one load",
        "root_cause": "No automatic status update", "owner": "Customer lead",
        "corrective_action": "Send a status message at each handoff"},
        follow_redirects=False)
    assert incident.status_code == 303
    queue = client.get(f"/operations/incidents?org={org_id}&status=open")
    assert "Customer status calls" in queue.text
    incident_id = int(re.search(r'/operations/incidents/(\d+)/promote', queue.text).group(1))
    promoted = client.post(f"/operations/incidents/{incident_id}/promote", data={
        "organization_id": org_id}, follow_redirects=False)
    assert promoted.status_code == 303
    assert "On action plan" in client.get(
        f"/operations/incidents?org={org_id}&status=open").text
    resolved = client.post(f"/operations/incidents/{incident_id}/resolve", data={
        "organization_id": org_id, "note": "Status update shipped"},
        follow_redirects=False)
    assert resolved.status_code == 303

    document = client.post("/operations/documents", data={
        "organization_id": org_id, "title": "Carrier contract", "doc_type": "contract",
        "reference": "CC-2026-9", "owner": "Commercial lead",
        "issued_on": "2026-01-01", "expires_on": "2026-11-01",
        "note": "Annual renewal"}, follow_redirects=False)
    assert document.status_code == 303
    docs = client.get(f"/operations/documents?org={org_id}")
    assert "Carrier contract" in docs.text
    doc_id = int(re.search(r'/operations/documents/(\d+)/renew', docs.text).group(1))
    renewed = client.post(f"/operations/documents/{doc_id}/renew", data={
        "organization_id": org_id, "expires_on": "2027-11-01"},
        follow_redirects=False)
    assert renewed.status_code == 303
    archived = client.post(f"/operations/documents/{doc_id}/archive", data={
        "organization_id": org_id}, follow_redirects=False)
    assert archived.status_code == 303

    csv_body = (b"metric_key,value,period_end,note\n"
                b"invoice_accuracy,99.2,2026-09-30,ERP close\n"
                b"not_a_metric,12,2026-09-30,skip me\n")
    imported = client.post("/operations/import", data={
        "organization_id": org_id, "kind": "metrics"},
        files={"file": ("metrics.csv", csv_body, "text/csv")},
        follow_redirects=False)
    assert imported.status_code == 303
    assert "/operations/imports/" in imported.headers["location"]
    report = client.get(imported.headers["location"])
    assert "1 of 2 rows imported" in report.text
    assert "unknown metric" in report.text

    export = client.get(f"/operations/metrics/export.csv?org={org_id}")
    assert export.status_code == 200
    assert "invoice_accuracy" in export.text

    token_page = client.post("/operations/tokens", data={
        "organization_id": org_id, "name": "WMS test", "scopes": "read,write"})
    assert token_page.status_code == 201
    raw_token = re.search(r"elps_[A-Za-z0-9_\-]+", token_page.text).group(0)
    auth = {"Authorization": f"Bearer {raw_token}"}
    api_summary = client.get("/api/v1/operations", headers=auth)
    assert api_summary.status_code == 200
    assert api_summary.json()["measured"] == 8
    api_write = client.post("/api/v1/operations/metrics", headers=auth, json={
        "metric_key": "fleet_utilization", "value": 82, "period_end": "2026-10-31"})
    assert api_write.status_code == 201
    assert api_write.json()["metric_key"] == "fleet_utilization"

    read_page = client.post("/operations/tokens", data={
        "organization_id": org_id, "name": "Read only", "scopes": "read"})
    read_token = re.search(r"elps_[A-Za-z0-9_\-]+", read_page.text).group(0)
    denied = client.post("/api/v1/operations/incidents", headers={
        "Authorization": f"Bearer {read_token}"}, json={"title": "Nope"})
    assert denied.status_code == 403

    dashboard = client.get("/dashboard")
    assert "Operating evidence" in dashboard.text
    activity = client.get(f"/operations?org={org_id}")
    assert "Workspace activity" in activity.text
    assert "Metric Recorded" in activity.text
    bundle = client.get(f"/operations/export.json?org={org_id}")
    assert bundle.status_code == 200
    assert bundle.json()["metrics"]


def test_department_questionnaires_are_focused(client):
    from elipsis_api import departments, services
    from elipsis_api.database import SessionLocal

    with SessionLocal() as db:
        finance = services.questionnaire_for_department(db, "Finance & commercial")
        dispatch = services.questionnaire_for_department(db, "Dispatch & fleet")
        assert finance is not None and dispatch is not None
        assert finance.id != dispatch.id
        finance_qs = services.get_questions(db, finance.id)
        dispatch_qs = services.get_questions(db, dispatch.id)
        assert len(finance_qs) == len(dispatch_qs) == 63
        finance_focus = set(departments.DEPARTMENT_BY_KEY["finance"]["focus"])
        dispatch_focus = set(departments.DEPARTMENT_BY_KEY["dispatch"]["focus"])
        assert {q.subdomain for q in finance_qs[:9]} == finance_focus
        assert {q.subdomain for q in dispatch_qs[:9]} == dispatch_focus
        assert finance_focus != dispatch_focus


def test_second_company_requires_premium(client):
    from fastapi.testclient import TestClient

    from elipsis_api import models, security
    from elipsis_api.database import SessionLocal
    from elipsis_api.main import app

    with SessionLocal() as db:
        db.add(models.User(
            email="premium-check@example.com", name="Non Pro",
            role="client", user_type="client",
            password_hash=security.hash_password("premium-pass")))
        db.commit()

    with TestClient(app) as fresh:
        signed = fresh.post("/login", data={
            "email": "premium-check@example.com", "password": "premium-pass"},
            follow_redirects=False)
        assert signed.status_code == 303
        first = fresh.post("/setup", data={
            "name": "First Company", "industry": "Logistics",
            "default_department": "Operations"}, follow_redirects=False)
        assert first.status_code == 303
        gate = fresh.get("/setup?new=1", follow_redirects=False)
        assert gate.status_code == 303
        assert gate.headers["location"] == "/pro?locked=companies"


def test_team_campaign_uses_department_questions_and_builds_master(signed_in):
    client = signed_in
    created = client.post("/api/v1/assessments", json={
        "organization": {"name": "Focused Campaign Co", "industry": "Logistics",
                         "employee_count": 45, "country": "Kenya"},
        "department": "Finance & commercial", "respondent": "Owner"})
    assert created.status_code == 201
    org_id = created.json()["organization_id"]

    shared = client.post(f"/company/{org_id}/share", data={
        "department": "Finance & commercial", "min_respondents": "1",
        "contact_mode": "required", "question_set": "Finance & commercial",
        "target_roles": "Finance Manager"}, follow_redirects=False)
    assert shared.status_code == 303
    token = shared.headers["location"].rstrip("/").split("/")[-1]

    landing = client.get(f"/q/{token}")
    assert landing.status_code == 200
    assert "Finance &amp; commercial" in landing.text

    started = client.post(f"/q/{token}/start", data={
        "name": "Finance Responder", "email": "finance@example.com"},
        follow_redirects=False)
    assert started.status_code == 303
    assessment_id = int(started.headers["location"].split("/a/")[1].split("/")[0])

    from elipsis_api import models, services
    from elipsis_api.database import SessionLocal
    with SessionLocal() as db:
        assessment = db.get(models.Assessment, assessment_id)
        questions = services.get_questions(db, assessment.questionnaire_id)
        assert len(questions) == 63
        assert {q.subdomain for q in questions[:9]} == {"MAN", "COL", "RPM"}
        qids = [q.id for q in questions]

    answer_data = {f"q{qid}": "4" for qid in qids}
    submitted = client.post(f"/q/{token}/a/{assessment_id}/submit",
                             data=answer_data, follow_redirects=False)
    assert submitted.status_code == 303

    with SessionLocal() as db:
        camp = db.get(models.CollectCampaign, token)
        assert camp.status == "reported"
        assert camp.master_assessment_id
        master = db.get(models.Assessment, camp.master_assessment_id)
        assert master.source == "team"
        master_qids = {q.id for q in services.get_questions(db, master.questionnaire_id)}
        assert len(master_qids) == len(qids)


def test_premium_checkout_and_dummy_return_grant_access():
    from fastapi.testclient import TestClient

    from elipsis_api import models, premium, security
    from elipsis_api.database import SessionLocal
    from elipsis_api.main import app

    with SessionLocal() as db:
        db.add(models.User(
            email="premium-buyer@example.com", name="Premium Buyer",
            role="client", user_type="client",
            password_hash=security.hash_password("premium-buyer-pass")))
        db.commit()

    with TestClient(app) as fresh:
        signed = fresh.post("/login", data={
            "email": "premium-buyer@example.com", "password": "premium-buyer-pass"},
            headers={"x-forwarded-for": "203.0.113.41"}, follow_redirects=False)
        assert signed.status_code == 303
        fresh.post("/setup", data={
            "name": "Buyer Co", "industry": "Logistics",
            "default_department": "Operations"}, follow_redirects=False)
        page = fresh.get("/pro")
        assert page.status_code == 200
        assert "$39" in page.text and "$390" in page.text
        checkout = fresh.post("/pro/checkout", data={"billing": "monthly"},
                              follow_redirects=False)
        assert checkout.status_code == 303
        location = checkout.headers["location"]
        assert "/pay/dummy/PRE_" in location
        reference = location.rsplit("/", 1)[-1]

        with SessionLocal() as db:
            payment = db.query(models.Payment).filter_by(reference=reference).one()
            assert payment.purpose == "premium"
            assert payment.currency == premium.CURRENCY
            assert payment.amount_minor == premium.amount_minor("monthly")
            assert payment.billing_cycle == "monthly"

        paid = fresh.get(f"/pay/return/{reference}", follow_redirects=False)
        assert paid.status_code == 303
        assert paid.headers["location"] == "/pro?upgraded=1"
        assert fresh.get("/setup?new=1", follow_redirects=False).status_code == 200


def test_paystack_webhook_requires_signature_and_grants_annual_access():
    import hashlib
    import hmac
    import json as jsonlib

    from fastapi.testclient import TestClient

    from elipsis_api import models, paystack, premium, security
    from elipsis_api.database import SessionLocal
    from elipsis_api.main import app

    with SessionLocal() as db:
        user = models.User(
            email="webhook-buyer@example.com", name="Webhook Buyer",
            role="client", user_type="client",
            password_hash=security.hash_password("webhook-buyer-pass"))
        db.add(user)
        db.commit()
        db.refresh(user)
        payment = models.Payment(
            user_id=user.id, reference="PRE_webhook_test", purpose="premium",
            amount_kes=0, currency=premium.CURRENCY,
            amount_minor=premium.amount_minor("annual"), billing_cycle="annual",
            status="pending")
        db.add(payment)
        db.commit()

    payload = jsonlib.dumps({
        "event": "charge.success",
        "data": {"reference": "PRE_webhook_test", "status": "success",
                 "amount": premium.amount_minor("annual"), "currency": premium.CURRENCY},
    }).encode()

    with TestClient(app) as fresh:
        assert fresh.post("/paystack/webhook", content=payload,
                          headers={"x-paystack-signature": "bad"}).status_code == 401
        signature = hmac.new(
            paystack.SECRET.encode(), payload, hashlib.sha512).hexdigest()
        ok = fresh.post("/paystack/webhook", content=payload,
                        headers={"x-paystack-signature": signature})
        assert ok.status_code == 200
        assert ok.json()["status"] == "ok"

    with SessionLocal() as db:
        user = db.query(models.User).filter_by(email="webhook-buyer@example.com").one()
        payment = db.query(models.Payment).filter_by(reference="PRE_webhook_test").one()
        prefs = db.get(models.UserPref, user.id)
        assert payment.status == "success"
        assert prefs is not None and prefs.pro_until not in (None, "", "active")


def test_free_user_is_gated_from_team_reports_and_sharing():
    from fastapi.testclient import TestClient

    from elipsis_api import models, security, services
    from elipsis_api.database import SessionLocal
    from elipsis_api.main import app

    with SessionLocal() as db:
        db.add(models.User(
            email="free-gates@example.com", name="Free Gates",
            role="client", user_type="client",
            password_hash=security.hash_password("free-gates-pass")))
        db.commit()

    with TestClient(app) as fresh:
        signed = fresh.post("/login", data={
            "email": "free-gates@example.com", "password": "free-gates-pass"},
            headers={"x-forwarded-for": "203.0.113.42"}, follow_redirects=False)
        assert signed.status_code == 303
        fresh.post("/setup", data={
            "name": "Free Gates Co", "industry": "Logistics",
            "default_department": "Operations"}, follow_redirects=False)
        with SessionLocal() as db:
            user = db.query(models.User).filter_by(email="free-gates@example.com").one()
            org_id = services.owned_orgs(db, user)[0].id
        created = fresh.post("/api/v1/assessments", json={
            "organization_id": org_id,
            "department": "Operations", "respondent": "Owner"})
        assert created.status_code == 201
        assessment_id = created.json()["id"]
        extra_company = fresh.post("/api/v1/organizations",
                                   json={"name": "Second Free Co"})
        assert extra_company.status_code == 402

        team = fresh.post("/start", data={
            "organization_id": str(org_id), "department": "Operations",
            "method": "team"}, follow_redirects=False)
        assert team.status_code == 303
        assert team.headers["location"] == "/pro?locked=team"

        campaign = fresh.post(f"/company/{org_id}/share", data={
            "department": "Operations"}, follow_redirects=False)
        assert campaign.status_code == 303
        assert campaign.headers["location"] == "/pro?locked=team"

        report = fresh.get(f"/assessment/{assessment_id}/report.pdf",
                           follow_redirects=False)
        assert report.status_code == 303
        assert report.headers["location"] == "/pro?locked=reports"

        export = fresh.get(f"/assessment/{assessment_id}/export.json",
                           follow_redirects=False)
        assert export.status_code == 303
        assert export.headers["location"] == "/pro?locked=reports"

        share = fresh.post(f"/assessment/{assessment_id}/share", data={"days": "30"},
                           follow_redirects=False)
        assert share.status_code == 303
        assert share.headers["location"] == "/pro?locked=reports"


def test_company_room_membership_collaboration_and_branding():
    from fastapi.testclient import TestClient

    from elipsis_api import models, security, services_room
    from elipsis_api.database import SessionLocal
    from elipsis_api.main import app

    with SessionLocal() as db:
        owner = models.User(
            email="room-owner@example.com", name="Room Owner", role="client",
            user_type="client", password_hash=security.hash_password("room-owner-pass"))
        db.add(owner)
        db.commit()
        org = models.Organization(name="Room Co", industry="Logistics")
        db.add(org)
        db.commit()
        db.add(models.OrgOwner(user_id=owner.id, organization_id=org.id,
                               role="owner", status="active"))
        db.add(models.UserPref(user_id=owner.id, pro_until="active"))
        db.commit()
        org_id = org.id

    with TestClient(app) as admin:
        login = admin.post("/login", data={
            "email": "room-owner@example.com", "password": "room-owner-pass"},
            headers={"x-forwarded-for": "203.0.113.77"}, follow_redirects=False)
        assert login.status_code == 303

        for path in (f"/company/{org_id}", f"/company/{org_id}/desk",
                     f"/company/{org_id}/discussion", f"/company/{org_id}/decisions",
                     f"/company/{org_id}/team", f"/company/{org_id}/brief"):
            page = admin.get(path)
            assert page.status_code == 200, (path, page.text[:300])
        ics = admin.get(f"/company/{org_id}/schedule.ics")
        assert ics.status_code == 200
        assert "BEGIN:VCALENDAR" in ics.text

        post = admin.post(f"/company/{org_id}/posts", data={
            "body": "Morning huddle: two vans down, reroute priority loads.",
            "tag": "risk"}, follow_redirects=False)
        assert post.status_code == 303
        with SessionLocal() as db:
            post_id = db.query(models.CompanyPost).filter_by(
                organization_id=org_id).one().id

        invite = admin.post(f"/company/{org_id}/invite", data={
            "email": "room-manager@example.com", "role": "manager",
            "title": "Dispatch lead", "department": "Operations",
            "note": "Own the morning huddle.", "days": "7", "max_uses": "1"},
            follow_redirects=False)
        assert invite.status_code == 303
        assert "Invite%20link%20ready" in invite.headers["location"]
        with SessionLocal() as db:
            created_invite = services_room.invites(db, org_id)[0]
            token = created_invite.token
        invite_page = admin.get(f"/company/{org_id}/invite?token={token}")
        assert invite_page.status_code == 200
        assert f"/invite/{token}" in invite_page.text

        with TestClient(app) as invited:
            page = invited.get(f"/invite/{token}")
            assert page.status_code == 200
            assert "Room Co" in page.text
            joined = invited.post(f"/invite/{token}", data={
                "name": "Room Manager", "email": "room-manager@example.com",
                "password": "room-manager-pass", "password2": "room-manager-pass",
                "accept_terms": "1"},
                headers={"x-forwarded-for": "203.0.113.78"}, follow_redirects=False)
            assert joined.status_code == 303
            assert joined.headers["location"] == f"/company/{org_id}?joined=1"
            assert invited.get(f"/company/{org_id}/desk").status_code == 200
            assert invited.get(f"/company/{org_id}/team").status_code == 200
            reply = invited.post(f"/company/{org_id}/posts/{post_id}/reply", data={
                "body": "Reroute confirmed; customer desk notified."},
                follow_redirects=False)
            assert reply.status_code == 303

        with SessionLocal() as db:
            membership = db.query(models.OrgOwner).filter_by(
                organization_id=org_id, user_id=db.query(models.User).filter_by(
                    email="room-manager@example.com").one().id).one()
            assert membership.role == "manager"
            assert membership.status == "active"

        decision = admin.post(f"/company/{org_id}/decisions", data={
            "title": "Move to a single dispatch board",
            "detail": "Remove the duplicate spreadsheet by month end.",
            "owner_name": "Room Manager", "due_date": "2026-12-01"},
            follow_redirects=False)
        assert decision.status_code == 303
        discussion = admin.get(f"/company/{org_id}/discussion")
        assert discussion.status_code == 200
        assert "Reroute confirmed" in discussion.text
        assert admin.get(f"/company/{org_id}/decisions").status_code == 200

        assessment = admin.post("/api/v1/assessments", json={
            "organization_id": org_id, "department": "Operations",
            "respondent": "Room Owner"})
        assert assessment.status_code == 201
        assessment_id = assessment.json()["id"]
        note = admin.post(f"/assessment/{assessment_id}/notes", data={
            "section": "Operations", "body": "Night shift is the constraint."},
            follow_redirects=False)
        assert note.status_code == 303
        results = admin.get(f"/assessment/{assessment_id}/results")
        assert results.status_code == 200
        assert "Night shift is the constraint." in results.text

        saved = admin.post(f"/company/{org_id}/settings", data={
            "accent_color": "#1f6f5c", "report_footer": "Board use only",
            "report_cover_note": "Prepared for the Q4 board review.",
            "week_start": "sunday", "huddle_day": "tuesday",
            "huddle_time": "09:15", "next": "/settings"}, follow_redirects=False)
        assert saved.status_code == 303
        assert saved.headers["location"] == "/settings?company=saved"
        with SessionLocal() as db:
            refreshed = db.get(models.Organization, org_id)
            assert refreshed.accent_color == "#1f6f5c"
            assert refreshed.report_footer == "Board use only"
            assert refreshed.huddle_day == "tuesday"
        prefs_page = admin.get("/settings")
        assert prefs_page.status_code == 200
        assert "Company identity" in prefs_page.text
        assert "room-owner-pass" not in prefs_page.text
        report = admin.get(f"/assessment/{assessment_id}/report")
        assert report.status_code == 200
        assert "Prepared for the Q4 board review." in report.text
        assert "Board use only" in report.text
        pdf = admin.get(f"/assessment/{assessment_id}/report.pdf")
        assert pdf.status_code == 200
        assert pdf.content[:4] == b"%PDF"


def test_service_public_surface_and_trust_headers(client):
    for path in ("/status", "/trust", "/dpa", "/subprocessors", "/accessibility",
                 "/service-standards", "/changelog", "/help",
                 "/help/start-first-assessment", "/.well-known/security.txt"):
        page = client.get(path)
        assert page.status_code == 200, (path, page.text[:200])
    status = client.get("/status")
    assert status.headers["x-request-id"]
    assert "Server-Timing" in status.headers
    assert "report-uri" not in status.text or "Content-Security-Policy" not in status.text
    security = client.get("/.well-known/security.txt")
    assert "security@elipsis.co.ke" in security.text
    sitemap = client.get("/sitemap.xml")
    assert "/trust" in sitemap.text and "/status" in sitemap.text


def test_signup_requires_and_records_terms_acceptance():
    import uuid

    from fastapi.testclient import TestClient

    from elipsis_api import models, services_success
    from elipsis_api.database import SessionLocal
    from elipsis_api.main import app

    email = f"terms-{uuid.uuid4().hex}@example.com"
    payload = {
        "name": "Terms Tester", "email": email,
        "password": "terms-test-pass", "password2": "terms-test-pass",
        "user_type": "client",
    }
    with TestClient(app) as fresh:
        rejected = fresh.post("/signup", data=payload,
                              headers={"x-forwarded-for": "198.51.100.201"})
        assert rejected.status_code == 400
        assert "agree" in rejected.text.lower() or "terms" in rejected.text.lower()

        accepted = fresh.post("/signup", data={**payload, "accept_terms": "1"},
                              headers={"x-forwarded-for": "198.51.100.202"},
                              follow_redirects=False)
        assert accepted.status_code == 303

    with SessionLocal() as db:
        user = db.query(models.User).filter_by(email=email).one()
        rows = db.query(models.LegalAcceptance).filter_by(
            user_id=user.id, document="terms").all()
        assert rows and rows[0].version == services_success.LEGAL_VERSION


def test_support_ticket_lifecycle_and_sla(signed_in):
    import uuid

    from elipsis_api import models, services_success
    from elipsis_api.database import SessionLocal

    client = signed_in
    subject = f"Status page publish gap {uuid.uuid4().hex[:8]}"
    created = client.post("/support", data={
        "subject": subject,
        "body": "The incident resolution did not appear on the public status page. "
                "Please check the publish step and confirm the gap.",
        "category": "bug", "priority": "high",
    }, headers={"x-forwarded-for": "198.51.100.210"}, follow_redirects=False)
    assert created.status_code == 303
    reference = created.headers["location"].split("/support/")[1].split("?")[0]

    page = client.get(f"/support/{reference}")
    assert page.status_code == 200
    assert subject in page.text
    assert "First response target" in page.text

    reply = client.post(f"/support/{reference}/reply", data={
        "body": "Adding one more detail: the publish timestamp was stale."},
        follow_redirects=False)
    assert reply.status_code == 303

    with SessionLocal() as db:
        ticket = db.query(models.SupportTicket).filter_by(reference=reference).one()
        ticket_id = ticket.id
        assert ticket.first_response_due and ticket.resolution_due
        assert ticket.status == "open"

    updated = client.post(f"/admin/service/tickets/{ticket_id}", data={
        "body": "Confirmed the publish race and shipped the fix.",
        "status": "resolved", "priority": "high"}, follow_redirects=False)
    assert updated.status_code == 303
    rated = client.post(f"/support/{reference}/csat", data={
        "score": "5", "comment": "Clear and fast."}, follow_redirects=False)
    assert rated.status_code == 303

    with SessionLocal() as db:
        ticket = db.query(models.SupportTicket).filter_by(reference=reference).one()
        assert ticket.status == "resolved"
        assert ticket.first_response_at
        assert ticket.csat_score == 5
        assert len(services_success.messages_for(db, ticket.id)) >= 2


def test_incident_status_page_and_subscribers(signed_in):
    import uuid

    from elipsis_api import models
    from elipsis_api.database import SessionLocal

    client = signed_in
    address = f"status-{uuid.uuid4().hex}@example.com"
    subscribed = client.post("/status/subscribe", data={"email": address},
                             headers={"x-forwarded-for": "198.51.100.220"},
                             follow_redirects=False)
    assert subscribed.status_code == 303

    title = f"Elevated report latency {uuid.uuid4().hex[:6]}"
    created = client.post("/admin/service/incidents", data={
        "title": title, "summary": "Reports are loading slower than normal.",
        "impact": "minor", "components": "web,reports"}, follow_redirects=False)
    assert created.status_code == 303
    with SessionLocal() as db:
        incident = db.query(models.ServiceIncident).filter_by(title=title).one()
        incident_id = incident.id
        subscriber = db.query(models.StatusSubscriber).filter_by(email=address).one()
        assert subscriber.active == 1

    updated = client.post(f"/admin/service/incidents/{incident_id}/update", data={
        "status": "resolved", "body": "Latency back to normal after a cache flush.",
        "postmortem": "Cache stampede after a deploy; added a jittered TTL and alert."},
        follow_redirects=False)
    assert updated.status_code == 303

    page = client.get("/status")
    assert page.status_code == 200
    assert title in page.text
    assert "Resolved" in page.text
    assert "jittered TTL" in page.text


def test_feedback_data_export_and_erasure_request(signed_in):
    from elipsis_api import models
    from elipsis_api.database import SessionLocal

    client = signed_in
    feedback = client.post("/feedback", data={
        "kind": "nps", "score": "9", "comment": "Useful weekly rhythm.",
        "context": "service"}, follow_redirects=False)
    assert feedback.status_code == 303

    exported = client.post("/account/data/export")
    assert exported.status_code == 200
    assert "attachment" in exported.headers["content-disposition"]
    payload = exported.json()
    assert payload["account"]["email"] == "admin@elipsis.local"
    assert payload["feedback"]

    requested = client.post("/account/data/request", data={
        "kind": "correction", "note": "Correct the display name."},
        follow_redirects=False)
    assert requested.status_code == 303
    assert "ELP-DR-" in requested.headers["location"]

    with SessionLocal() as db:
        row = db.query(models.DataRequest).filter_by(
            kind="correction").order_by(models.DataRequest.id.desc()).first()
        assert row.status == "received"
        request_id = row.id
        feedback_row = db.query(models.Feedback).filter_by(
            user_id=db.query(models.User).filter_by(
                email="admin@elipsis.local").one().id).order_by(
            models.Feedback.id.desc()).first()
        assert feedback_row.score == 9

    completed = client.post(f"/admin/service/data-requests/{request_id}/complete", data={
        "note": "Display name corrected."}, follow_redirects=False)
    assert completed.status_code == 303
    with SessionLocal() as db:
        assert db.get(models.DataRequest, request_id).status == "completed"


def test_settings_timezone_and_activation_page(signed_in):
    from elipsis_api import models
    from elipsis_api.database import SessionLocal

    client = signed_in
    saved = client.post("/settings", data={"timezone": "Africa/Nairobi"},
                        follow_redirects=False)
    assert saved.status_code == 303
    with SessionLocal() as db:
        user = db.query(models.User).filter_by(email="admin@elipsis.local").one()
        assert db.get(models.UserPref, user.id).timezone == "Africa/Nairobi"

    page = client.get("/getting-started", follow_redirects=False)
    assert page.status_code in (200, 303)
    if page.status_code == 200:
        assert "activation" in page.text.lower() or "first assessment" in page.text.lower()
    assert client.get("/support").status_code == 200
    assert client.get("/feedback").status_code == 200
    assert client.get("/account/data").status_code == 200
    assert client.get("/admin/service").status_code == 200


def test_activation_health_and_ticket_org_link():
    import uuid

    from fastapi.testclient import TestClient

    from elipsis_api import models, security, services_success
    from elipsis_api.database import SessionLocal
    from elipsis_api.main import app

    email = f"journey-{uuid.uuid4().hex}@example.com"
    with SessionLocal() as db:
        user = models.User(email=email, name="Journey Owner", role="client",
                           user_type="client", password_hash=security.hash_password("journey-pass"))
        db.add(user)
        db.commit()
        org = models.Organization(name="Journey Co", industry="Logistics")
        db.add(org)
        db.commit()
        db.add(models.OrgOwner(user_id=user.id, organization_id=org.id,
                               role="owner", status="active"))
        db.add(models.UserPref(user_id=user.id, timezone="Africa/Nairobi"))
        db.commit()
        activation = services_success.activation(db, user, org)
        health = services_success.customer_health(db, org)
        org_id = org.id
        assert activation["total"] == 7 and 0 <= activation["percent"] <= 100
        assert 0 <= health["score"] <= 100
        assert sum(item["max"] for item in health["factors"]) == 100

    with TestClient(app) as owner:
        login = owner.post("/login", data={"email": email, "password": "journey-pass"},
                           headers={"x-forwarded-for": "198.51.100.230"},
                           follow_redirects=False)
        assert login.status_code == 303
        page = owner.get("/getting-started")
        assert page.status_code == 200
        assert "Journey Co" in page.text
        assert owner.get("/dashboard").status_code == 200

        opened = owner.post("/support", data={
            "subject": "Onboarding question about the first assessment",
            "body": "Which department should own the first assessment in a small team?",
            "category": "general", "priority": "normal",
        }, headers={"x-forwarded-for": "198.51.100.231"}, follow_redirects=False)
        assert opened.status_code == 303

    with SessionLocal() as db:
        ticket = db.query(models.SupportTicket).filter_by(
            requester_email=email).one()
        assert ticket.organization_id == org_id
