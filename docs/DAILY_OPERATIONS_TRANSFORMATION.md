# Elipsis Daily Operations Transformation

Status: Draft for build
Version: 2.0
Date: 28 October 2026
Owner: Product and Engineering
Related documents: `docs/PLATFORM_MASTER_PLAN.md` (strategy and sequence), `docs/PLATFORM_UPGRADE_IMPLEMENTATION_GUIDE.md` (marketplace specification), `docs/COMPETITIVE_EDGE.md`, `docs/SERVICE_DELIVERY_STANDARD.md`

## 1. Purpose

This document is the technical annex to `docs/PLATFORM_MASTER_PLAN.md`. The main goal
of the platform is the diagnostic engine: measure how a logistics operation actually
runs, identify the constraints that cost the most, and produce a comprehensive report
with recommendations and an implementation roadmap. Diagnosis is the wedge and the
primary paid product.

Diagnosis is also periodic. An assessment every 90 days does not create a daily habit,
and a roadmap that is never run cannot be proven. This specification defines the
operating layer that keeps the diagnosis alive: a **daily operating console** for
logistics departments that turns the roadmap into owned work, captures the exceptions
and checks that feed the next diagnosis, and produces the evidence for a re-score.

The layer does not replace the diagnostic engine. It protects it: the report creates the
plan, the console runs the plan, and the next assessment proves the movement.

The target product answers one question every morning:

> What needs attention in my department in the next eight hours, who owns it, and what
> did the last shift leave open?

## 2. Decision summary

| Area | Decision |
|---|---|
| Product centre | The diagnostic engine and its report remain the core paid product. |
| Operating layer | `/today` control tower becomes the default authenticated workspace home. |
| Business layer | Assessment, Full Assessment, and marketplace remain, positioned as diagnose and implement. |
| Primary object | A daily `OpsTask` that exists without an assessment. |
| Department model | First-class departments with membership, leads, and scoped visibility. |
| Shift model | Lightweight shift open/close with a required handover when exceptions are open. |
| Exceptions | Existing `OperationalIncident` becomes the exception register, extended with owner, SLA, and escalation. |
| Routines | Recurring checklists per department and shift, with missed-run detection. |
| KPIs | Existing 8-metric logistics catalog gains per-department targets, warning thresholds, and stale-reading detection. |
| Notifications | Persistent daily-operations notifications plus email digest at the org huddle time. |
| Integrations | Reuse API tokens and webhooks. No TMS, WMS, telematics, dispatch, or load-board build. |
| Mobile | Daily capture flows must work one-handed on a phone; no separate native app in phase one. |
| Pricing | Daily operations is included in the operator plan; per-seat pricing is an open decision (section 18). |

## 3. Current state

### 3.1 What already exists

- Assessment engine, 63 questions, 36 metrics, 90-day plan, exports
  (`readiness.py`, `constants.py`, `elipsis_questions.py`).
- Full Assessment paywall and entitlements (`AssessmentPurchase`, `AssessmentPurchase`
  in `elipsis_api/models.py:478`, `elipsis_api/premium.py`).
- Marketplace request, bid, verification, conversation, handoff, and admin desk
  (`elipsis_api/routers/marketplace_ui.py`, `routers/admin.py`, `routers/bidder.py`).
- Operations ledger: 8 logistics KPIs, incidents, compliance documents, CSV import,
  API tokens (`elipsis_api/services_operations.py`,
  `elipsis_api/routers/operations_ui.py`).
- Company room: pulse, 14-day desk, huddle date, decisions, discussion, brief, ICS
  (`elipsis_api/services_room.py`, `routers/company_room.py`).
- Action board over assessment roadmap items (`routers/workspace.py`,
  `services_ops.action_items`).
- Webhooks, email events, digest scaffolding, Telegram bot (`services_webhooks.py`,
  `services_email_events.py`, `services_digest.py`, `telegram_bot/`).

### 3.2 What blocks daily use

1. **Daily work depends on an assessment.** `RoadmapItem.assessment_id` is non-null
   (`elipsis_api/models.py:283`). A supervisor cannot create a normal task before an
   assessment exists.
2. **No department workspace.** `departments.py` is diagnostic copy.
   `Organization` has no department model in use; `OrgOwner.department` is a free string
   (`models.py:318`). There is no department dashboard, lead, roster, or scope.
3. **No shift or handover.** No shift record, no handover note, no acknowledgement.
4. **No routines.** "Weekly huddle" is only a computed date
   (`services_room._next_huddle`, `services_room.py:455`).
5. **No shipment entity.** `OperationalIncident.shipment_ref` is free text
   (`models.py:956`). This is deliberate; see non-goals.
6. **KPIs are manual and unowned.** Fixed catalog, no department, no per-target owner,
   no alert threshold, no stale detection (`services_operations.py:15`).
