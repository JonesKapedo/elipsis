# Database migrations

Elipsis uses **Alembic** for schema changes. On every cold start the app also runs `Base.metadata.create_all` and seeds the question bank, so a fresh empty Postgres database becomes usable without a manual step. For production you should still run Alembic so the revision history stays accurate.

## Quick start

```bash
export ELIPSIS_DATABASE_URL='postgresql://user:pass@host/db?sslmode=require'
./scripts/migrate.sh
# or
alembic upgrade head
```

## Order

Migrations live under `alembic/versions/`. Run them in the order Alembic determines (`alembic upgrade head`). Do not apply the older hand-written SQL files under `migrations/` unless you are recovering a legacy database — the Alembic chain is the source of truth.

## Dev vs production

| Environment | Database | Notes |
| --- | --- | --- |
| Local | SQLite (default when `ELIPSIS_DATABASE_URL` is unset) | File beside the project. Fine for development only. |
| Production / Vercel | Postgres (Neon, Supabase, etc.) | **Required.** Set `ELIPSIS_DATABASE_URL`. Ephemeral SQLite under `/tmp` loses all data on cold starts. |

## After a new migration is added

1. Write the revision with `alembic revision --autogenerate -m "short description"` (review the generated file).
2. Test locally against a Postgres instance if possible.
3. Deploy; run `alembic upgrade head` against production (or rely on your CI/release step).
4. Confirm the app still seeds and serves assessments.

## Related files

- `alembic.ini` — Alembic config
- `alembic/env.py` — binds to the same engine as the app
- `scripts/migrate.sh` — one-liner wrapper
- `.env.example` — full list of environment variables
