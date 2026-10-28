# Elipsis Platform Master Plan

Market strategy, target audience, competitive position, product gaps, and the feature roadmap for the diagnostic engine and operating layer.

Status: Draft for approval
Version: 2.0
Date: 28 October 2026
Owner: Product and Engineering
Related documents: `docs/DAILY_OPERATIONS_TRANSFORMATION.md` (technical annex), `docs/PLATFORM_UPGRADE_IMPLEMENTATION_GUIDE.md` (marketplace specification), `docs/COMPETITIVE_EDGE.md`, `docs/SERVICE_DELIVERY_STANDARD.md`

---

## 1. Executive summary

Elipsis is a diagnostic engine for logistics operations. It measures how a logistics
business actually runs, identifies the constraints that cost the most money, and turns
the findings into a costed, owned, sequenced implementation roadmap.

The product exists because mid-market logistics operators are caught between two bad
options. Enterprise consultancies deliver credible diagnosis but cost more than the
problem appears to justify, take weeks, and leave the operator with a document rather
than a working cadence. Operational software sells execution but assumes the operator
already knows what to fix, and usually requires integrations, capital, and a long
implementation before value appears.

Elipsis owns the decision layer between the two: diagnosis, cost of inaction, priority,
roadmap, implementation options, and proof of movement.

The main goal is not to become another dashboard, TMS, or marketplace. The main goal is
to be the most credible, fastest, and most locally relevant way for a logistics operator
to understand what is wrong, what it costs, and what to do next.

The platform is delivered in three layers:

1. **Diagnose** — a structured 63-question assessment across seven pillars, producing an
   index, 36 executive metrics, ranked pain points, costed friction, and a 90-day plan.
2. **Implement** — a verified implementation marketplace and trusted partner path, with
   no commission, so the roadmap can become operating change.
3. **Operate** — a daily control tower (tasks, exceptions, routines, handover, KPIs) that
   keeps the diagnosis alive, generates continuous evidence, and earns repeat use.

Diagnosis is the wedge. Implementation is the value capture. Daily operations is the
retention engine. The product is strongest when all three form one closed loop.

This document defines who the platform serves, what those users need, who the peers are,
how peers deliver and tailor their services, where Elipsis has a durable edge, what is
currently weak, and which features will take the platform to the next level.

---

## 2. Product thesis

### 2.1 What Elipsis sells

Elipsis sells **clarity that can be defended and acted on**.

The deliverable is not a questionnaire result. It is a decision package:

- a trustworthy score and maturity band;
- the three constraints that matter most;
- the cost of leaving them unresolved;
- a sequenced roadmap with owners, dates, dependencies, and KPIs;
- transparent assumptions the buyer can challenge;
- implementation options with verified partners;
- a way to prove movement later.

### 2.2 What Elipsis is not

- Not a TMS, WMS, ERP, dispatch system, telematics platform, or load board.
- Not a consulting firm selling billable discovery.
- Not a generic survey tool.
- Not a marketplace that takes a commission on implementation.
- Not an AI product that generates advice without evidence and human review.

### 2.3 The product promise

> In one working session, a logistics operator can see how their operation really runs,
> what the constraints cost, and a credible plan to fix them — without a six-week
> consulting engagement or a system integration project.

### 2.4 The wedge and the expansion path

| Stage | Offer | Purpose |
|---|---|---|
| Wedge | Free diagnostic | Low-friction proof of insight. |
| First purchase | Full Assessment | The report, roadmap, and board pack. |
| Recurring | Operator plan | Unlimited assessments, team, daily operations. |
| Expansion | Department diagnostics | Land one department, expand across the operation. |
| Implementation | Marketplace / trusted partner | Convert diagnosis into delivery. |
| Proof | Re-assessment and movement | Demonstrate outcomes and renew. |

The commercial logic is deliberate: the diagnostic must be cheap enough to try,
credible enough to pay for, and useful enough to repeat. Every later feature should
strengthen one of those three properties.

---

## 3. The problem

### 3.1 The operator's reality

Mid-market logistics businesses typically run on a mix of ERP modules, spreadsheets,
WhatsApp groups, email, and experienced people who hold the process together. Growth
adds volume, sites, vehicles, staff, and exceptions faster than it adds control.

The symptoms are consistent:

- service promises are missed and discovered late;
- cost per shipment is unknown or contested;
- cash conversion is slow because invoicing depends on manual reconciliation;
- utilisation and capacity are estimated, not measured;
- compliance depends on memory and renewal scrambles;
- customer service absorbs avoidable contact;
- one or two people are single points of failure;
- improvement ideas compete without a shared economic basis.

### 3.2 Why the problem persists

| Root cause | Consequence |
|---|---|
| No shared definition of operational health | Every leader optimises a different number. |
| No cost of friction | Improvements are argued on opinion, not economics. |
| Consulting is slow and expensive | Diagnosis is reserved for crises or large enterprises. |
| Software assumes maturity | Tools are bought before the constraint is understood. |
| Data is fragmented | Operators cannot trust a single view. |
| Local context is ignored | Global benchmarks and assumptions do not reflect fuel, FX, informal transport, or infrastructure reality. |
| No ownership after the report | Recommendations do not become work with names and dates. |
| No proof of movement | Buyers cannot tell whether anything improved. |

### 3.3 The cost of the status quo

The platform does not need to claim a precise market number to make the case. The cost
is visible in four places:

1. **Labour drag** — repeated manual work, rework, and approval loops.
2. **Service failure** — claims, penalties, lost accounts, and expedited recovery.
3. **Capital misallocation** — software, vehicles, and headcount bought against the
   wrong constraint.
4. **Decision latency** — weeks lost because no one can defend a priority.

Elipsis converts those into an explicit, editable financial model so the buyer can
challenge the assumptions rather than accept a black box.

### 3.4 Why now

Three market conditions make the timing credible. These are public reference points, not
Elipsis customer results, and they are recorded in `elipsis_api/benchmarks.py`:

1. **The segment is large and fragmented.** Kenya alone has 14,479 registered logistics
   companies; 55% employ 10–49 people and 58% report USD 100K–1M revenue
   (InfobelPRO / Business Registration Service, 2026). Fragmented markets reward a
   product that can serve many operators without a bespoke engagement.
2. **Automation intent is high but uneven.** 78% of Kenyan firms automated at least one
   process in the previous 12 months, while transport and storage represented only 3% of
   respondents in the Central Bank of Kenya CEO survey (September 2025). The intent
   exists; the diagnostic discipline does not.
3. **The long tail is the economy.** Kenya has 7.41 million MSMEs, about 98% of
   businesses and roughly 33.8% of GDP (MSEA / KNBS, 2025). Most will never buy enterprise
   consulting or a multi-year transformation programme, but many will pay for a clear
   decision and a credible plan.

At the same time, buyers are more sceptical of software promises, AI claims, and
unverifiable savings. That favours a platform whose method, assumptions, and evidence are
visible.

---

## 4. Target audience

### 4.1 Ideal customer profile

The current ICP is defined in `elipsis_api/benchmarks.py`:

| Attribute | Definition |
|---|---|
| Sector | Logistics and field-operations companies: freight forwarding, transport, warehousing, distribution, field service. |
| Size | 10–1,000 staff. |
| Initial reference market | Kenya. The framework is not country-specific. |
| Typical firm | 10–49 staff, USD 100K–1M revenue, single or few sites. |
| Operating profile | Growth or margin pressure, fragmented systems, limited dedicated transformation resource. |
| Trigger | New COO or finance lead, service failure, expansion, funding, cost pressure, or a stalled software project. |

The ICP should be narrowed further in go-to-market even though the product can serve a
wider range. The strongest early segment is the **growth-stage logistics operator with
50–300 staff, multiple sites or fleets, and no internal transformation team**.

### 4.2 Sub-sector segments

| Segment | What they do | Primary pain | Fit |
|---|---|---|---|
| Freight forwarding and clearing | Coordinate carriers, customs, documents, clients | Document chasing, handoffs, quote-to-cash | High |
| Haulage and trucking | Move goods with owned or contracted fleet | Utilisation, on-time delivery, cost per trip | High |
| 3PL and contract logistics | Operate warehousing and distribution for clients | SLA proof, billing accuracy, multi-client complexity | High |
| Warehousing and distribution | Receive, store, pick, dispatch | Inventory accuracy, cycle time, space and labour | High |
| Last-mile and courier | High-volume delivery | Route density, failed delivery, customer contact | Medium-high |
| Fleet leasing and managed transport | Provide assets and drivers | Maintenance, compliance, asset visibility | Medium |
| Field service and installations | Dispatch technicians and parts | Scheduling, first-time fix, parts availability | Medium |
| Customs brokerage | Clear goods and manage compliance | Turnaround, documentation, exception handling | Medium |

### 4.3 Size and maturity fit

| Segment | Staff | Fit | Why |
|---|---|---|---|
| Micro operator | 1–9 | Low | Too few handoffs; diagnosis overkill. |
| Emerging operator | 10–49 | High | Enough complexity, low access to consulting. |
| Growth operator | 50–300 | Highest | Complexity, budget, and urgency coincide. |
| Mid-market group | 300–1,000 | High | Multi-site roll-up value; longer sales cycle. |
| Large enterprise | 1,000+ | Low for self-serve | Existing analytics teams, procurement, integration demands. Serve through consulting partners. |

### 4.4 Buyer personas

#### Economic buyer — Managing Director / CEO

- **Context:** 10–300 staff, owner-led or founder-led, personally exposed to margin.
- **Goals:** Grow without proportional cost, protect service reputation, avoid a bad
  software bet.
- **Frustrations:** Consultants who do not understand the operation; dashboards that
  show data without a decision; managers who report activity, not outcomes.
- **What they want to see:** A single score they can defend, the top three constraints,
  the cost of inaction, a plan with owners, and a credible path to execution.
- **Success:** A board-ready decision in one session, at a price that does not require a
  procurement project.

#### Champion — COO / Operations Director

- **Context:** Accountable for service, cost, and capacity across departments.
- **Goals:** Control the operating week, reduce firefighting, prove improvement.
- **Frustrations:** No shared view across dispatch, warehouse, transport, and finance;
  improvement ideas compete without evidence.
- **What they want to see:** Department-level diagnosis, ranked constraints, a roadmap
  they can assign, and daily visibility.
- **Success:** Fewer escalations, measurable SLA and cost movement, a plan the team owns.

#### Financial buyer — Finance Director / CFO

- **Context:** Approves spend and defends ROI.
- **Goals:** Margin protection, cash conversion, capital discipline, auditability.
- **Frustrations:** Unverifiable savings claims; software business cases built on
  optimism.
- **What they want to see:** Transparent assumptions, cost of inaction, payback, and a
  report that survives scrutiny.
- **Success:** A defensible business case and a renewal they can justify.

#### Operational user — Department head

- **Context:** Dispatch, warehouse, transport, customer service, compliance, or finance.
- **Goals:** Get through today, remove the recurring blocker, protect the team.
- **Frustrations:** Another report that creates work without removing it.
- **What they want to see:** Their department's constraint, a small set of actions, and
  tools that help run the shift.
- **Success:** Less rework, clearer ownership, a daily tool worth opening.

#### Transformation lead / PMO

- **Context:** Internal owner of change, often part-time.
- **Goals:** A governed roadmap, evidence, and progress reporting.
- **What they want to see:** Owners, dependencies, KPIs, version history, and exports.
- **Success:** A plan that stays current and a review that shows movement.

#### Technical buyer — IT / Data lead

- **Context:** Owns systems, integrations, and security review.
- **Goals:** Low integration burden, clear data handling, controlled access.
- **What they want to see:** No mandatory integration, export and API options, security
  documentation, role-based access, audit trail.
- **Success:** Approval without a long security exception.

#### Channel persona — Consultant or implementation partner

- **Context:** Advises logistics clients and needs credible diagnostic IP.
- **Goals:** Win engagements faster, standardise discovery, add value beyond opinion.
- **What they want to see:** White-label or co-branded reports, facilitator mode, client
  management, and a partner directory listing.
- **Success:** Shorter sales cycles and higher close rates.

### 4.5 User personas and daily context

| Persona | Environment | Device | Frequency | Core need |
|---|---|---|---|---|
| MD / CEO | Office, meetings, travel | Laptop, phone | Monthly / quarterly | Decision and board narrative. |
| COO / Ops Director | Office and floor | Laptop, phone | Daily / weekly | Control and movement. |
| Department head | Floor, warehouse, yard | Phone, shared terminal | Every shift | Today's work and blockers. |
| Supervisor | Floor | Phone | Every shift | Assign, escalate, hand over. |
| Analyst | Office | Laptop | Daily / weekly | Data entry, verification, reporting. |
| Finance | Office | Laptop | Monthly | ROI, assumptions, cash. |
| Consultant | Client sites | Laptop | Per engagement | Fast, credible diagnosis. |
| Bidder | Own office | Laptop | Per opportunity | Qualified demand and context. |

### 4.6 Anti-personas

Do not optimise for:

- owner-operators with fewer than 10 staff and no meaningful handoffs;
- enterprises with an existing analytics and transformation function that require
  bespoke procurement and integration;
- buyers who want a dispatch or telematics product;
- organisations unwilling to share a baseline or let staff participate;
- price-only buyers seeking a free audit with no intention to act.

### 4.7 Buying committee and motion

The typical buying committee is the MD (economic), COO (champion), Finance (approval),
and IT (security). The motion is:

1. Free diagnostic creates a shared, specific conversation.
2. Full Assessment converts insight into a paid decision package.
3. Operator plan converts the report into a recurring cadence.
4. Marketplace or trusted partner converts the plan into implementation.
5. Re-assessment converts delivery into proof and renewal.

The sale is consultative but product-led. The report does the persuading; the platform
removes the friction between insight and action.

### 4.8 Market sizing and qualification

Elipsis should size the market bottom-up rather than quote a top-down analyst figure.
The method is:

1. Count registered logistics firms in the target market by size band.
2. Apply the fit filters in 4.3 (10–1,000 staff; 50–300 highest fit).
3. Apply the operating-complexity filter (multi-site, fleet, warehouse, or high
   transaction volume).
4. Apply the buying trigger filter (growth, service failure, funding, cost pressure).
5. Multiply by a validated willingness-to-pay from design partners.

Public reference point for the initial market: 14,479 registered logistics companies in
Kenya, with 55% employing 10–49 people (InfobelPRO / BRS, 2026). That is a large enough
pool for a focused beachhead without requiring enterprise sales.