7. **Incidents have no SLA or escalation.** Status is only
   `open / investigating / resolved`.
8. **Navigation and pricing are assessment-led.** `base.html:76-98` leads with Company
   home and Assessments; Operations is a secondary item.
9. **Operations notifications are computed per request**, not stored per user
   (`services_ops.notifications`, `services_ops.py:134`).
10. **No floor-ready capture.** Forms are desktop-shaped; no quick-capture surface.

### 3.3 Baseline defects to fix before or during phase A

- `tests/test_api.py::test_growth_certification_imports_and_webhooks` fails with
  `UndefinedError: 'tuple object' has no attribute 'items'` on `/settings`.
- `tests/test_api.py::test_company_room_membership_collaboration_and_branding` fails
  with the same `/settings` error.
- `tests/test_hardening.py::test_marketplace_is_locked_while_coming_soon` expects 503,
  receives 404.
- Two role fields exist (`User.role` and `User.user_type`), contradicting the locked
  decision in the platform guide. `permissions.py:26` reads both.

## 4. Target product

### 4.1 Positioning

**Elipsis Control Tower: the daily operating console for logistics departments.**

It turns a diagnostic into a running cadence: today's work, exceptions, compliance,
checks, handover, and measurable movement. Assessment stays available when the team
needs a new diagnosis. Marketplace stays available when the team needs implementation.

### 4.2 Non-goals

- No telematics, ELD, GPS tracking, fuel-card, or camera integration.
- No dispatch, routing, load board, or carrier marketplace.
- No full TMS, WMS, or ERP replacement.
- No payroll, HR, or rostering engine beyond a shift record.
- No shipment master data in phase one. `shipment_ref` remains an external reference.
- No native mobile app in phase one; responsive web and PWA install only.

### 4.3 Success measures

| Measure | Target after 90 days |
|---|---|
| Weekly active departments per paying org | 2+ |
| Days per week with an opened `/today` per active department | 4+ |
| Tasks created per active department per week | 10+ |
| Handovers completed per active department per week | 5+ |
| Exceptions with an owner | 90% |
| Exceptions resolved inside SLA | 80% |
| Routine runs completed on time | 85% |
| 4-week retention of activated departments | 70% |
| Assessment-to-first-task time | under 24 hours |

## 5. Personas and jobs

| Persona | Department | Daily job |
|---|---|---|
| Operations manager | Operations | See cross-department load, unblock, own targets. |
| Shift supervisor | Dispatch, warehouse, transport | Open shift, assign work, escalate, close with handover. |
| Controller / planner | Dispatch, fleet | Track exceptions and SLA, reassign, update status. |
| Analyst | Operations, finance | Record KPIs, verify data, prepare review. |
| Compliance officer | Compliance | Watch expiries, run checks, close findings. |
| Executive | Cross-department | Read movement and risk without micro-management. |
| Platform admin | Platform | Support, audit, billing, verification. |

### 5.1 Jobs to be done

1. "At shift start, show me what is overdue, what is due, and what changed since I left."
2. "Let me capture a problem in under 20 seconds, from my phone, without a form marathon."
3. "Tell me who owns this and when it is due, without me chasing."
4. "When I hand over, let the next shift see exactly what is open."
5. "Show me which KPI is off target and which department owns it."
6. "Prove at the weekly review that the cadence ran and the constraint moved."

## 6. Roles and permissions

### 6.1 Role layers

- Organisation role: existing `OrgOwner.role` values
  `owner / manager / supervisor / analyst / viewer` (`permissions.py:16`).
- Department role: new `DepartmentMember.role` values
  `lead / planner / operator / viewer`.
- Platform admin: existing `User.is_admin`, `User.role`.

Do not add a fourth role system. Resolve `User.role` versus `User.user_type` in phase A:
`user_type` becomes the commercial identity (`client / bidder / admin`), `role` becomes
legacy and is migrated into `OrgOwner.role` and `is_admin`. `permissions.py` must read
one source per concern.

### 6.2 Permission matrix

| Action | Viewer | Analyst | Supervisor | Manager | Owner | Admin |
|---|---|---|---|---|---|---|
| View `/today` for own departments | Yes | Yes | Yes | Yes | Yes | Yes, audited |
| View another department | If org-wide visibility | If org-wide | Yes | Yes | Yes | Yes |
| Create own task | No | Yes | Yes | Yes | Yes | Yes |
| Assign task to another member | No | No | Within department | Yes | Yes | Yes |
| Change task status | Own only | Own only | Department | Department | All | All |
| Log metric reading | No | Yes | Yes | Yes | Yes | Yes |
| Set KPI target | No | No | No | Department | All | All |
| Create exception | No | Yes | Yes | Yes | Yes | Yes |
| Resolve exception | No | No | Department | Department | All | All |
| Escalate exception | No | No | Yes | Yes | Yes | Yes |
| Run routine | No | Yes | Yes | Yes | Yes | Yes |
| Create/edit routine | No | No | No | Department | All | All |
| Open/close shift | No | No | Yes | Yes | Yes | Yes |
| Write handover | No | Yes | Yes | Yes | Yes | Yes |
| Acknowledge handover | No | No | Yes | Yes | Yes | Yes |
| Manage department members | No | No | No | Department | All | All |

