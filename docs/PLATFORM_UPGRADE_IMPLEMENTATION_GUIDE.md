# Elipsis Platform Upgrade — Implementation Guide

Status: Draft for execution  
Version: 1.0  
Date: 23 October 2026  
Owner: Product and Engineering  
Related documents: `docs/COMPETITIVE_EDGE.md`, `docs/SERVICE_DELIVERY_STANDARD.md`

## 1. Purpose

This guide defines the upgrade that turns Elipsis from an assessment product into a controlled diagnostic-to-implementation platform:

- Elipsis sells assessments.
- Great Turbinez is the trusted, recommended implementation partner.
- Verified implementation companies subscribe to the marketplace.
- Requesting companies can move from diagnosis to a complete implementation request without losing assessment context.
- Every sensitive action is permissioned, auditable, and private by default.
- No implementation commission is charged. Revenue is assessment sales and bidder subscriptions.

This is a product and security specification. It does not change the scoring engine, the 63 questions, or the report calculations.

## 2. Locked decisions

| Area | Decision |
|---|---|
| Great Turbinez role | Third-party implementation and consulting partner. Trusted and pinned, but not exempt from platform rules. |
| Great Turbinez visibility | Appears only in implementation request flows and marketplace pages. The global footer credit appears across the platform. |
| Marketplace access | Public teaser cards for everyone. Full request details, documents, and contact information only for approved, active bidders. |
| Marketplace pages | Separate pages for requests and implementation companies. |
| Request approval | Every request starts as `pending_review`. Admin approval is mandatory. |
| Bid approval | Every bid starts as `pending_review`. Admin approves a bid before the requester can see it. |
| Award | Client indicates preference; admin performs the award to one bidder. No automatic assignment. |
| Conversation | Private between requester and bidder. Admin is added only when either party presses “Involve admin”. |
| Conversation expiry | 24 hours after the last message. |
| Single-assessment switches | Three bidder switches per paid assessment. Top-up costs $24.50 and grants three more switches. |
| Subscription switches | Unlimited switches among approved bids for subscribed requesters. |
| Platform fee | None. No commission on awarded work. |
| Bidder verification | Manual admin verification before subscription and listing. No automatic approval. |
| Subscriptions | Paystack auto-renew. Code integration is in scope; live plan codes and account setup are supplied later. |
| Admin panel | Private, guarded, noindex, and inaccessible to non-admin users. Every consequential action is audited. |
| Handoff security | Signed HMAC token, 15-minute expiry, sanitized payload only. |
| Physical packages | Retire `/physical` and the Pilot/physical pricing; redirect to the implementation request flow. |
| Launch pricing | Full Assessment one-time $49; subscriptions reduced by $10 from the prior proposal. |
| Super Admin | Not implemented in phase one. Permission checks are centralised so it can be added later. |
| Existing customers | Existing Premium entitlements are grandfathered. |

## 3. Product model

### 3.1 Free Diagnostic

- Full 63-question diagnostic.
- Elipsis Index, maturity band, and top three constraints.
- Sample 90-day plan.
- On-screen only.
- No PDF, Excel, JSON, share links, full 36-metric report, marketplace request, or partner handoff.
- Clear upgrade path to Full Assessment.

### 3.2 Full Assessment

Available as:

- one-time purchase for a single assessment, or
- monthly/annual subscription with unlimited assessments and team features.

The Full Assessment unlocks:

- complete Elipsis Index, confidence, and maturity band
- all 36 executive metrics with plain-English readings
- costed friction analysis and assumptions
- ranked pain points with impact and root causes
- three-phase 90-day roadmap
- owners, dates, dependencies, and KPIs
- scenario and sensitivity view
- benchmark and evidence-quality view
- PDF, Excel, and JSON exports
- print-ready board pack and read-only share link
- team annotations and re-assessment
- one implementation request with three bidder introductions
- Great Turbinez and marketplace implementation paths

### 3.3 Implementation

No implementation price is listed on Elipsis. Two paths:

- request implementation through Great Turbinez, the trusted partner
- publish the request to the verified marketplace

Both paths use the same request record and assessment summary.

## 4. Roles and permissions

### 4.1 Platform roles

