"""Server-side board-pack PDF generation (reportlab)."""

from __future__ import annotations

import io
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable,
)

INK = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#6b7280")
ACCENT = colors.HexColor("#b45309")
LINE = colors.HexColor("#e5e7eb")
SOFT = colors.HexColor("#fff7ed")


def _styles():
    base = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle("brand", parent=base["Normal"], fontName="Helvetica-Bold",
                                fontSize=11, textColor=INK, spaceAfter=2),
        "doc": ParagraphStyle("doc", parent=base["Normal"], fontName="Helvetica-Bold",
                             fontSize=8, textColor=ACCENT, spaceBefore=6, spaceAfter=4),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName="Helvetica-Bold",
                             fontSize=18, textColor=INK, spaceAfter=6, leading=22),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold",
                             fontSize=12, textColor=INK, spaceBefore=14, spaceAfter=6),
        "h3": ParagraphStyle("h3", parent=base["Heading3"], fontName="Helvetica-Bold",
                             fontSize=10, textColor=INK, spaceBefore=8, spaceAfter=4),
        "body": ParagraphStyle("body", parent=base["Normal"], fontName="Helvetica",
                               fontSize=9, textColor=INK, leading=13, spaceAfter=4),
        "muted": ParagraphStyle("muted", parent=base["Normal"], fontName="Helvetica",
                                fontSize=8, textColor=MUTED, leading=11),
        "score": ParagraphStyle("score", parent=base["Normal"], fontName="Helvetica-Bold",
                                fontSize=22, textColor=INK, alignment=2),
        "footer": ParagraphStyle("footer", parent=base["Normal"], fontName="Helvetica",
                                 fontSize=7, textColor=MUTED, leading=9),
    }


def _money(val, currency="KES"):
    try:
        n = float(val or 0)
    except (TypeError, ValueError):
        return "—"
    if abs(n) >= 1_000_000:
        return f"{currency} {n/1_000_000:.1f}M"
    if abs(n) >= 1_000:
        return f"{currency} {n/1_000:.0f}K"
    return f"{currency} {n:,.0f}"


