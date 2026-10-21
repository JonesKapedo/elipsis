"""Turn a computed assessment into a company digital-structure portrait."""

from __future__ import annotations


def _band(score: float) -> str:
    if score >= 75:
        return "structurally ready"
    if score >= 55:
        return "partially systematised"
    if score >= 35:
        return "person-dependent"
    return "informal and fragile"


def company_portrait(organization, department, result: dict) -> dict:
    name = getattr(organization, "name", None) or "the organisation"
    dept = getattr(department, "name", None)
    index = float(result.get("readiness_index") or 0)
    raw_pillars = result.get("pillars") or []
    if isinstance(raw_pillars, dict):
        from constants import PILLAR_LABELS
        pillars = [{"code": c, "label": PILLAR_LABELS.get(c, c), "score": v}
                   for c, v in raw_pillars.items()]
    else:
        pillars = list(raw_pillars)
    weakest = min(pillars, key=lambda p: p.get("score") or 0) if pillars else None
    strongest = max(pillars, key=lambda p: p.get("score") or 0) if pillars else None
    pains = result.get("pain_points") or result.get("pains") or []
    financial = result.get("financial") or {}
    staff = getattr(organization, "employee_count", None)
    industry = getattr(organization, "industry", None) or "its industry"

    where = f"{name}" + (f", specifically the {dept} function" if dept else "")
    structure = (
        f"{where} currently reads as {_band(index)} on the Elipsis digital-structure scale "
        f"({index:.1f}/100). The assessment is a snapshot of how work actually moves today: "
        f"what is written down, what still lives in people's heads, which decisions rest on "
        f"data, and which processes are too tangled to automate without first being redesigned."
    )
    if staff:
        structure += (
            f" With about {staff} people, small process defects compound quickly — "
            f"every repeated manual step is a weekly tax on capacity."
        )
    structure += f" The operating context is {industry}."

    pillar_lines = []
    for p in pillars:
        label = p.get("label") or p.get("code") or "Pillar"
        score = float(p.get("score") or 0)
        pillar_lines.append(
            f"{label} at {score:.0f}/100 — {_band(score)}. "
            + (
                "This is a constraint on any automation programme until the underlying flow is stabilised."
                if score < 50
                else "This is a usable base: automation here can be sequenced rather than invented from scratch."
            )
        )

    leverage = (
        "The useful starting point is not a tool purchase. It is a ranked map of procedures "
        "that are repetitive, rule-based, and expensive when they fail. The self-assessment "
        "identifies that map from the inside. A physical assessment then walks the floor, "
        "times the handoffs, and confirms which of those procedures are safe to automate first."
    )
    if weakest and strongest:
        leverage += (
            f" Today the binding constraint is {weakest.get('label') or weakest.get('code')} "
            f"({float(weakest.get('score') or 0):.0f}), while "
            f"{strongest.get('label') or strongest.get('code')} "
            f"({float(strongest.get('score') or 0):.0f}) is the strongest foundation to build on."
        )

    money = ""
    savings = financial.get("annual_savings")
    if savings:
        money = (
            f"On the stated assumptions the model places annual savings potential near "
            f"KES {float(savings):,.0f}. Treat that as a planning range, not a promise: "
            f"it sizes the prize so leadership can decide whether a floor sweep is worth commissioning."
        )

    risks = []
    for item in pains[:6]:
        if isinstance(item, dict):
            risks.append(item.get("title") or item.get("name") or str(item))
        else:
            risks.append(str(item))

    return {
        "structure": structure,
        "pillar_lines": pillar_lines,
        "leverage": leverage,
        "money": money,
        "risks": risks,
        "posture": _band(index),
    }


