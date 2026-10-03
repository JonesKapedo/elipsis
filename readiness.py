"""Elipsis readiness engine — PURE computation, no database coupling.

Shared by every transport layer (today: FastAPI + SQLAlchemy, later a worker
or the Telegram bot). Because this module is pure it is trivially unit-testable
and impossible to duplicate accidentally.

Two ideas drive the design:

1. **Declarative metrics.** The thirty-six executive metrics are defined as
   small formula strings in ``constants.METRIC_FORMULAS``. They are evaluated
   here by a deliberately restricted AST interpreter: only names, numbers,
   arithmetic and whitelisted helper calls are permitted. A typo in a formula
   fails loudly at import time instead of quietly producing a wrong number.

2. **Honest directionality.** Each metric is tagged ``score`` (higher is
   better) or ``risk`` (higher is worse). Risk metrics are built with
   ``invert()`` so that, for example, a Workflow Friction Index of 70 means
   *worse*, and the UI can label it correctly.
"""

import ast

from constants import (
    DEFAULT_HOURLY_RATE,
    EVIDENCE_MULTIPLIERS,
    METRIC_FORMULAS,
    METRIC_KINDS,
    METRIC_LABELS,
    METRIC_PILLAR,
    METRIC_READINGS,
    METRICS,
    PILLAR_LABELS,
    PILLAR_WEIGHTS,
    PHASES,
    SUBDOMAIN_LABELS,
    SUBDOMAIN_PILLAR,
    maturity_band,
)

THRESHOLD = 2  # a question scoring at or below this raises its pain point


# --- Formula helpers ------------------------------------------------------
# `invert` flips a capability score into a risk reading. The others are
# aggregation shorthands so a formula reads like the sentence it encodes.
def _mean(*values):
    """Mean of every supplied value.

    Accepts either varargs (``avg(OPS, WFL)``) or a single iterable, so the
    helpers compose naturally inside larger formulas.
    """
    flat = []
    for value in values:
        if isinstance(value, (list, tuple)):
            flat.extend(v for v in value if v is not None)
        elif value is not None:
            flat.append(value)
    return sum(flat) / len(flat) if flat else 0.0


METRIC_HELPERS = {
    "avg": _mean,                          # average of the given scores
    "mix": _mean,                          # same as avg; reads better inline
    "min": lambda *a: min(a),              # narrowest signal in the group
    "max": lambda *a: max(a),              # strongest signal in the group
    "invert": lambda x: 100.0 - x,         # capability -> risk
    "blend": lambda a, b, wa, wb: (
        (a * wa + b * wb) / (wa + wb) if (wa + wb) else 0.0),
}

_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name, ast.Constant,
    ast.Load, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.UAdd,
)


def validate_formula(formula: str):
    """Parse and whitelist-check a formula. Raises ValueError if unsafe."""
    tree = ast.parse(formula, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(f"disallowed syntax {type(node).__name__} in {formula!r}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in METRIC_HELPERS:
                raise ValueError(f"disallowed call in {formula!r}")
            if node.keywords:
                raise ValueError(f"keyword arguments not allowed in {formula!r}")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            raise ValueError(f"non-numeric constant in {formula!r}")
    return tree


def _eval_node(node, resolve):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, resolve)
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.Name):
        return resolve(node.id)
    if isinstance(node, ast.UnaryOp):
        val = _eval_node(node.operand, resolve)
        return -val if isinstance(node.op, ast.USub) else val
    if isinstance(node, ast.BinOp):
        left, right = _eval_node(node.left, resolve), _eval_node(node.right, resolve)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right if right else 0.0
        if isinstance(node.op, ast.Pow):
            return left ** right
    if isinstance(node, ast.Call):
        args = [_eval_node(a, resolve) for a in node.args]
        return METRIC_HELPERS[node.func.id](*args)
    raise ValueError(f"cannot evaluate {type(node).__name__}")


