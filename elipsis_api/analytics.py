"""Derived analytics and chart geometry built from a computed assessment result.

Every surface (results page, board pack, dashboard, PDF) reads the same
numbers from here so the views can never disagree with each other.
"""

from __future__ import annotations

import math
from typing import Any, Iterable

from constants import (
    MATURITY_BANDS, PILLAR_LABELS, PILLAR_WEIGHTS, SUBDOMAIN_LABELS, SUBDOMAIN_PILLAR,
)

TARGET_INDEX = 75.0
PHASE_WINDOWS = {1: (0, 3), 2: (3, 12), 3: (12, 24)}
PHASE_CAPTURE = {1: 0.3, 2: 0.7, 3: 1.0}
SEVERITY_ORDER = ("Critical", "High", "Medium", "Low")
SEVERITY_COLORS = {"Critical": "#7f1d1d", "High": "#b91c1c",
                   "Medium": "#d97706", "Low": "#0f766e"}


def num(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def clamp(value: Any, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, num(value)))


def heat_level(score: Any) -> int:
    """0 (critical) .. 4 (strength) for colour classes."""
    s = num(score)
    if s < 25:
        return 0
    if s < 40:
        return 1
    if s < 55:
        return 2
    if s < 70:
        return 3
    return 4


def reading(score: Any) -> str:
    return ("Critical gap", "Material weakness", "Developing",
            "Solid base", "Strength")[heat_level(score)]


def radar(series: dict[str, float], overlay: dict[str, float] | None = None,
          size: int = 320, target: float | None = TARGET_INDEX) -> dict[str, Any]:
    codes = list(series.keys()) or list(PILLAR_WEIGHTS.keys())
    n = max(len(codes), 3)
    cx = cy = size / 2
    radius = size / 2 - 58

    def point(i: int, value: float) -> tuple[float, float]:
        angle = -math.pi / 2 + 2 * math.pi * i / n
        r = radius * clamp(value) / 100
        return cx + r * math.cos(angle), cy + r * math.sin(angle)

    def polygon(values: dict[str, float] | None, fixed: float | None = None) -> str:
        pts = []
        for i, code in enumerate(codes):
            v = fixed if fixed is not None else num((values or {}).get(code))
            x, y = point(i, v)
            pts.append(f"{x:.1f},{y:.1f}")
        return " ".join(pts)

    axes = []
    for i, code in enumerate(codes):
        x2, y2 = point(i, 100)
        angle = -math.pi / 2 + 2 * math.pi * i / n
        lx = cx + (radius + 22) * math.cos(angle)
        ly = cy + (radius + 22) * math.sin(angle)
        cos = math.cos(angle)
        anchor = "middle" if abs(cos) < 0.3 else ("start" if cos > 0 else "end")
        dx, dy = point(i, num(series.get(code)))
        axes.append(dict(code=code, label=PILLAR_LABELS.get(code, code),
                         value=num(series.get(code)), x2=round(x2, 1), y2=round(y2, 1),
                         lx=round(lx, 1), ly=round(ly + 4, 1), anchor=anchor,
                         dx=round(dx, 1), dy=round(dy, 1)))
    return dict(
        size=size, cx=cx, cy=cy,
        rings=[polygon(None, fixed=f) for f in (25, 50, 75, 100)],
        points=polygon(series),
        overlay=polygon(overlay) if overlay else None,
        target=polygon(None, fixed=target) if target else None,
        axes=axes,
    )


def band_scale(index: Any) -> dict[str, Any]:
    score = clamp(index)
    segments, current, next_band = [], None, None
    for low, high, label in MATURITY_BANDS:
        top = min(high, 100)
        active = low <= score < high
        segments.append(dict(label=label, low=low, high=top,
                             width=top - low, active=active))
        if active:
            current = label
        elif low > score and next_band is None:
            next_band = dict(label=label, gap=round(low - score, 1))
    return dict(score=score, segments=segments, current=current, next=next_band)