Qualification checklist for a sales conversation:

| Criterion | Qualifies when |
|---|---|
| Size | 10–1,000 staff; 50–300 is the sweet spot. |
| Complexity | Multiple handoffs, sites, vehicles, or client SLAs. |
| Pain | Service, cost, cash, capacity, or compliance pressure is felt by a leader. |
| Authority | The economic buyer or a credible champion is accessible. |
| Willingness | The operator will share a baseline and let staff participate. |
| Urgency | A trigger exists: growth, funding, failure, new leadership, or a stalled system. |
| Ability to act | The organisation can assign owners and start within 90 days. |

Disqualify when the operator wants a free audit with no intention to act, demands a
bespoke build before the first diagnosis, or requires an integration just to start.

---

## 5. What the market wants to see

### 5.1 What buyers want from the report

1. **A number they trust** — a score with a stated method, confidence, and evidence.
2. **Plain language** — findings a busy operator can read without a glossary.
3. **The top three constraints** — not 36 equal findings that paralyse prioritisation.
4. **Cost of inaction** — the financial consequence of leaving the constraint in place.
5. **Local relevance** — assumptions that reflect their currency, labour cost, fuel,
   FX, infrastructure, and informal operating reality.
6. **Peer context** — comparison with similar size, sector, and geography, only where
   the sample is credible.
7. **A sequenced roadmap** — quick wins separated from structural bets.
8. **Owners and dates** — every action has a name, a due date, a dependency, and a KPI.
9. **Transparent assumptions** — editable inputs, not a black box.
10. **Board-ready output** — PDF, Excel, JSON, share link, print pack.
11. **Implementation options** — a trusted partner and a verified marketplace, with no
    hidden commission.
12. **A way to prove movement** — re-assessment, trend, and an audit trail.

### 5.2 What users want from the platform day to day

- A single place to see what needs attention now.
- Capture that takes seconds, on a phone, without training.
- Clear ownership and escalation.
- Fewer status meetings because the status is visible.
- Compliance and recurring checks that do not depend on memory.
- A handover that preserves context across shifts.
- KPIs that are current, owned, and interpreted.
- Confidence that data is private and access is controlled.

### 5.3 What the market does not want

- Another dashboard with no recommended action.
- A tool that requires a six-month integration before value.
- A consultant-style report that cannot be executed.
- A marketplace that pushes one vendor.
- Opaque scoring or savings claims.
- A per-seat tax on basic operational hygiene.

### 5.4 The report specification

The report is the product. It must be readable by a managing director in ten minutes and
defensible by a finance lead in a review. The required structure is:

1. **Decision page** — score, maturity band, confidence, movement since the last
   assessment, and the single most important sentence.
2. **What it costs** — savings potential, investment, payback, and the cost of inaction,
   with the assumptions summarised and editable.
3. **Top three constraints** — what each one is, where it shows up, what it costs, and
   what happens if nothing changes.
4. **The plan** — three phases, actions, owners, dates, dependencies, KPIs, and the first
   three things to do next week.
5. **Department view** — the same verdict at department level, with the constraint each
   department owns.
6. **Evidence and confidence** — what the result is based on, what is uncertain, and what
   evidence would raise confidence.
7. **Benchmarks** — peer comparison only where the cohort is credible, with sample size
   and method shown.
8. **Assumptions and method** — every financial input, every cap, and the published
   method note.
9. **Implementation options** — the trusted partner path, the marketplace path, and what
   a good implementation brief must contain.
10. **Appendix** — answers, evidence attachments, glossary, and version history.

Quality bar:

- Plain language. No consulting jargon without a definition.
- One decision per page. The reader should never have to infer the takeaway.
- Every number has a source, a range, or an assumption label.
- Every recommendation has an owner, a date, and a KPI.
- No orphan findings. If it is in the report, it is in the plan or explicitly deferred.
- Confidence is stated, not implied.
- Red flags and limitations are visible, not buried.
- Local currency and operating context by default.
- Accessible, print-ready, and readable on a phone.
- AI-assisted text, if used, is labelled and human-reviewed.

Anti-patterns to avoid:

- Leading with 36 metrics instead of the verdict.
- Generic recommendations that could apply to any business.
- Hidden assumptions or a single savings number with no range.
- A roadmap with no owners or dependencies.
- Benchmark comparisons from an unrepresentative cohort.
- A report that cannot be exported, shared, or annotated.

---

## 6. Competitive landscape

### 6.1 Peer categories

| Category | Representative peers | What they sell | Typical delivery | Where they fall short for our ICP |
|---|---|---|---|---|
| Advisory and maturity diagnostics | KPMG Atlas, Deloitte, PwC, McKinsey, boutique logistics consultancies | Credibility, benchmarks, transformation programmes | Project-based, workshops, interviews, PDF, implementation upsell | Cost, duration, dependency, generic benchmarks, no operating cadence. |
| Fleet and telematics | Samsara, Motive, Geotab, Fleetio | Asset visibility, safety, maintenance, compliance | Hardware + subscription + onboarding | Execution data, not diagnosis; capital and installation; assumes the constraint. |
| Supply-chain visibility | project44, Descartes, Shippeo, Manhattan | Shipment visibility, routing, execution | Enterprise integration, implementation partners | Long deployments, integration heavy, enterprise pricing. |
| TMS / WMS / ERP | SAP TM, Oracle OTM, Odoo, Microsoft Dynamics, regional vendors | Transactional system of record | Licence + implementation + systems integrator | Months to value; configuration and customisation cost; requires mature process. |
| Frontline operations and inspections | SafetyCulture | Checklists, audits, frontline capture | Per-seat SaaS, templates, mobile | Strong at capture, weak at economic diagnosis and prioritisation. |
| Status quo | Excel, WhatsApp, email, internal analysts | Familiar, cheap, flexible | Manual | Fragile, person-dependent, no audit trail, no benchmark, no proof. |

### 6.2 How peers deliver services

Five delivery models dominate:

1. **Project consulting** — fixed-fee or time-and-materials discovery, interviews,
   workshops, maturity model, report, and a separate implementation proposal. High
   credibility, high cost, slow.
2. **Subscription software** — monthly or annual licence, onboarding, support tiers,
   usage-based or per-asset pricing. Fast to buy, slow to realise value without process
   change.
3. **Land-and-expand platforms** — a narrow initial module, then upsell into modules and
   services. Requires a strong initial hook and low integration burden.
4. **Partner-led implementation** — software vendor plus systems integrator or
   consultancy. Scales delivery but fragments accountability and raises cost.
5. **Self-serve assessment** — free or low-cost online diagnostic. Cheap acquisition,
   weak depth, low perceived credibility, poor conversion to action.

Elipsis combines the credibility of model 1, the economics of model 2, the hook of model
4, and the reach of model 5 — without the cost or dependency of any single one.

### 6.3 How peers tailor their platforms

