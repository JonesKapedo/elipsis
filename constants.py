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

# --- Answer scales, one per question type --------------------------------
# A single "Never -> Always" ladder is wrong for questions that ask about
# counts, speed or volume, and it inverts the meaning of risk questions
# ("Always copying and pasting" is bad). So each question carries a `scale`
# key naming a scale built for what it asks.
#
# INVARIANT, relied on by the scoring engine: **the highest-scoring option of
# every scale always means "most ready"**. Authoring reverses the ladder for
# "less is better" questions, so no formula or metric needs to know the
# polarity. `tests/test_questions.py::test_scales_ascend_toward_ready` enforces
# this.
#
# Each option is (score, emoji, label, plain explanation).
def _s(*options):
    """Build a scale, auto-numbering the scores 0..n-1 in listed order."""
    return tuple((i, emoji, label, help_text)
                 for i, (emoji, label, help_text) in enumerate(options))


SCALES = {
    # --- documentation & ownership -----------------------------------------
    "coverage_more": _s(
        ("❌", "None of it", "Nothing is written down."),
        ("🔸", "Only a little", "A small part is written down."),
        ("🟠", "About half", "About half is written down."),
        ("🟡", "Most of it", "Most of it is written down."),
        ("🟢", "Nearly all", "Nearly all of it is written down."),
        ("⭐", "All of it, kept current", "All of it is written down and kept up to date."),
    ),
    "consistency_more": _s(
        ("🔴", "Different everywhere", "Every team does it their own way."),
        ("🟠", "Mostly different", "Most teams differ from each other."),
        ("🟡", "Mixed", "Some teams match, some do not."),
        ("🟢", "Mostly the same", "Nearly every team works the same way."),
        ("🔵", "Almost the same", "The same everywhere, with rare exceptions."),
        ("⭐", "Exactly the same", "Exactly the same way, every time."),
    ),
    "ownership_more": _s(
        ("❌", "Nobody", "Nobody knows who is responsible."),
        ("🔸", "It is vague", "It is not clear who is responsible."),
        ("🟠", "Some jobs", "Some jobs have an owner."),
        ("🟡", "Most jobs", "Most jobs have an owner."),
        ("🟢", "Every main job", "Every main job has a named owner."),
        ("⭐", "Owner who checks", "Every job has an owner who checks it regularly."),
    ),

    # --- workflow shape ----------------------------------------------------
    "stepcount": _s(
        ("🔴", "More than 10 steps", "It takes more than ten separate steps."),
        ("🟠", "6 to 10 steps", "It takes six to ten steps."),
        ("🟡", "4 or 5 steps", "It takes four or five steps."),
        ("🟢", "About 3 steps", "It takes about three steps."),
        ("🔵", "About 2 steps", "It takes about two steps."),
        ("⭐", "One step", "One step, start to finish."),
    ),
    "approvals": _s(
        ("🔴", "Five or more people", "Five or more people must approve it."),
        ("🟠", "Three or four people", "Three or four people must approve it."),
        ("🟡", "Two people", "Two people must approve it."),
        ("🟢", "One manager", "Only one manager approves it."),
        ("🔵", "Often not at all", "Often no approval is needed."),
        ("⭐", "Never needs approval", "It never needs approval, it just runs."),
    ),
    "waiting_less": _s(
        ("🔴", "Almost all waiting", "Nearly all the time is spent waiting."),
        ("🟠", "Most of it waiting", "Most of the time is spent waiting."),
        ("🟡", "Half waiting", "Waiting and working are about equal."),
        ("🟢", "A small wait", "Waiting is a small part of the time."),
        ("🔵", "Rarely any wait", "Waiting is rare."),
        ("⭐", "No waiting", "There is virtually no waiting."),
    ),

    # --- people & capacity -------------------------------------------------
    "idletime_less": _s(
        ("🔴", "All the time", "People sit idle with nothing to do almost all the time."),
        ("🟠", "Most days", "People are idle on most working days."),
        ("🟡", "Most weeks", "People are idle on most weeks."),
        ("🟢", "Occasionally", "People are idle from time to time."),
        ("🔵", "Rarely", "People are rarely idle."),
        ("⭐", "Practically never", "There is practically no idle time."),
    ),
    "overtime_less": _s(
        ("🔴", "Every week", "Extra hours are needed every week."),
        ("🟠", "Most weeks", "Extra hours are needed most weeks."),
        ("🟡", "Most months", "Extra hours are needed most months."),
        ("🟢", "A few times a year", "Extra hours are needed a few times a year."),
        ("🔵", "Very rarely", "Extra hours are very rarely needed."),
        ("⭐", "Never", "Normal hours are always enough."),
    ),
    "balance_more": _s(
        ("🔴", "Always overloaded", "One team is always overloaded while another has nothing."),
        ("🟠", "Most months", "This imbalance happens most months."),
        ("🟡", "A few times a year", "This imbalance happens a few times a year."),
        ("🟢", "Occasionally", "It happens occasionally."),
        ("🔵", "Mostly fair", "Work is mostly shared fairly."),
        ("⭐", "Always fair", "Work is always shared fairly."),
    ),

    # --- automation opportunity -------------------------------------------
    "repetition": _s(
        ("❌", "Never repeats", "Every job is different, nothing repeats."),
        ("🔸", "Rarely repeats", "Work very rarely repeats."),
        ("🟠", "A few times a month", "Work repeats a few times a month."),
        ("🟡", "Most days", "Work repeats on most days."),
        ("🟢", "Many times a day", "Work repeats many times a day."),
        ("⭐", "All day, every day", "The same work repeats all day, every day."),
    ),
    "schedule_more": _s(
        ("🔴", "Comes whenever", "It comes whenever it comes."),
        ("🟠", "Rarely the same", "It is rarely the same time."),
        ("🟡", "Sometimes regular", "It is regular from time to time."),
        ("🟢", "Mostly scheduled", "It mostly happens on a schedule."),
        ("🔵", "Nearly always", "It nearly always happens on a schedule."),
        ("⭐", "Fixed schedule", "Exactly on a set schedule, every time."),
    ),
    "cover_less": _s(
        ("🔴", "Work stops", "The work stops completely if that person is away."),
        ("🟠", "Stops mostly", "Most of the work stops if that person is away."),
        ("🟡", "Someone finishes part", "Someone else can finish part of it."),
        ("🟢", "Someone finishes most", "Someone else can finish most of it."),
        ("🔵", "Someone finishes all", "Someone else can finish all of it."),
        ("⭐", "Anyone can do it", "Anyone who is trained can do it."),
    ),
    "rules_more": _s(
        ("❌", "Decided by feel", "Nothing is written down; people decide by feel."),
        ("🔸", "Very few written", "Very few rules are written down."),
        ("🟠", "Some written", "Some rules are written down."),
        ("🟡", "Most written", "Most decisions follow written rules."),
        ("🟢", "Nearly all written", "Nearly all decisions follow written rules."),
        ("⭐", "Every rule written", "Every decision follows a written rule."),
    ),
    "conditions_more": _s(
        ("❌", "Chosen by feel", "People choose by feel; the conditions are not written."),
        ("🔸", "Hardly ever", "The conditions are hardly ever written."),
        ("🟠", "Sometimes", "The conditions are sometimes written."),
        ("🟡", "Mostly", "The conditions are mostly written down."),
        ("🟢", "Nearly always", "The conditions are nearly always written."),
        ("⭐", "Always and clear", "The conditions are always written and clear."),
    ),
    "exception_less": _s(
        ("🔴", "Almost every time", "Something unexpected happens almost every time."),
        ("🟠", "Most of the time", "Something unexpected happens most of the time."),
        ("🟡", "Often", "Something unexpected happens often."),
        ("🟢", "Sometimes", "It happens from time to time."),
        ("🔵", "Rarely", "It happens rarely."),
        ("⭐", "Almost never", "It almost never happens."),
    ),

    # --- manual effort -----------------------------------------------------
    "effort_less": _s(
        ("🔴", "Nearly all day", "It takes up nearly the whole working day."),
        ("🟠", "Most of the day", "It takes up most of the working day."),
        ("🟡", "About half the day", "It takes up about half the day."),
        ("🟢", "A small part", "It takes up a small part of the day."),
        ("🔵", "Very little", "It takes up very little time."),
        ("⭐", "Almost none", "It happens on its own, automatically."),
    ),
    "copying_less": _s(
        ("🔴", "All day, every day", "Information is copied all day, every day."),
        ("🟠", "Most days", "Information is copied on most days."),
        ("🟡", "Most weeks", "Information is copied most weeks."),
        ("🟢", "Sometimes", "Information is copied from time to time."),
        ("🔵", "Rarely", "Information is rarely copied."),
        ("⭐", "Never", "Information moves between systems on its own."),
    ),

    # --- technology ----------------------------------------------------
    "software_count": _s(
        ("❌", "None at all", "Everything is done in Word and Excel."),
        ("🔸", "One area", "One part of the business has its own software."),
        ("🟠", "Two areas", "Two parts have their own software."),
        ("🟡", "About half", "About half the business has its own software."),
        ("🟢", "Most areas", "Most parts have their own software."),
        ("⭐", "Every area", "Every area that needs it has software built for it."),
    ),
    "share_more": _s(
        ("❌", "None", "None of it."),
        ("🔸", "A small part", "A small part of it."),
        ("🟠", "About a quarter", "About a quarter of it."),
        ("🟡", "About half", "About half of it."),
        ("🟢", "Most of it", "Most of it."),
        ("⭐", "All of it", "All of it."),
    ),
    "outage_less": _s(
        ("🔴", "Business stops", "The business stops completely."),
        ("🟠", "Most work stops", "Most of the work stops."),
        ("🟡", "Big parts stop", "Big parts of the business stop."),
        ("🟢", "A few areas held up", "A few areas are held up."),
        ("🔵", "Small delays only", "Only small delays."),
        ("⭐", "Nothing important stops", "Nothing important stops."),
    ),
    "paper_less": _s(
        ("🔴", "Almost all of it", "Almost all of it is still on paper."),
        ("🟠", "Most of it", "Most of it is still on paper."),
        ("🟡", "About half", "About half of it is still on paper."),
        ("🟢", "A small part", "A small part is still on paper."),
        ("🔵", "Very little", "Very little is still on paper."),
        ("⭐", "None", "Everything is on a computer."),
    ),
    "email_less": _s(
        ("🔴", "Almost everything", "Almost every decision goes through email."),
        ("🟠", "Most decisions", "Most decisions go through email."),
        ("🟡", "About half", "About half go through email."),
        ("🟢", "A small part", "A small part goes through email."),
        ("🔵", "Very little", "Very little goes through email."),
        ("⭐", "Almost none", "It happens inside the work systems instead."),
    ),
    "spreadsheet_less": _s(
        ("🔴", "For most jobs", "A spreadsheet is the official record for most jobs."),
        ("🟠", "For many jobs", "A spreadsheet is the official record for many jobs."),
        ("🟡", "For a few jobs", "A spreadsheet is the official record for a few jobs."),
        ("🟢", "One or two jobs", "A spreadsheet is the official record for one or two jobs."),
        ("🔵", "One small area", "Only one small area still uses a spreadsheet."),
        ("⭐", "Never", "Systems always hold the official record."),
    ),
    "integration_more": _s(
        ("❌", "Nothing talks", "No system passes anything to another."),
        ("🔸", "One pair", "One pair of systems is connected."),
        ("🟠", "A few pairs", "A few pairs of systems are connected."),
        ("🟡", "About half", "About half of the systems are connected."),
        ("🟢", "Most systems", "Most systems are connected."),
        ("⭐", "All that need to be", "Every pair that needs to is connected."),
    ),
    "blockers_less": _s(
        ("🔴", "Many", "Many known problems, and nothing connects."),
        ("🟠", "Several", "Several known problems."),
        ("🟡", "A few", "A few known problems."),
        ("🟢", "Some", "Some known problems."),
        ("🔵", "One or two", "Only one or two known problems."),
        ("⭐", "None known", "There are no known blockers we know of."),
    ),
    "ease_more": _s(
        ("❌", "Impossible today", "It is impossible today."),
        ("🔴", "Very hard", "It is very hard."),
        ("🟠", "Hard", "It is hard."),
        ("🟡", "Doable with help", "It is doable, with help."),
        ("🟢", "Fairly easy", "It is fairly easy."),
        ("⭐", "Easy and documented", "It is easy and written down."),
    ),
    "security_more": _s(
        ("🔴", "Anyone, never checked", "Anyone can get in and nobody checks."),
        ("🟠", "Nearly anyone", "Nearly anyone can get in."),
        ("🟡", "Many, rarely reviewed", "Many people can get in and it is rarely reviewed."),
        ("🟢", "Some control", "There is some control, reviewed now and then."),
        ("🔵", "Good control", "Good control, reviewed regularly."),
        ("⭐", "Strict and cleaned", "Strict control, reviewed and cleaned on a schedule."),
    ),
    "core_system_more": _s(
        ("❌", "Records are scattered", "The official records are scattered everywhere."),
        ("🔸", "Almost none in one place", "Almost nothing is in one place."),
        ("🟠", "Some records in one place", "Some records are in one place."),
        ("🟡", "Most records in one place", "Most records are in one place."),
        ("🟢", "Nearly all in one place", "Nearly all records are in one place."),
        ("⭐", "All in one system", "All official records are in one system."),
    ),

    # --- data ---
    "dataquality_less": _s(
        ("🔴", "Almost every record", "It happens on almost every record."),
        ("🟠", "Most records", "It happens on most records."),
        ("🟡", "Often", "It happens often."),
        ("🟢", "Sometimes", "It happens from time to time."),
        ("🔵", "Rarely", "It rarely happens."),
        ("⭐", "Almost never", "It almost never happens."),
    ),
    "tracking_more": _s(
        ("❌", "Not tracked", "Nothing is tracked."),
        ("🔸", "Loosely", "A little is tracked, loosely."),
        ("🟠", "A few", "A few things are tracked."),
        ("🟡", "Some properly", "Some things are tracked properly."),
        ("🟢", "Most properly", "Most things are tracked properly."),
        ("⭐", "The same way every time", "A small agreed set, tracked the same way every time."),
    ),

    # --- customer service & knowledge ---
    "volume_count": _s(
        ("❌", "None", "We get none."),
        ("🔸", "A few a week", "A few a week."),
        ("🟠", "About 10 a week", "About ten a week."),
        ("🟡", "About 30 a week", "About thirty a week."),
        ("🟢", "About 100 a week", "About a hundred a week."),
        ("⭐", "More than 100 a week", "More than a hundred a week."),
    ),
    "repeats_count": _s(
        ("❌", "None", "None of them are the same."),
        ("🔸", "1 or 2 out of 10", "One or two out of every ten."),
        ("🟠", "About 3 out of 10", "About three out of every ten."),
        ("🟡", "About 5 out of 10", "About five out of every ten."),
        ("🟢", "About 8 out of 10", "About eight out of every ten."),
        ("⭐", "All 10 out of 10", "All ten out of every ten are the same."),
    ),
    "knowledge_more": _s(
        ("❌", "In people's heads", "It is in people's heads; nothing is stored."),
        ("🔸", "Scattered everywhere", "It is scattered across many people's computers."),
        ("🟠", "Shared folders, untidy", "It sits in shared folders, untidy."),
        ("🟡", "One place, partly sorted", "One place, partly organised."),
        ("🟢", "One tidy place", "One organised place."),
        ("⭐", "One system everyone uses", "One system that everyone actually uses."),
    ),
    "speed_more": _s(
        ("❌", "They must ask someone", "They have to ask a person."),
        ("🔴", "Hours or days", "It takes hours or days."),
        ("🟠", "Most of a day", "It takes most of a day."),
        ("🟡", "A few minutes", "It takes a few minutes."),
        ("🟢", "Under a minute", "It takes under a minute."),
        ("⭐", "Straight away", "It is the first place they look; they find it straight away."),
    ),

    # --- planning ---
    "planning_more": _s(
        ("❌", "Does not plan", "The business does not plan ahead."),
        ("🔸", "A few weeks", "It plans a few weeks ahead."),
        ("🟠", "A few months", "It plans a few months ahead."),
        ("🟡", "Six months", "It plans about six months ahead."),
        ("🟢", "A year", "It plans about a year ahead."),
        ("⭐", "More than a year", "It plans more than a year ahead."),
    ),
    "growth_more": _s(
        ("🔴", "Always needs more staff", "Every increase needs more people."),
        ("🟠", "Nearly always", "Nearly every increase needs more people."),
        ("🟡", "About half", "About half of the growth needs new people."),
        ("🟢", "Most is absorbed", "Most of the growth is absorbed."),
        ("🔵", "Nearly all is absorbed", "Nearly all of the growth is absorbed."),
        ("⭐", "Absorbed fully", "Growth is absorbed without more people."),
    ),

    # --- people risk & growth blockers ---
    "keyperson_less": _s(
        ("🔴", "Business would stop", "The business would stop."),
        ("🟠", "Barely function", "It would barely function."),
        ("🟡", "It would limp on", "It would limp on."),
        ("🟢", "Cope with delays", "We would cope, with delays."),
        ("🔵", "Cope well", "We would cope well."),
        ("⭐", "Nothing affected", "Nothing important would be affected."),
    ),
    "concentration_less": _s(
        ("🔴", "Everything waits", "Everything waits for them."),
        ("🟠", "Almost everything", "Almost everything waits for them."),
        ("🟡", "Many decisions", "Many decisions wait for them."),
        ("🟢", "Some decisions", "Some decisions wait for them."),
        ("🔵", "Only a few", "Only a few decisions wait for them."),
        ("⭐", "Spread across the team", "Decisions are spread across the team."),
    ),
    "succession_more": _s(
        ("❌", "Nobody is trained", "Nobody is trained to cover."),
        ("🔸", "Almost nobody", "Almost nobody is trained to cover."),
        ("🟠", "A few jobs", "A few jobs have trained cover."),
        ("🟡", "Several jobs", "Several jobs have trained cover."),
        ("🟢", "Most important jobs", "Most important jobs have trained cover."),
        ("⭐", "All important jobs", "All important jobs have trained cover."),
    ),
    "blocker_less": _s(
        ("🔴", "Stops us completely", "It stops the business growing completely."),
        ("🟠", "Stops us a lot", "It stops the business growing a lot."),
        ("🟡", "Clearly holds us back", "It clearly holds us back."),
        ("🟢", "Slows us a little", "It slows us down a little."),
        ("🔵", "Hardly matters", "It hardly matters at all."),
        ("⭐", "Does not hold us back", "It does not hold us back at all."),
    ),
}