Rules:

- Deny by default. Every route calls the central permission service.
- Organisation admins do not bypass department scope silently; any read outside their
  department is audit-logged.
- A user may belong to multiple departments. `DepartmentMember.is_primary` controls the
  default `/today` filter.
- Org-wide visibility is the default for `manager` and `owner`; other roles see their
  departments unless the org sets `department_visibility = "org"`.

## 7. Daily operating loop

The product is organised around one loop, repeated per shift and reviewed weekly.

1. **Start shift** — supervisor opens shift, confirms roster, runs the start checklist.
2. **See today** — tasks due, overdue, exceptions, expiring documents, KPI watchlist.
3. **Run work** — update task status, assign, add notes, capture new work.
4. **Capture exceptions** — log a delay, claim, safety event, or control break with an
   owner and SLA.
5. **Escalate** — breach or risk triggers supervisor, then manager, then owner.
6. **Hand over** — close shift with a structured note and open-issue list.
7. **Review** — weekly manager view of completion, SLA, routines, KPI movement.

## 8. Information architecture

### 8.1 Navigation change

Replace the current `Operate` group in `base.html:83-85` with:

```
Operate
  Today            /today
  My work          /tasks?mine=1
  Exceptions       /exceptions
  Handover         /handover
  Operations       /operations        (ledger: KPIs, compliance, data)

Team
  Routines         /routines
  Team             /team
```

Keep `Diagnose` and `Implement` groups. Make `/today` the post-login destination for
users with an organisation; keep `/dashboard` as the assessment overview, reachable
from Diagnose.

### 8.2 Route map

| Route | Method | Purpose |
|---|---|---|
| `/today` | GET | Daily control tower for org and department. |
| `/today/capture` | POST | Unified quick capture: task, exception, metric, note. |
| `/tasks` | GET | Task board, filters: mine, department, status, due, owner. |
| `/tasks/new` | GET/POST | Create task. |
| `/tasks/{id}` | GET | Task detail and activity. |
| `/tasks/{id}/status` | POST | Transition status. |
| `/tasks/{id}/assign` | POST | Assign or reassign. |
| `/tasks/{id}/note` | POST | Add note. |
| `/tasks/bulk` | POST | Bulk status/assign/due. |
| `/exceptions` | GET | Exception queue with SLA state. |
| `/exceptions/new` | GET/POST | Log exception. |
| `/exceptions/{id}` | GET | Detail, timeline, root cause, corrective action. |
| `/exceptions/{id}/status` | POST | Transition status. |
| `/exceptions/{id}/escalate` | POST | Manual escalation. |
| `/routines` | GET | Routine list and today's runs. |
| `/routines/new` | GET/POST | Create routine. |
| `/routines/{id}` | GET | Definition, items, recent runs. |
| `/routines/{id}/run` | POST | Start or resume a run. |
| `/routines/runs/{run_id}` | GET/POST | Complete checks. |
| `/handover` | GET | Handover log and open issues. |
| `/handover/new` | POST | Write handover for current shift. |
| `/handover/{id}` | GET | Read handover. |
| `/handover/{id}/ack` | POST | Acknowledge handover. |
| `/kpis` | GET | Targets versus actuals by department. |
| `/kpis/targets` | POST | Set or update target. |
| `/kpis/reading` | POST | Record reading with department. |
| `/team` | GET | Roster, departments, workload. |
| `/team/departments` | POST | Create or update department. |
| `/team/members` | POST | Add, move, or remove member. |

API mirror under `/api/v1/ops`:

`GET /today`, `GET/POST /tasks`, `PATCH /tasks/{id}`, `GET/POST /exceptions`,
`PATCH /exceptions/{id}`, `GET/POST /routines`, `POST /routines/{id}/runs`,
`POST /handover`, `GET /kpis`, `POST /kpis/readings`.

All API routes use the existing bearer token model (`ApiToken`) and the same permission
service as the UI. No separate authorization path.

## 9. Domain model

All timestamps are ISO 8601 strings, matching the existing convention
(`default=_now`). All tables use integer primary keys. New tables are added by one
Alembic revision.

### 9.1 New tables

#### `departments` (extend existing)

| Column | Type | Notes |
|---|---|---|
| `key` | String | Stable slug, unique per organisation. |
| `lead_user_id` | FK users, nullable | Department lead. |
| `description` | Text | What the department owns. |
| `timezone` | String | Defaults to org timezone. |
| `huddle_day` | String | Defaults to org huddle day. |
| `huddle_time` | String | Defaults to org huddle time. |
| `active` | Boolean | Default true. |
| `sort_order` | Integer | Navigation order. |