| Role | Description |
|---|---|
| Anonymous visitor | Marketing pages and free diagnostic start only. |
| Client | Runs assessments, buys Full Assessments, creates requests, manages conversations. |
| Bidder | Verified implementation company with an active subscription. |
| Admin | Platform owner. Approves requests, verifies bidders, approves bids, awards work, manages users and billing. |
| Super Admin | Future extension. Full system and admin management. |

Implementation uses the existing `User.user_type`, `User.is_admin`, and company membership roles. Do not add a second conflicting role field. Core checks live in `elipsis_api/permissions.py` (admin, membership, org roles, Pro access, visible organisations); `services.py` re-exports them for existing callers.

Company workspace roles remain unchanged: owner, manager, supervisor, analyst, viewer.

### 4.2 Permission matrix

| Action | Client | Bidder | Admin |
|---|---|---|---|
| View own assessments | Yes | No | Yes |
| View another client’s assessment | No | No | Yes, audited |
| Create implementation request | Yes, if entitled | No | No |
| View public request teaser | Yes | Yes | Yes |
| View full request | Own only | Approved and active only | Yes |
| Submit bid | No | Approved and active only | No |
| View own bid | No | Yes | Yes |
| View other bids | No | No | Yes |
| Approve request | No | No | Yes |
| Approve bid | No | No | Yes |
| Award request | No | No | Yes |
| View conversation | Participant only | Participant only | Involved or audited override |
| Involve admin | Participant | Participant | N/A |
| Suspend bidder | No | No | Yes |
| Change billing entitlement | No | No | Yes, audited |

### 4.3 Admin privacy

- `/admin` and `/api/v1/admin` are invisible to all non-admin users.
- Non-admin requests return 404, not 403, to avoid confirming the admin surface.
- No admin links appear in the normal navigation.
- Admin pages are `noindex, nofollow`.
- Admin read access to a client request, bidder verification file, or conversation is audit-logged.
- Admin actions require a valid admin session and are rate-limited.
- A separate `admin_base.html` layout prevents accidental admin components leaking into public templates.

## 5. Entitlements and pricing

### 5.1 Launch pricing

Pricing is configuration, not hard-coded template copy. Final figures can be changed without a schema migration.

| Plan | Price | Grants |
|---|---:|---|
| Free Diagnostic | $0 | Limited on-screen result |
| Full Assessment — one-time | $49 | One assessment, full report, 3 bidder switches |
| Full Assessment — monthly | $29/month | Unlimited assessments, team features, unlimited switches |
| Full Assessment — annual | $380/year | Same as monthly, annual commitment |
| Switch top-up | $24.50 | 3 additional switches |
| Bidder — monthly | $39/month | Verified listing and bidding |
| Bidder — six months | $119 | Verified listing and bidding |
| Bidder — annual | $219 | Verified listing and bidding |

Rules:

- No per-award commission.
- One-time purchase is tied to one assessment.
- Subscription is tied to the user and their organisations.
- A top-up is available only to a one-time assessment requester.
- Existing Premium customers keep current access until expiry and are then offered the closest new plan.
- Admin can grant or extend entitlements manually. Every change is audited.

### 5.2 Upgrade and cancellation

- Upgrades take effect immediately.
- Cancellation ends renewal at the current period end.
- Access continues until period end, then falls back to the free tier.
- Failed renewal enters a three-day grace period with email reminders.
- After grace, paid features lock but data remains exportable.

## 6. Assessment and results experience

### 6.1 Payment timing

- Users complete the free diagnostic before paying.
- The free result shows the score, band, and top three constraints.
- The full report is locked until payment succeeds or an active subscription is detected.
- Answers are preserved; the user does not repeat the assessment.
- Payment success unlocks the full report and request entitlement.

### 6.2 Results hierarchy

The results page must lead with the decision, not the data dump:

1. Executive verdict: score, band, confidence, movement.
2. Savings potential, investment, ROI, and payback.
3. Top three constraints with cost of inaction.
4. Decision: request implementation.
5. 90-day plan preview with owners and dates.
6. Full metrics and pillar detail.
7. Benchmark and evidence quality.
8. Financial assumptions.
9. Exports, sharing, annotations, and evidence.

### 6.3 Next steps

Great Turbinez is not named on the results page itself. The results page presents:

- “Request implementation” as the primary next step.
- “Publish to the marketplace” as the secondary next step.
- Both open the guided request builder.
- Great Turbinez appears inside the request builder and marketplace, where the implementation decision is being made.
- “Download board pack”, “Share read-only link”, and “View full metrics” remain available.

