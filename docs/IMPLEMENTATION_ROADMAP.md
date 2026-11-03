# Elipsis Implementation Roadmap

**Single Source of Truth**  
Version: 1.0  
Date: 3 November 2026  
Owner: Founder  
Status: Active

---

## Executive Summary

**Product Positioning:**  
Elipsis is a global automation implementation marketplace for logistics organizations. Like Upwork but specifically for logistics automation, with a professional assessment that answers "what should we automate first?"

**Value Proposition:**  
Logistics operators (10-300 staff) get a professional assessment ($49) that identifies what to automate, the cost of inaction, and a 90-day plan. They can then publish requests to vetted implementation partners. Partners pay monthly ($39-$219) to access and bid on these requests.

**Market Opportunity:**  
- Logistics automation software: $8.9B (2025) → $30.5B (2033), 17% CAGR
- Consulting: $5K-$25K diagnostic, $25K-$150K+ implementation (out of reach for mid-market)
- Fiverr/Upwork: $10-$1,350/gig but no structure, no credibility
- **Gap:** Mid-market logistics operators need professional, affordable, credible automation guidance

**Timeline:** 12 weeks to launch → 6 months to validate revenue

---

## The Sharpened Wedge

### Three Products (Simple, Clear)

| Product | Price | What You Get | Customer |
|---------|-------|--------------|----------|
| **Free Diagnostic** | $0 | Elipsis Index, maturity band, top 3 constraints, sample 90-day plan (on-screen only) | Any logistics operator |
| **Full Assessment** | $49 one-time | Complete 36-metric report, costed friction analysis, ranked pain points, 90-day roadmap with owners/dates/KPIs, PDF/Excel/JSON exports, 3 bidder introductions | Logistics operators ready to act |
| **Marketplace Access** | $39/mo, $119/6mo, $219/yr | Verified listing, access to all published requests, bidding rights, conversation access, admin verification | Automation implementation partners |

### Non-Goals (Do Not Build)

❌ Daily operations layer (control tower, tasks, shifts, routines) - Separate product  
❌ Telematics, GPS, fleet management integration  
❌ Dispatch, routing, load board, carrier marketplace  
❌ Full TMS/WMS/ERP replacement  
❌ Native mobile app (responsive web only)  
❌ AI/ML features (assessment is sophisticated enough)  
❌ Enterprise sales (target mid-market 10-300 staff)  
❌ Expansion beyond logistics sector

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
- Test suite (119 tests, 2 failing)

✅ **Documentation**
- Platform master plan (strategy, ICP, features)
- Implementation guide (marketplace specification)
- Service delivery standard (SLA, support)
- Release checklist

### Technical Debt (Must Fix)

🔴 **Critical Blockers**
1. **Test failures** - 2 tests fail with template error on `/settings`
   - `test_growth_certification_imports_and_webhooks`
   - `test_company_room_membership_collaboration_and_branding`
   - Error: `UndefinedError: 'tuple object' has no attribute 'items'`
   - Impact: Blocks confidence in deployment

2. **Role field conflict** - Two role fields exist (`User.role` and `User.user_type`)
   - Platform guide locked decision: use only `user_type`
   - `permissions.py:26` reads both fields
   - Impact: Confusing permissions, potential security gaps

🟡 **Medium Priority**
3. **Marketplace disabled** - `ELIPSIS_MARKETPLACE_ENABLED=0` in config
   - Full marketplace flow exists but not accessible
   - Needs Paystack plan codes for live billing
   - Impact: Cannot generate revenue

4. **Theme changes uncommitted** - Staged CSS/template changes on branch
   - `feat/theme-default-dark-responsive-polish` branch
   - Changes not merged to main
   - Impact: Unclear what UI state is current

5. **Test expectation mismatch** - `test_marketplace_is_locked_while_coming_soon` expects 503, receives 404
   - Hardening test needs update
   - Impact: Test suite fails

---

## Implementation Phases

### Phase 1: Ship the Core (Weeks 1-2)

**Objective:** Enable marketplace and achieve first end-to-end transaction

#### Week 1: Fix & Launch

