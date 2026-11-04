# Elipsis Implementation Roadmap

**Single Source of Truth**  
Version: 1.1  
Date: 4 November 2026  
Owner: Founder  
Status: Active

---

## Executive Summary

**Product Positioning:**  
Elipsis is a global automation implementation marketplace for logistics organizations. Like Upwork but specifically for logistics automation, with a professional assessment that answers "what should we automate first?"

**Value Proposition:**  
Logistics operators (10-300 staff) get a professional assessment ($49) that identifies what to automate, the cost of inaction, and a 90-day plan. They can then publish requests to vetted implementation partners. Partners pay monthly ($39-$219) to access and bid on these requests.

**Market Opportunity:**  
- Logistics automation market: ~$75–90B (2025) → $130–230B (2030–34), ~8–12% CAGR (hardware-heavy; software/services more accessible to mid-market)
- Consulting diagnostics: $5K–$25K+ (out of reach for mid-market)
- Horizontal freelance platforms: volume exists but low trust/structure for complex implementation work
- **Gap:** Mid-market logistics operators need professional, affordable, credible automation guidance and a path to the right implementer

**Timeline:** 12 weeks to launch → 6 months to validate revenue

**Strategic posture (v1.1):** Treat the **assessment as the primary product** until there is clear proof it converts to paid work and documented outcomes. Activate the marketplace deliberately once demand quality is proven. Prioritise bidder **quality over quantity**.

---

## The Sharpened Wedge

### Three Products (Simple, Clear)

| Product | Price | What You Get | Customer |
|---------|-------|--------------|----------|
| **Free Diagnostic** | $0 | Elipsis Index, maturity band, top 3 constraints, sample 90-day plan (on-screen only) | Any logistics operator |
| **Full Assessment** | $49 one-time (test higher later) | Complete 36-metric report, costed friction analysis, ranked pain points, 90-day roadmap with owners/dates/KPIs, PDF/Excel/JSON exports, path to implementer intros | Logistics operators ready to act |
| **Marketplace Access** | $39/mo, $119/6mo, $219/yr | Verified listing, access to published requests, bidding rights, conversation access, admin verification | Automation implementation partners |

### Non-Goals (Do Not Build)

❌ Daily operations layer (control tower, tasks, shifts, routines) - Separate product  
❌ Telematics, GPS, fleet management integration  
❌ Dispatch, routing, load board, carrier marketplace  
❌ Full TMS/WMS/ERP replacement  
❌ Native mobile app (responsive web only)  
❌ AI/ML features (assessment is sophisticated enough)  
❌ Enterprise sales (target mid-market 10-300 staff)  
❌ Expansion beyond logistics sector

**Discipline rule:** Every hour spent on non-wedge work reduces the chance of hitting early revenue and liquidity milestones. Say no by default.

---

## Success Levers (How We Improve Odds)

These levers are locked into execution. They come from market reality (mid-market CAPEX fear, integration complexity, need for trust) and are non-negotiable for the next 12 weeks.

### 1. Assessment is the primary product (longer)
- Delay **heavy** marketplace activation until there is proof that assessments convert to paid work (even via manual intros or offline delivery).
- Target **30–50 paying assessments** and documented outcomes before treating the marketplace as the main growth engine.
- Marketplace infrastructure stays ready; promotion and bidder acquisition stay measured until demand quality is clear.

**How to achieve it:**
- Week 1–2: Ship core, enable marketplace flag for internal/manual use only if needed.
- Weeks 2–6: Obsess over assessment completion rate, paid conversion, and collecting outcome stories.
- Only scale bidder recruitment and public request volume once 10+ paid assessments exist and at least a few have clear next-step intent or completed work.

### 2. Strengthen “cost of inaction” and outcome proof
- The $49 report wins when friction is quantified in money and the 90-day plan feels specific and actionable.
- Make financial model and recommendations logistics-specific (warehouse, 3PL, transport operations language and cost ranges).
- Collect and publish even small case studies or anonymised before/after numbers as soon as they exist.

**How to achieve it:**
- Week 3–4: Research and hard-code realistic logistics cost ranges; tighten recommendation copy.
- After every paid assessment: request a 15-minute feedback call; capture one quantifiable insight or quote.
- Publish 2–3 anonymised mini case studies by end of Week 8 (even if outcomes are partial).

### 3. Bidder side: quality over quantity
- 5–10 excellent, logistics-experienced implementers who deliver results create more trust than 20 general freelancers.
- Manual high-touch verification and early success stories matter more than automated onboarding early on.

**How to achieve it:**
- Prioritise outreach to people with logistics domain experience (ex-ops, small logistics software shops, consultants who have done warehouse/3PL automation).
- Free first month for the first 5–10 verified bidders who meet quality bar.
- Require a short portfolio or reference check before verification; document wins publicly (with permission).

### 4. Distribution realism
LinkedIn outreach is necessary but insufficient.

**Layer in:**
- Partnerships with logistics associations, software resellers, accountants/ERP implementers who already serve the ICP.
- Content that ranks for intent queries (“what should we automate in our warehouse/3PL”, “cost of manual processes in logistics”).
- Warm intros and referrals once the first 5–10 assessments are done.