| Mechanism | How peers use it | Implication for Elipsis |
|---|---|---|
| Industry templates | Prebuilt questions, KPIs, and workflows per vertical. | Ship logistics sub-sector templates. |
| Configuration | Custom fields, statuses, thresholds. | Expose department and KPI configuration, not a settings maze. |
| Custom development | Paid enhancements and bespoke reports. | Avoid; use exports, API, and white-label instead. |
| Connectors | Integrations with ERP, TMS, WMS, accounting. | Start with CSV and API; add read-only connectors later. |
| Dedicated success | Named CSM, QBRs, onboarding services. | Productise success through reports, reviews, and service standards. |
| Partner ecosystem | Consultants and integrators deliver and customise. | Build a verified partner directory and consultant mode. |
| White-label | Agencies and consultants rebrand the tool. | Offer a consultant edition with co-branded reports. |

### 6.4 The gap in the market

No peer currently combines all of the following for a mid-market logistics operator:

- a credible, plain-language diagnosis;
- an explicit financial model with editable assumptions;
- department-level granularity;
- local operating context;
- a sequenced implementation roadmap;
- verified implementation options without commission;
- a daily operating cadence that keeps the diagnosis alive;
- proof of movement through re-assessment.

That combination is the platform's strategic space.

---

## 7. Competitive edge

The edge must be specific, defensible, and visible in the product. The following ten
edges are ordered by importance.

### 7.1 Closed loop from diagnosis to proof

**What:** Assess → cost the constraint → assign owned actions → run the cadence →
implement through a verified partner → re-assess and prove movement.

**Why it is defensible:** Peers sell a point solution. The loop creates switching costs,
compounding data, and a credible outcome story.

**Product proof:** Results, roadmap, action board, marketplace, operations ledger,
re-assessment, trend history.

**How to protect:** Never let a report end without a next action; never let an action
live without an owner; never let an implementation end without a re-score.

### 7.2 Costed friction with transparent assumptions

**What:** Every constraint is translated into labour exposure, service cost, working
capital, or capital misallocation, with editable inputs and stated caps.

**Why it is defensible:** It converts an opinion into an economic case a finance lead can
defend. Most peers either avoid numbers or hide them in a black box.

**Product proof:** `AssessmentAssumption`, financial model, assumptions editor, exports,
method note (`elipsis_api/benchmarks.py`).

**How to protect:** Publish the method, invite challenge, and never claim audited savings.

### 7.3 Local context by design

**What:** Currency, labour rates, fuel volatility, FX, infrastructure, informal
transport, and multi-site reality are explicit assumptions, not footnotes.

**Why it is defensible:** Global peers benchmark against conditions the operator does not
operate in. Local credibility is hard to copy without local data.

**Product proof:** Kenya-first reference market, localised financial model, currency
configuration.

**How to protect:** Build a consented benchmark cohort by country, sector, and size.

### 7.4 Department-level diagnosis and roll-up

**What:** Diagnose operations, dispatch, warehouse, transport, customer service, finance,
compliance, procurement, people, and technology separately, then roll up to the company.

**Why it is defensible:** Department buy-in is how mid-market change actually happens.
Company-only diagnostics create a report the department heads do not own.

**Product proof:** `elipsis_api/departments.py`, department-scoped assessments, company
pulse.

**How to protect:** Make department ownership the default expansion motion.

### 7.5 No integration prerequisite

**What:** A credible diagnosis from structured operator input in one session, with no
mandatory ERP, TMS, WMS, or telematics connection.

**Why it is defensible:** Integration is the biggest cause of stalled operational
software projects. Removing it collapses time to value and widens the addressable market.

**Product proof:** 63-question instrument, evidence attachments, CSV/API options.

**How to protect:** Keep the core independent of integrations; treat connectors as
enhancement, never as a gate.

### 7.6 Verified implementation without commission

**What:** A curated marketplace of verified implementation partners, with admin review,
no per-award commission, and a trusted partner path.

**Why it is defensible:** Vendors that take commission cannot credibly recommend the
cheapest or best option. A no-commission stance is a trust signal and a differentiator.

**Product proof:** Bidder verification, bid approval, award workflow, pinned trusted
partner with the same rules.

**How to protect:** Publish the verification standard and enforce it evenly, including
for the trusted partner.

### 7.7 Speed and accessibility of the first insight

**What:** A free diagnostic that produces a score, band, top constraints, and sample plan
in one sitting.

**Why it is defensible:** Consulting cannot match the price and speed; software cannot
match the decision quality at that speed.

**Product proof:** Free diagnostic, live scoring, sample plan.

**How to protect:** Keep the free result genuinely useful but incomplete enough to
justify the paid report.

### 7.8 Service as product

**What:** Published SLA, status page, support desk, trust centre, data rights, legal
versioning, accessibility, and change log.

**Why it is defensible:** Mid-market buyers are often neglected by enterprise vendors.
Legible service is a differentiator, not a cost centre.

**Product proof:** `/service-standards`, `/status`, `/trust`, `/support`, `/dpa`,
`/accessibility`.

**How to protect:** Measure every standard and publish the evidence.

### 7.9 Operator-first language and design

**What:** Plain-language questions, no consulting jargon, phone-ready capture, clear
next actions.

**Why it is defensible:** Most competitors are designed for analysts or enterprise
buyers. Floor adoption is the real bottleneck.

**Product proof:** Question-writing rules in `elipsis_questions.py`, mobile capture
requirements.

**How to protect:** Test every feature with a supervisor on a phone, not only with a
manager on a laptop.

### 7.10 Compounding benchmark data

**What:** Anonymised, consented cohort benchmarks by sector, size, country, and
department, shown only above a credible sample.

**Why it is defensible:** It improves with every assessment and cannot be bought quickly.

**Product proof:** `benchmarks.py`, minimum cohort of five, suppressed peer medians.

**How to protect:** Be transparent about sample size, never fabricate comparisons, and
make participation consent-based.

### 7.11 Edge summary

| Edge | Copyability | Time to replicate | Strategic weight |
|---|---|---|---|
| Closed loop | Medium | 12–24 months | Highest |
| Costed transparency | Medium | 6–12 months | High |
| Local context | Hard | 12+ months | High |
| Department granularity | Easy | 3–6 months | High |
| No-integration diagnosis | Easy | 3–6 months | Medium |
| No-commission marketplace | Medium | 6–12 months | High |
| Speed | Easy | Immediate | Medium |
| Service as product | Medium | 6–12 months | Medium |
| Operator-first design | Medium | 6–12 months | High |
| Benchmark data | Hard | 18+ months | Highest |

---

## 8. Positioning and messaging

### 8.1 Category

**Operational diagnostic and implementation intelligence for logistics.**

Not "business transformation platform" as the lead. That phrase is broad, abstract, and
invites comparison with consultancies and enterprise suites. Lead with the concrete job:
diagnose the operation, cost the constraint, own the plan.

### 8.2 Positioning statement

> For mid-market logistics operators who suspect operational friction is capping growth
> but cannot justify a consulting engagement, Elipsis is a diagnostic engine that turns a
> structured assessment into a board-ready, costed report and a prioritised
> implementation roadmap, with verified partners to execute it — without integrations,
> consultants, or a long discovery project.

### 8.3 Messaging pillars

| Pillar | Message | Proof |
|---|---|---|
| Diagnose in one sitting | "See how your operation really runs in one working session." | 63 questions, 36 metrics, 7 pillars. |
| Cost the constraint | "Know what the friction costs before you spend to fix it." | Editable financial model, cost of inaction. |
| Own the plan | "Leave with owners, dates, dependencies, and KPIs." | 90-day roadmap, action board. |
| Verify the partner | "Implement with vetted partners. No commission, no bias." | Verification workflow, no-fee policy. |
| Prove the movement | "Re-assess and show the board what changed." | Trends, re-score, audit trail. |