| Day | Task | Owner | Acceptance Criteria |
|-----|------|-------|---------------------|
| 1 | Fix test failures - debug `/settings` template error | Founder | Both tests pass |
| 2 | Fix test failures - implement fix | Founder | Test suite green |
| 2 | Resolve role field conflict - plan migration | Founder | Migration script ready |
| 3 | Resolve role field conflict - execute migration | Founder | `User.role` unused, `user_type` only |
| 3 | Commit theme changes - review diff | Founder | All changes intentional |
| 4 | Commit theme changes - merge to main | Founder | Branch clean, tests pass |
| 4 | Enable marketplace on staging - set flag | Founder | Marketplace routes accessible |
| 5 | Manual QA - assessment → request flow | Founder | Full flow works end-to-end |
| 5 | Manual QA - bidder signup → bid flow | Founder | Full flow works end-to-end |
| 6 | Manual QA - admin approval → award flow | Founder | Full flow works end-to-end |
| 6 | Deploy to production - verify | Founder | Production marketplace live |
| 7 | Monitoring - watch for errors | Founder | No critical errors in 24hrs |

**Deliverables:**
- Clean test suite (all 119+ tests passing)
- Marketplace enabled on production
- First end-to-end transaction (even if test data)

#### Week 2: Validation

| Day | Task | Owner | Acceptance Criteria |
|-----|------|-------|---------------------|
| 1 | Recruit 3-5 logistics operators | Founder | 3 operators committed |
| 2 | Guide operators through assessment | Founder | 3 assessments completed |
| 3 | Guide operators to create requests | Founder | 3 requests created |
| 3 | Recruit 2-3 bidders | Founder | 2 bidders signed up |
| 4 | Verify bidders manually | Founder | 2 bidders verified |
| 4 | Notify bidders of requests | Founder | Bidders receive notifications |
| 5 | Monitor bid submission | Founder | At least 1 bid submitted |
| 5 | Admin approve bid | Founder | Bid approved |
| 6 | Award first request | Founder | First award completed |
| 6 | Start conversation | Founder | Conversation active |
| 7 | Document learnings | Founder | Lessons captured in doc |

**Deliverables:**
- 3 real assessment completions
- 3 real marketplace requests
- 2 verified bidders
- First real bid → award → conversation

**Success Metrics:**
- 0 critical bugs in production
- 100% of recruited users complete assessment
- 100% of bidders verified successfully
- Conversation closes within 24 hours

---

### Phase 2: Polish the Assessment (Weeks 3-4)

**Objective:** Make assessment feel like premium consulting product

#### Week 3: Professional Curation

| Day | Task | Owner | Acceptance Criteria |
|-----|------|-------|---------------------|
| 1 | Review all 63 questions for logistics specificity | Founder | Question audit document |
| 2 | Add logistics examples to generic questions | Founder | 10+ questions enhanced |
| 2 | Improve "why" explanations | Founder | All "why" text compelling |
| 3 | Add 3-5 logistics-specific questions | Founder | Questions integrated |
| 3 | Update question weights if needed | Founder | Scoring still valid |
| 4 | Test new question flow | Founder | Assessment completes successfully |
| 4 | Update scoring if needed | Founder | Metrics still 0-100 range |
| 5 | A/B test question wording with 2 users | Founder | User feedback captured |
| 5 | Iterate based on feedback | Founder | Questions refined |
| 6 | Document question changes | Founder | Change log updated |
| 6 | Migration script for new questions | Founder | Migration tested |
| 7 | Deploy question changes | Founder | Production updated |

**Deliverables:**
- Logistics-specific question set
- Enhanced "why" explanations
- 3-5 new logistics questions
- Migration script
- Change log

#### Week 4: Report Polish

| Day | Task | Owner | Acceptance Criteria |
|-----|------|-------|---------------------|
| 1 | Redesign results page hierarchy | Founder | Executive summary first |
| 1 | Wireframe new layout | Founder | Design approved |
| 2 | Implement new layout | Founder | Page renders correctly |
| 2 | Add cost-of-inaction calculator | Founder | Calculator functional |
| 3 | Research realistic logistics cost figures | Founder | Cost database created |
| 3 | Integrate cost figures into calculator | Founder | Costs realistic |
| 4 | Improve 90-day plan output | Founder | Plans more specific |
| 4 | Add logistics-specific recommendations | Founder | 10+ logistics recommendations |
| 5 | Mobile responsive testing | Founder | Works on phone |
| 5 | Fix mobile issues | Founder | Mobile polished |
| 6 | Performance testing | Founder | Load < 3 seconds |
| 6 | Optimize if needed | Founder | Performance target met |
| 7 | Deploy report changes | Founder | Production updated |

**Deliverables:**
- New results page layout
- Cost-of-inaction calculator with logistics figures
- Improved 90-day plans
- Mobile-polished reports
- Performance optimized