def contributions(pillars: dict[str, float]) -> list[dict[str, Any]]:
    rows = []
    total_weight = sum(PILLAR_WEIGHTS.get(c, 0) for c in pillars) or 1
    for code, score in pillars.items():
        weight = PILLAR_WEIGHTS.get(code, 0) / total_weight
        s = clamp(score)
        rows.append(dict(
            code=code, label=PILLAR_LABELS.get(code, code), score=s,
            weight=round(weight * 100, 1),
            contribution=round(s * weight, 2),
            lost=round((100 - s) * weight, 2),
            gap=round(max(0.0, TARGET_INDEX - s), 1),
            uplift=round(max(0.0, TARGET_INDEX - s) * weight, 2),
            level=heat_level(s), reading=reading(s),
        ))
    rows.sort(key=lambda r: r["uplift"], reverse=True)
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows


def subdomain_heat(subdomains: dict[str, float]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for code, score in subdomains.items():
        pillar = SUBDOMAIN_PILLAR.get(code, "")
        groups.setdefault(pillar, []).append(dict(
            code=code, label=SUBDOMAIN_LABELS.get(code, code),
            score=clamp(score), level=heat_level(score)))
    return [dict(pillar=p, label=PILLAR_LABELS.get(p, p), cells=cells)
            for p, cells in groups.items()]


def severity_donut(pain_points: Iterable[dict[str, Any]], radius: float = 54) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for p in pain_points:
        sev = (p.get("severity") or "Low").title()
        counts[sev] = counts.get(sev, 0) + 1
    total = sum(counts.values())
    circumference = 2 * math.pi * radius
    offset, segments = 0.0, []
    ordered = [s for s in SEVERITY_ORDER if s in counts] + \
        [s for s in counts if s not in SEVERITY_ORDER]
    for sev in ordered:
        length = circumference * counts[sev] / total if total else 0
        segments.append(dict(label=sev, count=counts[sev],
                             share=round(100 * counts[sev] / total, 1) if total else 0,
                             color=SEVERITY_COLORS.get(sev, "#6b6570"),
                             dash=f"{length:.2f} {circumference - length:.2f}",
                             offset=f"{-offset:.2f}"))
        offset += length
    return dict(total=total, radius=radius, segments=segments)


def priority_matrix(recommendations: Iterable[dict[str, Any]], width: int = 520,
                    height: int = 300, pad: int = 40) -> dict[str, Any]:
    recs = list(recommendations)
    max_roi = max([num(r.get("roi")) for r in recs] + [100])
    points = []
    for i, r in enumerate(recs, start=1):
        pr = clamp(r.get("priority"))
        roi = max(0.0, num(r.get("roi")))
        x = pad + (width - 2 * pad) * pr / 100
        y = height - pad - (height - 2 * pad) * roi / max_roi
        quadrant = ("Do now" if pr >= 50 and roi >= max_roi / 2 else
                    "Plan" if pr >= 50 else
                    "Opportunistic" if roi >= max_roi / 2 else "Defer")
        points.append(dict(n=i, title=r.get("title") or "", x=round(x, 1), y=round(y, 1),
                           priority=pr, roi=roi, phase=r.get("phase") or 1,
                           quadrant=quadrant))
    return dict(width=width, height=height, pad=pad, max_roi=round(max_roi),
                mid_x=width / 2, mid_y=height / 2, points=points)


def gantt(roadmap: Iterable[dict[str, Any]], months: int = 24) -> dict[str, Any]:
    rows = []
    for phase in roadmap:
        number = int(num(phase.get("number"), 1)) or 1
        start, end = PHASE_WINDOWS.get(number, (0, months))
        rows.append(dict(label=phase.get("label") or f"Phase {number}",
                         horizon=phase.get("horizon") or "",
                         count=int(num(phase.get("count") or len(phase.get("items") or []))),
                         start=start, end=end,
                         left=round(100 * start / months, 2),
                         width=round(100 * (end - start) / months, 2),
                         number=number))
    ticks = [dict(month=m, left=round(100 * m / months, 2)) for m in range(0, months + 1, 3)]
    return dict(rows=rows, ticks=ticks, months=months)


def waterfall(financial: dict[str, Any]) -> dict[str, Any]:
    current = max(0.0, num(financial.get("current_cost")))
    savings = max(0.0, num(financial.get("annual_savings")))
    future = max(0.0, num(financial.get("future_cost")))
    investment = max(0.0, num(financial.get("investment")))
    top = max(current, future + savings, investment, 1)

    def pct(v: float) -> float:
        return round(100 * v / top, 2)

    return dict(bars=[
        dict(label="Current friction cost", value=current, bottom=0, height=pct(current), kind="cost"),
        dict(label="Savings captured", value=savings, bottom=pct(future), height=pct(savings), kind="save"),
        dict(label="Projected cost", value=future, bottom=0, height=pct(future), kind="future"),
        dict(label="Investment", value=investment, bottom=0, height=pct(investment), kind="invest"),
    ])


def cashflow_curve(financial: dict[str, Any], months: int = 24, width: int = 520,
                   height: int = 220, pad: int = 36) -> dict[str, Any]:
    savings = max(0.0, num(financial.get("annual_savings"))) / 12
    investment = max(0.0, num(financial.get("investment")))
    values, cumulative, breakeven = [], -investment, None
    for m in range(0, months + 1):
        if m > 0:
            ramp = min(1.0, m / 6)
            cumulative += savings * ramp
        values.append(cumulative)
        if breakeven is None and cumulative >= 0 and m > 0:
            breakeven = m
    lo, hi = min(values + [0]), max(values + [0])
    span = (hi - lo) or 1

    def xy(i: int, v: float) -> tuple[float, float]:
        return (pad + (width - 2 * pad) * i / months,
                height - pad - (height - 2 * pad) * (v - lo) / span)

    pts = [xy(i, v) for i, v in enumerate(values)]
    _, zero_y = xy(0, 0)
    return dict(width=width, height=height, pad=pad,
                points=" ".join(f"{x:.1f},{y:.1f}" for x, y in pts),
                area=(f"{pts[0][0]:.1f},{zero_y:.1f} "
                      + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
                      + f" {pts[-1][0]:.1f},{zero_y:.1f}"),
                zero_y=round(zero_y, 1), breakeven=breakeven,
                breakeven_x=round(xy(breakeven, 0)[0], 1) if breakeven else None,
                end_value=round(values[-1], 2), low=round(lo, 2), high=round(hi, 2),
                ticks=[dict(m=m, x=round(xy(m, 0)[0], 1)) for m in range(0, months + 1, 6)])


def sensitivity(financial: dict[str, Any]) -> list[dict[str, Any]]:
    savings = max(0.0, num(financial.get("annual_savings")))
    investment = max(0.0, num(financial.get("investment")))
    rows = []
    for capture in (0.5, 0.75, 1.0, 1.25):
        s = savings * capture
        rows.append(dict(
            scenario={0.5: "Conservative", 0.75: "Cautious", 1.0: "Modelled",
                      1.25: "Stretch"}[capture],
            capture=int(capture * 100), savings=round(s, 2),
            roi=round(100 * (s - investment) / investment, 1) if investment else 0.0,
            payback=round(12 * investment / s, 1) if s else None))
    return rows


def sparkline(values: list[float], width: int = 260, height: int = 64, pad: int = 6) -> dict[str, Any]:
    vals = [clamp(v) for v in values]
    if not vals:
        return dict(width=width, height=height, points="", dots=[])
    if len(vals) == 1:
        vals = vals * 2
    lo, hi = min(vals) - 5, max(vals) + 5
    span = (hi - lo) or 1
    step = (width - 2 * pad) / (len(vals) - 1)
    dots = [dict(x=round(pad + i * step, 1),
                 y=round(height - pad - (height - 2 * pad) * (v - lo) / span, 1), v=v)
            for i, v in enumerate(vals)]
    return dict(width=width, height=height,
                points=" ".join(f"{d['x']},{d['y']}" for d in dots), dots=dots)


def executive_actions(result: dict[str, Any], contribs: list[dict[str, Any]]) -> list[str]:
    actions = []
    if contribs:
        top = contribs[0]
        actions.append(
            f"Lift {top['label']} from {top['score']:.0f} to {TARGET_INDEX:.0f}: worth "
            f"+{top['uplift']:.1f} index points, the single largest lever.")
    quick = [r for r in (result.get("recommendations") or []) if (r.get("phase") or 1) == 1]
    if quick:
        actions.append(f"Fund {len(quick)} quick win{'s' if len(quick) != 1 else ''} "
                       f"from operating budget, starting with “{quick[0].get('title')}”.")
    severe = [p for p in (result.get("pain_points") or [])
              if (p.get("severity") or "").title() in ("Critical", "High")]
    if severe:
        actions.append(f"Assign owners to {len(severe)} high-severity pain point"
                       f"{'s' if len(severe) != 1 else ''} within 30 days.")
    fin = result.get("financial") or {}
    if num(fin.get("payback_months")):
        actions.append(f"Track savings capture monthly against a "
                       f"{num(fin.get('payback_months')):.1f}-month payback target.")
    actions.append("Re-run the assessment after 90 days to evidence movement.")
    return actions


def build(result: dict[str, Any] | None) -> dict[str, Any]:
    """Every derived view for one result, ready for templates or the PDF."""
    result = result or {}
    pillars = {k: num(v) for k, v in (result.get("pillars") or {}).items()}
    subdomains = {k: num(v) for k, v in (result.get("subdomains") or {}).items()}
    financial = result.get("financial") or {}
    contribs = contributions(pillars)
    ordered_subs = sorted(subdomains.items(), key=lambda kv: kv[1])
    risks = sorted([m for m in (result.get("metric_rows") or []) if m.get("kind") == "risk"],
                   key=lambda m: num(m.get("value")), reverse=True)
    scores = [m for m in (result.get("metric_rows") or []) if m.get("kind") != "risk"]
    answered, total = num(result.get("answered")), num(result.get("total"))
    return dict(
        target=TARGET_INDEX,
        radar=radar(pillars),
        band=band_scale(result.get("readiness_index")),
        contributions=contribs,
        heat=subdomain_heat(subdomains),
        weakest=[dict(code=c, label=SUBDOMAIN_LABELS.get(c, c), score=s,
                      pillar=SUBDOMAIN_PILLAR.get(c, "")) for c, s in ordered_subs[:3]],
        strongest=[dict(code=c, label=SUBDOMAIN_LABELS.get(c, c), score=s,
                        pillar=SUBDOMAIN_PILLAR.get(c, "")) for c, s in ordered_subs[::-1][:3]],
        top_risks=risks[:5],
        risk_exposure=round(sum(num(m.get("value")) for m in risks) / len(risks), 1) if risks else None,
        capability=round(sum(num(m.get("value")) for m in scores) / len(scores), 1) if scores else None,
        donut=severity_donut(result.get("pain_points") or []),
        matrix=priority_matrix(result.get("recommendations") or []),
        gantt=gantt(result.get("roadmap") or []),
        waterfall=waterfall(financial),
        cashflow=cashflow_curve(financial),
        sensitivity=sensitivity(financial),
        coverage=round(100 * answered / total, 1) if total else 0.0,
        potential_index=round(num(result.get("readiness_index"))
                              + sum(c["uplift"] for c in contribs), 1),
        actions=executive_actions(result, contribs),
    )
