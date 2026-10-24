# Deploy Elipsis on Vercel

The production web UI is the **FastAPI + Jinja2** app (`elipsis_api.main:app`).
Do not point Vercel at the Telegram bot or at the incomplete React SPA under `frontend/`.

## 1. Connect the repo

1. Import `JonesKapedo/elipsis` in the [Vercel dashboard](https://vercel.com/new).
2. Framework preset: **Other** (or leave auto-detect).
3. Root directory: repository root.
4. Build command: leave empty (Python serverless; no frontend build required for the SSR app).
5. Output directory: leave empty.

`vercel.json` routes all traffic to `elipsis_api/main.py` via `@vercel/python`.

## 2. Environment variables (required for production)

| Variable | Required | Notes |
| --- | --- | --- |
| `ELIPSIS_DATABASE_URL` | **Yes** | PostgreSQL URL, e.g. `postgresql://user:pass@host:5432/db?sslmode=require`. If missing or unreachable, the app starts in **degraded mode** (SQLite + visible config errors) instead of crashing. Fix this before trusting any data. |
| `ELIPSIS_SECRET_KEY` | **Yes** | Long random string used to sign session cookies. If absent in production, sessions use a per-process random secret (users are logged out on cold start) and the error is reported in health detail. |
| `ELIPSIS_ADMIN_EMAIL` | Recommended | First admin when the users table is empty. Default: `admin@elipsis.local` |
| `ELIPSIS_ADMIN_PASSWORD` | **Yes** | If absent in production, the default admin is not seeded; sign-up remains available. |
| `ELIPSIS_ENV` | **Yes** | Set to `production` (Vercel also sets `VERCEL`). |
| `PAYSTACK_SECRET_KEY` / `PAYSTACK_PUBLIC_KEY` | **Yes** | Real keys. The in-app dummy checkout is disabled in production. |
| `ELIPSIS_ALLOWED_ORIGINS` | Optional | Comma-separated extra origins for CORS/CSRF. Same-origin works without it. |
| `RESEND_API_KEY` | Recommended | Transactional email for verification, password reset, invites, marketplace events, receipts, and digests. Free tier: 3,000/month, 100/day. |
| `EMAIL_SERVICE` / `EMAIL_FROM_EMAIL` | Recommended | Set `EMAIL_SERVICE=resend` and a sender on a domain verified in Resend. `EMAIL_REPLY_TO` is optional. |
| `ELIPSIS_PUBLIC_URL` | Recommended | Public origin used in email links, e.g. `https://elipsis.ai`. |
| `ELIPSIS_MARKETPLACE_ENABLED` | Optional | Default `0` (coming-soon page; API returns 503). Set to `1` only when the marketplace is ready. |

`psycopg[binary]` is already in `requirements.txt`.

## 3. Database

Use any managed Postgres (Neon, Supabase, Vercel Postgres, RDS). Apply all migrations before deploy:

```bash
ELIPSIS_DATABASE_URL='postgresql://...' alembic upgrade head
```

The current head adds editable assumptions, evidence attachments, action-plan ownership/status/phone, campaign review tables, review dates, share-view analytics, the organisation audit trail, saved views, notification read state, digests, and signed webhook endpoints.

The app still seeds the question bank and first administrator on cold start. Future schema changes belong in `alembic/versions/`; do not edit production tables by hand.

### Scheduled digest

Send due daily/weekly digests from a cron job or Vercel Cron:

```bash
ELIPSIS_DATABASE_URL='postgresql://...' python -m elipsis_api.services_digest
```

Without `RESEND_API_KEY`, digest attempts are logged and reported as `email_not_configured`; they do not mark the digest as sent. SendGrid and SES remain supported through `EMAIL_SERVICE=sendgrid|ses`.

## 4. After deploy

1. Open `https://<your-deployment>/login`
2. Sign in with the admin credentials you set
3. Start an assessment from **New assessment**
4. API docs: `/docs`

## 5. Local parity

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set admin password
python run_api.py      # http://127.0.0.1:8001
```

## 6. Production env checklist

Set these in **Vercel → Project → Settings → Environment Variables → Production**,
then redeploy. Preview deployments need their own values if you want email,
billing, or handoff to work there.

### Core

- [ ] `ELIPSIS_ENV=production`
- [ ] `ELIPSIS_DATABASE_URL` — managed Postgres with `sslmode=require`
- [ ] `ELIPSIS_SECRET_KEY` — long random value, unique to production
- [ ] `ELIPSIS_ADMIN_EMAIL` and `ELIPSIS_ADMIN_PASSWORD` — first admin only
- [ ] `ELIPSIS_PUBLIC_URL` — the real public origin, no trailing slash

### Transactional email (Resend)

- [ ] `EMAIL_SERVICE=resend`
- [ ] `RESEND_API_KEY`
- [ ] `EMAIL_FROM_EMAIL` — address on a domain verified in Resend
- [ ] `EMAIL_FROM_NAME=Elipsis`
- [ ] `EMAIL_REPLY_TO` — monitored support address

Resend setup:

1. Create an API key in Resend and add the sending domain.
2. Add the SPF and DKIM DNS records Resend shows, then wait for **Verified**.
3. Send a test to Gmail and Outlook before launch and confirm SPF/DKIM pass.
4. `onboarding@resend.dev` only delivers to the Resend account owner; it is not
   a production sender.

### Storage, billing, handoff

- [ ] `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_BUCKET`, `AWS_REGION`
  for document uploads; serverless filesystems are ephemeral
- [ ] `PAYSTACK_SECRET_KEY` and `PAYSTACK_PUBLIC_KEY` — live keys
- [ ] `PAYSTACK_PLAN_PREMIUM_MONTHLY`, `PAYSTACK_PLAN_PREMIUM_ANNUAL`
- [ ] `PAYSTACK_PLAN_BIDDER_MONTHLY`, `PAYSTACK_PLAN_BIDDER_SIX_MONTHS`,
  `PAYSTACK_PLAN_BIDDER_YEARLY`
- [ ] `ELIPSIS_HANDOFF_SECRET` — long random signing secret
- [ ] `ELIPSIS_HANDOFF_FETCH_SECRET` — shared with the partner
- [ ] `ELIPSIS_PARTNER_HANDOFF_URL` — partner endpoint
- [ ] `ELIPSIS_ALLOWED_ORIGINS` only if an extra trusted origin is required

Paystack dashboard webhook URL: `https://<production-domain>/paystack/webhook`.
Enable `charge.success`, `subscription.create`, `subscription.not_renew`,
`subscription.disable`, and `invoice.payment_failed`. Prices are charged in USD;
create the Paystack plans in USD and paste the plan codes above.

### Feature flags

Keep the marketplace closed until listings, partners, and terms are ready:

- [ ] `ELIPSIS_MARKETPLACE_ENABLED=0` for launch, then `1` after sign-off
- [ ] `ELIPSIS_MESSAGING_ENABLED=1`
- [ ] `ELIPSIS_BILLING_ENABLED=1`
- [ ] `ELIPSIS_HANDOFF_ENABLED=1` only when the partner endpoint is live
- [ ] `ELIPSIS_VERIFICATION_ENABLED=1`

## 7. Vercel smoke test plan

Run against the production URL after the deploy is **Ready** and migrations are
at head (`alembic upgrade head`).

### Platform

- [ ] `GET /api/v1/health/detail` shows no `configuration_errors` and uses Postgres
- [ ] `/login` works for the seeded admin; sign out and sign back in
- [ ] Password reset email arrives and the link opens the reset form
- [ ] Sign up a new account, verify the email, and confirm the welcome email
- [ ] Invite a teammate; both the invite and workspace-added emails arrive
- [ ] Upload a document and reopen it from a second session

### Marketplace

- [ ] Submit a request as a client; approval/rejection emails arrive
- [ ] Approve a bidder; bidder verification emails arrive
- [ ] Submit and approve a bid; client notification email arrives
- [ ] Award the request; both parties receive email and the conversation opens
- [ ] Send messages both ways; email notifications arrive; opt-out is honored
- [ ] Use a switch top-up and confirm old/new bidder emails
- [ ] Trigger a handoff and confirm the partner accepts the signed token
- [ ] Non-admin users receive `404` on admin routes; admin actions are audited

### Billing

- [ ] Run one low-value live Paystack charge and confirm the receipt email
- [ ] Confirm the entitlement is applied and the payment is idempotent on webhook retry
- [ ] Cancel a test subscription and confirm the cancellation email
- [ ] Simulate a failed invoice and confirm the grace-period email

### Email deliverability

- [ ] Send to Gmail, Outlook, and a company domain; check spam placement
- [ ] Confirm links point at `ELIPSIS_PUBLIC_URL`, not localhost or `.vercel.app`
- [ ] Check Vercel function logs for Resend errors without exposing secrets

## Notes

- **Static assets** are served from `/static/` (repo-root `static/`); the premium layer is `premium.css`.
- **Telegram bot** is separate (`requirements-bot.txt`, `python -m telegram_bot.bot`). It is not part of the Vercel deployment.
- **React frontend** under `frontend/` is experimental; the board-ready product path is the server-rendered templates. `frontend/node_modules` and `frontend/dist` are no longer tracked.
- **Security**: signed, database-backed sessions with expiry/revocation; same-origin CSRF checks on unsafe methods; rate-limited login, signup, and password reset; per-organisation authorisation on assessment and marketplace APIs.
- **Degraded mode**: check `GET /api/v1/health/detail` for `configuration_errors`. A degraded deployment is for diagnosis only, not for storing real client data.