**Success Metrics:**
- Assessment completion rate > 80%
- Time to complete assessment < 30 minutes
- User satisfaction score > 4/5
- Mobile traffic > 30% of total

---

### Phase 3: Bidder Supply (Weeks 5-6)

**Objective:** Build marketplace liquidity with active bidders

#### Week 5: Bidder Recruitment

| Day | Task | Owner | Acceptance Criteria |
|-----|------|-------|---------------------|
| 1 | Create bidder landing page | Founder | Page live, compelling copy |
| 1 | Explain opportunity clearly | Founder | Value proposition clear |
| 2 | Compile bidder outreach list | Founder | 50+ contacts identified |
| 2 | Create outreach templates | Founder | 3 templates ready |
| 3 | LinkedIn outreach to automation consultants | Founder | 20 messages sent |
| 3 | Outreach to n8n/Zapier/Make specialists | Founder | 20 messages sent |
| 4 | Outreach to small logistics software shops | Founder | 20 messages sent |
| 4 | Outreach to independent logistics consultants | Founder | 20 messages sent |
| 5 | Offer free first month to first 10 | Founder | Offer communicated |
| 5 | Respond to interested bidders | Founder | All replies handled |
| 6 | Manually verify first 5 bidders | Founder | 5 bidders verified |
| 6 | Onboard verified bidders | Founder | Bidders can bid |
| 7 | Publish bidder verification guide | Founder | Guide in help center |

**Deliverables:**
- Bidder landing page
- Outreach list (80+ contacts)
- Outreach templates
- 5-10 verified bidders
- Verification guide

#### Week 6: Marketplace Activation

| Day | Task | Owner | Acceptance Criteria |
|-----|------|-------|---------------------|
| 1 | Publish first 3-5 real requests | Founder | Requests visible to bidders |
| 1 | Even if test cases, make them realistic | Founder | Requests credible |
| 2 | Notify bidders of new requests | Founder | Bidders receive emails |
| 2 | Set up automated request alerts | Founder | Alerts working |
| 3 | Monitor bid quality | Founder | Bid quality documented |
| 3 | Adjust pricing if needed | Founder | Pricing data analyzed |
| 4 | Encourage first bids | Founder | Manual follow-up if needed |
| 4 | Review incoming bids | Founder | Bids assessed |
| 5 | Admin approve first real bid | Founder | Bid approved |
| 5 | Award first real request | Founder | Award completed |
| 6 | Start conversation | Founder | Conversation active |
| 6 | Monitor conversation quality | Founder | Conversation documented |
| 7 | Document marketplace activation | Founder | Process documented |

**Deliverables:**
- 3-5 published requests
- Automated request alerts
- First real bid
- First real award
- Conversation documentation

**Success Metrics:**
- 5-10 active bidders
- 3-5 published requests
- Average bids per request > 2
- Time to first bid < 48 hours
- Conversation closure rate > 80%

---

### Phase 4: Growth (Weeks 7-12)

**Objective:** 10 paying clients, 20 active bidders, revenue validation

#### Week 7-8: Marketing Funnel

| Day | Task | Owner | Acceptance Criteria |
|-----|------|-------|---------------------|
| 1 | Create landing page focused on "What should we automate first?" | Founder | Page live |
| 1 | A/B test headline variants | Founder | Winner identified |
| 2 | Write 3 case studies (can be hypothetical) | Founder | Case studies published |
| 2 | Create social proof section | Founder | Testimonials/logos added |
| 3 | Set up email sequence for assessment completers | Founder | Sequence active |
| 3 | Create assessment reminder emails | Founder | Reminders scheduled |
| 4 | LinkedIn outreach to logistics COOs | Founder | 50 messages sent |
| 4 | LinkedIn outreach to Operations Directors | Founder | 50 messages sent |
| 5 | Join logistics LinkedIn groups | Founder | 5 groups joined |
| 5 | Share value in groups (not spam) | Founder | 10 posts |
| 6 | Create referral program | Founder | Program defined |
| 6 | Implement referral tracking | Founder | Tracking working |
| 7 | Measure funnel metrics | Founder | Dashboard live |
| 7 | Optimize based on data | Founder | Iterations planned |

**Deliverables:**
- Landing page with clear value prop
- 3 case studies
- Email sequences
- LinkedIn outreach (100+ messages)
- Referral program
- Funnel dashboard

#### Week 9-10: Product Refinement

