"""The scoring engine: bounds, formula safety, readiness gating and edges."""
import pytest

import constants as C
import elipsis_questions as EQ
import readiness as R


@pytest.fixture(scope="module")
def questions():
    return [dict(id=i + 1, **q) for i, q in enumerate(EQ.as_dicts())]


def answers_for(questions, score, evidence="none"):
    return {q["id"]: {"score": score, "evidence": evidence} for q in questions}


def segment_questions(questions):
    """Segments carry the raw question dicts; attach the seeded ids by code."""
    by_code = {q["code"]: q for q in questions}
    return [dict(by_code[q["code"]]) for s in EQ.segments() for q in s["questions"]]


# --- metric bounds and completeness ---------------------------------------

def test_all_metrics_computed(questions):
    result = R.compute(questions, answers_for(questions, 3))
    assert set(result["metrics"]) == set(C.METRIC_FORMULAS)
    assert len(result["metric_rows"]) == 36


def test_metrics_within_bounds(questions):
    for score in (0, 1, 2, 3, 4, 5):
        result = R.compute(questions, answers_for(questions, score))
        for code, value in result["metrics"].items():
            assert 0.0 <= value <= 100.0, f"{code}={value} at score {score}"


def test_index_extremes(questions):
    worst = R.compute(questions, answers_for(questions, 0))
    best = R.compute(questions, answers_for(questions, 5, "multi"))
    assert worst["readiness_index"] == 0.0
    assert best["readiness_index"] == 100.0
    assert worst["maturity_band"] == "Foundational"
    assert best["maturity_band"] == "Intelligent Enterprise Ready"


def test_risk_metrics_point_the_right_way(questions):
    """A risk metric must be HIGH when things are bad and LOW when good."""
    worst = R.compute(questions, answers_for(questions, 0))
    best = R.compute(questions, answers_for(questions, 5))
    for row in worst["metric_rows"]:
        if row["kind"] != "risk":
            continue
        assert worst["metrics"][row["code"]] > best["metrics"][row["code"]], (
            f"{row['code']} is tagged risk but does not fall as readiness rises")


def test_every_metric_has_a_label_and_reading(questions):
    result = R.compute(questions, answers_for(questions, 3))
    for row in result["metric_rows"]:
        assert row["label"].strip()
        assert row["reading"].strip()
        assert row["kind"] in ("score", "risk")


# --- the formula evaluator is genuinely restricted ------------------------

@pytest.mark.parametrize("formula", [
    '__import__("os").system("ls")',
    'open("/etc/passwd")',
    "OPS.__class__",
    "lambda: 1",
    "[x for x in (1, 2)]",
    "OPS if 1 else 2",
    "avg(OPS).__class__",
])
def test_evaluator_rejects_unsafe_formulas(formula):
    with pytest.raises(ValueError):
        R.validate_formula(formula)


def test_evaluator_rejects_unknown_references(monkeypatch):
    monkeypatch.setitem(C.METRIC_FORMULAS, "ZZZ", "avg(NO_SUCH_THING)")
    with pytest.raises(ValueError, match="unknown name"):
        R.validate_metrics({"Q01"})


def test_circular_metric_reference_is_reported(monkeypatch):
    monkeypatch.setitem(C.METRIC_FORMULAS, "LOOP_A", "LOOP_B")
    monkeypatch.setitem(C.METRIC_FORMULAS, "LOOP_B", "LOOP_A")
    engine = R.MetricEngine({}, frozenset())
    with pytest.raises(ValueError, match="circular"):
        engine.resolve("LOOP_A")


# --- maturity band edges (regression: a gap once made 20.36 "Unknown") ----

@pytest.mark.parametrize("score,expected", [
    (0, "Foundational"), (20.36, "Foundational"), (20.99, "Foundational"),
    (21, "Emerging"), (40.99, "Emerging"),
    (41, "Developing"), (47.9, "Developing"), (60.99, "Developing"),
    (61, "Transformation Ready"), (80.99, "Transformation Ready"),
    (81, "Intelligent Enterprise Ready"), (100, "Intelligent Enterprise Ready"),
])
def test_maturity_band_edges(score, expected):
    assert C.maturity_band(score) == expected


def test_every_score_gets_a_band():
    for score in [i / 4 for i in range(0, 401)]:
        assert C.maturity_band(score) != "Unknown"


# --- partial and empty forms ----------------------------------------------

def test_empty_answers_do_not_crash(questions):
    result = R.compute(questions, {})
    assert result["readiness_index"] == 0.0
    assert result["answered"] == 0
    assert len(result["metrics"]) == 36


def test_partial_answers_do_not_crash(questions):
    for n in (1, 5, 31, 62):
        partial = answers_for(questions[:n], 4)
        result = R.compute(questions, partial)
        assert result["answered"] == n
        assert len(result["metrics"]) == 36


# --- live scoring ---------------------------------------------------------

def test_live_reports_progress(questions):
    live = R.compute_live(questions, {}, "OPS")
    assert live["percent"] == 0
    assert live["answered"] == 0


def test_live_holds_back_metrics_whose_inputs_are_missing(questions):
    """A metric must not report a number until every input it names exists."""
    first_subdomain = EQ.segments()[0]["subdomain"]
    first_three = segment_questions(questions)[:3]
    live = R.compute_live(questions, answers_for(first_three, 4), first_subdomain)
    for row in live["segment_metrics"]:
        assert row["value"] is None, (
            f"{row['code']} reported {row['value']} before its inputs existed")
        assert row["ready"] is False

    live2 = R.compute_live(questions, answers_for(segment_questions(questions)[:6], 4),
                           first_subdomain)
    assert any(row["ready"] for row in live2["segment_metrics"])


def test_live_never_shows_a_fake_hundred_risk_value(questions):
    """An unanswered subdomain scores zero, which would invert to a scary 100."""
    first = EQ.segments()[0]["subdomain"]
    live = R.compute_live(questions, answers_for(segment_questions(questions)[:3], 5), first)
    for row in live["segment_metrics"]:
        if row["kind"] == "risk":
            assert row["value"] is None, f"{row['code']} showed a misleading risk value"


# --- roadmap --------------------------------------------------------------

def test_roadmap_has_three_phases_covering_every_recommendation(questions):
    result = R.compute(questions, answers_for(questions, 1))
    assert len(result["roadmap"]) == 3
    on_roadmap = sum(p["count"] for p in result["roadmap"])
    assert on_roadmap == len(result["recommendations"])
    assert all(p["count"] > 0 for p in result["roadmap"])


def test_top_opportunities_match_the_ranking(questions):
    result = R.compute(questions, answers_for(questions, 1))
    priorities = [r["priority"] for r in result["recommendations"]]
    assert priorities == sorted(priorities, reverse=True)
    assert len(result["top_opportunities"]) == min(3, len(priorities))
