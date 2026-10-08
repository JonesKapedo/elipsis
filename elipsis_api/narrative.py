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
