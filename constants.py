"""Elipsis brand, framework & identifier constants.

Single source of truth for every public-facing name, code identifier and
derived-metric definition. Renaming the brand should require editing this
file only.

Metric formulas are stored as small declarative strings and evaluated by the
restricted interpreter in ``readiness.py``. Keeping them here means the whole
measurement model is auditable in one place.
"""

# --- Brand ----------------------------------------------------------------
BRAND_NAME = "Elipsis"
BRAND_SHORT = "ELIPSIS"
BRAND_TAGLINE = "Turning operational flow into business power."
BRAND_MARK = "\u22ef"  # the ellipsis glyph
FRAMEWORK_NAME = "Elipsis Transformation Framework"
ASSESSMENT_NAME = "Elipsis Transformation Assessment"

# --- Flagship metric ------------------------------------------------------
# NOTE: the neutral field name below is used in the database and API so a
# future rebrand never requires a schema change.
INDEX_NAME = "Elipsis Index"
INDEX_SHORT = "Elipsis Score"
INDEX_CODE = "readiness_index"

# --- Companion metrics ----------------------------------------------------
CONFIDENCE_NAME = "Elipsis Confidence Index"
EVIDENCE_NAME = "Elipsis Evidence Strength Scale"
MATURITY_NAME = "Elipsis Maturity Scale"

REPORT_HEADER = "ELIPSIS \u2014 BUSINESS TRANSFORMATION ASSESSMENT"

# --- Assessment instrumentation -------------------------------------------
QUESTIONNAIRE_CODE = "ORG-001"  # generalised: no longer finance-only
QUESTIONNAIRE_NAME = "Elipsis Organisation Readiness Assessment"
QUESTIONNAIRE_VERSION = "2.0"
CURRENCY = "KES"
DEFAULT_HOURLY_RATE = 500  # KES/hour, per the Elipsis financial impact model

# --- Maturity scale (0-100) -----------------------------------------------
# Bands are contiguous half-open ranges: (low, high_exclusive). An earlier
# version used inclusive integer bounds, which left a gap where a fractional
# score such as 20.36 matched no band at all.
MATURITY_BANDS = (
    (0, 21, "Foundational"),
    (21, 41, "Emerging"),
    (41, 61, "Developing"),
    (61, 81, "Transformation Ready"),
    (81, 101, "Intelligent Enterprise Ready"),
)


def maturity_band(score: float) -> str:
    """Return the Elipsis maturity band label for a 0-100 score."""
    try:
        score = float(score)
    except (TypeError, ValueError):
        return "Unknown"
    for low, high, label in MATURITY_BANDS:
        if low <= score < high:
            return label
    return "Unknown"


# --- The seven intelligence pillars ---------------------------------------
# Weights drive the Overall Elipsis Index. Automation Readiness carries the
# highest weight: it is the platform's core mission.
# (code, label, weight, core objective)
PILLARS = (
    ("OEI", "Operational Efficiency Intelligence", 0.20,
     "Determine how work actually flows and where friction, waste and human "
     "dependency sit."),
    ("ARI", "Automation Readiness Intelligence", 0.25,
     "Identify what can be automated immediately versus later, and at what return."),
    ("DMI", "Digital Maturity Intelligence", 0.15,
     "Determine how digitally evolved the organisation actually is."),
    ("DII", "Data Intelligence & Analytics", 0.15,
     "Determine whether decisions rest on facts or on assumptions."),
    ("AIR", "AI Readiness Intelligence", 0.10,
     "Determine whether AI can create measurable business value."),
    ("TII", "Technology & Integration Infrastructure", 0.05,
     "Assess whether the technology environment can host automation at all."),
    ("SSI", "Strategic Scalability Intelligence", 0.10,
     "Determine whether the business can grow without operational collapse."),
)
PILLAR_LABELS = {code: label for code, label, _, _ in PILLARS}
PILLAR_OBJECTIVES = {code: obj for code, _, _, obj in PILLARS}
PILLAR_WEIGHTS = {code: weight for code, _, weight, _ in PILLARS}


