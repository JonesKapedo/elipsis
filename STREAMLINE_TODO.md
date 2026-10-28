# Elipsis Streamline TODO

**Goal:** Make Elipsis a complete professional workspace — clear products/services, single coherent website, fully operable flows.

**Production path (confirmed):** FastAPI + SQLAlchemy + Jinja2 (Vercel).  
**Experimental:** React SPA under `frontend/` — not the deploy target.

---

## Status legend
- [ ] Not started
- [~] In progress
- [x] Done

---

## 1. Streamline products / services (pricing, navigation, product structure)

- [x] Pricing page exists and is clear ($0 diagnostic · $49 Full Assessment · $29/mo Operator)
- [x] Implementation story is documented (Great Turbinez direct + Marketplace, no commission)
- [x] Bidder/partner plans defined in `premium.py`
- [x] Public product menu consistent (Method · Pricing · Partners · Sample · Help)
- [x] README products & pricing summary table added
- [ ] Workspace navigation labels match the public product story (Diagnose → Operate → Implement) — optional polish
- [ ] Light pricing polish: “What you get” comparison if needed

**Owner focus:** Keep the commercial story to three clear offers + marketplace.

---

## 2. Clean up dual frontend paths (Jinja vs React)

- [x] Production deploy target is FastAPI + Jinja2 (`DEPLOY.md`, `vercel.json`, `main.py`)
- [x] React SPA lives under `frontend/`
- [x] Explicit “Frontend decision” section added to README
- [x] `frontend/README.md` added stating experimental / not deployed
- [x] No production route points at the React SPA

**Decision (locked):** Jinja2 is the single production UI.

---

## 3. Finish marketplace UI flows

- [x] Backend marketplace, bidder, admin, organizations, files, messaging, analytics routers exist
- [x] Jinja marketplace templates + `marketplace_ui.py` routes exist (list, detail, new request, apply, partner desk, companies, messaging hooks)
- [x] Feature flags: `ELIPSIS_MARKETPLACE_ENABLED`, messaging, billing, handoff, verification
- [x] Coming-soon page when marketplace flag is off
- [~] End-to-end client / bidder / admin flows — code is present; enable flag and run live QA on production data
- [ ] Marketplace locked state for free users is conversion-oriented (copy polish)

---

## 4. Fix operability issues (auth, assessment → results, exports, mobile)

- [x] Auth (login / signup / logout / session cookie) exists
- [x] Assessment start → step → results path exists
- [x] PDF / board-pack report routes exist
- [x] Security middleware, CSRF guard, rate-limit module present
- [ ] Full auth resilience (email confirmation messaging, password reset UX)
- [ ] Assessment → results → export → share frictionless on mobile (manual QA)
- [ ] Mobile drawer + responsive sidebar behaviour verified (manual QA)

---

## 5. Add missing pages, polish workspace sidebar, improve public site

- [x] Public nav: Method · Pricing · Partners · Sample · Help · Sign in · CTA
- [x] Workspace sidebar: Company home · Overview · Assessments · Action plan · Operations · Marketplace · Settings · Admin
- [x] Footer trust + company links present
- [ ] Ensure every public footer link resolves to a real page (spot-check)
- [ ] Polish empty states and “next action” CTAs inside the workspace
- [ ] Landing page product story matches pricing page exactly (spot-check)

---

## 6. Database-related code, migrations helpers, etc.

- [x] Alembic migrations present
- [x] `create_all` + seed on startup
- [x] `scripts/migrate.sh` added
- [x] `MIGRATIONS.md` added
- [x] `.env.example` is comprehensive (database, Supabase, Paystack, email, marketplace flags, handoff)
- [x] SQLite fallback documented as dev-only in README and MIGRATIONS.md

---

## Definition of “whole”

- A new visitor understands the three offers in under 10 seconds.
- A signed-in operator can go from “New assessment” → results → board pack → marketplace request without leaving the Jinja app.
- Marketplace (client + bidder + admin) works end-to-end when the feature flag is on.
- There is only one production frontend path.
- Migrations and env are documented so a cold deploy is predictable.

**Progress this session:** dual-frontend locked, STREAMLINE_TODO + frontend README + migrate helper + MIGRATIONS.md + README products table shipped.

Last updated: 2026-10-28