def board_narrative(organization, department, assessment, result: dict, *,
                    benchmark: dict | None = None,
                    actions: list | None = None) -> dict:
    """A deterministic, citation-backed board narrative.

    Every claim points at a computed field from this assessment. No external
    model writes the text, so the board can trace each sentence back to the
    score, assumption, or action that produced it.
    """
    from constants import PILLAR_LABELS

    org_name = getattr(organization, "name", None) or "The organisation"
    dept_name = getattr(department, "name", None)
    scope = f"{org_name}" + (f" · {dept_name}" if dept_name else "")
    index = float(result.get("readiness_index") or 0)
    band = result.get("maturity_band") or _band(index)
    confidence = result.get("confidence_index")
    pillars = result.get("pillars") or {}
    if not isinstance(pillars, dict):
        pillars = {p.get("code"): p.get("score") for p in pillars}
    ordered = sorted(
        [(code, float(score or 0)) for code, score in pillars.items()],
        key=lambda pair: pair[1],
    )
    weakest = ordered[0] if ordered else None
    strongest = ordered[-1] if ordered else None
    financial = result.get("financial") or {}
    assumptions = financial.get("assumptions") or {}
    pains = result.get("pain_points") or []
    actions = actions or []
    open_actions = [a for a in actions if (getattr(a, "status", None) or "not_started") != "done"]

    citations: list[dict] = []

    def cite(cid: str, label: str, value, source: str) -> str:
        citations.append({"id": cid, "label": label, "value": value, "source": source})
        return f"[{cid}]"

    r1 = cite("R1", "Readiness index", f"{index:.1f}/100", "Elipsis score")
    r2 = cite("R2", "Maturity band", band, "Elipsis band")
    r3 = cite("R3", "Confidence", f"{float(confidence):.1f}" if confidence is not None else "—",
              "Answer completeness")
    p_refs = []
    for code, score in ordered:
        p_refs.append(cite(f"P-{code}", PILLAR_LABELS.get(code, code),
                           f"{score:.1f}/100", "Pillar score"))
    f_refs = []
    if financial.get("annual_savings") is not None:
        f_refs.append(cite("F1", "Annual savings potential",
                           f"KES {float(financial['annual_savings']):,.0f}",
                           "Management estimate"))
    if financial.get("investment") is not None:
        f_refs.append(cite("F2", "Indicative investment",
                           f"KES {float(financial['investment']):,.0f}",
                           "Management estimate"))
    if financial.get("roi") is not None:
        f_refs.append(cite("F3", "ROI", f"{float(financial['roi']):.0f}%",
                           "Modelled return"))
    if financial.get("payback_months") is not None:
        f_refs.append(cite("F4", "Payback", f"{float(financial['payback_months']):.1f} months",
                           "Modelled payback"))
    a_refs = []
    for idx, item in enumerate(open_actions[:3], start=1):
        a_refs.append(cite(f"A{idx}", getattr(item, "title", "Action"),
                           getattr(item, "status", "not_started") or "not_started",
                           "90-day plan"))
    d_refs = []
    for idx, pain in enumerate(pains[:2], start=1):
        title = pain.get("title") if isinstance(pain, dict) else str(pain)
        d_refs.append(cite(f"D{idx}", title or "Finding", "triggered", "Assessment logic"))
    b_ref = None
    if benchmark and benchmark.get("available"):
        b_ref = cite("B1", "Peer median",
                     f"{benchmark.get('median')} from {benchmark.get('sample')} peers",
                     "Elipsis cohort")

    weakest_text = ""
    strongest_text = ""
    if weakest and strongest:
        weak_label = PILLAR_LABELS.get(weakest[0], weakest[0])
        strong_label = PILLAR_LABELS.get(strongest[0], strongest[0])
        weakest_text = (
            f" The binding constraint is {weak_label} at {weakest[1]:.1f}/100 "
            f"{p_refs[ordered.index(weakest)]}."
        )
        strongest_text = (
            f" The strongest foundation is {strong_label} at {strongest[1]:.1f}/100 "
            f"{p_refs[ordered.index(strongest)]}."
        )

    money_text = ""
    if f_refs:
        money_text = (
            f" On the stated assumptions, the model places annual savings potential at "
            f"KES {float(financial.get('annual_savings') or 0):,.0f} {f_refs[0]}, "
            f"against an indicative investment of KES {float(financial.get('investment') or 0):,.0f}"
            + (f" {f_refs[1]}" if len(f_refs) > 1 else "")
            + (f", a modelled ROI of {float(financial.get('roi') or 0):.0f}% {f_refs[2]}"
               if len(f_refs) > 2 else "")
            + (f" and payback of {float(financial.get('payback_months') or 0):.1f} months {f_refs[3]}"
               if len(f_refs) > 3 else "")
            + ". These are planning estimates, not audited savings."
        )

    action_text = ""
    if a_refs:
        action_text = (
            f" The first three open actions are {getattr(open_actions[0], 'title', 'the first action')} {a_refs[0]}"
            + (f", {getattr(open_actions[1], 'title', 'the second action')} {a_refs[1]}"
               if len(a_refs) > 1 else "")
            + (f", and {getattr(open_actions[2], 'title', 'the third action')} {a_refs[2]}"
               if len(a_refs) > 2 else "")
            + ". Assign an owner and a date before funding anything else."
        )
    elif d_refs:
        action_text = (
            f" The assessment triggered {len(pains)} named finding(s), led by "
            f"{getattr(pains[0], 'title', 'the first finding') if pains else 'the first finding'} {d_refs[0]}. Turn the first finding into an owned action "
            "before adding tools."
        )

    benchmark_text = ""
    if b_ref:
        benchmark_text = (
            f" Peer context is available: the median is {benchmark.get('median')} across "
            f"{benchmark.get('sample')} comparable assessments {b_ref}"
            + (f", placing this organisation at the {benchmark.get('percentile')}th percentile."
               if benchmark.get("percentile") is not None else ".")
        )
    else:
        benchmark_text = (
            " Peer comparison is suppressed until at least five comparable completed "
            "assessments exist. That is deliberate: a median from four companies is not a benchmark."
        )

    assumption_text = ""
    if assumptions:
        assumption_text = (
            f" The financial case rests on {assumptions.get('staff', '—')} staff, a blended "
            f"hourly rate of KES {float(assumptions.get('hourly_rate') or 0):,.0f}, "
            f"{assumptions.get('working_hours_per_month', '—')} hours per month, and a "
            f"{float(assumptions.get('max_savings_share') or 0) * 100:.0f}% savings cap. "
            "Change any of those on the assumptions page and the numbers recompute."
        )

    return {
        "title": f"Board narrative — {scope}",
        "subtitle": "Deterministic, citation-backed, generated from this assessment.",
        "generated_at": getattr(assessment, "completed_at", None),
        "sections": [
            {
                "heading": "The headline",
                "paragraphs": [
                    f"{org_name}{(' · ' + dept_name) if dept_name else ''} scores "
                    f"{index:.1f}/100 {r1}, in the {band} band {r2}. "
                    f"Confidence in the input is {float(confidence):.1f} {r3}."
                    if confidence is not None else
                    f"{org_name}{(' · ' + dept_name) if dept_name else ''} scores "
                    f"{index:.1f}/100 {r1}, in the {band} band {r2}."
                ],
            },
            {
                "heading": "What is driving the score",
                "paragraphs": [
                    (weakest_text + strongest_text).strip()
                    or "Pillar scores were not available for this assessment.",
                ],
            },
            {
                "heading": "What it is worth",
                "paragraphs": [
                    ("The financial model sizes the prize rather than promising it." + money_text).strip(),
                ],
            },
            {
                "heading": "What to do next",
                "paragraphs": [(action_text or "No actions have been generated yet.").strip()],
            },
            {
                "heading": "How to challenge this",
                "paragraphs": [
                    (benchmark_text + assumption_text).strip(),
                ],
            },
        ],
        "citations": citations,
    }