# --- Subdomains: three per pillar, twenty-one in total -------------------
# (code, pillar, label, what it measures)
SUBDOMAINS = (
    ("OPS", "OEI", "Process Standardisation",
     "SOP availability, process consistency, documentation, ownership"),
    ("WFL", "OEI", "Workflow Efficiency",
     "Workflow steps, approval layers, waiting times, handoffs"),
    ("RSU", "OEI", "Resource Utilisation",
     "Employee utilisation, overtime dependency, capacity usage"),
    ("REP", "ARI", "Repetition Analysis",
     "Task frequency, time regularity, single-employee involvement"),
    ("RUL", "ARI", "Rule-Based Decision Analysis",
     "Fixed decisions, conditional processes, exception rates"),
    ("MAN", "ARI", "Manual Effort Analysis",
     "Data entry, copy-pasting, reporting, follow-ups"),
    ("ADO", "DMI", "Technology Adoption",
     "Software usage, cloud usage, system dependency"),
    ("DWF", "DMI", "Digital Workflow Adoption",
     "Paper usage, email dependency, spreadsheet dependency"),
    ("INM", "DMI", "Integration Maturity",
     "Connected systems, data synchronisation, integration depth"),
    ("COL", "DII", "Data Collection",
     "Collection consistency, collection method, ownership"),
    ("DQU", "DII", "Data Quality",
     "Missing data, duplicate data, errors"),
    ("RPM", "DII", "Reporting Maturity",
     "KPI tracking, dashboard usage, decision reporting"),
    ("CSV", "AIR", "Customer Service Assessment",
     "Inquiry volume, FAQ coverage, ticket volume"),
    ("KMA", "AIR", "Knowledge Management",
     "SOP repositories, documentation quality, retrieval speed"),
    ("PRD", "AIR", "Predictive Opportunity",
     "Forecasting needs, demand planning, sales forecasting"),
    ("ECO", "TII", "Software Ecosystem",
     "ERP, CRM, POS, accounting and operations systems"),
    ("INC", "TII", "Integration Capability",
     "APIs available, database accessibility, integration limits"),
    ("SEC", "TII", "Security Readiness",
     "Access control, backups, governance"),
    ("SCA", "SSI", "Scalability Assessment",
     "Linear staffing growth, capacity limits, operational resilience"),
    ("KPD", "SSI", "Key Person Dependency",
     "Knowledge concentration, decision concentration, succession cover"),
    ("GCA", "SSI", "Growth Constraint Analysis",
     "Operational, technology and process blockers to growth"),
)
SUBDOMAIN_LABELS = {code: label for code, _, label, _ in SUBDOMAINS}
SUBDOMAIN_PILLAR = {code: pillar for code, pillar, _, _ in SUBDOMAINS}
SUBDOMAIN_MEASURES = {code: measures for code, _, _, measures in SUBDOMAINS}