This respects the rule that Great Turbinez appears only when a request is in progress or in the marketplace.

## 7. Guided request builder

The builder converts an assessment into a complete implementation brief.

### 7.1 Auto-attached assessment summary

- Elipsis Index and maturity band.
- Top three constraints and impact.
- Cost of inaction and savings potential.
- Recommended 90-day focus.
- Company size, industry, country, and operating context.
- Opaque assessment reference, never the internal ID.

The snapshot is immutable once attached. Later assessment changes do not silently rewrite an active request.

### 7.2 Requester-supplied sections

- What should be implemented.
- Current process and pain.
- Expected outcome and success measures.
- Scope and specifications.
- Sites and locations.
- Timeline and constraints.
- Budget range.
- Attachments.
- Contact preference.
- Consent to share the summary with approved bidders.

Guided prompts and examples help non-technical operators produce a complete brief. The admin can request clarification before approval.

### 7.3 Privacy

- Public teasers show an anonymised summary: industry, country, size band, title, and “Premium request” badge.
- Company name and contact details are visible only to approved active bidders.
- Direct contact details are revealed only after an award.
- Documents are private and access-controlled, never public URLs.

## 8. Partner handoff

The handoff is partner-neutral. Great Turbinez uses an external redirect; platform bidders consume the same summary internally.

### 8.1 Payload

- company name
- contact name and email
- country, city, size band
- Index and maturity band
- top three constraints
- requester summary, expectations, and specifications
- opaque handoff reference
- expiry timestamp

Never include:

- raw answers
- uploaded evidence files
- team annotations
- internal assessment IDs
- other clients’ data

### 8.2 Security

Use an HMAC-signed, short-lived token:

- expiry: 15 minutes
- single-use where possible
- signature verified server-to-server
- no sensitive data in readable query parameters
- handoff creation logged
- invalid, expired, or reused tokens show a safe error and ask the user to return to Elipsis

If the external partner cannot verify a token, use an opaque handoff ID and a server-side fetch endpoint. A plain unsigned redirect carrying the summary is not acceptable.

### 8.3 Handoff flow

1. Requester chooses a partner from the request.
2. Elipsis creates a handoff record.
3. External partner receives a signed token or handoff ID.
4. Partner verifies and shows a short introduction and pre-filled form.
5. Partner confirms lead capture.
6. Elipsis records the handoff status.

## 9. Marketplace information architecture

### 9.1 Pages

- `/marketplace` — overview, pinned trusted partner, latest requests, directory preview.
- `/marketplace/requests` — request teaser cards visible to all.
- `/marketplace/requests/{id}` — full request only for owner, approved active bidder, or admin.
- `/marketplace/companies` — verified implementation company directory.
- `/marketplace/companies/{slug}` — public verified profile.
- `/marketplace/apply` — bidder application, linked discreetly from the directory footer.
- `/marketplace/request/new` — guided request builder for entitled clients.

### 9.2 Request cards

Public card:

- title
- anonymised organisation descriptor
- industry, country, size band
- short summary
- bid count
- gold crown and “Premium request” label
- “Sign in as a verified partner to view details”

Approved bidder card adds:

- organisation name
- full summary
- budget and timeline
- documents
- “Submit bid”

### 9.3 Partner directory

- Horizontal banner cards arranged in a professional grid.
- Pinned Great Turbinez card marked “Trusted partner”.
- Verified companies marked “Verified implementation partner”.
- Logo or monogram, name, services, regions, years in business, rating, completed jobs.
- No public email or phone. Contact happens through the platform.
- Copy conveys confidence and verification, not the verification process.

Suggested copy:

> Vetted implementation partners. Every company listed here has passed verification for legal registration, delivery capability, and client references. Work with a partner who can turn the diagnostic into operating change.

### 9.4 Premium signalling

- Use the existing gold crown consistently on every paid feature.
- Request cards: “Premium request”.
- Locked report actions: crown badge.
- Bidder directory: plan badge, not a crown on every card.
- Do not overuse the crown; it should signal paid access, not decorate.

## 10. Bidder onboarding and verification

### 10.1 Application

The bidder creates an account and submits:

- legal company name and registration number
- country, address, website
- company description and services
- sectors and regions served
- team size and years in business
- two relevant case studies
- two client references
- contact details
- acceptance of marketplace terms, confidentiality, and data-processing terms

### 10.2 Verification states

`draft → submitted → more_info → approved → rejected → suspended → expired`

Only `approved` plus an active subscription can see full requests and bid.

### 10.3 Admin review

Admin checks:

- registration is real
- portfolio and references are credible
- services match logistics and field operations
- delivery capacity is plausible
- no conflict or sanctions concern
- confidentiality and data terms accepted

Admin can request more information, approve, or reject with a reason. Every decision is audited. Rejected bidders may reapply after 30 days.

### 10.4 Subscription activation

- Bidders pay only after approval.
- Payment activates listing and bidding.
- Subscription expiry removes listing and bidding rights but preserves history.
- Renewal is automatic through Paystack.
- Failed renewal enters grace, then suspension.
- Annual re-verification is required.

### 10.5 Public profile

- verified badge
- services and regions
- case studies
- completed jobs and rating
- no verification-process explanation
- no direct contact details

## 11. Request lifecycle

Statuses:

`pending_review → approved → awarded → closed`

Plus `rejected`.

Transitions:

1. Client submits a complete request.
2. Admin reviews and may request clarification.
3. Admin approves or rejects with a reason.
4. Approved requests are visible in full only to approved, active bidders.
5. Bids arrive and are reviewed by admin.
6. Admin awards one bid.
7. Conversation opens.
8. Request closes after agreement, no-agreement, or expiry.

Rules:

- Only admin can approve, reject, award, override, or reopen.
- Client can withdraw before award.
- Admin can close a request for abuse, duplication, or policy breach.
- Every transition is timestamped and audited.

## 12. Bids

Statuses:

`pending_review → approved → awarded`

Plus `not_selected`, `withdrawn`, `rejected`.

A bid includes:

- short message to the requester
- implementation roadmap document
- scope and assumptions
- timeline
- price or budget response
- relevant case studies

Rules:

- Only approved, active bidders can bid.
- One active bid per bidder per request.
- Admin reviews every bid before the requester sees it.
- Admin can reject with a reason.
- Admin awards one bid. No automatic assignment.
- Other approved bids become `not_selected`.
- Bid documents are private and access-controlled.

## 13. Conversations

### 13.1 Opening

When admin awards a bid:

- conversation opens automatically
- requester and bidder are participants
- winning bid and roadmap are attached
- request status becomes `awarded`
- email and in-app notifications are sent

### 13.2 Privacy

- Only the requester and bidder can read messages by default.
- Admin cannot read the conversation unless involved.
- “Involve admin” adds an admin participant and records the reason.
- Admin involvement is visible to both parties.
- Every admin access is audited.
- Messages are never public and never indexed.

### 13.3 Expiry

- Conversation closes 24 hours after the last message.
- A visible countdown shows the remaining time.
- Lazy closure on read plus a scheduled job prevents stale-open conversations.
- On close, both parties choose an outcome: `agreement`, `no_agreement`, or `no_response`.
- If nobody responds, the platform records `closed_unconfirmed`.

The platform does not claim a legally binding contract exists. It records that the introduction and platform conversation have closed. The contract is between the parties.

### 13.4 Switching

- One-time assessment: three switches.
- Switch top-up: $24.50, granting three more switches.
- Subscription: unlimited switches among approved bids.
- Client can switch only to a bid already approved by admin, or ask admin to award another bid.
- Switching closes the current conversation and reopens the same request; the request is not recreated.
- The previous bidder is notified.
- The switch count is visible to the client before confirming.
- Great Turbinez has no exemption and follows the same rules.

### 13.5 Accountability disclaimer

Display in the conversation and marketplace terms:

> Elipsis is an assessment and introduction platform, not a party to implementation contracts. For introductions and conversations conducted on Elipsis, we will investigate reported platform misuse and enforce our platform terms. We are not responsible for work, payments, or agreements made outside the platform or after a conversation closes.

## 14. Notifications

Events:

- request submitted, approved, rejected, withdrawn
- bid submitted, approved, rejected
- request awarded
- new conversation message
- admin added to conversation
- conversation expiring soon
- conversation closed
- switch available or used
- subscription renewed, failed, cancelled, expired
- bidder verification status changed
- handoff created or failed