Unique constraint: `(organization_id, key)`. Index: `(organization_id, active)`.

#### `department_members`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `organization_id` | FK | |
| `department_id` | FK | |
| `user_id` | FK | |
| `role` | String | `lead / planner / operator / viewer`. |
| `is_primary` | Boolean | Default false. |
| `status` | String | `active / inactive`. |
| `created_at` | String | |

Unique: `(department_id, user_id)`. Indexes: `(organization_id, user_id)`,
`(department_id, status)`.

#### `ops_tasks`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `organization_id` | FK | Required. |
| `department_id` | FK, nullable | Null means org-wide. |
| `title` | String | Required. |
| `detail` | Text | |
| `status` | String | `todo / in_progress / blocked / done / cancelled`. |
| `priority` | String | `low / normal / high / urgent`. |
| `source` | String | `manual / assessment / exception / routine / import`. |
| `assessment_id` | FK, nullable | Context only, never required. |
| `roadmap_item_id` | FK, nullable | Link when migrated from a plan action. |
| `incident_id` | FK, nullable | Corrective task for an exception. |
| `created_by` | FK users | |
| `assigned_to` | FK users, nullable | |
| `owner_label` | String | Fallback for non-user owners. |
| `due_at` | String | ISO datetime, nullable. |
| `started_at` | String | |
| `completed_at` | String | |
| `blocked_reason` | Text | |
| `escalation_level` | Integer | Default 0. |
| `tags` | String | Comma-separated. |
| `created_at` | String | |
| `updated_at` | String | |

Indexes: `(organization_id, status, due_at)`, `(department_id, status, due_at)`,
`(assigned_to, status)`, `(organization_id, created_at)`.

#### `shifts`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `organization_id` | FK | |
| `department_id` | FK | |
| `name` | String | `Day / Night / A / B`. |
| `starts_at` | String | |
| `ends_at` | String | |
| `status` | String | `planned / open / closed`. |
| `opened_by` | FK users | |
| `opened_at` | String | |
| `closed_by` | FK users | |
| `closed_at` | String | |
| `note` | Text | |

Index: `(department_id, starts_at)`. Unique: `(department_id, starts_at, name)`.

#### `shift_handovers`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `shift_id` | FK shifts | |
| `organization_id` | FK | |
| `department_id` | FK | |
| `author_id` | FK users | |
| `summary` | Text | Required. |
| `open_issues` | Text | Structured list rendered from open tasks/exceptions. |
| `safety_notes` | Text | |
| `next_actions` | Text | |
| `acknowledged_by` | FK users, nullable | |
| `acknowledged_at` | String | |
| `created_at` | String | |

Index: `(department_id, created_at)`.

#### `routines`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `organization_id` | FK | |
| `department_id` | FK, nullable | |
| `title` | String | |
| `description` | Text | |
| `cadence` | String | `per_shift / daily / weekly / monthly / manual`. |
| `schedule` | Text | JSON: `{"time":"07:00","weekdays":[0,1,2,3,4],"day_of_month":1}`. |
| `owner_user_id` | FK users, nullable | |
| `active` | Boolean | |
| `created_by` | FK users | |
| `created_at` | String | |
| `updated_at` | String | |

Index: `(organization_id, active)`.

#### `routine_items`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `routine_id` | FK | |
| `position` | Integer | |
| `label` | String | |
| `kind` | String | `check / measure / note / photo`. |
| `required` | Boolean | |
| `metric_key` | String, nullable | When `kind = measure`. |
| `help` | Text | |

Index: `(routine_id, position)`.

#### `routine_runs`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `routine_id` | FK | |
| `organization_id` | FK | |
| `department_id` | FK, nullable | |
| `shift_id` | FK, nullable | |
| `run_date` | String | Date. |
| `status` | String | `open / completed / missed`. |
| `started_by` | FK users | |
| `completed_by` | FK users | |
| `completed_at` | String | |
| `score` | Float | Percent of required items passed. |
| `created_at` | String | |

Unique: `(routine_id, run_date, shift_id)`. Index: `(organization_id, run_date, status)`.

#### `routine_checks`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `run_id` | FK | |
| `item_id` | FK routine_items | |
| `state` | String | `pending / pass / fail / na`. |
| `value` | Float, nullable | |
| `note` | Text | |
| `checked_by` | FK users | |
| `checked_at` | String | |

Unique: `(run_id, item_id)`.

#### `kpi_targets`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `organization_id` | FK | |
| `department_id` | FK, nullable | |
| `metric_key` | String | Must exist in `METRIC_CATALOG`. |
| `target_value` | Float | |
| `warning_value` | Float, nullable | |
| `direction` | String | `higher / lower`. |
| `owner_user_id` | FK users, nullable | |
| `effective_from` | String | Date. |
| `effective_to` | String, nullable | Date. |
| `created_at` | String | |