| Day | Task | Owner | Acceptance Criteria |
|-----|------|-------|---------------------|
| 1 | Analyze assessment completion drop-off | Founder | Drop-off points identified |
| 1 | Add progress indicator if needed | Founder | Progress bar implemented |
| 2 | Simplify question flow if needed | Founder | Flow optimized |
| 2 | Reduce assessment time if needed | Founder | Time < 25 minutes |
| 3 | Improve request-to-bid conversion | Founder | Conversion funnel analyzed |
| 3 | Add request templates | Founder | Templates available |
| 4 | Improve bidder dashboard | Founder | Dashboard more useful |
| 4 | Add request alerts to dashboard | Founder | Alerts visible |
| 5 | Improve admin desk efficiency | Founder | Admin time reduced |
| 5 | Add bulk actions | Founder | Bulk operations working |
| 6 | Gather user feedback | Founder | 10+ interviews |
| 6 | Prioritize feedback | Founder | Backlog prioritized |
| 7 | Deploy top 3 improvements | Founder | Improvements live |

**Deliverables:**
- Assessment flow optimized
- Request templates
- Improved bidder dashboard
- Improved admin desk
- User feedback captured
- 3 improvements deployed

#### Week 11-12: Scaling

| Day | Task | Owner | Acceptance Criteria |
|-----|------|-------|---------------------|
| 1 | Automate bidder verification where possible | Founder | Automation documented |
| 1 | Keep manual verification for quality | Founder | Quality maintained |
| 2 | Add featured bidder option | Founder | Feature implemented |
| 2 | Set featured bidder pricing | Founder | Pricing decided |
| 3 | Improve SEO for logistics keywords | Founder | Keywords identified |
| 3 | Implement SEO changes | Founder | SEO improved |
| 4 | Set up Google Analytics | Founder | Analytics tracking |
| 4 | Set up conversion tracking | Founder | Conversions tracked |
| 5 | Review pricing strategy | Founder | Strategy documented |
| 5 | Adjust if needed | Founder | New pricing live |
| 6 | 12-week retrospective | Founder | Lessons documented |
| 6 | Plan next 12 weeks | Founder | Roadmap updated |
| 7 | Communicate progress (blog, social) | Founder | Progress shared |

**Deliverables:**
- Automated verification (partial)
- Featured bidder option
- SEO improvements
- Analytics setup
- Pricing review
- 12-week retrospective
- Next 12-week plan

**Success Metrics (End of Week 12):**
- 10 paying clients (Full Assessment)
- 20 active bidders
- Monthly recurring revenue > $2,000
- Assessment completion rate > 75%
- Bid conversion rate > 20%
- Net Promoter Score > 40

---

## Resource Allocation

### Solo Founder Schedule (9 hours/day, 7 days/week = 63 hours/week)

| Activity | Hours/Week | Percentage |
|----------|------------|------------|
| Development (coding, testing, deployment) | 25 | 40% |
| User outreach & recruitment | 15 | 24% |
| Product refinement (copy, UX, feedback) | 10 | 16% |
| Marketing (content, social, SEO) | 8 | 13% |
| Admin & operations (support, billing, monitoring) | 5 | 8% |
| **Total** | **63** | **100%** |

### Time Blocking Recommendation

| Time Block | Activity | Notes |
|------------|----------|-------|
| 6:00-9:00 (3h) | Deep work - Development | No interruptions, focus on coding |
| 9:00-12:00 (3h) | User outreach & communication | Emails, messages, calls |
| 12:00-13:00 (1h) | Break/Lunch with family | Family time |
| 13:00-16:00 (3h) | Product refinement | Copy, UX, feedback analysis |
| 16:00-17:00 (1h) | Marketing | Content creation, social media |
| 17:00-18:00 (1h) | Admin & wrap-up | Support, monitoring, planning |
| 18:00+ | Family time | No work |

---

## Success Metrics

### Leading Indicators (Week 1-4)

| Metric | Target Week 4 | Measurement |
|--------|---------------|-------------|
| Test suite pass rate | 100% | pytest |
| Assessment completions | 10 | Database |
| Request creation rate | 30% of assessments | Database |
| Bidder signups | 5 | Database |
| Time to complete assessment | < 30 min | Analytics |
| Assessment completion rate | > 80% | Analytics |

### Lagging Indicators (Week 5-12)