class MetricEngine:
    """Resolves metric formulas against a live score table.

    Metrics may reference subdomains, pillars, individual questions *and*
    other metrics. References are resolved lazily with memoisation, so a
    metric that depends on another metric declared earlier or later both work;
    a genuine cycle is reported rather than recursed into.
    """

    def __init__(self, scores: dict, known_names=frozenset()):
        self.scores = scores
        # Question codes declared by the instrument but left unanswered score
        # zero rather than raising, so a partial assessment still computes.
        self.known_names = set(known_names)
        self._cache: dict = {}
        self._stack: list = []

    def resolve(self, name: str) -> float:
        if name in self._cache:
            return self._cache[name]
        if name in self.scores:
            self._cache[name] = self.scores[name]
            return self._cache[name]
        if name in self.known_names and name not in METRIC_FORMULAS:
            self._cache[name] = 0.0
            return 0.0
        if name in self._stack:
            raise ValueError(f"circular metric reference: {' -> '.join(self._stack + [name])}")
        value = self._eval_metric(name)
        self._cache[name] = value
        return value

    def _eval_metric(self, code: str) -> float:
        formula = METRIC_FORMULAS.get(code)
        if formula is None:
            raise ValueError(f"unknown metric or score reference: {code!r}")
        self._stack.append(code)
        try:
            tree = validate_formula(formula)
            raw = _eval_node(tree, self.resolve)
        finally:
            self._stack.pop()
        return max(0.0, min(100.0, raw))

    def all_metrics(self) -> dict:
        """Compute every declared metric, keyed by code.

        The resolution cache also holds subdomains, pillars and questions it
        touched on the way through, so the result is filtered back down to the
        metric codes themselves.
        """
        for code in METRIC_FORMULAS:
            self.resolve(code)
        return {code: self._cache[code] for code in METRIC_FORMULAS
                if code in self._cache}


def validate_metrics(question_codes) -> None:
    """Fail fast if any formula references a name we cannot resolve."""
    known = set(SUBDOMAIN_LABELS) | set(PILLAR_LABELS) | set(METRIC_FORMULAS) | set(question_codes)
    for code, formula in METRIC_FORMULAS.items():
        tree = validate_formula(formula)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id not in METRIC_HELPERS:
                if node.id not in known:
                    raise ValueError(f"metric {code} references unknown name {node.id!r}")