### 8.4 Proof points

- A free diagnostic that produces a usable result.
- A paid report that is board-ready, not a data dump.
- Transparent assumptions and a published method.
- Local context and currency.
- Department-level detail.
- Verified implementation partners.
- Service commitments with published evidence.
- Privacy, access control, and audit by default.

### 8.5 Objection handling

| Objection | Response |
|---|---|
| "We already know our problems." | "Then the value is in ranking them, costing them, and proving movement. The report gives you a defensible priority and a plan." |
| "We tried a consultant." | "Consultants deliver a document. Elipsis delivers a decision package, a cadence, and a verified implementation path at a fraction of the cost." |
| "We don't have clean data." | "The diagnosis is designed for operator input, not perfect data. Evidence is optional and graded; integrations are optional." |
| "This is just a survey." | "A survey stops at a score. Elipsis produces 36 metrics, costed constraints, a roadmap, and an operating layer." |
| "We can build this internally." | "You can build a survey. The method, benchmarks, local assumptions, and implementation network are the hard parts." |
| "Why not a TMS?" | "A TMS assumes you know what to fix. Elipsis tells you what to fix before you spend on execution software." |

### 8.6 How Elipsis delivers its service

Elipsis uses four delivery modes. The first three are product-led; the fourth is
partner-led. No mode requires a custom build to reach first value.

| Mode | Who it serves | What happens | Time to first value |
|---|---|---|---|
| Self-serve | Operators and small teams | The buyer completes the diagnostic and receives the report online. | Same day |
| Facilitated | Teams that want help completing the diagnosis | An Elipsis facilitator runs a guided session using the same instrument. | 1–3 days |
| Guided implementation | Operators who want the roadmap run with support | Elipsis helps set owners, cadence, and reviews; implementation is delivered by a verified partner. | 1–2 weeks |
| Partner-led | Consultants and implementation firms | A partner uses Elipsis under the consultant edition to diagnose and manage clients. | Per engagement |

Service commitments are defined in `docs/SERVICE_DELIVERY_STANDARD.md` and are binding:
published SLA, status page, support desk, data rights, accessibility, and legal
versioning. Service is part of the product, not an afterthought.

Delivery principles:

- The diagnosis is never gated behind a custom integration.
- Onboarding must reach first value in under seven days.
- The first review happens within 30 days of the report, not at renewal.
- Every paid account gets an annual or quarterly review using its own movement data.
- Partners are held to the same verification and conduct standards as the platform.

### 8.7 How Elipsis tailors the platform

Tailoring is configuration and content, never a fork. The goal is to make the product
feel local and sector-specific without a services business hiding inside the product.

| Tailoring layer | Mechanism | Boundary |
|---|---|---|
| Sector | Question framing, metric emphasis, roadmap templates for forwarding, haulage, 3PL, warehousing, and last mile. | Same scoring engine. |
| Department | Department selection, scope, targets, and reports. | Same data model. |
| Market | Currency, labour rate, working hours, fuel and FX assumptions, country benchmarks. | Explicit, editable inputs. |
| Organisation | Branding, report footer, huddle day and time, site list. | Presentation only. |
| Role | Permission profiles and default views. | Central permission service. |
| Partner | Co-branded reports and multi-client management in the consultant edition. | No code changes. |
| Integration | CSV, API, and webhooks; connectors added over time. | Core remains integration-optional. |

Explicitly out of scope: custom forks, bespoke modules sold as one-offs, custom scoring
formulas per client, and on-premise deployment. If a buyer needs a bespoke build, the
correct path is the partner ecosystem, not the core product.

---

## 9. Pricing and packaging

### 9.1 Current structure

| Plan | Price | Grants |
|---|---:|---|
| Free diagnostic | $0 | On-screen score, band, top three constraints, sample plan. |
| Full Assessment | $49 once | Full report, 36 metrics, costed friction, 90-day plan, exports, 3 bidder introductions. |
| Operator monthly | $29 / month | Unlimited assessments, team features, unlimited switches, daily operations. |
| Operator annual | $380 / year | Same as monthly, annual commitment. |
| Switch top-up | $24.50 | Three additional bidder switches. |
| Bidder monthly | $39 / month | Verified listing and bidding. |
| Bidder six months | $119 | Verified listing and bidding. |
| Bidder annual | $219 | Verified listing and bidding. |

### 9.2 Packaging principles

- The free diagnostic must be useful, not crippled.
- The Full Assessment is the primary paid conversion; price it for a manager's approval
  threshold, not procurement.
- The operator plan is the retention product; daily operations belongs here.
- The marketplace is a trust product, not a commission engine.
- Enterprise and consultant editions are priced separately and should not distort the
  self-serve ladder.

### 9.3 Proposed future packaging

| Edition | Buyer | Scope | Status |
|---|---|---|---|
| Free | Any operator | One diagnostic, limited result. | Existing |
| Full Assessment | Operator | One complete diagnosis and report. | Existing |
| Operator | Operator team | Unlimited diagnoses, departments, daily operations. | Existing, expand |
| Consultant | Advisory firm | Multi-client, white-label reports, facilitator mode. | Proposed |
| Enterprise | Multi-country group | SSO, audit, custom benchmarks, support SLA. | Proposed |

Open question: whether to introduce per-seat pricing above a member threshold. The
recommendation is to include a generous team allowance and charge for scale, not for
basic participation.

---

## 10. What the platform fixes and the benefits

### 10.1 Problem to benefit map

| Problem | Platform capability | Benefit | Measurable outcome |
|---|---|---|---|
| No shared definition of operational health | Seven-pillar index and 36 metrics | A common language for leaders and departments | One score used in reviews |
| Priorities argued on opinion | Ranked pain points and cost of inaction | A defensible priority order | Top three constraints agreed |
| Consulting is slow and expensive | One-session diagnostic and report | Decision-ready in days, not weeks | Time to report under 48 hours |
| Software bought against the wrong constraint | Diagnosis before implementation | Better capital allocation | Fewer stalled projects |
| Fragmented data | Operator-input diagnosis and optional evidence | Insight without an integration project | No mandatory connector |
| Global benchmarks mislead | Local assumptions and cohort benchmarks | Credible comparisons | Assumptions edited and accepted |
| Recommendations die after the report | Owners, dates, KPIs, action board | Execution accountability | Actions assigned within 14 days |
| Vendor selection is opaque | Verified, no-commission marketplace | Trusted implementation choice | Time to first qualified bid |
| No proof of movement | Re-assessment and trends | Evidence for the board and renewal | 90-day re-score rate |
| Daily work is invisible | Control tower, tasks, exceptions, handover | Fewer status meetings, faster escalation | Daily active departments |

### 10.2 Benefits by buyer

**MD / CEO:** A defensible decision, a board narrative, and a plan that does not require
a consulting budget.

**COO / Ops Director:** A ranked constraint, department accountability, and a cadence
that turns the plan into work.

**Finance:** Transparent assumptions, a cost-of-inaction case, and a measurable payback.

**Department head:** A focused set of actions that removes a real blocker, plus tools
that help run the shift.

**Consultant:** Credible diagnostic IP, faster discovery, and a differentiated client
proposal.