| Metric | Target Week 8 | Target Week 12 | Measurement |
|--------|---------------|----------------|-------------|
| Paying clients (Full Assessment) | 5 | 10 | Database |
| Active bidders | 10 | 20 | Database |
| Published requests | 5 | 15 | Database |
| Monthly recurring revenue | $500 | $2,000 | Billing |
| Assessment-to-request conversion | 25% | 35% | Database |
| Request-to-bid conversion | 15% | 25% | Database |
| Bid-to-award conversion | 10% | 20% | Database |
| Net Promoter Score | 30 | 40 | Survey |

### Financial Targets

| Month | Assessments | Bidder Subs | Annual Subs | MRR |
|-------|-------------|-------------|-------------|-----|
| Month 1 | 5 | 3 | 0 | $117 |
| Month 2 | 10 | 5 | 0 | $245 |
| Month 3 | 20 | 10 | 2 | $790 |
| Month 4 | 30 | 15 | 4 | $1,447 |
| Month 5 | 50 | 20 | 6 | $2,138 |
| Month 6 | 80 | 30 | 10 | $3,390 |

*Assumptions: Full Assessment $49, Bidder Monthly $39, Bidder Annual $219 (amortized $18.25/mo)*

---

## Risk Management

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Test failures block deployment | Medium | High | Fix in Week 1, keep tests green |
| Database migration fails | Low | High | Test on staging first, backup before prod |
| Payment provider outage | Low | Medium | Feature flag, manual billing fallback |
| Marketplace bugs impact reputation | Medium | High | Extensive QA, gradual rollout |
| Performance issues under load | Low | Medium | Monitor, optimize, scale when needed |

### Go-to-Market Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Can't recruit bidders | Medium | High | Personal outreach, offer free months |
| Can't recruit clients | Medium | High | Free diagnostic lowers friction, LinkedIn outreach |
| Assessments too long/complex | Medium | Medium | A/B test, simplify based on data |
| Bids low quality | Medium | Medium | Manual verification, quality standards |
| Pricing too high/low | Low | Medium | A/B test pricing, adjust based on data |

### Founder Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Burnout | Medium | High | Work within 9hr limit, take weekends off |
| Family obligations conflict | Medium | Medium | Clear boundaries, communicate schedule |
| Feature creep | High | Medium | Stick to roadmap, say NO to new features |
| Losing focus | Medium | High | Review this document weekly, stay disciplined |

---

## Decision Log

### Locked Decisions (Do Not Reopen Without Strong Reason)

1. **Marketplace model** - No commission on awards. Revenue from assessments and bidder subscriptions.
2. **Target segment** - Logistics operators 10-300 staff. Not enterprises, not micro-businesses.
3. **Pricing** - Free diagnostic, $49 Full Assessment, $39-$219 bidder subscriptions.
4. **Tech stack** - FastAPI + SQLAlchemy + Jinja2 on Vercel. No React SPA in production.
5. **Assessment scope** - 63 questions, 7 pillars, 36 metrics. Do not expand.
6. **Non-goals** - No daily operations layer, no telematics, no native mobile app, no AI/ML.

### Pending Decisions (Make by Week 2)

1. **Paystack plan codes** - Create in Paystack dashboard and set in env vars
2. **Featured bidder pricing** - Determine if and how much to charge
3. **Referral program** - Define incentive structure
4. **Assessment time target** - Confirm < 30 minutes or adjust

### Open Questions (Research During Execution)

1. **Optimal assessment length** - A/B test different lengths
2. **Best outreach channels** - Test LinkedIn, email, cold call, referrals
3. **Bidder verification level** - How strict should verification be?
4. **Conversation expiry time** - 24 hours enough or too short?

---

## Definition of Done

### Phase 1 Complete When:
- [ ] All tests passing (119+)
- [ ] Marketplace enabled on production
- [ ] First end-to-end transaction completed
- [ ] No critical bugs in production for 48 hours
- [ ] Documentation updated

### Phase 2 Complete When:
- [ ] Assessment logistics-specific
- [ ] Results page redesigned
- [ ] Cost-of-inaction calculator working
- [ ] Mobile polished
- [ ] Performance < 3 seconds
- [ ] User satisfaction > 4/5

### Phase 3 Complete When:
- [ ] 5-10 active bidders
- [ ] 3-5 published requests
- [ ] First real bid → award → conversation
- [ ] Bidder landing page live
- [ ] Verification guide published

### Phase 4 Complete When:
- [ ] 10 paying clients
- [ ] 20 active bidders
- [ ] MRR > $2,000
- [ ] Funnel dashboard live
- [ ] 12-week retrospective completed
- [ ] Next 12-week plan defined

---

## Communication Plan