# --- Pain-point rule catalogue --------------------------------------------
# Keyed by trigger question code. Severity is the baseline; the realised
# severity scales with how far below THRESHOLD the answer fell.
#
# `phase` places the recommendation on the three-phase roadmap:
#   1 Quick Wins (0-90 days)        low-complexity, repetitive work
#   2 Process Automation (3-12mo)   structural change to the flow
#   3 AI Enablement (12-24mo)       predictive/generative AI on a clean base
PAIN_CATALOG = {
    # --- Pillar 1: Operational Efficiency --------------------------------
    "Q01": dict(title="Tribal Knowledge Risk", severity="High", phase=1,
                base_hours=28, share=0.1, investment=90000,
                solution="Document the core processes and stand up a searchable SOP library",
                technology="SOP / knowledge-base platform", complexity="Low"),
    "Q03": dict(title="Unowned Process Risk", severity="Medium", phase=1,
                base_hours=14, share=0.06, investment=60000,
                solution="Assign a named process owner and a review cadence for each core process",
                technology="Process register + governance rhythm", complexity="Low"),
    "Q05": dict(title="Approval Bottleneck", severity="Medium", phase=2,
                base_hours=16, share=0.08, investment=140000,
                solution="Collapse approval layers and route low-value requests automatically",
                technology="Workflow engine with approval rules", complexity="Medium"),
    "Q06": dict(title="Cycle-Time Drag", severity="High", phase=2,
                base_hours=24, share=0.12, investment=180000,
                solution="Re-engineer the flow to remove queue time between steps",
                technology="Process redesign + workflow automation", complexity="Medium"),
    "Q08": dict(title="Overtime Dependency", severity="Medium", phase=2,
                base_hours=20, share=0.1, investment=130000,
                solution="Rebalance capacity against measured demand to remove overtime",
                technology="Capacity planning + scheduling tool", complexity="Medium"),
    # --- Pillar 2: Automation Readiness ----------------------------------
    "Q10": dict(title="High-Frequency Repetitive Work", severity="High", phase=1,
                base_hours=45, share=0.15, investment=210000,
                solution="Automate the highest-frequency recurring tasks first",
                technology="RPA / workflow automation", complexity="Low"),
    "Q13": dict(title="Rule-Based Decision Backlog", severity="High", phase=1,
                base_hours=32, share=0.12, investment=190000,
                solution="Encode fixed decision rules into an automated decision service",
                technology="Rules engine / decision service", complexity="Medium"),
    "Q16": dict(title="Manual Data Entry Burden", severity="High", phase=1,
                base_hours=38, share=0.14, investment=175000,
                solution="Replace manual entry with capture at source and API transfer",
                technology="Form capture / OCR / API integration", complexity="Low"),
    "Q17": dict(title="Copy-Paste Dependency", severity="Critical", phase=1,
                base_hours=40, share=0.13, investment=195000,
                solution="Remove re-keying by connecting the systems directly",
                technology="API / iPaaS", complexity="Medium"),
    "Q18": dict(title="Manual Reporting & Chasing", severity="High", phase=1,
                base_hours=42, share=0.15, investment=160000,
                solution="Automate recurring reporting and exception chasing",
                technology="Reporting suite (BI / Metabase)", complexity="Low"),
    # --- Pillar 3: Digital Maturity -------------------------------------
    "Q22": dict(title="Paper Reliance", severity="Medium", phase=2,
                base_hours=18, share=0.1, investment=150000,
                solution="Digitise intake and capture at the point of work",
                technology="Digital forms / document capture", complexity="Medium"),
    "Q24": dict(title="Spreadsheet Dependency", severity="High", phase=1,
                base_hours=35, share=0.12, investment=200000,
                solution="Migrate spreadsheet system-of-record into a governed platform",
                technology="BI platform / operational database", complexity="Medium"),
    "Q27": dict(title="Integration Constraint", severity="High", phase=3,
                base_hours=26, share=0.08, investment=340000,
                solution="Expose documented APIs and build an integration layer",
                technology="iPaaS / API middleware", complexity="High"),
    # --- Pillar 4: Data Intelligence -------------------------------------
    "Q29": dict(title="Unowned Critical Data", severity="Medium", phase=1,
                base_hours=14, share=0.05, investment=85000,
                solution="Publish data ownership and quality standards per dataset",
                technology="Data ownership register", complexity="Low"),
    "Q33": dict(title="Late Data Errors", severity="High", phase=2,
                base_hours=28, share=0.1, investment=185000,
                solution="Add automated validation at the point of capture",
                technology="Validation rules / data-quality tooling", complexity="Medium"),
    "Q35": dict(title="Absent Decision Dashboard", severity="Medium", phase=3,
                base_hours=22, share=0.08, investment=165000,
                solution="Publish a live KPI dashboard fed from systems of record",
                technology="BI dashboard layer", complexity="Medium"),
    # --- Pillar 5: AI Readiness -----------------------------------------
    "Q38": dict(title="Support Knowledge Deficit", severity="Medium", phase=3,
                base_hours=20, share=0.08, investment=140000,
                solution="Build a maintained FAQ and self-service knowledge base",
                technology="Knowledge base + assisted search", complexity="Low"),
    "Q40": dict(title="No Central Knowledge Repository", severity="High", phase=1,
                base_hours=24, share=0.1, investment=150000,
                solution="Consolidate scattered knowledge into one governed repository",
                technology="Knowledge-base platform", complexity="Low"),
    "Q44": dict(title="Forecast Blind Spot", severity="High", phase=3,
                base_hours=30, share=0.1, investment=260000,
                solution="Introduce demand forecasting on a defined horizon",
                technology="Forecasting model / planning tool", complexity="High"),
    # --- Pillar 6: Technology & Integration ------------------------------
    "Q46": dict(title="No Core System of Record", severity="Critical", phase=3,
                base_hours=36, share=0.2, investment=650000,
                solution="Implement a core ERP as the authoritative record",
                technology="ERP platform + implementation", complexity="High"),
    "Q52": dict(title="Weak Access Governance", severity="High", phase=2,
                base_hours=20, share=0.07, investment=170000,
                solution="Introduce role-based access control with regular recertification",
                technology="IAM / RBAC tooling", complexity="Medium"),
    "Q53": dict(title="Recovery Exposure", severity="Critical", phase=2,
                base_hours=26, share=0.06, investment=150000,
                solution="Automate backups and prove recovery with scheduled restore tests",
                technology="Backup + recovery automation", complexity="Low"),
    # --- Pillar 7: Strategic Scalability --------------------------------
    "Q58": dict(title="Key Person Dependency", severity="Critical", phase=1,
                base_hours=18, share=0.09, investment=95000,
                solution="Cross-train and document critical knowledge, remove single-owner steps",
                technology="SOP system + cross-training", complexity="Low"),
    "Q59": dict(title="Decision Concentration", severity="High", phase=2,
                base_hours=16, share=0.08, investment=130000,
                solution="Delegate decisions below a defined threshold with guardrails",
                technology="Delegation matrix + workflow", complexity="Low"),
    "Q61": dict(title="Operational Growth Ceiling", severity="High", phase=2,
                base_hours=30, share=0.14, investment=230000,
                solution="Remove the operational blockers constraining the next growth step",
                technology="Capacity + process intervention", complexity="Medium"),
}


