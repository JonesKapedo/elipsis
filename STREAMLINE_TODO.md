# Elipsis Streamline TODO

**Goal:** Make Elipsis a complete professional workspace.

**Production path:** FastAPI + SQLAlchemy + Jinja2 (Vercel).  
**Experimental:** React SPA under `frontend/` — not deployed.

---

## Status (2026-10-28)

### 1. Products / services — DONE
- Pricing page + comparison table (“What you get”)
- Implementation story (Great Turbinez + Marketplace, no commission)
- README products table

### 2. Dual frontend — DONE
- Jinja locked as production
- `frontend/README.md` + README section

### 3. Marketplace UI — READY FOR LIVE QA
- Full Jinja flows: list, detail, new request, apply, partner desk, companies, messaging hooks
- Feature flag `ELIPSIS_MARKETPLACE_ENABLED`
- Empty state + conversion CTAs polished
- **Operator action:** set `ELIPSIS_MARKETPLACE_ENABLED=1` on Vercel and run one client → admin → bidder → message path

### 4. Operability — DONE (code)
- Password reset + email verification routes and templates
- Login success messages (`?reset=1`, `?verify=invalid`)
- Assessment → results → PDF/Excel/JSON/share already wired
- Mobile: hero-actions wrap; sidebar drawer present

### 5. Public site + workspace polish — DONE
- Nav groups: **Diagnose · Operate · Implement · Account**
- Footer links map to existing pages
- Marketplace empty state improved

### 6. Database / env — DONE
- `scripts/migrate.sh`, `MIGRATIONS.md`, comprehensive `.env.example`

---

## Live QA checklist (operator)

1. Set `ELIPSIS_MARKETPLACE_ENABLED=1` (and email/S3/Paystack as needed).
2. Client: `/start` → complete assessment → `/marketplace/requests/new` → submit.
3. Admin: `/admin/requests` → verify → publish.
4. Bidder: `/marketplace/apply` → subscribe if required → open request → bid → message.
5. Client: view bids → message → award/close.
6. Mobile: open results page → confirm export buttons wrap and are tappable.

When that path succeeds on production, the product is whole.