Channels:

- in-app notification center
- email for high-value events
- no marketing email mixed with transactional events

Add a persistent notification table for marketplace events and read state. Keep existing computed operations notifications unchanged.

## 15. Payments and subscriptions

### 15.1 One-time purchases

Products:

- Full Assessment unlock
- Switch top-up

Each purchase creates a payment record and an entitlement. Payment success is idempotent. The entitlement is granted only after server-side verification or a verified webhook.

### 15.2 Auto-renew subscriptions

Products:

- requester monthly and annual
- bidder monthly, six-month, and annual

Use Paystack plans and subscription codes. Store:

- provider plan code
- provider subscription code
- provider email token where required
- current period start and end
- cancel-at-period-end
- grace-until
- status

Webhook events:

- `charge.success`
- `subscription.create`
- `subscription.not_renew`
- `subscription.disable`
- `invoice.payment_failed`

Rules:

- Verify every webhook signature.
- Make processing idempotent by event ID and payment reference.
- Never trust an amount or currency without checking it.
- Grant entitlement server-side only.
- Cancellation does not revoke access before period end.
- Failed payment enters three-day grace, then locks paid access.
- Send renewal and failure emails.

Environment variables:

- `PAYSTACK_SECRET_KEY`
- `PAYSTACK_PUBLIC_KEY`
- requester plan codes
- bidder plan codes
- `ELIPSIS_BILLING_CALLBACK_URL`

No live keys or plan codes are committed.

## 16. Admin desk

Private pages:

- overview and health
- request queue: pending, approved, awarded, closed, rejected
- bid queue: pending, approved, rejected
- bidder verification queue
- bidder subscriptions
- conversations with admin involvement
- handoffs
- audit log
- entitlements and refunds

Admin powers:

- approve, reject, request clarification
- approve or reject bids
- award or reassign
- extend conversation expiry
- suspend bidder
- grant entitlement or switch top-up
- view audit trail

All admin reads and writes of sensitive data are logged. Admin notes are never shown to clients or bidders.

## 17. Security and privacy

- Central permission service; no scattered role checks.
- Deny by default.
- Client assessment data is visible only to the client, their authorised company members, and admin.
- Bidders see only the approved request summary.
- Full request access requires approved bidder status and active subscription.
- Direct contact details revealed only after award.
- Documents served through an authorised download route, not public URLs.
- Signed handoff tokens, 15-minute expiry.
- No internal IDs in public links; use opaque references.
- Rate-limit request creation, bidding, messages, admin login, and handoff creation.
- CSRF protection on all state-changing forms.
- Admin noindex and private layout.
- Audit events for admin approvals, awards, verifications, role changes, entitlement changes, and sensitive reads.
- Data retention and deletion follow the published DPA.
- Terms and privacy updated for marketplace messaging, handoff, and subscriptions.

## 18. UI and mobile polish

- Results page hierarchy and spacing as defined in section 6.
- Primary CTA larger and higher contrast than secondary.
- Pricing has three clear sections: Free, Full Assessment, Implementation.
- Full Assessment is the visually dominant paid option.
- One-time and subscription options are distinct, not confusing.
- Gold crown on paid features.
- Partner directory uses horizontal banners on desktop and stacked cards on mobile.
- Inputs slightly taller, stronger focus ring, errors placed next to fields.
- Primary buttons full-width on small screens.
- Cards stack cleanly with consistent gaps.
- Empty states explain the next action.
- Confirmation messages are specific and reassuring.
- Hover and focus states are subtle and consistent.
- Header, footer, buttons, and spacing match across homepage, pricing, results, and dashboard.
- Accessibility: WCAG 2.2 AA target, keyboard navigation, labels, reduced motion, contrast.

## 19. Data model changes

New or extended records:

- `User`: no conflicting role field; keep `user_type` and `is_admin`.
- `AssessmentPurchase`: user, assessment, organisation, payment, source, active.
- `PhysicalAssessmentRequest`: add `user_id`, `assessment_id`, `summary_snapshot`, `expectations`, `specifications`, `status`, `reviewed_by`, `reviewed_at`, `rejection_reason`, `awarded_bid_id`, `closed_at`, `closed_reason`, `switches_used`, `switches_granted`.
- `BidderCompany`: add `slug`, `verification_status`, `verification_submitted_at`, `verified_at`, `verified_by`, `verification_notes`, `partner_tier`, `pinned_rank`, `rating`, `completed_jobs`, `logo_url`.
- `BidSubmission`: add `status`, `admin_reviewed_by`, `admin_reviewed_at`, `admin_notes`, `roadmap_document_id`.
- `BidDocument`: new private document record.
- `MarketplaceConversation`: request, bid, requester, bidder, status, opened_at, last_message_at, closes_at, closed_at, close_reason, admin_involved.
- `ConversationMessage`: conversation, author, body, created_at, internal flag.
- `ConversationRead`: conversation, user, last_read_at.
- `MarketplaceNotification`: user, event, title, detail, url, read_at.
- `BillingSubscription`: user, organisation, bidder company, plan code, provider, provider subscription code, status, period dates, cancel flag, grace.
- `Payment`: extend with purpose, plan code, subscription, metadata, processed timestamp.
- `AuditEvent`: reuse for all admin actions.

Indexes:

- request status and created date
- request organisation and assessment
- bid request and status
- conversation request, bidder, status, last message
- message conversation and created date
- bidder verification status and partner tier
- subscription status and period end
- audit actor and created date

## 20. Migrations and backfill

- Add columns and tables with Alembic.
- Migrate request statuses: `pending → pending_review`, `verified/published → approved`, keep `rejected`.
- Backfill request `user_id` from organisation owner or oldest active member.
- Set existing bidders to `submitted` for review unless already actively approved by admin.
- Preserve existing bids; map `pending → pending_review`, `submitted → pending_review`.
- Preserve existing Premium entitlements in `pro_until`; do not revoke.
- Legacy physical service packages and `/physical` are deprecated and redirect to implementation request.
- Run migration on a copy first; verify counts and no orphan records.

## 21. Feature flags and rollout

- `ELIPSIS_MARKETPLACE_ENABLED`
- `ELIPSIS_MARKETPLACE_MESSAGING_ENABLED`
- `ELIPSIS_BILLING_RECURRING_ENABLED`
- `ELIPSIS_PARTNER_HANDOFF_ENABLED`
- `ELIPSIS_REQUIRE_BIDDER_VERIFICATION`

Rollout:

1. Internal admin only.
2. Approved test bidders.
3. Existing Premium customers.
4. Public marketplace.

Keep the marketplace closed to the public until verification, audit, and messaging tests pass.

## 22. Testing

Required tests:

- anonymous, client, other client, unverified bidder, verified bidder, admin
- no access to another client’s assessment
- no access to pending or rejected requests
- no access to full request without approved bidder status and active subscription
- no access to conversation without participation
- admin routes return 404 to non-admin
- admin actions create audit events
- handoff token tamper, expiry, and reuse
- request lifecycle and bid lifecycle
- bid approval before visibility
- award notifies requester and bidder
- conversation closes 24 hours after last message
- switch count, top-up, and subscription unlimited switching
- one-time entitlement per assessment
- webhook signature, idempotency, renewal, failure, cancellation
- no public document URLs
- mobile layout and accessible forms
- migration and backfill

## 23. Delivery phases

### Phase 0 — Specification and fixtures

- approve pricing and copy
- create seed data for Great Turbinez and test bidders
- define Paystack plan placeholders
- finalise status names and permissions

### Phase 1 — Security, roles, and billing foundation

- permission service
- admin guards and audit
- request ownership fix
- bidder verification fields
- entitlement and payment models
- handoff token service
- tests for leaks and permissions

### Phase 2 — Results, request builder, and handoff

- free versus full result
- payment unlock
- guided request builder
- assessment snapshot
- results hierarchy
- Great Turbinez request-flow entry
- handoff

### Phase 3 — Marketplace and partner directory

- public teaser pages
- separate requests and companies pages
- verified partner banners
- pinned Great Turbinez
- bidder application and admin verification
- bid submission, admin approval, award

### Phase 4 — Conversations and notifications

- conversation rooms
- admin involvement
- 24-hour expiry
- switching and top-ups
- notifications and email
- accountability disclaimer

### Phase 5 — Pricing, visual polish, and QA

- three-section pricing
- premium crown system
- mobile and form polish
- results depth
- accessibility
- end-to-end tests