# --- Financial model ------------------------------------------------------
# The previous model multiplied a fixed `base_hours` by severity and a flat
# hourly rate, so a 5-person firm and a 500-person firm with identical answers
# reported identical savings. Savings are now derived from the size of the
# organisation actually being assessed:
#
#   affected staff   = staff x share_of_workforce_affected
#   annual hours     = affected staff x hours_per_person_per_year x severity
#   current cost     = annual hours x blended hourly rate
#   recoverable      = current cost x efficiency(complexity)
#
# The total is then capped so the result can never exceed MAX_SAVINGS_SHARE of
# the organisation's labour line. Every figure is returned in `assumptions` so
# the report can show the working and the number can be defended.
WORKING_HOURS_PER_MONTH = 160      # ~40 hours a week, 12 months
WORKING_DAYS_PER_YEAR = 220

# Blended fully-loaded hourly rate (KES) by organisation size. Smaller
# employers pay less, so the same automation is worth less money to them.
WAGE_TIERS = (
    (0, 50, 250.0),
    (51, 200, 450.0),
    (201, 500, 650.0),
    (501, None, 900.0),
)

# Hard ceiling: never promise more than this share of the labour line.
MAX_SAVINGS_SHARE = 0.12

DEFAULT_STAFF = 50


def blended_hourly_rate(staff, default=DEFAULT_HOURLY_RATE):
    """Blended fully-loaded hourly rate for an organisation of this size."""
    try:
        staff = int(staff)
    except (TypeError, ValueError):
        return default
    for low, high, rate in WAGE_TIERS:
        if staff >= low and (high is None or staff <= high):
            return rate
    return default


def labour_line(staff, rate):
    """Annual payroll for the organisation being assessed."""
    staff = max(0, int(staff or 0))
    return staff * WORKING_HOURS_PER_MONTH * 12 * rate


EFFICIENCY = {"Low": 0.70, "Medium": 0.60, "High": 0.50}
EASE = {"Low": 1.00, "Medium": 0.60, "High": 0.30}

CONFIDENCE_BANDS = (
    (95, "Exceptional Confidence"),
    (80, "High Confidence"),
    (60, "Moderate Confidence"),
    (40, "Limited Confidence"),
    (0, "Low Confidence"),
)


def evidence_factor(key):
    return EVIDENCE_MULTIPLIERS.get(key or "none", 0.70)


def confidence_band(aci):
    for floor, label in CONFIDENCE_BANDS:
        if aci >= floor:
            return label
    return "Low Confidence"


def _weighted(pairs):
    num = sum(score * weight for score, weight in pairs)
    den = sum(weight for _, weight in pairs)
    return num / den if den else 0.0


def _horizon(complexity, priority):
    """Legacy single-horizon label kept for API compatibility."""
    if complexity == "Low" and priority >= 60:
        return "Horizon 1 - Quick Wins (0-90 days)"
    if complexity == "High" and priority < 70:
        return "Horizon 4 - AI Transformation (24-36 months)"
    if priority >= 55:
        return "Horizon 2 - Operational Optimization (3-12 months)"
    return "Horizon 3 - Enterprise Automation (12-24 months)"