**Implementation partner:** Qualified demand with enough context to quote without a
discovery call.

### 10.3 The economic logic

The platform does not promise audited savings. It promises a defensible estimate built
from:

- labour exposure and process drag;
- service failure and claims;
- working-capital delay;
- avoided capital misallocation;
- the cost of decision latency.

Every input is editable, every cap is stated, and the method note is published. That is
what makes the case credible to a finance lead.

---

## 11. Current product truth

### 11.1 What exists and works

| Capability | Maturity | Evidence |
|---|---|---|
| 63-question instrument across 7 pillars | Strong | `elipsis_questions.py`, `constants.py`, `readiness.py` |
| 36 executive metrics and confidence | Strong | `readiness.py`, `constants.METRIC_FORMULAS` |
| Results, exports, share links | Strong | `routers/pages.py`, `routers/value.py`, `report_pdf.py` |
| Financial assumptions and editing | Strong | `AssessmentAssumption`, `services_core.py` |
| Department diagnostic definitions | Partial | `elipsis_api/departments.py` |
| Company workspace, pulse, decisions | Functional | `services_room.py`, `routers/company_room.py` |
| Action board | Functional, assessment-bound | `routers/workspace.py`, `models.RoadmapItem` |
| Operations ledger (KPIs, incidents, compliance) | Functional | `services_operations.py`, `routers/operations_ui.py` |
| Marketplace request, bid, award | Functional | `routers/marketplace_ui.py`, `routers/admin.py` |
| Verified partner directory | Functional | `routers/bidder.py`, `models.BidderCompany` |
| Billing and entitlements | Partial | `premium.py`, `paystack.py`, `models.BillingSubscription` |
| Service delivery layer | Strong | `routers/service.py`, `services_success.py` |
| Permissions and audit | Functional, with role debt | `permissions.py`, `models.AuditEvent` |
| Daily operations control tower | Not built | Specification in `DAILY_OPERATIONS_TRANSFORMATION.md` |

### 11.2 Product maturity by layer

| Layer | Maturity | Comment |
|---|---|---|
| Diagnose | 8/10 | Engine is credible; report hierarchy and benchmarks need work. |
| Report | 6/10 | Rich data; decision-first structure and board packaging need refinement. |
| Implement | 6/10 | Marketplace flows exist; liquidity and outcome tracking are immature. |
| Operate | 3/10 | Ledger and workspace exist; no true daily control tower. |
| Trust | 7/10 | Strong service layer; QA and role cleanup outstanding. |

---

## 12. Flaws and risks

This section is deliberately blunt. A credible plan must name what is weak.

### 12.1 Product flaws

| Flaw | Impact | Severity | Recommendation |
|---|---|---|---|
| Assessment-first product is periodic | Low repeat use, weak retention | Critical | Build the daily operating layer and continuous pulse checks. |
| Report is data-rich but not decision-first enough | Buyers may not reach the "what to do" moment | High | Reorder results: verdict, savings, top constraints, next step. |
| Daily actions are tied to an assessment | Cannot run normal operations without a diagnosis | Critical | Introduce standalone `OpsTask`. |
| No department workspace | Department heads do not own the result | High | Department membership, scope, targets, and dashboards. |
| Benchmarks depend on cohort size | Weak peer comparison at launch | Medium | Show only above minimum sample; build consented cohorts. |
| Local context is mostly assumptions, not local data | Credibility gap outside Kenya | High | Localise currency, labour, and operating inputs by market. |
| No continuous diagnostic | No early warning between 90-day reviews | High | Add pulse diagnostics and drift signals. |
| No post-award implementation tracking | Cannot prove implementation value | High | Add implementation milestones and outcome verification. |
| Marketplace liquidity is uncertain | Buyers may see few qualified bids | High | Recruit verified partners before public launch; measure supply. |
| Manual KPI entry | Data goes stale; adoption risk | Medium | CSV/API first, read-only connectors later. |
| Mobile capture is weak | Floor users avoid the product | High | Design `/today` mobile-first with quick capture. |
| Report language can drift into consulting jargon | Reduces operator trust | Medium | Enforce plain-language rules and test with operators. |

### 12.2 Technical and quality flaws

| Flaw | Evidence | Recommendation |
|---|---|---|
| Three failing baseline tests | `/settings` Jinja `tuple` error; marketplace lock returns 404 not 503 | Fix before any new phase. |
| Two role fields | `User.role` and `User.user_type`; `permissions.py:26` reads both | Consolidate: `user_type` for commercial identity, `OrgOwner.role` for org role. |
| Fragmented routers | Many feature routers with duplicated guards | Extract a shared permission dependency. |
| Computed notifications only | `services_ops.notifications` rebuilt per request | Persist daily notifications with read state. |
| No cron worker | Vercel serverless only | Add a secured idempotent tick endpoint. |
| Manual deployment verification | Live Paystack plans, auth sessions, screenshots pending | Add a release checklist and smoke tests. |
| Accessibility not evidenced | WCAG target stated, no audit | Add automated and manual checks per release. |
| Benchmark transparency | Minimum cohort enforced, but small samples | Publish sample size and method beside every comparison. |

### 12.3 Commercial and market risks

| Risk | Impact | Mitigation |
|---|---|---|
| Positioned too broadly as "transformation" | Weak differentiation, long sales cycles | Lead with logistics diagnostic and costed roadmap. |
| Free diagnostic cannibalises paid report | Low conversion | Keep the free result useful but incomplete. |
| Consulting firms see the platform as a threat | Channel resistance | Offer a consultant edition and partner programme. |
| Marketplace partners underdeliver | Brand damage | Verification, references, ratings, outcome tracking, removal policy. |
| Enterprise buyers demand custom work | Distraction | Serve through partners; keep the core standardised. |
| Price anchored too low | Perceived low value | Anchor on cost of inaction, not on survey pricing. |
| Local data moat takes time | Weak peer benchmarks early | Be transparent; start with public reference points. |

---

## 13. Recommendations

### 13.1 Strategic

1. **Lead with the diagnostic engine.** The report is the wedge. Make it the most
   credible, decision-ready artefact in the mid-market logistics segment.
2. **Narrow the beachhead.** Focus on growth-stage logistics operators with 50–300 staff
   in one or two markets before broadening.
3. **Sell the loop, not the tool.** Diagnose, cost, plan, implement, prove. Every page and
   every sales conversation should reinforce the loop.
4. **Make department ownership the expansion motion.** Land with one department, prove
   movement, expand to the next.
5. **Keep the marketplace no-commission.** It is a trust position and a long-term
   differentiator.
6. **Build the benchmark moat deliberately.** Consent-based, anonymised, minimum sample,
   published method.

### 13.2 Product

1. **Rebuild the report hierarchy** around the executive verdict, cost of inaction, top
   three constraints, implementation decision, and plan.
2. **Add department diagnostics and roll-up** with department-specific reports.
3. **Add continuous diagnostics** through short pulse checks and drift detection.
4. **Add implementation tracking** with milestones, owners, and outcome verification.
5. **Build the daily control tower** so the product is used between assessments.
6. **Make assumptions and method visible** in every financial claim.
7. **Add sub-sector templates** for forwarding, haulage, 3PL, warehousing, and last mile.
8. **Add consultant mode** with multi-client management and co-branded reports.
9. **Harden mobile capture** for supervisors and floor users.
10. **Introduce AI assistance with guardrails** for narrative drafting, evidence
    summarisation, and scope drafting — never for scoring or unreviewed advice.

