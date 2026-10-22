# Elipsis Service Delivery Standard

Version 1.0, effective 22 October 2026. Owner: founder / customer operations.
Review cadence: monthly metrics review, quarterly policy review.

This standard defines the service Elipsis commits to deliver, how each commitment is measured, and where the evidence lives. It applies to every paid plan. Free accounts receive the same security, privacy and accessibility commitments, but not paid support-response targets or service credits.

## Customer promise

Elipsis turns an operating assessment into a decision, a costed constraint and an owned 90-day plan. The service promise is therefore wider than uptime: the customer must be able to start, understand their result, act on it with their team, and get help without chasing us.

## The 26 standards

| # | Standard | Commitment | Measure and evidence | Owner | Cadence |
|---|---|---|---|---|---|
| 1 | Availability | 99.9% monthly availability for the web application and API. | Status page and incident records. Monthly report. | Engineering | Monthly |
| 2 | Service credits | Paid accounts receive 10% credit below 99.9%, 25% below 99.5%, 50% below 99.0% in a month. | Support ticket plus billing adjustment. | Founder | Per incident |
| 3 | Support channels | In-app ticket desk, email and public help centre. Security reports use the published security contact. | `/support`, `/help`, `/.well-known/security.txt`. | Customer operations | Continuous |
| 4 | Support coverage | Urgent issues: 24/7. High: 07:00-19:00 UTC, Monday-Saturday. Normal and low: 08:00-18:00 UTC, Monday-Friday. | Ticket timestamps and SLA dashboard. | Customer operations | Weekly |
| 5 | Severity model | Urgent = service unavailable or data at risk. High = core workflow blocked. Normal = degraded but workable. Low = question or request. | Ticket priority plus written definition. | Customer operations | Per ticket |
| 6 | Response SLA | Urgent 30 minutes, high 2 hours, normal 8 hours, low 1 business day. | First-response timestamp against due time. | Customer operations | Weekly |
| 7 | Resolution SLA | Urgent 4 hours, high 1 business day, normal 3 business days, low 5 business days. | Resolution timestamp, excluding customer-caused waits. | Customer operations | Weekly |
| 8 | Status transparency | Public status page shows components, active incidents, resolution notes and 30-day availability. | `/status`. | Engineering | Continuous |
| 9 | Incident communication | Acknowledge urgent incidents within 30 minutes, update at least every 60 minutes, and publish a postmortem within 5 business days. | Incident record and status history. | Engineering | Per incident |
| 10 | Blameless postmortems | Every urgent incident gets a written timeline, customer impact, root cause, corrective actions and owners. | Incident postmortem link. | Engineering | Per incident |
| 11 | Ticket transparency | Every ticket has a public reference, full conversation, status history and a named queue. Customers can see what happens next. | `/support/{reference}`. | Customer operations | Continuous |
| 12 | Closed-loop feedback | Every resolved ticket asks for CSAT. Scores of 1-2 trigger a follow-up within one business day. | Ticket CSAT and follow-up queue. | Customer operations | Weekly |
| 13 | Relationship feedback | NPS is collected in-product and reviewed monthly; detractors receive a personal follow-up. CES is tracked for onboarding. | `/feedback` and feedback summary. | Founder | Monthly |
| 14 | Activation contract | New accounts see seven activation milestones and a next best action. Activation is measured within 14 days. | `/getting-started` and dashboard banner. | Product | Weekly |
| 15 | Customer health | Every company has a transparent health score covering profile completeness, assessment recency, action progress, team depth, collaboration and support risk. | Company health card and admin console. | Customer operations | Weekly |
| 16 | Proactive outreach | At-risk accounts are contacted within 2 business days. Every paid account gets a quarterly review offer. | Health queue and QBR log. | Founder | Weekly / quarterly |
| 17 | Change communication | Material changes are published in the changelog. Breaking or deprecating changes get at least 30 days' notice and a migration path. | `/changelog` and release policy. | Product | Per release |
| 18 | Self-service help | Searchable knowledge base with at least 12 task-based articles, each linking to the relevant product screen. | `/help?q=`. | Customer operations | Monthly |
| 19 | Trust centre | One page links security controls, privacy, DPA, subprocessors, accessibility, status, SLA and data rights. | `/trust`. | Founder | Quarterly |
| 20 | Data processing terms | A plain-language DPA and a named subprocessor register are publicly available. Customers are told before a new subprocessor handles their data. | `/dpa` and `/subprocessors`. | Founder | Quarterly |
| 21 | Data rights | Self-service JSON export is immediate. Erasure and correction requests are acknowledged within 2 business days and completed within 30 calendar days. | `/account/data` and data-request queue. | Founder | Per request |
| 22 | Retention and deletion | Active data is retained while the account is active. Closed-account data is deleted within 90 days, with a 35-day rolling backup expiry. | Retention schedule and deletion log. | Engineering | Quarterly |
| 23 | Vulnerability disclosure | Security reports are acknowledged within 2 business days and triaged within 5 business days. Safe-harbour terms are published. | `/.well-known/security.txt` and `/security`. | Engineering | Per report |
| 24 | Accessibility | WCAG 2.2 AA target for public and authenticated journeys. Keyboard focus, reduced motion, contrast and form labelling are checked each release. | `/accessibility` and release checklist. | Product | Per release |
| 25 | Legal versioning | Terms and privacy versions are dated. Acceptance is recorded with user, document, version and timestamp. Material changes require fresh acceptance. | Signup and `/settings`. | Founder | Per change |
| 26 | Billing transparency | Prices, renewal dates, what is included and refund/credit rules are visible before payment. Receipts show the exact amount and period. | `/pricing` and billing records. | Founder | Per change |