Unique: `(organization_id, department_id, metric_key, effective_from)`.

#### `ops_notifications`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `organization_id` | FK | |
| `user_id` | FK | |
| `department_id` | FK, nullable | |
| `kind` | String | `task_due / task_overdue / exception_created / exception_sla / handover_ready / routine_due / routine_missed / kpi_breach / mention`. |
| `title` | String | |
| `body` | Text | |
| `url` | String | |
| `severity` | String | `info / warning / critical`. |
| `read_at` | String | |
| `created_at` | String | |

Index: `(user_id, read_at, created_at)`, `(organization_id, department_id)`.

### 9.2 Extended tables

#### `operational_incidents`

Add:

| Column | Type | Notes |
|---|---|---|
| `department_id` | FK, nullable | |
| `owner_user_id` | FK users, nullable | Replaces free-text owner when set. |
| `reported_by` | FK users, nullable | |
| `category` | String | `delay / damage / claim / safety / documentation / system`. |
| `sla_due_at` | String | Computed from severity at creation. |
| `first_response_at` | String | |
| `escalated_at` | String | |
| `escalation_level` | Integer | Default 0. |
| `resolved_by` | FK users, nullable | |
| `resolution_note` | Text | |
| `recurrence_of_id` | FK self, nullable | |

Keep `shipment_ref` as an external reference string.

#### `operational_metrics`

Add:

| Column | Type | Notes |
|---|---|---|
| `department_id` | FK, nullable | |
| `entered_by` | FK users, nullable | |
| `source_ref` | String, nullable | External id for idempotent imports. |

#### `audit_events`

Add nullable `department_id`, `object_type`, `object_id` for filtering. Existing
`action`, `detail`, `user_id`, `organization_id`, `assessment_id` remain.

#### `roadmap_items`

No schema change. It remains the assessment plan record. `ops_tasks` is the daily
record. `/tasks` shows both, labelled `Plan action` and `Task`, until the phase C
migration converts open plan actions into tasks.

## 10. Screens

### 10.1 `/today`

Header:

- Organisation switcher.
- Department switcher, defaulting to the user's primary department.
- Date, local time, shift state (`Not opened / Open since 06:00 / Closed 14:02`).
- Huddle time and next huddle.

Band 1, four counters:

- Overdue tasks.
- Due today.
- Open high or critical exceptions.
- Documents expiring within 14 days.

Band 2, "Start of shift":

- Today's routine runs, with progress and a large `Run` action.
- If no routine exists, an explainer with `Create routine`.

Band 3, "My work today":

- Tasks assigned to me, overdue first, then due today, then blocked.
- Inline status transitions and a note field.
- Empty state: "Nothing due today. Pull work from the team queue."

Band 4, "Team queue":

- Unassigned, blocked, and overdue tasks across the selected department.
- Group by owner with counts.

Band 5, "Exceptions":

- Exceptions ordered by SLA state: breached, due soon, open.
- Owner, severity, time remaining, `Escalate`, `Resolve`.

Band 6, "Watchlist":

- KPIs off target, stale readings (older than the expected cadence), and documents
  expiring.

Band 7, "Handover":

- Last handover summary and open issues.
- `Write handover` when a shift is open.
- Acknowledged state and who acknowledged.

Band 8, "Activity":

- Department-scoped audit feed, not org-wide noise.

Persistent quick capture bar, sticky on mobile:

`Task | Exception | Metric | Note`

Each opens a single-field-first sheet. Required fields only; everything else optional.
Target: capture a task in 20 seconds or fewer.

### 10.2 `/tasks`

- Views: `My work`, `Team`, `Blocked`, `Overdue`, `Done`.
- Filters: department, owner, priority, due range, source, tag.
- Table on desktop, cards on mobile.
- Bulk actions: assign, status, due date.
- Saved views reuse `SavedView` with `scope = "tasks"`.
- Plan actions from assessments appear in a separate collapsible section, read-only,
  with a `Convert to task` action.

### 10.3 `/exceptions`

- Summary: breached, due soon, open, resolved this week, recurrence rate.
- Queue columns: reference, title, department, owner, severity, SLA remaining, status.
- Detail: timeline, customer impact, root cause, corrective action, linked tasks,
  linked prior exception, resolution note.
- Status flow: `open → investigating → resolved`, plus `reopened`.
- Manual escalation with reason and level.

### 10.4 `/routines`

- Today's runs by department and shift.
- Routine definitions with cadence and owner.
- Run screen: one item per row, large tap targets, pass/fail/NA, value input,
  note, progress bar, completion summary.
- Failed required check prompts "Create exception?" with prefilled context.
- Missed runs are visible, not hidden.