# --- Scales added so individual questions fit their own wording -----------
SCALES.update({
    "captured_more": _s(
        ("🔴", "Written down later", "It is written down later, from memory."),
        ("🟠", "Almost always later", "It is almost always written down later."),
        ("🟡", "Usually later", "It is usually written down later."),
        ("🟢", "Sometimes while working", "It is sometimes recorded while the work is done."),
        ("🔵", "Almost always while working", "It is almost always recorded while the work is done."),
        ("⭐", "Always, as part of the job", "It is always recorded as part of the job."),
    ),
    "kpi_more": _s(
        ("❌", "Not tracked at all", "No measures are tracked."),
        ("🔸", "Change all the time", "A few are tracked, but they change all the time."),
        ("🟠", "A few, loosely", "A few are tracked loosely."),
        ("🟡", "Some tracked properly", "Some measures are tracked properly."),
        ("🟢", "Most tracked properly", "Most measures are tracked properly."),
        ("⭐", "A small agreed set", "A small agreed set, tracked the same way every time."),
    ),
    "dashboard_more": _s(
        ("❌", "Everything must be requested", "Nothing is visible; everything must be asked for."),
        ("🔸", "One thing, rarely", "One thing is visible, and rarely."),
        ("🟠", "A few things, if asked", "A few things are visible, if you ask."),
        ("🟡", "Some things visible", "Some things are visible."),
        ("🟢", "Most things visible", "Most things are visible."),
        ("⭐", "Everything needed is live", "Everything needed is live on a screen."),
    ),
    "reliability_more": _s(
        ("🔴", "Rarely on time", "Reports rarely arrive when they should."),
        ("🟠", "Often late", "Reports are often late."),
        ("🟡", "Sometimes late", "Reports are sometimes late."),
        ("🟢", "Usually on time", "Reports usually arrive on time."),
        ("🔵", "Almost always on time", "Reports almost always arrive on time."),
        ("⭐", "Always on the agreed day", "Reports always arrive on the same agreed day."),
    ),
    "databased_more": _s(
        ("❌", "All opinion", "It is all opinion; no data is used."),
        ("🔴", "Almost all opinion", "It is almost all opinion."),
        ("🟠", "Mostly opinion", "It is mostly opinion."),
        ("🟡", "About half data", "About half of it comes from data."),
        ("🟢", "Mostly data", "Most of it comes from data."),
        ("⭐", "All data, checked", "It all comes from data, and is checked against reality."),
    ),
    "fit_more": _s(
        ("❌", "They get worked around", "People work around them because they do not fit."),
        ("🔴", "Almost none do", "Almost none of them actually do their job."),
        ("🟠", "A few do", "A few of them do their job."),
        ("🟡", "About half do", "About half of them do their job."),
        ("🟢", "Most do", "Most of them do their job."),
        ("⭐", "All of them", "All of them do the job they are meant to do."),
    ),
    "restore_more": _s(
        ("🔴", "No backups at all", "There are no backups at all."),
        ("🟠", "Never tested", "Backups exist but have never been tested."),
        ("🟡", "Tested long ago", "Backups exist; they were tested a long time ago."),
        ("🟢", "Tested once", "Backups exist and have been tested once."),
        ("🔵", "Tested regularly", "Backups are tested regularly."),
        ("⭐", "Tested, and fast", "Backups are tested and getting working again is fast."),
    ),
    "headroom_more": _s(
        ("🔴", "None, we are full", "We are already full."),
        ("🟠", "Almost none", "There is almost no room."),
        ("🟡", "A little", "We could take on a little more."),
        ("🟢", "About a quarter more", "We could take on about a quarter more work."),
        ("🔵", "About half again", "We could take on about half again as much work."),
        ("⭐", "Roughly double", "We could take on roughly double the work."),
    ),
})

MAX_SCORE = 5
SCALE_KEYS = tuple(SCALES)


def scale_options(key: str):
    """Return the option list for a scale key, or None if the key is unknown."""
    return SCALES.get(key)


def scale_ascends(key: str) -> bool:
    """True when a scale's options are ordered lowest-score first.

    Every scale satisfies this; the check exists so a future scale that
    accidentally reverses the ordering fails a test rather than silently
    inverting a metric.
    """
    options = SCALES.get(key) or ()
    return [o[0] for o in options] == sorted(o[0] for o in options)

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
