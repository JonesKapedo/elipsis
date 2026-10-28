# Elipsis Release Checklist

Use this before every production deploy. Tick each item; do not deploy with an
unchecked **blocking** item.

## 1. Code and tests

- [ ] Working tree reviewed (`git status`, `git diff`) and contains only intended changes.
- [ ] No secrets, tokens, `.env` files, customer exports, or database dumps in the diff.
- [ ] Full suite is green: `.venv/bin/python -m pytest -q`.
- [ ] Lint is clean: `.venv/bin/python -m ruff check elipsis_api tests scripts`.
- [ ] Migration heads are linear: `.venv/bin/python -m alembic heads` shows one head.
- [ ] New migrations include a working `downgrade()` or a documented reason it is irreversible.

## 2. Configuration

- [ ] `ELIPSIS_ENV=production` on the target.
- [ ] `ELIPSIS_DATABASE_URL` points at the intended Postgres database (not a local SQLite file).
- [ ] `ELIPSIS_SECRET_KEY` is long, random, and unchanged for the environment.
- [ ] `ELIPSIS_ADMIN_EMAIL` is set for bootstrap access.
- [ ] Supabase, email, and Paystack keys match the environment (test vs live).
- [ ] `ELIPSIS_MARKETPLACE_ENABLED` matches the launch decision.
- [ ] `ELIPSIS_BASE_URL` and cookie/domain settings match the public hostname.

## 3. Database

- [ ] Backup or PITR checkpoint exists before applying migrations.
- [ ] Migrations applied: `.venv/bin/python -m alembic upgrade head`.
- [ ] Seed state verified: `GET /api/v1/health` returns `"status": "ok"`.
- [ ] Role consolidation migration `a9b8c7d6e5f4` verified: platform admins have
      `is_admin = true`; no authorization depends on the legacy `users.role` column.
- [ ] No long-running locks or table rewrites on large tables.

## 4. Security and access

- [ ] Admin routes reject non-admin users (403) and anonymous users (redirect/401).
- [ ] Assessment results are scoped to the owning organization.
- [ ] Marketplace requests and conversations are private until approved.
- [ ] Session cookies are `HttpOnly`, `Secure`, and `SameSite=Lax` in production.
- [ ] Rate limits apply to login, registration, password reset, and public writes.
- [ ] No debug tracebacks or stack traces exposed to users.

## 5. Billing and email

- [ ] Paystack webhook signature verification is enabled.
- [ ] Recurring bidder plans and subscription status transitions are tested in test mode.
- [ ] Payment failure, cancellation, and refund states are visible to admins.
- [ ] Transactional email renders and links use the production base URL.
- [ ] Email suppression/bounce handling is configured.

## 6. Product smoke paths

- [ ] Register → login → create organization works.
- [ ] Start assessment → answer questions → submit → report renders.
- [ ] Report PDF/export downloads and contains the organization name and date.
- [ ] Daily operations page loads with the correct department and date.
- [ ] Marketplace request creation and bidder visibility rules hold.
- [ ] Admin dashboard loads and shows live counts.

## 7. Observability

- [ ] `/api/v1/health` monitored externally with an alert on `degraded`.
- [ ] `/api/v1/health/detail` checked by operators after deploy.
- [ ] Error tracking (Sentry or equivalent) is receiving events.
- [ ] Backups are scheduled and restore has been tested in the last quarter.

## 8. Deploy and verify

- [ ] Deploy completed and the new version is serving (check build/commit hash if available).
- [ ] Run the smoke test against the deployed host:

  ```bash
  ELIPSIS_SMOKE_BASE_URL=https://your-host \
    .venv/bin/python scripts/smoke.py
  ```

- [ ] Optional authenticated smoke: set `ELIPSIS_SMOKE_COOKIE` from a test account
      and re-run; `/dashboard` and `/marketplace` must return 200.
- [ ] Watch error rate, latency, and database connections for 15 minutes.
- [ ] Record the deploy in the release log, including migration IDs and rollback plan.

## Rollback

- [ ] Previous application version is deployable.
- [ ] Database rollback decision is explicit: schema downgrade, forward fix, or restore.
- [ ] Feature flags can disable new surfaces without a redeploy.
