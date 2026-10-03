"""The ORG-001 instrument: structure, wording and answer-scale integrity."""
from collections import Counter

import pytest

import constants as C
import elipsis_questions as EQ


@pytest.fixture(scope="module")
def bank():
    return EQ.as_dicts()


def test_question_count(bank):
    assert len(bank) == 63


def test_codes_unique(bank):
    codes = [q["code"] for q in bank]
    assert len(set(codes)) == len(codes)


def test_nine_questions_per_pillar(bank):
    counts = Counter(q["pillar"] for q in bank)
    assert set(counts) == set(C.PILLAR_LABELS)
    assert set(counts.values()) == {9}, counts


def test_segments_are_three_questions_each():
    segments = EQ.segments()
    assert len(segments) == 21
    assert {len(s["questions"]) for s in segments} == {3}


def test_every_question_explains_itself(bank):
    for q in bank:
        assert q["text"].strip(), f"{q['code']} has no text"
        assert q["why"].strip(), f"{q['code']} has no why"
        assert len(q["text"]) > 15, f"{q['code']} text too terse"
        assert q["text"].endswith("?"), f"{q['code']} is not phrased as a question"


def test_text_is_plain_english(bank):
    """No jargon that a non-business reader would stumble on."""
    banned = ("SOP", "KPI", "API", "ERP", "CRM", "POS", "workflow", "throughput",
              "utilisation rate", "leverage", "synergy")
    for q in bank:
        for word in banned:
            assert word not in q["text"], f"{q['code']} contains jargon {word!r}"


def test_no_orphaned_subdomain(bank):
    assert {q["subdomain"] for q in bank} == set(C.SUBDOMAIN_LABELS)


# --- the per-question answer scales ---------------------------------------

def test_every_question_names_a_real_scale(bank):
    for q in bank:
        assert q["scale"] in C.SCALES, f"{q['code']} names unknown scale {q['scale']!r}"


def test_scales_have_six_options():
    for key, options in C.SCALES.items():
        assert len(options) == 6, f"{key} has {len(options)} options"


def test_scales_ascend_toward_ready():
    """Every scale must be ordered lowest-score first.

    The scoring engine assumes a higher score always means more ready, so a
    scale listed out of order would silently invert a metric.
    """
    for key in C.SCALES:
        assert C.scale_ascends(key), f"scale {key} is not in ascending score order"


def test_scale_options_are_self_explanatory():
    for key, options in C.SCALES.items():
        scores = [o[0] for o in options]
        assert scores == list(range(len(options))), f"{key} scores are not 0..n-1"
        for score, emoji, label, help_text in options:
            assert label.strip(), f"{key}/{score} has no label"
            assert help_text.strip(), f"{key}/{score} has no explanation"
            assert emoji.strip(), f"{key}/{score} has no emoji"


def test_each_question_gets_options_that_fit_it(bank):
    """Spot-check that a question's options speak to what it asks.

    Guards against a scale being reused where its wording does not apply.
    """
    by_code = {q["code"]: q for q in bank}
    cases = [
        ("Q05", "approvals", "people"),        # counts approvers, not frequency
        ("Q04", "stepcount", "steps"),         # counts steps
        ("Q37", "volume_count", "week"),       # counts volume per week
        ("Q42", "speed_more", "quickly"),      # measures speed
        ("Q17", "copying_less", "copied"),     # inverted: more copying = worse
    ]
    for code, scale, word in cases:
        q = by_code[code]
        assert q["scale"] == scale, f"{code} should use {scale}, got {q['scale']}"
        labels = " ".join(o[2].lower() for o in C.SCALES[scale])
        assert word.lower() in labels or word.lower() in q["text"].lower(), (
            f"{code} options do not mention {word!r}")


def test_risk_questions_are_inverted_at_authoring_time(bank):
    """"More is worse" questions must put the worst outcome on the lowest score."""
    inverted = {"Q15", "Q16", "Q17", "Q22", "Q23", "Q24", "Q31", "Q32", "Q33",
                "Q51", "Q61", "Q62", "Q63"}
    by_code = {q["code"]: q for q in bank}
    for code in inverted:
        assert by_code[code]["scale"].endswith("_less"), (
            f"{code} is a 'less is better' question but uses {by_code[code]['scale']}")
