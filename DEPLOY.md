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
| `ELIPSIS_DATABASE_URL` | **Yes** | PostgreSQL URL, e.g. `postgresql://user:pass@host:5432/db?sslmode=require`. Without this, SQLite under `/tmp` is used and **all data is lost on every cold start**. |
| `ELIPSIS_ADMIN_EMAIL` | Recommended | First admin when the users table is empty. Default: `admin@elipsis.local` |
| `ELIPSIS_ADMIN_PASSWORD` | **Yes before public** | Change from the default. |
| `ELIPSIS_ENV` | Optional | Set to `production` |

`psycopg[binary]` is already in `requirements.txt`.

## 3. Database

Use any managed Postgres (Neon, Supabase, Vercel Postgres, RDS). Create an empty database; the app runs `create_all` and seeds the question bank on cold start.

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
- **React frontend** under `frontend/` is experimental; the board-ready product path is the server-rendered templates.