### 13.3 Delivery and service

1. Fix the baseline test failures and role debt before new features.
2. Publish a release checklist covering auth, payments, exports, and mobile.
3. Measure and publish the service standards already defined.
4. Build an onboarding path that reaches first value in under seven days.
5. Offer a facilitated diagnostic service for buyers who want help completing it.
6. Run quarterly customer reviews using the platform's own movement data.

### 13.4 Go-to-market

1. Publish a sample report and a methodology page that a finance lead can scrutinise.
2. Build proof through design partners, not testimonials alone.
3. Recruit verified implementation partners before opening the marketplace.
4. Create a consultant partner programme with white-label reports.
5. Use the free diagnostic as the primary lead magnet, not gated content.
6. Anchor pricing on the cost of inaction and the cost of consulting, not on software.

### 13.5 Trust

1. Complete the security and QA baseline.
2. Publish data handling, retention, and subprocessor details.
3. Add role-based access and audit evidence to the trust centre.
4. Never use customer data to train third-party models.
5. Make every AI-assisted output labelled and human-reviewable.

### 13.6 90-day priorities

| Priority | Outcome |
|---|---|
| Fix baseline quality | Green tests, single role model, clean `/settings`. |
| Report v2 | Decision-first report, board pack, transparent assumptions. |
| Department diagnostics | One department can complete and own a diagnosis. |
| Continuous pulse | A short re-check between full assessments. |
| Implementation tracking | Awarded work has milestones and an outcome record. |
| Daily control tower phase A | `/today`, quick capture, handover. |
| Benchmark scaffolding | Consented cohort with minimum sample and published method. |

---

## 14. Features to take the platform to the next step

Features are grouped by priority and mapped to the layer they strengthen.

### 14.1 Tier 1 — Must build next (0–90 days)

| Feature | Layer | Description | User value | Success measure |
|---|---|---|---|---|
| Report v2 hierarchy | Report | Executive verdict, savings, top constraints, decision, plan, detail. | Buyer reaches a decision without reading a data dump. | Report-to-request conversion. |
| Board pack export | Report | Print-ready pack with verdict, economics, roadmap, assumptions. | MD can take it to the board. | Download rate. |
| Assumption editor v2 | Diagnose | Guided inputs with ranges, caps, and local defaults. | Finance can defend the numbers. | Assumption completion rate. |
| Department roll-up | Diagnose | Department scores, constraints, and a company roll-up. | Department heads own the result. | Departments per paid account. |
| Continuous pulse | Diagnose | 5–10 question check between full assessments. | Early warning and freshness. | Pulse completion rate. |
| Implementation tracker | Implement | Milestones, owners, status, evidence after award. | Proves implementation progress. | Award-to-milestone rate. |
| `/today` control tower | Operate | Daily view of overdue, due, exceptions, documents, handover. | A reason to open the product daily. | Weekly active departments. |
| Quick capture | Operate | One-screen task, exception, metric, note. | Floor adoption. | Captures per active user. |
| Standalone tasks | Operate | Tasks without an assessment. | Real daily work. | Tasks per department per week. |
| Role consolidation | Trust | One role source per concern. | Predictable permissions. | Permission test pass rate. |
| Baseline quality | Trust | Green suite, `/settings` fix, release checklist. | Reliability. | Zero failing tests. |

### 14.2 Tier 2 — Next (3–6 months)

| Feature | Layer | Description | User value |
|---|---|---|---|
| Sub-sector templates | Diagnose | Forwarding, haulage, 3PL, warehousing, last mile. | Relevance and faster completion. |
| Peer cohorts | Diagnose | Benchmarks by sector, size, country, department. | Credible comparison. |
| Scenario modelling | Diagnose | Compare improvement paths and investment levels. | Better capital decisions. |
| Evidence library | Diagnose | Upload and grade documents, photos, reports. | Higher confidence. |
| Facilitator mode | Diagnose | Guided workshop mode for consultants and internal leads. | Faster group completion. |
| Consultant edition | Commercial | Multi-client, co-branded reports. | Channel growth. |
| Bid comparison | Implement | Side-by-side scope, price, timeline, references. | Better partner choice. |
| Outcome verification | Implement | Re-score and evidence after implementation. | Proof of value. |
| Exceptions and SLA | Operate | Owner, severity, SLA, escalation, recurrence. | Service control. |
| Routines and checklists | Operate | Recurring checks per department and shift. | Operational hygiene. |
| Shift handover | Operate | Structured handover with acknowledgement. | Continuity across shifts. |
| KPI targets | Operate | Department targets, thresholds, stale detection. | Accountability. |
| API and webhooks v1 | Integrations | Tasks, exceptions, metrics, handover. | System integration without a project. |
| Notification centre | Operate | Persistent events, read state, email digest. | Fewer missed items. |

### 14.3 Tier 3 — Later (6–12 months)

| Feature | Layer | Description | User value |
|---|---|---|---|
| Read-only TMS/WMS connectors | Integrations | Import shipments, service events, inventory signals. | Lower data entry. |
| Accounting connector | Integrations | Invoice, cost, and cash signals. | Finance-grade diagnosis. |
| Multi-country consolidation | Enterprise | Group roll-up, currency, local benchmarks. | Group control. |
| SSO and SCIM | Enterprise | Identity and user lifecycle. | Enterprise readiness. |
| AI narrative assistant | Diagnose | Draft findings from evidence, with human review. | Speed and consistency. |
| AI scope assistant | Implement | Turn a diagnosis into a draft brief. | Faster implementation start. |
| Predictive risk signals | Operate | Flag likely SLA or compliance failure. | Prevention. |
| Marketplace ratings and references | Implement | Verified completed-work evidence. | Trust and selection. |
| Mobile PWA offline drafts | Operate | Capture without connectivity. | Field reliability. |
| White-label platform | Commercial | Partner-branded instance. | Channel scale. |
| Benchmark data products | Commercial | Sector reports and indices. | New revenue and authority. |

### 14.4 Feature principles

- Every feature must strengthen the loop: diagnose, decide, implement, operate, prove.
- No feature may require an integration to deliver first value.
- No feature may hide its assumptions or method.
- No feature may create a second source of truth for roles, tasks, or notifications.
- No feature may ship without a mobile path if a floor user needs it.
- No AI feature may score, decide, or publish without human review.

---

## 15. Persona to feature traceability

| Persona | Must-have features | Delight features |
|---|---|---|
| MD / CEO | Report verdict, cost of inaction, board pack, movement | Peer benchmark, scenario view |
| COO / Ops Director | Department roll-up, roadmap, `/today`, exceptions, KPI targets | Predictive risk, weekly digest |
| Finance Director | Assumption editor, ROI, exports, audit trail | Scenario modelling, accounting signals |
| Department head | Department diagnosis, tasks, routines, handover | Mobile capture, saved views |
| Supervisor | `/today`, quick capture, exceptions, handover | Offline drafts, escalation shortcuts |
| Analyst | KPI entry, evidence, import, export | Bulk actions, data quality checks |
| Transformation lead | Roadmap owners, dependencies, progress | Implementation tracker, QBR pack |
| IT / Data lead | Roles, SSO, API, audit, DPA | Connectors, data residency |
| Consultant | Multi-client, white-label, facilitator mode | Benchmark library, proposal pack |
| Bidder | Verified profile, request detail, bid workflow | Ratings, outcome history |