def compute(questions, answers, respondent_coverage=1 / 3.0, consistency=1.0,
            staff=None):
    """Compute the full Elipsis result.

    questions : iterable of mappings with keys
                id, code, subdomain, pillar, weight, evidence_required
    answers   : mapping of question_id -> {"score": int|None, "evidence": str}

    staff : the number of people in the organisation being assessed. Drives
            the size of the financial impact; defaults to DEFAULT_STAFF.

    Returns a plain dict; writes nothing. The caller persists it.
    """
    questions = list(questions)
    total = len(questions)
    answered = [q for q in questions
                if answers.get(q["id"]) and answers[q["id"]].get("score") is not None]

    # Evidence-adjusted score per question, 0-100.
    scored = {}
    for q in questions:
        answer = answers.get(q["id"])
        if not answer or answer.get("score") is None:
            continue
        normalized = (answer["score"] / 5.0) * 100.0
        scored[q["id"]] = min(100.0, normalized * evidence_factor(answer.get("evidence")))

    subdomain_pairs, pillar_pairs = {}, {}
    for q in questions:
        if q["id"] not in scored:
            continue
        subdomain_pairs.setdefault(q["subdomain"], []).append((scored[q["id"]], q["weight"]))
        pillar_pairs.setdefault(q["pillar"], []).append((scored[q["id"]], q["weight"]))

    subdomains = {code: round(_weighted(p), 1) for code, p in subdomain_pairs.items()}
    pillars = {code: round(_weighted(p), 1) for code, p in pillar_pairs.items()}

    # --- Overall Elipsis Index: weighted pillar blend ---------------------
    index_num = sum(pillars.get(code, 0.0) * w for code, w in PILLAR_WEIGHTS.items())
    index_den = sum(w for code, w in PILLAR_WEIGHTS.items() if code in pillars)
    readiness_index = round(index_num / index_den, 2) if index_den else 0.0
    organisation_score = (
        round(sum(subdomains.values()) / len(subdomains), 1) if subdomains else 0.0)

    # --- Confidence index -------------------------------------------------
    completeness = len(answered) / total if total else 0.0
    required = [q for q in questions if q.get("evidence_required")]
    with_evidence = [q for q in required
                     if answers.get(q["id"]) and (answers[q["id"]].get("evidence") or "none") != "none"]
    evidence_avail = len(with_evidence) / len(required) if required else 1.0
    confidence_index = round(
        100 * (completeness + evidence_avail + min(1.0, respondent_coverage) + consistency) / 4, 1)

    # --- The thirty-six executive metrics --------------------------------
    # Scope exposes subdomains, pillars, question codes AND metric codes so
    # formulas can compose (e.g. Quick-Win Potential uses Automation Opportunity).
    scope = {}
    scope.update(subdomains)
    scope.update(pillars)
    scope.update({q["code"]: round(scored[q["id"]], 1)
                  for q in questions if q["id"] in scored})
    validate_metrics({q["code"] for q in questions})
    # Anything a formula may legitimately reference but that has no score yet
    # (unanswered questions, untouched subdomains/pillars) resolves to zero.
    known_names = ({q["code"] for q in questions}
                   | set(SUBDOMAIN_LABELS) | set(PILLAR_LABELS))
    raw_metrics = MetricEngine(scope, known_names).all_metrics()
    metrics = {code: round(value, 1) for code, value in raw_metrics.items()}

    metric_rows = [
        dict(code=code, pillar=METRIC_PILLAR[code], label=METRIC_LABELS[code],
             kind=METRIC_KINDS[code], value=metrics.get(code, 0.0),
             reading=METRIC_READINGS[code])
        for code, _, _, _, _, _ in METRICS
    ]

    # --- Pain points, recommendations, financial model --------------------
    staff_count = max(1, int(staff or DEFAULT_STAFF))
    hourly_rate = blended_hourly_rate(staff_count)
    payroll = labour_line(staff_count, hourly_rate)
    savings_cap = payroll * MAX_SAVINGS_SHARE

    pain_points, recommendations = [], []
    current_total = future_total = investment_total = 0.0
    for q in questions:
        if q["code"] not in PAIN_CATALOG or q["id"] not in scored:
            continue
        raw = answers[q["id"]]["score"]
        if raw is None or raw > THRESHOLD:
            continue
        spec = PAIN_CATALOG[q["code"]]
        sev = (5 - raw) / 5.0
        # Scale the cost by how much of the workforce this pain touches.
        share = spec.get("share", 0.05)
        affected = staff_count * share
        annual_hours = affected * spec["base_hours"] * sev
        current = annual_hours * hourly_rate
        future = current * (1 - EFFICIENCY[spec["complexity"]])
        savings = current - future
        investment = float(spec["investment"])
        roi = (savings / investment * 100) if investment else 0.0
        priority = round(100 * (sev * 0.40 + min(1.0, roi / 1000) * 0.25
                                + sev * 0.20 + EASE[spec["complexity"]] * 0.15), 1)
        pain_points.append(dict(trigger=q["code"], title=spec["title"],
                                severity=spec["severity"], impact=round(sev * 100, 1),
                                detail=f"Question {q['code']} scored {raw}/5."))
        recommendations.append(dict(trigger=q["code"], title=spec["solution"],
                                    solution=spec["solution"], technology=spec["technology"],
                                    complexity=spec["complexity"], priority=priority,
                                    phase=spec["phase"], horizon=_horizon(spec["complexity"], priority),
                                    roi=round(roi, 1), pillar=q["pillar"]))
        current_total += current
        future_total += future
        investment_total += investment

    total_savings = current_total - future_total
    # Never promise more than the cap; if the raw figure exceeds it, scale
    # every line down so the arithmetic the client sees still adds up.
    scaling = 1.0
    if total_savings > savings_cap > 0:
        scaling = savings_cap / total_savings
        total_savings = savings_cap
        current_total *= scaling
        future_total *= scaling
    roi_total = (total_savings / investment_total * 100) if investment_total else 0.0
    payback_total = (investment_total / (total_savings / 12)) if total_savings > 0 else 0.0

    assumptions = dict(
        staff=staff_count,
        hourly_rate=hourly_rate,
        working_hours_per_month=WORKING_HOURS_PER_MONTH,
        labour_line=round(payroll),
        savings_cap=round(savings_cap),
        max_savings_share=MAX_SAVINGS_SHARE,
        capped=scaling < 1.0,
        cap_applied=round(savings_cap),
        raw_savings=round(total_savings / scaling),
        scale_factor=round(scaling, 4),
        friction_cost=round(current_total),
        hours_freed=round(total_savings / hourly_rate) if hourly_rate else 0,
    )

    # --- Three-phase roadmap ---------------------------------------------
    ordered = sorted(recommendations, key=lambda x: -x["priority"])
    roadmap = []
    for num, label, horizon, note in PHASES:
        items = [r for r in ordered if r["phase"] == num]
        roadmap.append(dict(number=num, label=label, horizon=horizon, note=note,
                            count=len(items), items=items,
                            value=round(sum(r["roi"] for r in items), 1)))

    return dict(
        readiness_index=readiness_index,
        organisation_score=organisation_score,
        # `department_score` is retained as an alias so older API clients and
        # stored reports keep working through the rebrand.
        department_score=organisation_score,
        confidence_index=confidence_index,
        confidence_band=confidence_band(confidence_index),
        maturity_band=maturity_band(readiness_index),
        pillars=pillars,
        subdomains=subdomains,
        metrics=metrics,
        metric_rows=metric_rows,
        metrics_by_pillar={
            code: [m for m in metric_rows if m["pillar"] == code]
            for code in PILLAR_LABELS
        },
        answered=len(answered),
        total=total,
        pain_points=sorted(pain_points, key=lambda x: -x["impact"]),
        recommendations=ordered,
        roadmap=roadmap,
        top_opportunities=[r["title"] for r in ordered[:3]],
        financial=dict(current_cost=round(current_total), future_cost=round(future_total),
                       annual_savings=round(total_savings), investment=round(investment_total),
                       roi=round(roi_total, 1), payback_months=round(payback_total, 1),
                       assumptions=assumptions),
    )


