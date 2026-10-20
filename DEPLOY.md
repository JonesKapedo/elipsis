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
| `SENDGRID_API_KEY` / `SENDGRID_FROM_EMAIL` | Recommended | Password reset and email verification. Without email transport, reset links are not delivered. |
| `ELIPSIS_MARKETPLACE_ENABLED` | Optional | Default `0` (coming-soon page; API returns 503). Set to `1` only when the marketplace is ready. |

`psycopg[binary]` is already in `requirements.txt`.

## 3. Database

Use any managed Postgres (Neon, Supabase, Vercel Postgres, RDS). Apply all migrations before deploy:

```bash
ELIPSIS_DATABASE_URL='postgresql://...' alembic upgrade head
```

The current head adds editable assumptions, evidence attachments, action-plan ownership/status, campaign review tables, review dates, share-view analytics, and the organisation audit trail.

The app still seeds the question bank and first administrator on cold start. Future schema changes belong in `alembic/versions/`; do not edit production tables by hand.

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

## Notes

- **Static CSS** is served from `/static/style.css` (repo-root `static/`).
- **Telegram bot** is separate (`requirements-bot.txt`, `python -m telegram_bot.bot`). It is not part of the Vercel deployment.
- **React frontend** under `frontend/` is experimental; the board-ready product path is the server-rendered templates. `frontend/node_modules` and `frontend/dist` are no longer tracked.
- **Security**: signed, database-backed sessions with expiry/revocation; same-origin CSRF checks on unsafe methods; rate-limited login, signup, and password reset; per-organisation authorisation on assessment and marketplace APIs.
- **Degraded mode**: check `GET /api/v1/health/detail` for `configuration_errors`. A degraded deployment is for diagnosis only, not for storing real client data.
