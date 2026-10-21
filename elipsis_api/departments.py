"""Logistics department definitions used by self and team diagnostics."""

from __future__ import annotations

DEPARTMENTS = (
    {
        "key": "operations",
        "label": "Operations",
        "roles": "COO, Operations Manager, Shift Supervisor",
        "focus": ("OPS", "WFL", "RSU"),
        "intro": "Map how work actually moves from order to delivery, and where handoffs, approvals, and rework cost the operation money.",
        "promise": "See the operating constraint that is slowing every lane, then receive a sequenced plan to remove it.",
    },
    {
        "key": "dispatch",
        "label": "Dispatch & fleet",
        "roles": "Dispatch Manager, Fleet Controller, Route Planner",
        "focus": ("REP", "RUL", "RSU"),
        "intro": "Test route planning, driver assignment, vehicle utilisation, and the daily decisions that depend on one or two experienced people.",
        "promise": "Quantify the dispatch effort that can be automated without losing control of service.",
    },
    {
        "key": "warehouse",
        "label": "Warehouse & inventory",
        "roles": "Warehouse Manager, Inventory Controller, Receiving Lead",
        "focus": ("WFL", "RSU", "DQU"),
        "intro": "Review receiving, put-away, picking, stock accuracy, and the physical handoffs that decide whether the warehouse keeps its promises.",
        "promise": "Find the warehouse constraint that is inflating cost, delaying release, or hiding inventory risk.",
    },
    {
        "key": "transport",
        "label": "Transport & line-haul",
        "roles": "Transport Manager, Line-haul Planner, Fleet Supervisor",
        "focus": ("RSU", "WFL", "KPD"),
        "intro": "Assess line-haul planning, asset utilisation, exception handling, and how much of the schedule depends on individual experience.",
        "promise": "Turn transport variability into a costed improvement case with clear operating ownership.",
    },
    {
        "key": "customer_service",
        "label": "Customer service",
        "roles": "Customer Service Manager, Key Account Lead, Claims Handler",
        "focus": ("CSV", "KMA", "RPM"),
        "intro": "Examine inquiry volume, response consistency, claims handling, and how quickly the team can answer without escalating.",
        "promise": "Reduce avoidable contact and give the team a repeatable service standard customers can feel.",
    },
    {
        "key": "finance",
        "label": "Finance & commercial",
        "roles": "Finance Manager, Commercial Manager, Billing Lead",
        "focus": ("MAN", "COL", "RPM"),
        "intro": "Review billing accuracy, reconciliation effort, cash visibility, and the manual work behind commercial decisions.",
        "promise": "Show where finance is paying for rework and where faster, cleaner data improves margin.",
    },
    {
        "key": "compliance",
        "label": "Compliance & risk",
        "roles": "Compliance Officer, HSE Lead, Risk Manager",
        "focus": ("SEC", "OPS", "KMA"),
        "intro": "Test document control, access governance, incident learning, and whether compliance depends on memory rather than a system.",
        "promise": "Turn compliance from a recurring scramble into a controlled, auditable operating routine.",
    },
    {
        "key": "procurement",
        "label": "Procurement & suppliers",
        "roles": "Procurement Manager, Vendor Lead, Contracts Officer",
        "focus": ("RUL", "MAN", "ECO"),
        "intro": "Review supplier onboarding, purchase approvals, contract visibility, and the manual work in the procurement cycle.",
        "promise": "Shorten the procurement cycle while improving control over spend and supplier risk.",
    },
    {
        "key": "people",
        "label": "People & capability",
        "roles": "HR Manager, Talent Lead, Operations Trainer",
        "focus": ("KPD", "KMA", "SCA"),
        "intro": "Assess role clarity, knowledge concentration, onboarding, and whether the operating model can grow without adding layers.",
        "promise": "Identify the capability risks that would slow growth or break service during peak demand.",
    },
    {
        "key": "technology",
        "label": "Technology & data",
        "roles": "IT Manager, Data Lead, Systems Administrator",
        "focus": ("ADO", "INM", "DQU"),
        "intro": "Review system adoption, integration health, data quality, and whether the current stack can support the next operating model.",
        "promise": "Give leadership a practical view of what the technology estate can carry, and what must change first.",
    },
)

DEPARTMENT_BY_LABEL = {item["label"]: item for item in DEPARTMENTS}
DEPARTMENT_BY_KEY = {item["key"]: item for item in DEPARTMENTS}
DEPARTMENT_LABELS = tuple(item["label"] for item in DEPARTMENTS)
DEPARTMENT_CHOICES = tuple({"key": item["key"], "label": item["label"]} for item in DEPARTMENTS)


def department_brief(label: str | None) -> dict:
    if not label:
        return DEPARTMENT_BY_LABEL["Operations"]
    return DEPARTMENT_BY_LABEL.get(label) or {
        "key": "whole_company",
        "label": label,
        "roles": "Leadership team",
        "focus": (),
        "intro": "Review the operating model across functions, handoffs, systems, and decision rights.",
        "promise": "See the constraint holding the whole company back and the first moves that release it.",
    }


def ordered_steps(steps: list[dict], label: str | None) -> list[dict]:
    focus = department_brief(label)["focus"]
    if not focus:
        return steps
    rank = {code: i for i, code in enumerate(focus)}
    return sorted(
        steps,
        key=lambda step: (rank.get(step.get("subdomain"), len(rank)), step.get("number", 0)),
    )