### 10.5 `/handover`

- Chronological handovers by department.
- Filter: unacknowledged, today, this week.
- Handover detail: summary, open issues, safety notes, next actions, acknowledgements.
- New handover pulls open tasks and exceptions automatically; the supervisor can
  exclude items and add context.
- Closing a shift with open exceptions requires a handover; closing with no handover
  records `closed_without_handover` and alerts the manager.

### 10.6 `/kpis`

- Targets versus latest reading by department.
- Status: `good / watch / risk / stale / no target`.
- Department owner and last update.
- Inline reading entry with period end and note.
- Target editing for managers.
- Link to the existing KPI ledger for history and export.

### 10.7 `/team`

- Department cards: lead, headcount, open tasks, open exceptions.
- Roster: member, role, department, primary, workload.
- Add or move member.
- Department settings: name, key, timezone, huddle day and time, visibility.

## 11. Workflows and state machines

### 11.1 Task

```
todo → in_progress → done
  ↓         ↓
blocked ←───┘
  ↓
todo / in_progress

any → cancelled (reason required)
done → todo (reopen, audited)
```

Rules:

- `blocked` requires `blocked_reason`.
- `done` records `completed_at` and an optional completion note.
- Assignment changes are audited.
- Overdue is computed, not stored.
- A task with `sla_due_at` past due appears in escalations even if not blocked.

### 11.2 Exception

```
open → investigating → resolved
  ↑          |
  └─ reopened┘

open/investigating → escalated (level increases, status unchanged)
```

SLA defaults, configurable per organisation:

| Severity | First response | Resolution |
|---|---|---|
| critical | 30 minutes | 4 hours |
| high | 2 hours | 1 business day |
| normal | 8 hours | 3 business days |
| low | 1 business day | 5 business days |

Escalation:

- At 75% of SLA, notify owner.
- At breach, notify owner and department lead.
- At 2x breach, notify manager and owner.
- Manual escalation always notifies the next level and records a reason.

### 11.3 Shift

```
planned → open → closed
```

- Only one open shift per department at a time.
- Opening a shift prompts the start routine.
- Closing a shift requires a handover when open exceptions exist.
- The next shift lead must acknowledge within the configured window (default 12 hours)
  or the handover is flagged to the manager.

### 11.4 Routine run

```
open → completed
open → missed (lazy or scheduled when the window closes)
```

- A run is created lazily on first view after the due time, and by a scheduled job.
- `completed` requires all required items to have a state.
- `missed` is terminal; a late run is a new run with `late = true` in the note.

### 11.5 Handover

```
draft → submitted → acknowledged
```

- `submitted` notifies the next shift lead and department manager.
- `acknowledged` records who and when.
- A handover cannot be edited after acknowledgement; corrections are new notes.

## 12. Notifications and automation

### 12.1 Events

- Task assigned, due soon, overdue, blocked, completed.
- Exception created, owner changed, SLA warning, SLA breach, escalated, resolved.
- Handover submitted, unacknowledged, acknowledged.
- Routine due, missed, failed required check.
- KPI off target or stale.
- Document expiring within 14 and 3 days.

### 12.2 Channels

- In-app: `ops_notifications`, bell badge, `/notifications` unified view.
- Email: immediate for critical events; daily digest otherwise.
- Webhook: `task.*`, `exception.*`, `handover.*`, `routine.*`, `kpi.*`.
- Telegram: optional per-user preference, reusing the existing bot identity.

### 12.3 Digests

- Daily per-user digest at the department huddle time in the department timezone.
- Weekly manager digest: completion rate, SLA, routines, KPI movement, unacknowledged
  handovers.
- Respect `UserPref.notify_email` and quiet hours.
- Digests are transactional, never mixed with marketing.

### 12.4 Scheduler

Vercel has no long-running worker. Use a secured cron endpoint:

`POST /api/v1/ops/cron/tick` with `X-Elipsis-Cron` secret.

Tick responsibilities, idempotent and minute-bucketed:

- Create due routine runs and mark missed runs.
- Evaluate SLA warnings and breaches.
- Send digests at the right local time.
- Flag unacknowledged handovers.
- Detect stale KPI readings.

The same tick can be invoked by an external scheduler every 15 minutes.

## 13. Integrations

### 13.1 Inbound

- `POST /api/v1/ops/tasks`
- `POST /api/v1/ops/exceptions`
- `POST /api/v1/ops/metrics`
- `POST /api/v1/ops/routines/{id}/runs`
- `POST /api/v1/ops/handover`

Requirements:

- Bearer `ApiToken`, org-scoped, revocable.
- `Idempotency-Key` header or `source_ref` per object.
- Rate limits per token.
- Validation errors returned with field paths.
- Every write audited with `source = api`.

Extend CSV import to `tasks` and `kpi_targets`, reusing the existing import pattern
(`services_operations.import_csv`).

