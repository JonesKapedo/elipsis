"""The financial impact model: sizing, tiers, ceiling and honest arithmetic."""
import pytest

import elipsis_questions as EQ
import readiness as R


@pytest.fixture(scope="module")
def questions():
    return [dict(id=i + 1, **q) for i, q in enumerate(EQ.as_dicts())]


@pytest.fixture(scope="module")
def poor_answers(questions):
    """A badly-run organisation: almost every answer scores 0-1."""
    return {q["id"]: {"score": 1 if i % 2 else 0, "evidence": "none"}
            for i, q in enumerate(questions)}


# --- the defect this model exists to fix ---------------------------------

def test_savings_scale_with_company_size(questions, poor_answers):
    """Identical answers must produce different savings for different sizes."""
    small = R.compute(questions, poor_answers, staff=8)["financial"]
    large = R.compute(questions, poor_answers, staff=600)["financial"]
    assert large["annual_savings"] > small["annual_savings"] * 50


def test_wage_tiers_rise_with_size():
    assert R.blended_hourly_rate(10) < R.blended_hourly_rate(100)
    assert R.blended_hourly_rate(100) < R.blended_hourly_rate(300)
    assert R.blended_hourly_rate(300) < R.blended_hourly_rate(900)
    assert R.blended_hourly_rate(0) > 0
    assert R.blended_hourly_rate(None) == R.DEFAULT_HOURLY_RATE


def test_labour_line_matches_staff_times_rate():
    staff, rate = 120, R.blended_hourly_rate(120)
    assert R.labour_line(staff, rate) == staff * 160 * 12 * rate


# --- the ceiling ----------------------------------------------------------

def test_savings_never_exceed_the_cap(questions, poor_answers):
    for staff in (8, 30, 120, 400, 900):
        f = R.compute(questions, poor_answers, staff=staff)["financial"]
        assert f["annual_savings"] <= f["assumptions"]["savings_cap"] + 1


def test_cap_is_a_share_of_the_labour_line(questions, poor_answers):
    f = R.compute(questions, poor_answers, staff=200)["financial"]
    x = f["assumptions"]
    assert x["savings_cap"] == pytest.approx(x["labour_line"] * 0.12, rel=1e-6)


def test_capped_result_still_adds_up(questions, poor_answers):
    """When the cap bites, the line items must still reconcile."""
    f = R.compute(questions, poor_answers, staff=5)["financial"]
    assert f["current_cost"] - f["future_cost"] == pytest.approx(
        f["annual_savings"], abs=2)


# --- arithmetic a client could check --------------------------------------

def test_savings_are_consistent_with_cost_lines(questions, poor_answers):
    f = R.compute(questions, poor_answers, staff=50)["financial"]
    assert f["current_cost"] >= f["future_cost"] >= 0
    assert f["annual_savings"] == round(f["current_cost"] - f["future_cost"])


def test_investment_and_roi_are_positive(questions, poor_answers):
    f = R.compute(questions, poor_answers, staff=80)["financial"]
    assert f["investment"] > 0
    assert f["roi"] > 0
    assert f["payback_months"] > 0


def test_a_perfect_organisation_has_no_pain_points(questions):
    answers = {q["id"]: {"score": 5, "evidence": "multi"} for q in questions}
    f = R.compute(questions, answers, staff=100)["financial"]
    assert f["annual_savings"] == 0
    assert f["investment"] == 0


def test_assumptions_block_is_reported(questions, poor_answers):
    x = R.compute(questions, poor_answers, staff=64)["financial"]["assumptions"]
    for key in ("staff", "hourly_rate", "labour_line", "savings_cap",
                "max_savings_share", "capped", "hours_freed"):
        assert key in x
    assert x["hours_freed"] >= 0