### Internal (Founder)

| Frequency | Activity | Format |
|----------|----------|--------|
| Daily | Review today's progress, plan tomorrow | Personal notes |
| Weekly | Review roadmap, update status | This document |
| Monthly | Financial review, goal check | Spreadsheet + this doc |
| Quarterly | Strategic review, pivot if needed | Document + decision log |

### External (Users)

| Frequency | Activity | Channel |
|----------|----------|---------|
| Weekly | Feature updates, bug fixes | In-app notification |
| Monthly | Product roadmap, what's coming | Email newsletter |
| Quarterly | State of the platform, metrics | Blog post |

---

## Tools & Infrastructure

### Development
- **Code**: Python, FastAPI, SQLAlchemy, Jinja2
- **Version control**: Git (GitHub)
- **Testing**: pytest
- **Migrations**: Alembic
- **Linting**: ruff

### Deployment
- **Hosting**: Vercel
- **Database**: Neon (PostgreSQL) or SQLite fallback
- **Storage**: S3 (for documents) or local fallback
- **Email**: Resend
- **Payments**: Paystack

### Monitoring
- **Health**: `/api/v1/health`
- **Error tracking**: (Add Sentry when budget allows)
- **Analytics**: Google Analytics (Week 11)
- **Status page**: Build when time allows

---

## Weekly Check-in Template

### Week: [X] of [12]

**Completed:**
- [ ] Task 1
- [ ] Task 2
- [ ] Task 3

**Blocked On:**
- Issue: [description]
- Mitigation: [plan]

**Metrics:**
- Assessments completed: [X]
- Requests created: [X]
- Bidders signed up: [X]
- MRR: $[X]

**Learnings:**
- [Insight 1]
- [Insight 2]

**Next Week Focus:**
- [ ] Priority 1
- [ ] Priority 2
- [ ] Priority 3

**Roadmap Changes:**
- [ ] None / [Description of change]

---

## Appendix

### Contact Lists to Build

**Logistics Operators (Target Clients)**
- LinkedIn: Search "COO Logistics", "Operations Director", "Logistics Manager"
- Filters: 10-300 employees, logistics industry
- Geography: Start with Kenya, expand regionally
- Outreach template: Personalized, focus on "what should we automate first?"

**Implementation Partners (Target Bidders)**
- LinkedIn: Search "Automation Consultant", "n8n developer", "Zapier expert"
- Filters: Open to work, logistics experience preferred
- Outreach template: Explain marketplace opportunity, free first month
- Groups: n8n community, automation communities, logistics tech groups

**Consulting Firms (Partners, Not Competitors)**
- Boutique logistics consulting firms
- Independent supply chain consultants
- Pitch: White-label assessments, referral fees

### Copy Templates

**Assessment Outreach (LinkedIn)**
```
Hi [Name],

I built a tool that answers "what should we automate first?" for logistics operations. It's a 25-minute assessment that gives you a professional report, costed constraints, and a 90-day plan.

Free to try: [link]

Would you be open to testing it and giving feedback?

Thanks,
[Your name]
```

**Bidder Outreach (LinkedIn)**
```
Hi [Name],

I'm launching a marketplace for logistics automation implementation. Operators post requests (with professional assessment data), and vetted partners bid on them.

First 10 verified bidders get free first month. $39/mo after that.

Interested? [link to apply]

Thanks,
[Your name]
```

**Assessment Reminder (Email)**
```
Subject: Finish your automation assessment

Hi [Name],

You started the Elipsis assessment but didn't finish. It takes about 25 minutes and will show you:

- Your Elipsis Index (automation readiness score)
- Top 3 constraints holding you back
- Cost of inaction
- Sample 90-day plan

Pick up where you left off: [link]

Questions? Just reply to this email.

Thanks,
Elipsis team
```

### Key File Locations

- **Assessment engine**: `readiness.py`, `constants.py`, `elipsis_questions.py`
- **Marketplace**: `elipsis_api/routers/marketplace_ui.py`, `services_marketplace.py`
- **Models**: `elipsis_api/models.py`
- **Tests**: `tests/test_api.py`, `tests/test_marketplace_lifecycle.py`
- **Config**: `elipsis_api/config.py`, `.env.example`
- **Deployment**: `vercel.json`, `DEPLOY.md`
- **Documentation**: `docs/` directory

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 3 Nov 2026 | Initial roadmap created |

---

**This document is the single source of truth. All changes to scope, timeline, or priorities must be reflected here.**