# --- Executive metrics (thirty-six derived indicators) --------------------
# Each metric is (code, pillar, label, kind, formula, reading).
#
#   kind    "score" -> higher is better, "risk" -> higher is worse.
#   formula a small declarative expression over subdomain codes, pillar codes
#           and individual question codes (see METRIC_HELPERS in readiness.py).
#   reading a one-line interpretation for the report.
#
# Every formula resolves only names declared in this file; readiness.py
# validates them at import time so a typo fails loudly rather than silently.
METRICS = (
    # --- Pillar 1: Operational Efficiency Intelligence ----------------------
    ("PES", "OEI", "Process Efficiency Score", "score",
     "avg(OPS, WFL)",
     "How efficiently work is documented and sequenced."),
    ("WFI", "OEI", "Workflow Friction Index", "risk",
     "invert(WFL)",
     "Step count, approvals and waiting time in the operating flow."),
    ("ACS", "OEI", "Approval Complexity Score", "risk",
     "invert(blend(Q05, Q04, 0.6, 0.4))",
     "How many layers and steps a routine transaction must clear."),
    ("OWI", "OEI", "Operational Waste Index", "risk",
     "invert(blend(RSU, avg(Q06, Q07), 0.5, 0.5))",
     "Idle capacity, overtime and elapsed time paid for but not worked."),
    ("HDR", "OEI", "Human Dependency Ratio", "risk",
     "invert(blend(avg(Q03, Q12), KPD, 0.5, 0.5))",
     "How much of the operation only works because a person knows how."),
    # --- Pillar 2: Automation Readiness Intelligence -----------------------
    ("RPI", "ARI", "Repetition Index", "score",
     "REP",
     "How much of the work is frequent, regular and single-owner."),
    ("ACMS", "ARI", "Automation Compatibility Score", "score",
     "blend(REP, RUL, 0.5, 0.5)",
     "Whether the work follows rules a machine could follow."),
    ("MBS", "ARI", "Manual Burden Score", "risk",
     "invert(MAN)",
     "Entry, copying, reporting and chasing done by hand."),
    ("AOI", "ARI", "Automation Opportunity Index", "score",
     "blend(avg(REP, RUL), invert(MAN), 0.6, 0.4)",
     "Combined size of the automatable workload."),
    ("AUI", "ARI", "Automation Urgency Index", "score",
     "blend(AOI, invert(ARI), 0.5, 0.5)",
     "Opportunity forgone because readiness is still low."),
    ("QWP", "ARI", "Quick-Win Potential", "score",
     "mix(AOI, invert(MAN), avg(Q16, Q18))",
     "High-value work that can be automated without a rebuild."),
    ("EAR", "ARI", "Estimated Automation ROI", "score",
     "mix(ACMS, AOI, invert(MAN))",
     "Return signal behind the modelled savings in section 6."),
    # --- Pillar 3: Digital Maturity Intelligence ---------------------------
    ("DMS", "DMI", "Digital Maturity Score", "score",
     "mix(ADO, DWF, INM)",
     "Software adoption, workflow digitisation and integration depth."),
    ("SUS", "DMI", "Software Utilization Score", "score",
     "ADO",
     "How widely the software already in place is actually used."),
    ("SDI", "DMI", "Spreadsheet Dependency Index", "risk",
     "invert(Q24)",
     "Where a spreadsheet is still the system of record."),
    ("PRI", "DMI", "Paper Reliance Index", "risk",
     "invert(Q22)",
     "Work that still begins or ends on paper."),
    ("DTX", "DMI", "Digital Transformation Readiness", "score",
     "mix(DMI, INM)",
     "Whether the digital base can carry further change."),
)
METRICS += (
    # --- Pillar 4: Data Intelligence & Analytics ---------------------------
    ("DQS", "DII", "Data Quality Score", "score",
     "DQU",
     "Missing, duplicated and erroneous data in operational records."),
    ("AMS", "DII", "Analytics Maturity Score", "score",
     "RPM",
     "KPI discipline, dashboards and decision reporting."),
    ("RES", "DII", "Reporting Effectiveness Score", "score",
     "mix(RPM, DQU)",
     "Whether reports arrive trustworthy and on time."),
    ("DIS", "DII", "Decision Intelligence Score", "score",
     "mix(RPM, DQU, COL)",
     "How far decisions rest on facts rather than assumption."),
    ("DTI", "DII", "Data Trust Index", "score",
     "mix(DQU, COL)",
     "Confidence leadership places in the numbers."),
    # --- Pillar 5: AI Readiness Intelligence -------------------------------
    ("ARS", "AIR", "AI Readiness Score", "score",
     "mix(CSV, KMA, PRD)",
     "Whether the organisation can absorb AI at all."),
    ("GAOI", "AIR", "Generative AI Opportunity Index", "score",
     "mix(KMA, CSV)",
     "Scope for generative AI in support and knowledge work."),
    ("PAOI", "AIR", "Predictive AI Opportunity Index", "score",
     "PRD",
     "Scope for forecasting and predictive work."),
    ("KAS", "AIR", "Knowledge Automation Score", "score",
     "KMA",
     "Whether institutional knowledge is captured and retrievable."),
    ("AVP", "AIR", "AI Value Potential", "score",
     "mix(ARS, PRD, KMA)",
     "Combined value at stake from applying AI well."),
    # --- Pillar 6: Technology & Integration Infrastructure -----------------
    ("TRS", "TII", "Technology Readiness Score", "score",
     "ECO",
     "Whether the software estate can host new capability."),
    ("ICI", "TII", "Integration Complexity Index", "risk",
     "invert(INC)",
     "How hard systems are to connect and data to move."),
    ("SRS", "TII", "Security Readiness Score", "score",
     "SEC",
     "Access control, recovery and governance strength."),
    ("ADR", "TII", "Automation Deployment Readiness", "score",
     "mix(ECO, SEC, INM)",
     "Whether an automation project could actually be landed."),
    # --- Pillar 7: Strategic Scalability Intelligence ----------------------
    ("SCS", "SSI", "Scalability Score", "score",
     "SCA",
     "Whether growth requires proportional headcount."),
    ("GCI", "SSI", "Growth Constraint Index", "risk",
     "invert(GCA)",
     "Blockers that will slow the next stage of growth."),
    ("KPR", "SSI", "Key Person Risk Score", "risk",
     "invert(KPD)",
     "Concentration of knowledge and decisions in few people."),
    ("ORS", "SSI", "Organizational Resilience Score", "score",
     "mix(SCA, SEC)",
     "Ability to absorb shock without operational failure."),
    ("FRI", "SSI", "Future Readiness Index", "score",
     "mix(SCA, KPD, GCA)",
     "Combined outlook for scaling the organisation."),
)