### 13.2 Outbound

Reuse `services_webhooks` with HMAC signatures. Event payloads include org, department,
object, actor, and a stable event id. Retries follow the existing delivery model.

No direct TMS/WMS/ERP connector in phase one. Teams can integrate through the API,
webhooks, or CSV.

## 14. Security and privacy

- Central permission service only; no route-local role checks.
- Department scoping enforced server-side on every read and write.
- Cross-department admin reads are audit-logged.
- Deny by default; non-members get 404.
- CSRF protection already applies to state-changing forms; new routes inherit it.
- Rate-limit capture, bulk actions, API writes, and cron.
- No internal IDs in public links.
- Handover content is private to the organisation.
- Data retention follows the published DPA; deleted accounts remove personal notes
  while preserving aggregate audit records.

## 15. UX and accessibility

- WCAG 2.2 AA. Keyboard-first, visible focus, labelled inputs.
- Mobile-first capture: sticky action bar, 44px minimum targets, no horizontal scroll.
- Reduced-motion support.
- Plain-language labels: "Exception", not "Operational incident", in the daily UI.
- Empty states always name the next action.
- Confirmation messages state what changed and what happens next.
- One primary action per screen.
- Numbers use the organisation locale and timezone.
- Performance: `/today` under 2 seconds on a mid-range phone with 50 tasks and
  20 exceptions.

## 16. Data migration and backfill

One Alembic revision, e.g. `9d1e2f3a4b5c_daily_operations.py`.

Steps:

1. Create new tables.
2. Add nullable columns to `operational_incidents`, `operational_metrics`,
   `audit_events`, `departments`.
3. Seed departments from `elipsis_api/departments.py` for organisations that have none,
   on first access rather than bulk, to avoid guessing.
4. Map `OrgOwner.department` free text to `Department.key` where it matches a known
   key; leave unmatched rows null and report them.
5. Backfill incident SLA due dates from severity and creation time.
6. Backfill `ops_tasks` from open `RoadmapItem` rows only when the
   `ELIPSIS_DAILY_OPS_UNIFY_ACTIONS` flag is on; keep `roadmap_item_id`.
7. Do not delete `roadmap_items`.
8. Run on a branch first; verify counts, orphans, and permission scope.

Rollback: new tables and nullable columns are safe to drop. The task backfill records
its source so it can be reversed without touching assessments.

## 17. Feature flags and rollout

- `ELIPSIS_DAILY_OPS_ENABLED` — mount `/today`, `/tasks`, `/exceptions`,
  `/routines`, `/handover`, `/team`.
- `ELIPSIS_DAILY_OPS_TASKS` — standalone tasks.
- `ELIPSIS_DAILY_OPS_SLA` — SLA and escalation.
- `ELIPSIS_DAILY_OPS_ROUTINES` — routines.
- `ELIPSIS_DAILY_OPS_DIGEST` — digests and cron.
- `ELIPSIS_DAILY_OPS_UNIFY_ACTIONS` — merge plan actions into tasks.
- `ELIPSIS_DAILY_OPS_CRON_SECRET` — cron authentication.

Rollout:

1. Internal org with seed data.
2. Three design-partner logistics departments.
3. All paying operator accounts.
4. Public default for new signups.
5. Assessment-only orgs see `/today` as an empty-state invitation.

## 18. Open decisions

1. **Pricing.** Is daily operations included in the $29 operator plan, or a per-seat
   add-on? Recommendation: include up to 25 members, then per-seat.
2. **Department visibility default.** Org-wide or department-only? Recommendation:
   org-wide read for `manager` and `owner`, department-only for others.
3. **Shift complexity.** Is a shift required, or optional for teams without formal
   shifts? Recommendation: optional; `/today` works without a shift.
4. **Default routines.** Ship three templates: dispatch start-of-shift, warehouse
   receiving, compliance weekly. Recommendation: yes, opt-in.
5. **Task unification.** Convert open assessment actions immediately or dual-show?
   Recommendation: dual-show for two releases, then convert.
6. **Metric catalog.** Keep the fixed 8 metrics or allow custom metrics in phase D?
   Recommendation: fixed for now; custom later with a unit and direction field.
7. **SLA defaults.** Adopt the table in 11.2 or per-org on day one? Recommendation:
   defaults plus per-org overrides.
8. **Free tier.** Show `/today` read-only on free, or hide it? Recommendation: show a
   one-department, one-routine preview to drive conversion.

## 19. Testing

Required automated tests:

