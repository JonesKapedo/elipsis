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
    assert client.get("/assessments").status_code == 200


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