METRIC_LABELS = {code: label for code, _, label, _, _, _ in METRICS}
METRIC_KINDS = {code: kind for code, _, _, kind, _, _ in METRICS}
METRIC_PILLAR = {code: pillar for code, pillar, _, _, _, _ in METRICS}
METRIC_FORMULAS = {code: formula for code, _, _, _, formula, _ in METRICS}
METRIC_READINGS = {code: reading for code, _, _, _, _, reading in METRICS}
METRICS_BY_PILLAR = {code: [m for m in METRICS if m[1] == code]
                     for code in PILLAR_LABELS}

# --- Implementation phases ------------------------------------------------
# The three-phase roadmap the platform recommends.
PHASES = (
    (1, "Phase 1 \u2014 Quick Wins", "0-90 days",
     "Low-complexity automation on repetitive work: fast payback, no rebuild."),
    (2, "Phase 2 \u2014 Process Automation", "3-12 months",
     "Structural change to the flow: approvals, integrations and controls."),
    (3, "Phase 3 \u2014 AI Enablement", "12-24 months",
     "Predictive and generative AI on top of a cleaned, integrated base."),
)
PHASE_LABELS = {num: label for num, label, _, _ in PHASES}
PHASE_HORIZONS = {num: horizon for num, _, horizon, _ in PHASES}
PHASE_NOTES = {num: note for num, _, _, note in PHASES}

# --- Evidence strength multipliers ----------------------------------------
EVIDENCE_MULTIPLIERS = {
    "none": 0.70,
    "document": 0.85,
    "verified": 1.00,
    "multi": 1.10,
}
EVIDENCE_LABELS = {
    "none": "No evidence",
    "document": "Supporting document",
    "verified": "Verified documentation",
    "multi": "Multi-source verification",
}