---

## 16. Success metrics

### 16.1 North star

**Completed diagnoses that produce an owned action within 14 days and a re-score within
90 days.**

This single measure captures diagnosis quality, activation, execution, and proof.

### 16.2 Funnel

| Stage | Metric | Target |
|---|---|---|
| Acquisition | Visitor to diagnostic start | Establish baseline. |
| Activation | Start to completed diagnostic | 60%+ |
| Conversion | Complete to paid report | 15%+ |
| Expansion | Paid to operator plan | 30%+ |
| Implementation | Report to request | 25%+ |
| Outcome | Award to re-score | 50%+ |

### 16.3 Retention and engagement

- Weekly active departments per paying org: 2+.
- Days per week with an opened `/today`: 4+.
- 90-day re-assessment rate: 40%+.
- Operator renewal rate: 80%+.
- Team invitation rate: 50%+ of paid accounts.

### 16.4 Marketplace

- Verified partner supply per active market.
- Time to first qualified bid.
- Award rate.
- Implementation completion rate.
- Dispute and removal rate.

### 16.5 Service and trust

- SLA attainment.
- CSAT after support.
- NPS.
- Security and accessibility findings closed on time.
- Zero critical data incidents.

---

## 17. Delivery roadmap

| Phase | Duration | Focus | Exit criteria |
|---|---|---|---|
| Phase 0 — Stabilise | 2 weeks | Tests, `/settings`, role consolidation, release checklist, measurement | Green suite; one role model. |
| Phase 1 — Report and diagnosis | 4 weeks | Report v2, board pack, assumptions, department roll-up, templates | A buyer can decide from the report without a call. |
| Phase 2 — Continuous and implementation | 4 weeks | Pulse checks, implementation tracker, outcome verification, bid comparison | Diagnosis stays current; delivery is visible. |
| Phase 3 — Operating layer | 6 weeks | `/today`, tasks, exceptions, routines, handover, KPI targets | A department runs its week in the product. |
| Phase 4 — Integrations and scale | 6 weeks | API, webhooks, CSV expansion, read-only connectors, mobile PWA | Data entry drops; mobile adoption rises. |
| Phase 5 — Channel and enterprise | 8 weeks | Consultant edition, white-label, SSO, multi-country | Channel revenue and enterprise readiness. |

The detailed operating-layer build is specified in
`docs/DAILY_OPERATIONS_TRANSFORMATION.md`. That specification remains valid; this master
plan sets the sequence and the strategic rationale.

---

## 18. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Report quality does not meet consulting-grade expectations | Medium | High | Design partners, expert review, published method. |
| Adoption stalls because the product is periodic | High | High | Continuous pulse and daily operating layer. |
| Marketplace supply is insufficient | High | Medium | Recruit partners before launch; seed trusted partner. |
| Local data is too thin for benchmarks | High | Medium | Public reference points, minimum sample, transparency. |
| Scope creep into TMS/WMS | Medium | High | Enforce non-goals; partner instead of build. |
| Price too low to fund service | Medium | Medium | Anchor on cost of inaction; review after 90 days. |
| Security or data incident | Low | Critical | Audit, least privilege, DPA, incident response, testing. |
| Key-person dependency in delivery | Medium | High | Document method, productise onboarding. |
| AI output erodes trust | Medium | High | Human review, labelling, no training on customer data. |
| Channel conflict with consultants | Medium | Medium | Consultant edition and referral programme. |

---

## 19. Open decisions

1. **Beachhead market.** Confirm Kenya as the first market and the second market to add.
2. **Report pricing.** Hold $49 one-time or raise for the expanded report.
3. **Operator packaging.** Include daily operations in the $29 plan or introduce a team
   tier.
4. **Consultant edition.** Build now for channel growth or after self-serve retention is
   proven.
5. **Department visibility default.** Org-wide read for managers, department-only for
   others.
6. **Continuous pulse design.** Number of questions, cadence, and whether it affects the
   official score.
7. **Implementation tracking scope.** Milestones only or full statement-of-work tracking.
8. **Benchmark policy.** Minimum sample, consent language, and publication format.
9. **AI scope.** Which outputs are assisted, and what the review workflow is.
10. **Integration priority.** First connector after CSV/API.

---

## 20. Appendix A — Glossary

| Term | Meaning |
|---|---|
| Elipsis Index | The headline readiness score. |
| Confidence Index | A measure of how much the result can be trusted. |
| Pillar | One of seven dimensions of operational readiness. |
| Subdomain | A narrower capability within a pillar. |
| Constraint | The pain point with the greatest cost or blocking effect. |
| Cost of inaction | The estimated financial consequence of leaving a constraint unresolved. |
| Roadmap | The sequenced implementation plan with owners, dates, and KPIs. |
| Operator plan | The recurring subscription for ongoing diagnosis and operations. |
| Verified partner | An implementation company approved by platform review. |
| Control Tower | The daily operating console. |

## 21. Appendix B — Current implementation map

| Area | Primary files |
|---|---|
| Questions and scoring | `elipsis_questions.py`, `constants.py`, `readiness.py` |
| Assessment workflow | `elipsis_api/routers/pages.py`, `elipsis_api/services_core.py` |
| Results, exports, assumptions | `elipsis_api/routers/value.py`, `elipsis_api/report_pdf.py` |
| Company workspace | `elipsis_api/routers/company_room.py`, `elipsis_api/services_room.py` |
| Action board | `elipsis_api/routers/workspace.py`, `elipsis_api/services_ops.py` |
| Operations ledger | `elipsis_api/routers/operations_ui.py`, `elipsis_api/services_operations.py` |
| Marketplace | `elipsis_api/routers/marketplace_ui.py`, `elipsis_api/services_marketplace.py` |
| Admin desk | `elipsis_api/routers/admin.py`, `elipsis_api/routers/marketplace_ui.py` |
| Billing | `elipsis_api/premium.py`, `elipsis_api/paystack.py` |
| Service layer | `elipsis_api/routers/service.py`, `elipsis_api/services_success.py` |
| Permissions and audit | `elipsis_api/permissions.py`, `elipsis_api/models.py` |
| Benchmarks and ICP | `elipsis_api/benchmarks.py` |

## 22. Appendix C — Relationship to existing documents

| Document | Role after this update |
|---|---|
| `PLATFORM_MASTER_PLAN.md` | Single source of truth for market, audience, positioning, edges, gaps, and sequence. |
| `DAILY_OPERATIONS_TRANSFORMATION.md` | Technical annex for the operating layer. |
| `PLATFORM_UPGRADE_IMPLEMENTATION_GUIDE.md` | Marketplace and entitlement specification; remains authoritative for those flows. |
| `COMPETITIVE_EDGE.md` | Background market read; superseded in positioning by this document. |
| `SERVICE_DELIVERY_STANDARD.md` | Service commitments; unchanged and binding. |

---

## 23. Definition of success

Elipsis succeeds when a logistics operator can say, with evidence:

> "We know what is holding the operation back, what it costs, who owns the fix, and what
> changed since we started. We run the week in Elipsis, and the board sees the movement."

That is the standard this plan is built to meet.