## 24. Acceptance criteria

- Every completed Full Assessment can produce a complete request without retyping the assessment.
- Free users cannot create requests or see full metrics.
- No request becomes visible without admin approval.
- No bid becomes visible to the requester without admin approval.
- No bidder sees a request without verification and an active subscription.
- No conversation is readable by an uninvolved admin.
- A conversation closes 24 hours after the last message.
- One-time requesters get exactly three switches, and can buy a half-price top-up for three more.
- Subscribed requesters can switch without limit among approved bids.
- Great Turbinez is pinned and trusted but obeys the same marketplace rules.
- The platform takes no implementation commission.
- Auto-renewal, cancellation, failure, and grace work through Paystack.
- Every admin action is audited.
- All public pages work on mobile, and paid CTAs meet contrast and tap-target requirements.

## 25. Risks and assumptions

- 24 hours after the last message is short for complex implementation negotiations. The platform records closure, not a legally binding contract. The parties can continue off-platform, but Elipsis accountability ends.
- Pricing is a launch hypothesis and should be reviewed after the first 90 days.
- Great Turbinez must supply its handoff endpoint and shared secret.
- Paystack plan codes and account setup are external dependencies.
- Marketplace liquidity depends on verified bidder supply. Do not open publicly before enough verified partners exist.
- Verification reduces risk but does not guarantee delivery quality. Ratings, references, and completed-job evidence must be visible.
- The existing `/physical` service packages and pricing must be retired to avoid contradicting the new model.

## 26. Definition of real value

The upgrade is not successful merely because it has more screens. It is successful when:

- a logistics operator can move from score to a complete implementation brief in one session
- verified partners receive enough context to quote without a discovery call
- the requester can compare implementation approaches without exposing private data
- the partner directory is credible enough for a finance or operations lead to trust
- completed work produces a re-score and visible movement
- the platform remains private, auditable, and controllable as usage grows

## 27. As-built status

Implemented on `marketplace-platform-upgrade` and opened as PR #15:

- Marketplace models, verification states, entitlements, switch helpers, conversations, notifications, billing records, and signed handoffs.
- Request privacy and admin-only review APIs; non-admin admin routes return 404.
- Admin request desk detail, bid approval/rejection, award, client preference, bidder verification, conversation view, and handoff view.
- Client preference recorded before award (`preferred_bid_id`, `preferred_at`); admin confirms the award.
- Private request documents set and use `s3_key`; download remains behind marketplace access checks.
- Full Assessment `$49` checkout and results paywall; paid report unlocked per assessment via `AssessmentPurchase`.
- Private conversations with 24-hour reply window, lazy expiry, admin involvement, outcome recording, and persistent notifications.
- Switches and `$24.50` three-switch top-ups; requester billing records update the request entitlement.
- HMAC handoff: 15-minute single-use token, sanitized payload, server-to-server fetch secret.
- Partner directory, application flow, verification-document upload, partner console, and one-time bidder subscription checkout (monthly `$39`, six months `$119`, annual `$219`).
- Great Turbinez seeded as trusted/pinned verified partner with inactive subscription (no marketplace exemption).
- Feature flags: messaging, billing, handoff, and verification.
- Paystack recurring wiring: plan codes are read from environment; checkout passes the plan when configured; `charge.success`, `subscription.create`, `subscription.not_renew`, `subscription.disable`, and `invoice.payment_failed` renew or update access and `BillingSubscription` records.
- Transactional email with Resend as the recommended provider: branded verification, welcome, password reset, workspace invite, marketplace lifecycle, conversation, payment receipt, failed payment, cancellation, and digest messages. `notify_email` is respected for non-security events.
- Migrations `1ba0fb9462ad`, `5b7b51e54c7c`, and `6c1f2a9d8e44`; `alembic check` is clean on SQLite.
- Core authorization is centralised in `elipsis_api/permissions.py`; marketplace visibility helpers call it directly instead of duplicating role checks.
- Regression suite passes (`119` tests; lifecycle suite `5` passing).

Deferred pending provider/partner details:

- Live Paystack plan codes and USD checkout verification (the code path is wired; values belong in Vercel).
- Turbinez `/from-elipsis` contract and shared fetch secret.
- Browser/screenshot QA and production auth-session diagnosis.
- Full-repo ruff baseline remains dirty outside changed files.