**How to achieve it:**
- Weeks 2–4: Identify 10–15 potential partners; send personalised partnership notes (referral or co-branded diagnostic).
- Weeks 4–8: Publish 4–6 practical content pieces (LinkedIn + simple site pages).
- After each successful assessment: ask for one introduction.

### 5. Pricing experiments
- $49 is aggressive for acquisition. Once quality is proven, test higher price points or bundles.

**How to achieve it:**
- Keep $49 until 15–20 paid assessments and positive feedback exist.
- Then A/B or sequential test $99–$149, and/or an “Assessment + 3 qualified intros” bundle.
- Track conversion rate and willingness-to-pay feedback in every post-assessment call.

### 6. Measurement discipline
Track the full funnel religiously. Treat early metrics as leading indicators of whether the model works.

| Stage | Metric | Early target |
|-------|--------|--------------|
| Top of funnel | Assessment starts | Growing weekly |
| Completion | Completion rate | > 75–80% |
| Revenue | Paid Full Assessments | 30–50 before heavy marketplace push |
| Intent | Request published or explicit next-step | Rising % of paid |
| Supply | Verified quality bidders | 5–10 strong |
| Match | Bid → award → successful delivery | Document every one |

Review these numbers in the weekly check-in. If assessment-to-paid or paid-to-next-step stalls, fix that before scaling marketplace promotion.

---

## Technical Foundation

### What Exists (Production-Ready)

✅ **Assessment Engine**
- 63-question instrument across 7 pillars, 21 subdomains
- 36 executive metrics with declarative formulas
- Automated scoring, maturity bands, pain points, recommendations
- 90-day roadmap with owners, dates, dependencies, KPIs
- Financial model with cost-of-inaction calculations
- Pure Python implementation (`readiness.py`, `constants.py`)

✅ **Marketplace Infrastructure**
- Request creation, admin approval, publishing
- Bidder verification, subscription management
- Bid submission, admin approval, award
- Private conversations with 24-hour expiry
- Switch system (3 switches per assessment, unlimited for subscribers)
- Admin desk for requests, bids, bidders, conversations
- Feature flags (messaging, billing, handoff, verification)

✅ **Payment Integration**
- Paystack checkout for one-time purchases
- Paystack recurring subscriptions (wired, needs plan codes)
- Webhook signature verification
- Grace period handling
- Entitlement management

✅ **Deployment Stack**
- FastAPI + SQLAlchemy + Jinja2
- Vercel deployment configuration
- PostgreSQL (Neon) or SQLite fallback
- Alembic migrations
- Test suite

✅ **Documentation**
- Platform master plan, implementation guide, service delivery standard, release checklist

### Technical Debt (Must Fix — Week 1)

🔴 **Critical**
1. Test failures (settings template / related)
2. Role field conflict — use only `user_type` + `is_admin` (locked decision)

🟡 **Medium**
3. Marketplace flag still off until Paystack plan codes and deliberate activation decision
4. Theme / UI polish merge
5. Any remaining test expectation mismatches

---

## Implementation Phases

### Phase 1: Ship the Core (Weeks 1–2)

**Objective:** Green tests, role consolidation, assessment live and reliable. Marketplace infrastructure available for controlled/manual use; do not force public liquidity yet.

#### Week 1: Fix & Launch

| Day | Task | Owner | Acceptance Criteria |
|-----|------|-------|---------------------|
| 1–2 | Fix test failures | Founder | Full suite green |
| 2–3 | Complete role consolidation (`user_type` only) | Founder | Legacy `role` unused for auth |
| 3–4 | Merge theme / UI polish | Founder | Dark-first + light option live |
| 4–5 | Manual QA of assessment → results → export | Founder | Happy path solid |
| 5–6 | Deploy to production | Founder | Production stable |
| 6–7 | Monitoring + first real assessment invites | Founder | No critical errors; pipeline started |

**Deliverables:** Clean test suite, production assessment path reliable, first operators in pipeline.

#### Week 2: Assessment Traction (not full marketplace push)

| Day | Task | Owner | Acceptance Criteria |
|-----|------|-------|---------------------|
| 1–3 | Recruit 5–10 logistics operators | Founder | Committed to try assessment |
| 2–5 | Guide completions; convert free → paid where possible | Founder | Paying assessments started |
| 3–5 | Identify 5–8 high-quality bidder candidates | Founder | Shortlist ready |
| 5–7 | Manual verification of first 2–3 bidders (quality bar) | Founder | Verified and briefed |
| 7 | Document learnings; update cost-of-inaction notes | Founder | Insights captured |

**Deliverables:** Real assessment completions, early paid conversions, small set of quality bidders ready.

---

### Phase 2: Polish the Assessment (Weeks 3–4)

**Objective:** Make the assessment feel like a premium consulting product. Maximise completion, perceived value, and conversion to paid / next step.