- Organisation isolation: no cross-org reads or writes.
- Department isolation: non-member gets 404; manager sees org.
- Role matrix for every action in section 6.2.
- Task transitions, blocked reason, reopen, assignment audit.
- Exception SLA computation, warning, breach, escalation levels, reopen.
- Shift single-open rule and close-without-handover flag.
- Handover acknowledgement window.
- Routine lazy creation, completion validation, missed runs.
- KPI target resolution by department, stale detection, direction handling.
- Notification creation, read state, digest deduplication.
- Cron idempotency and secret rejection.
- API idempotency and token revocation.
- Migration and backfill counts.
- Mobile snapshot or responsive smoke test for `/today`, `/tasks`, `/routines`.

Extend the existing suite in `tests/`; follow `tests/conftest.py` fixtures and the
current `TestClient` pattern. The suite must be green before phase A merges; fix the
three known failures first.

## 20. Delivery phases

### Phase A — Foundation and Today (2 weeks)

- Fix the three failing tests and the `/settings` template error.
- Add departments, department members, shifts, handovers, notifications schema.
- Department seeding and membership UI.
- `/today` using existing metrics, incidents, documents, and plan actions.
- Quick capture for task, exception, metric, and note.
- Nav change and post-login redirect.
- Permission service extensions and tests.

Exit: a design-partner supervisor can open `/today`, see real work, capture a task,
and close a shift with a handover.

### Phase B — Tasks, team, routines (2 weeks)

- Standalone `ops_tasks`, board, detail, bulk actions, saved views.
- `/team` roster and workload.
- Routines, items, runs, checks, missed detection.
- Convert-to-task from plan actions.
- API for tasks and routines.

Exit: a department runs a full week on tasks and routines without touching an
assessment.

### Phase C — Exceptions, KPIs, notifications (2 weeks)

- Exception SLA, escalation, recurrence, corrective tasks.
- KPI targets, stale detection, department ownership.
- Persistent notifications, daily digest, weekly manager digest.
- Cron tick and webhook events.
- Unify plan actions into tasks behind the flag.

Exit: SLA and KPI breaches reach the right person without manual chasing.

### Phase D — Integrations and polish (2 weeks)

- Inbound API hardening, idempotency, rate limits.
- CSV import for tasks and targets.
- Mobile capture polish, PWA install, offline-safe drafts.
- Saved views, search across daily objects.
- Performance and accessibility pass.

Exit: a mobile supervisor can run a shift end to end on a phone.

### Phase E — Repositioning (1 week)

- Update pricing copy and comparison.
- Home and onboarding lead with the daily loop; assessment becomes the first diagnosis.
- Update README, `STREAMLINE_TODO.md`, and the platform guide cross-reference.
- Customer migration notes.

Exit: new signups understand Elipsis as a daily tool first and diagnosis second.

## 21. Acceptance criteria

1. A supervisor can open `/today` with no assessment and see tasks, exceptions,
   compliance, and handover.
2. A task can be created, assigned, blocked with a reason, completed, and reopened
   without any assessment record.
3. A user sees only their departments unless their role grants org-wide visibility.
4. Every department-scoped page returns 404 to a non-member.
5. Closing a shift with an open exception requires a handover.
6. The next shift lead sees the handover, acknowledges it, and the acknowledgement is
   audited.
7. A routine run is created automatically when due, cannot complete with missing
   required checks, and is marked missed after its window.
8. A critical exception notifies the owner, then the lead at breach, then the manager
   at 2x breach.
9. KPI status resolves against the department target, falls back to the org target, and
   flags stale readings.
10. Daily digest arrives at the department's local huddle time and contains only that
    user's work.
11. Quick capture creates a task or exception in 20 seconds or fewer on a phone.
12. Existing assessment, results, marketplace, and admin flows continue to pass their
    tests.
13. The full suite is green, including the three baseline failures.

## 22. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Scope drifts into TMS or dispatch | Enforce the non-goals; incidents reference shipments, never own them. |
| Duplicate task systems (`RoadmapItem` and `OpsTask`) | Dual-show, then convert with a flag and reversible backfill. |
| Supervisors do not adopt data entry | Quick capture, routines, and auto-pull handovers; measure time-to-capture. |
| Department model is wrong for matrix organisations | Many-to-many membership plus a primary department. |
| SLA defaults do not fit 24/7 operations | Per-org overrides and business-hours calendars in phase D. |
| Timezone errors | Store UTC, render in department timezone, test with two timezones. |
| Daily features cannibalise paid assessment revenue | Keep diagnosis and implementation value explicit; include daily ops in the operator plan. |
| Cron is unreliable on Vercel | Idempotent tick plus lazy evaluation on read; external scheduler supported. |
| Notification fatigue | Severity-based routing, digest batching, and per-user preferences. |

## 23. Definition of done

The transformation is complete when a logistics department can run its week inside
Elipsis without a spreadsheet or a chat group:

- every shift starts on `/today`;
- every commitment is a task with an owner and a due time;
- every service failure is an exception with an SLA;
- every recurring control is a routine;
- every shift ends with a handover;
- every week ends with a review that shows movement against the last assessment.