def _inputs_ready(formula: str, scope: dict) -> bool:
    """True when every named input in a metric formula has a real score."""
    for node in ast.walk(validate_formula(formula)):
        if isinstance(node, ast.Name) and node.id not in METRIC_HELPERS:
            if node.id not in scope:
                return False
    return True


# --- Live scoring while the form is being filled --------------------------
def compute_live(questions, answers, segment_code: str):
    """Score the form so far, without submitting it.

    Called after every answer so the respondent sees their section update as
    they go. Returns only what the live panel needs:

        answered / total / percent     progress
        segment_score                  the section just completed (0-100)
        pillar_score                   the pillar that section belongs to
        overall_index                  the running Elipsis Index
        metrics                        the metrics this segment actually moves
        metrics_by_pillar              the full live picture, per pillar

    A partially-answered form is normal here, so every unresolved reference
    simply scores zero rather than raising.
    """
    questions = list(questions)
    total = len(questions)
    answered = [q for q in questions
                if answers.get(q["id"]) and answers[q["id"]].get("score") is not None]

    scored = {}
    for q in questions:
        answer = answers.get(q["id"])
        if not answer or answer.get("score") is None:
            continue
        normalized = (answer["score"] / 5.0) * 100.0
        scored[q["id"]] = min(100.0, normalized * evidence_factor(answer.get("evidence")))

    def group(key):
        pairs = {}
        for q in questions:
            if q["id"] not in scored:
                continue
            pairs.setdefault(q[key], []).append((scored[q["id"]], q["weight"]))
        return {code: round(_weighted(p), 1) for code, p in pairs.items()}

    subdomains = group("subdomain")
    pillars = group("pillar")

    index_num = sum(pillars.get(code, 0.0) * w for code, w in PILLAR_WEIGHTS.items())
    index_den = sum(w for code, w in PILLAR_WEIGHTS.items() if code in pillars)
    overall = round(index_num / index_den, 1) if index_den else 0.0

    scope = {}
    scope.update(subdomains)
    scope.update(pillars)
    scope.update({q["code"]: round(scored[q["id"]], 1)
                  for q in questions if q["id"] in scored})
    known = ({q["code"] for q in questions}
             | set(SUBDOMAIN_LABELS) | set(PILLAR_LABELS))
    metrics = MetricEngine(scope, known).all_metrics()

    # A metric is only trustworthy once every input its formula names has a
    # real score. Mid-form an unanswered subdomain scores zero, which would
    # invert into a frightening 100 on a risk metric. So report those as
    # `ready: False` and let the UI show a dash instead of a fake number.
    ready = {code: _inputs_ready(formula, scope) for code, formula in METRIC_FORMULAS.items()}

    def metric_row(code, pillar):
        return dict(code=code, pillar=pillar, label=METRIC_LABELS[code],
                    kind=METRIC_KINDS[code],
                    value=round(metrics.get(code, 0.0), 1) if ready.get(code) else None,
                    reading=METRIC_READINGS[code],
                    ready=bool(ready.get(code)))

    segment_pillar = SUBDOMAIN_PILLAR.get(segment_code)
    segment_metrics = [metric_row(code, pillar)
                       for code, pillar, _, _, _, _ in METRICS
                       if pillar == segment_pillar]

    return dict(
        answered=len(answered), total=total,
        percent=round(100 * len(answered) / total) if total else 0,
        segment_code=segment_code,
        segment_score=subdomains.get(segment_code),
        pillar=segment_pillar,
        pillar_score=pillars.get(segment_pillar),
        overall_index=overall,
        metrics={code: (round(value, 1) if ready.get(code) else None)
                 for code, value in metrics.items()},
        metrics_by_pillar={
            code: [metric_row(m[0], code) for m in METRICS if m[1] == code]
            for code in PILLAR_LABELS
        },
        segment_metrics=segment_metrics,
        subdomains=subdomains,
        pillars=pillars,
    )
