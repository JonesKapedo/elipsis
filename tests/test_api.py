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
        assert "Why we ask" in page.text
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


def test_start_persists_logistics_organisation_fields(signed_in):
    client = signed_in
    created = client.post("/start", data={
        "organization_name": "Mombasa Line Haul",
        "industry": "Logistics",
        "sub_industry": "Freight forwarding",
        "employee_count": "140",
        "revenue_band": "USD 1M–10M",
        "country": "Kenya",
        "city": "Mombasa",
        "department": "Operations",
        "respondent": "Ops lead",
    }, follow_redirects=False)
    assert created.status_code == 303
    assessment_id = int(created.headers["location"].split("/")[2])

    from elipsis_api import models
    from elipsis_api.database import SessionLocal
    with SessionLocal() as db:
        assessment = db.get(models.Assessment, assessment_id)
        assert assessment is not None
        org = db.get(models.Organization, assessment.organization_id)
        assert org.name == "Mombasa Line Haul"
        assert org.industry == "Logistics"
        assert org.sub_industry == "Freight forwarding"
        assert org.employee_count == 140
        assert org.revenue_band == "USD 1M–10M"
        assert org.city == "Mombasa"
        assert org.country == "Kenya"
        org_id = org.id

    dashboard = client.get(f"/dashboard?org={org_id}")
    assert dashboard.status_code == 200
    assert "Mombasa Line Haul at a glance" in dashboard.text
    assert "Freight forwarding" in dashboard.text
    assert "Mid-sized operator" in dashboard.text
    assert "USD 1M–10M" in dashboard.text

    diagnostics = client.get(f"/assessments?org={org_id}")
    assert diagnostics.status_code == 200
    assert "holding Mombasa Line Haul back" in diagnostics.text

    start = client.get(f"/start?org={org_id}")
    assert start.status_code == 200
    assert "Continue Mombasa Line Haul's diagnostic" in start.text
    assert "Freight forwarding" in start.text


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
    assert "On action board" in client.get(
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