#### Week 3: Professional Curation
- Logistics-specific question language and examples
- Stronger “why this matters” copy
- 3–5 additional logistics-specific questions if gaps exist
- Keep scoring integrity

#### Week 4: Report & Cost-of-Inaction Polish
- Results hierarchy: executive summary and money impact first
- Realistic logistics cost figures in the calculator
- More specific 90-day plan language and recommendations
- Mobile polish and performance

**Success metrics (end Phase 2):** Completion rate > 80%, time < 30 min, user satisfaction > 4/5, clear cost-of-inaction numbers that operators recognise.

---

### Phase 3: Controlled Marketplace Activation (Weeks 5–6)

**Objective:** Only after assessment traction is visible — introduce quality bidders and a small number of real requests.

#### Week 5: Quality Bidder Recruitment
- Landing page and clear opportunity story
- Targeted outreach (logistics-experienced implementers preferred)
- Free first month for first 5–10 who pass quality bar
- Manual verification + short onboarding

#### Week 6: First Real Matches
- Publish a small number of real (or highly realistic) requests tied to assessments
- Notify verified bidders
- Support first bids → award → conversation
- Document quality and any delivery outcomes

**Success metrics:** 5–10 strong verified bidders, first awards, conversation and delivery notes captured.

---

### Phase 4: Growth (Weeks 7–12)

**Objective:** 10+ paying assessment clients, proven conversion path, 10–20 quality bidders, early MRR from subscriptions, and clear evidence the model works.

Focus areas:
- Marketing funnel (assessment-led)
- Partnerships and content
- Pricing tests once proof exists
- Referral loop
- Funnel dashboard and weekly metric review
- Retrospective and next-12-week plan

**End of Week 12 targets (adjusted for assessment-first posture):**
- 30–50 paying Full Assessments (stretch) or clear trajectory toward it
- Documented outcomes / mini case studies
- 10–20 quality active bidders
- Marketplace matches happening with positive delivery signals
- MRR from bidder subscriptions starting to appear
- NPS or equivalent satisfaction signal > 40 where measured

---

## Resource Allocation

### Solo Founder Schedule (guideline)

| Activity | Hours/Week | Notes |
|----------|------------|-------|
| Development / product | ~20–25 | Keep decreasing as core stabilises |
| Operator outreach & assessment support | ~15–18 | Highest leverage early |
| Bidder quality recruitment & verification | ~5–8 | Quality over volume |
| Content, partnerships, distribution | ~6–8 | Compound over time |
| Admin, metrics, support | ~5 | Weekly funnel review non-negotiable |

Protect family time. Review this roadmap weekly.

---

## Decision Log

### Locked Decisions
1. Marketplace model — no commission on awards. Revenue from assessments + bidder subscriptions.
2. Target segment — logistics operators 10–300 staff.
3. Pricing baseline — Free diagnostic, $49 Full Assessment (subject to later tests), $39–$219 bidder plans.
4. Tech stack — FastAPI + SQLAlchemy + Jinja2 on Vercel.
5. Assessment scope — 63 questions, 7 pillars, 36 metrics (do not expand casually).
6. Non-goals — as listed above.
7. **Assessment-first posture** — prove assessment value and conversion before heavy marketplace scaling.
8. **Bidder quality over quantity** — prefer fewer excellent, logistics-relevant implementers.

### Pending (by Week 2–4)
- Paystack plan codes
- Exact timing of public marketplace promotion (data-triggered)
- First pricing experiment design
- Partnership shortlist

---

## Definition of Done (Updated)

### Phase 1
- [ ] All critical tests passing
- [ ] Role consolidation done (`user_type` authoritative)
- [ ] Assessment path production-stable
- [ ] First real operators in pipeline

### Phase 2
- [ ] Logistics-specific assessment polish live
- [ ] Cost-of-inaction numbers credible
- [ ] Completion and satisfaction targets hit or clearly trending

### Phase 3
- [ ] 5–10 quality verified bidders
- [ ] First real request → bid → award path completed
- [ ] Outcome notes captured

### Phase 4
- [ ] Meaningful volume of paying assessments
- [ ] Documented outcomes / case studies
- [ ] Marketplace matches with positive signals
- [ ] Funnel dashboard in use
- [ ] 12-week retrospective and next plan written

---

## Weekly Check-in Template

### Week: [X] of [12]

**Completed:**
- [ ] ...

**Blocked On:**
- ...

**Funnel metrics:**
- Assessment starts / completions / paid: [ ]
- Requests published / bids / awards: [ ]
- Quality bidders active: [ ]
- MRR: [ ]

**Learnings (especially cost-of-inaction & operator language):**
- ...

**Next week focus (max 3):**
- [ ] ...

**Roadmap changes:** None / [description]

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 3 Nov 2026 | Initial roadmap |
| 1.1 | 4 Nov 2026 | Assessment-first posture; cost-of-inaction & outcome proof; bidder quality over quantity; distribution realism; pricing experiments; stronger measurement discipline. ICP kept at logistics 10–300. |

---

**This document is the single source of truth. All changes to scope, timeline, or priorities must be reflected here.**