Additional operating standards:

| # | Standard | Commitment |
|---|---|---|
| 27 | AI data governance | Customer assessment data is not used to train third-party models. AI-assisted output is labelled and requires human review before it becomes a decision. |
| 28 | Global clock | Support due times and incident times are shown in the customer's saved timezone, with UTC preserved in the audit record. |
| 29 | Escalation | A customer can escalate any ticket to the founder after one missed SLA. Escalations are answered within 4 business hours. |
| 30 | Performance budget | Public pages target LCP under 2.5 seconds on a mid-range mobile connection; authenticated core pages target under 3 seconds. Regressions are treated as defects. |

## Severity definitions

- **Urgent (P1):** The service is unavailable, a security or privacy incident is suspected, or customer data is at risk. No workaround.
- **High (P2):** A core workflow is blocked for multiple users, such as signup, assessment submission, report access or payment entitlement. No reasonable workaround.
- **Normal (P3):** A feature is degraded or a single user is blocked, but a workaround exists.
- **Low (P4):** Question, documentation issue, cosmetic defect or feature request.

Priority is set by impact, not by customer tier. A paid customer can escalate priority by showing broader impact.

## Support workflow

1. Customer submits a ticket or emails support.
2. The system assigns a reference, severity, first-response due time and resolution due time.
3. The queue owner acknowledges, states the next action and gives the next update time.
4. Resolution is recorded in plain language.
5. The customer receives a CSAT request.
6. Low scores enter the follow-up queue. Repeated issues become a product or documentation fix.

## Measurement

Weekly operating review:

- Tickets opened, resolved, breached and reopened.
- First-response and resolution SLA attainment.
- CSAT, response count and low-score follow-ups.
- Activation rate at 14 days.
- At-risk accounts and outreach completed.

Monthly service review:

- Availability and incident count.
- NPS and verbatim themes.
- Health distribution and churn/expansion signals.
- Knowledge-base gaps and changelog adherence.

Quarterly policy review:

- Re-test standards against customer journey and peer benchmarks.
- Review subprocessors, retention and legal versions.
- Publish a short service report to paid customers.

## Exclusions

The SLA does not cover outages caused by customer systems, misuse, force majeure, or scheduled maintenance announced at least 48 hours in advance. Scheduled maintenance is excluded from availability calculations only when it is announced and kept within the published window.

## Enforcement

A standard without evidence is not a standard. Every commitment above must have a route, record, report or test. Missing evidence is logged as a service defect and fixed in the next operating cycle.