def _table(headers, rows, col_widths=None):
    data = [headers] + rows
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("TEXTCOLOR", (0, 1), (-1, -1), INK),
        ("LINEBELOW", (0, 0), (-1, 0), 1, LINE),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def build_pdf(
    *,
    brand_name: str,
    brand_tagline: str,
    index_name: str,
    index_short: str,
    currency: str,
    organization: Any,
    department: Any,
    assessment: Any,
    result: dict[str, Any],
    pillar_labels: dict[str, str] | None = None,
    comparison_rows: list[dict] | None = None,
) -> bytes:
    """Return a complete board-pack PDF as bytes."""
    styles = _styles()
    pillar_labels = pillar_labels or {}
    org_name = getattr(organization, "name", None) or "Organisation"
    dept_name = getattr(department, "name", None) or "Organisation-wide"
    fin = result.get("financial") or {}
    fx = fin.get("assumptions") or {}

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"{index_name} — {org_name}",
        author=brand_name,
    )
    story = []

    score = result.get("readiness_index") or 0
    band = result.get("maturity_band") or "—"
    cover_top = Table([
        [Paragraph(brand_name, styles["brand"]),
         Paragraph(f"<font size=\"22\"><b>{score:.1f}</b></font><br/>{band}", styles["score"])],
    ], colWidths=[110 * mm, 60 * mm])
    cover_top.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(cover_top)
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT, spaceAfter=8))
    story.append(Paragraph("EXECUTIVE BOARD PACK", styles["doc"]))
    story.append(Paragraph(index_name, styles["h1"]))
    story.append(Paragraph(f"<b>{org_name}</b> · {dept_name}", styles["body"]))
    meta = []
    if getattr(assessment, "respondent", None):
        meta.append(str(assessment.respondent))
    if getattr(assessment, "completed_at", None):
        meta.append(str(assessment.completed_at))
    if meta:
        story.append(Paragraph(" · ".join(meta), styles["muted"]))

    kpi_data = [[
        Paragraph(f"<font color='#6b7280' size='7'>CONFIDENCE</font><br/>"
                  f"<b>{(result.get('confidence_index') or 0):.1f}</b><br/>"
                  f"<font size='7'>{result.get('confidence_band') or ''}</font>", styles["body"]),
        Paragraph(f"<font color='#6b7280' size='7'>ANNUAL SAVINGS</font><br/>"
                  f"<b>{_money(fin.get('annual_savings'), currency)}</b><br/>"
                  f"<font size='7'>Management estimate</font>", styles["body"]),
        Paragraph(f"<font color='#6b7280' size='7'>PAYBACK</font><br/>"
                  f"<b>{(fin.get('payback_months') or 0):.1f} months</b><br/>"
                  f"<font size='7'>ROI {(fin.get('roi') or 0):.0f}%</font>", styles["body"]),
    ]]
    kpi_t = Table(kpi_data, colWidths=[56 * mm, 56 * mm, 56 * mm])
    kpi_t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
        ("BACKGROUND", (0, 0), (-1, -1), SOFT),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(Spacer(1, 8))
    story.append(kpi_t)
    story.append(PageBreak())

    story.append(Paragraph("1. Executive narrative", styles["h2"]))
    story.append(Paragraph(
        f"This assessment evaluated <b>{org_name}</b> ({dept_name}) across seven weighted "
        f"intelligence pillars. The resulting {index_short} of <b>{score:.1f}</b> places the unit "
        f"in the <b>{band}</b> band. Annual savings potential is estimated at "
        f"<b>{_money(fin.get('annual_savings'), currency)}</b> against indicative investment of "
        f"{_money(fin.get('investment'), currency)} "
        f"(payback {(fin.get('payback_months') or 0):.1f} months).",
        styles["body"]))
    tops = result.get("top_opportunities") or []
    if tops:
        story.append(Paragraph("Headline opportunities", styles["h3"]))
        for i, o in enumerate(tops[:5], 1):
            story.append(Paragraph(f"{i}. {o}", styles["body"]))

    story.append(Paragraph("2. Intelligence pillars", styles["h2"]))
    prow = []
    for code, sc in (result.get("pillars") or {}).items():
        label = pillar_labels.get(code, code)
        reading = ("Critical" if sc < 25 else "Weak" if sc < 40 else
                   "Developing" if sc < 55 else "Solid" if sc < 70 else "Strength")
        prow.append([label, f"{sc:.1f}", reading])
    if prow:
        story.append(_table(["Pillar", "Score", "Reading"], prow,
                            col_widths=[80 * mm, 25 * mm, 55 * mm]))

    pains = result.get("pain_points") or []
    if pains:
        story.append(Paragraph("3. Material pain points", styles["h2"]))
        prows = [[p.get("severity", ""), p.get("title", ""),
                  f"{(p.get('impact') or 0):.0f}%", (p.get("detail") or "")[:120]]
                 for p in pains[:12]]
        story.append(_table(["Severity", "Finding", "Impact", "Detail"], prows,
                            col_widths=[22 * mm, 45 * mm, 18 * mm, 75 * mm]))

    story.append(PageBreak())
    story.append(Paragraph("4. Implementation roadmap", styles["h2"]))
    for phase in (result.get("roadmap") or []):
        story.append(Paragraph(
            f"{phase.get('label', '')} · {phase.get('horizon', '')}", styles["h3"]))
        note = phase.get("note") or ""
        if note:
            story.append(Paragraph(note, styles["muted"]))
        items = phase.get("items") or []
        if items:
            rrows = [[f"{(r.get('priority') or 0):.0f}", r.get("title", ""),
                      r.get("technology") or "—", f"{(r.get('roi') or 0):.0f}%"]
                     for r in items[:8]]
            story.append(_table(["Pri", "Recommendation", "Technology", "ROI"], rrows,
                                col_widths=[12 * mm, 90 * mm, 40 * mm, 18 * mm]))

    story.append(Paragraph("5. Financial impact — deep dive", styles["h2"]))
    story.append(Paragraph(
        f"Friction cost is modelled from labour exposure and process drag signals. "
        f"Current annual friction is estimated at <b>{_money(fin.get('current_cost'), currency)}</b>; "
        f"post-intervention at {_money(fin.get('future_cost'), currency)}. "
        f"The gap — <b>{_money(fin.get('annual_savings'), currency)}</b> — is an upper bound "
        f"for prioritisation. A savings ceiling "
        f"({(fx.get('max_savings_share') or 0)*100:.0f}% of labour line) keeps estimates board-credible.",
        styles["body"]))
    frows = [
        ["Current annual friction cost", _money(fin.get("current_cost"), currency)],
        ["Projected cost (post-intervention)", _money(fin.get("future_cost"), currency)],
        ["Annual savings potential", _money(fin.get("annual_savings"), currency)],
        ["Indicative investment", _money(fin.get("investment"), currency)],
        ["Return on investment", f"{(fin.get('roi') or 0):.1f}%"],
        ["Payback period", f"{(fin.get('payback_months') or 0):.1f} months"],
    ]
    if fx:
        frows += [
            ["Staff in scope", str(fx.get("staff", "—"))],
            ["Blended hourly rate", f"{currency} {(fx.get('hourly_rate') or 0):.0f}"],
            ["Labour line (annual)", _money(fx.get("labour_line"), currency)],
            ["Hours freed / year (modelled)", str(fx.get("hours_freed", "—"))],
        ]
    story.append(_table(["Metric", "Value"], frows, col_widths=[100 * mm, 60 * mm]))
    story.append(Paragraph(
        "Leadership action: validate the top three opportunities with process owners, "
        "fund Horizon-1 quick wins from operational budgets, and re-run after 90 days.",
        styles["body"]))

    if comparison_rows:
        story.append(Paragraph("6. Department comparison", styles["h2"]))
        story.append(Paragraph(
            "Relative readiness across units highlights where investment should concentrate first.",
            styles["body"]))
        crows = [[r.get("department", "—"),
                  f"{(r.get('readiness_index') or 0):.1f}",
                  r.get("maturity_band") or "—",
                  r.get("respondent") or "—"]
                 for r in comparison_rows[:12]]
        story.append(_table(["Department", "Index", "Band", "Respondent"], crows,
                            col_widths=[55 * mm, 25 * mm, 35 * mm, 45 * mm]))

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=LINE, spaceAfter=6))
    story.append(Paragraph(
        f"<b>{brand_name}</b> — {brand_tagline}. Management decision-support only; "
        f"figures are estimates, not audited results. Confidential.",
        styles["footer"]))

    doc.build(story)
    return buf.getvalue()
