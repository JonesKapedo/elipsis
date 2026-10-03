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
