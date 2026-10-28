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
- [ ] Workspace navigation labels match the public product story (Diagnose → Operate → Implement)
- [ ] Light pricing polish: “What you get” comparison if needed
- [ ] Remove or hide any half-finished commercial claims from public pages

**Owner focus:** Keep the commercial story to three clear offers + marketplace.

---

## 2. Clean up dual frontend paths (Jinja vs React)

- [x] Production deploy target is FastAPI + Jinja2 (`DEPLOY.md`, `vercel.json`, `main.py`)
- [x] React SPA lives under `frontend/`
- [x] Explicit “Frontend decision” section added to README
- [x] `frontend/README.md` added stating experimental / not deployed
- [x] No production route points at the React SPA

**Decision (locked):** Jinja2 is the single production UI. React may be used later for highly interactive pieces only after the Jinja flows are finished.

---

## 3. Finish marketplace UI flows

- [x] Backend marketplace, bidder, admin, organizations, files, messaging, analytics routers exist
- [x] Jinja marketplace templates exist (`marketplace*.html`)
- [ ] End-to-end client flow: create request → upload docs → admin verify/publish → receive bids → message → close
- [ ] End-to-end bidder flow: shop profile → portfolio → bid → message
- [ ] Admin verification panel fully wired and usable
- [ ] Marketplace locked state for free users is clear and conversion-oriented
- [ ] Partner desk (`/marketplace/partner`) is complete for bidder user_type

---

## 4. Fix operability issues (auth, assessment → results, exports, mobile)

- [x] Auth (login / signup / logout / session cookie) exists
- [x] Assessment start → step → results path exists
- [x] PDF / board-pack report routes exist
- [ ] Full auth resilience (email confirmation, password reset, clear error messages)
- [ ] Assessment → results → export → share is frictionless on mobile
- [ ] Mobile drawer + responsive sidebar behaviour verified
- [ ] 404 / error pages consistent

---

## 5. Add missing pages, polish workspace sidebar, improve public site

- [x] Public nav: Method · Pricing · Partners · Sample · Help · Sign in · CTA
- [x] Workspace sidebar: Company home · Overview · Assessments · Action plan · Operations · Marketplace · Settings · Admin
- [ ] Ensure every public footer link resolves to a real page
- [ ] Polish empty states and “next action” CTAs inside the workspace
- [ ] Landing page product story matches pricing page exactly

---

## 6. Database-related code, migrations helpers, etc.

- [x] Alembic migrations present
- [x] `create_all` + seed on startup
- [ ] Document exact migration order for production (Neon / Postgres)
- [ ] Add `scripts/migrate.sh` or documented one-liner
- [ ] Ensure `.env.example` lists every required production variable
- [ ] Confirm SQLite fallback is clearly marked “dev only”

---

## Definition of “whole”

- A new visitor understands the three offers in under 10 seconds.
- A signed-in operator can go from “New assessment” → results → board pack → marketplace request without leaving the Jinja app.
- Marketplace (client + bidder + admin) works end-to-end.
- There is only one production frontend path.
- Migrations and env are documented so a cold deploy is predictable.

Last updated: 2026-10-28