# --- The answer scale (identical for every question) ----------------------
# One scale, used everywhere, in plain language. A respondent should be able
# to fill the whole form without reading instructions.
#
# (score, emoji, short label, plain explanation)
ANSWER_SCALE = (
    (0, "⛔", "Never",
     "We never do this."),
    (1, "🔴", "Hardly ever",
     "We do this very rarely, and only by hand."),
    (2, "🟠", "Sometimes",
     "We do this some of the time, but not always."),
    (3, "🟡", "Often",
     "We do this most of the time."),
    (4, "🟢", "Almost always",
     "We do this nearly every time."),
    (5, "⭐", "Always, and it runs itself",
     "We do this every time, and it happens automatically."),
)

ANSWER_EMOJI = {score: emoji for score, emoji, _, _ in ANSWER_SCALE}
ANSWER_LABELS = {score: label for score, _, label, _ in ANSWER_SCALE}
ANSWER_HELP = {score: help_text for score, _, _, help_text in ANSWER_SCALE}
MAX_SCORE = 5

# Retained under the old names so existing templates and the bot keep working.
MATURITY_ANSWER_LABELS = ANSWER_LABELS
MATURITY_ANSWER_HINTS = ANSWER_HELP


# --- Presentation helpers ------------------------------------------------
# One icon per pillar, used across the dashboard, the form and the report so a
# respondent can recognise a section without reading it.
PILLAR_ICONS = {
    "OEI": "⚙️",    # gear - how work flows
    "ARI": "🤖",    # robot - what can be automated
    "DMI": "💻",    # laptop - digital maturity
    "DII": "📊",    # bar chart - data intelligence
    "AIR": "🧠",    # brain - AI readiness
    "TII": "🔌",    # plug - technology & integration
    "SSI": "📈",    # chart up - scalability
}

SUBDOMAIN_ICONS = {
    "OPS": "📝", "WFL": "🔀", "RSU": "👥",
    "REP": "🔁", "RUL": "⚖️", "MAN": "⌨️",
    "ADO": "🖥️", "DWF": "🗂️", "INM": "🔗",
    "COL": "🧺", "DQU": "🧹", "RPM": "📈",
    "CSV": "🎧", "KMA": "📚", "PRD": "🔮",
    "ECO": "🧰", "INC": "🔌", "SEC": "🛡️",
    "SCA": "📶", "KPD": "👤", "GCA": "🧱",
}

METRIC_ICONS = {
    "PES": "⚙️", "WFI": "🔀", "ACS": "✋", "OWI": "🗑️", "HDR": "🧑",
    "RPI": "🔁", "ACMS": "🤖", "MBS": "⌨️", "AOI": "🎯", "AUI": "⏱️",
    "QWP": "⚡", "EAR": "💰",
    "DMS": "💻", "SUS": "🖥️", "SDI": "📗", "PRI": "📄", "DTX": "🚀",
    "DQS": "🧹", "AMS": "📊", "RES": "📑", "DIS": "🧠", "DTI": "🔍",
    "ARS": "🤖", "GAOI": "✍️", "PAOI": "🔮", "KAS": "📚", "AVP": "💡",
    "TRS": "🧰", "ICI": "🔗", "SRS": "🛡️", "ADR": "🚀",
    "SCS": "📶", "GCI": "🧱", "KPR": "👤", "ORS": "💪", "FRI": "🔭",
}

# Short, jargon-free prompts shown at the top of each pillar during the form.
PILLAR_PLAIN = {
    "OEI": "How well does work actually flow through your business?",
    "ARI": "What can a machine or a robot do for you instead of a person?",
    "DMI": "How far along is your business with computers and digital tools?",
    "DII": "Do you make decisions using real facts, or using guesses?",
    "AIR": "Could artificial intelligence (AI) create real value for you?",
    "TII": "Can your current technology even support automation?",
    "SSI": "Can your business grow without falling apart?",
}
