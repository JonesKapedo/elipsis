#!/usr/bin/env bash
# Elipsis production migration helper
# Usage: ./scripts/migrate.sh
# Requires: ELIPSIS_DATABASE_URL (or DATABASE_URL) set to a Postgres URL

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DB_URL="${ELIPSIS_DATABASE_URL:-${DATABASE_URL:-}}"

if [[ -z "$DB_URL" ]]; then
  echo "ERROR: Set ELIPSIS_DATABASE_URL (or DATABASE_URL) to your Postgres connection string."
  echo "Example: export ELIPSIS_DATABASE_URL='postgresql://user:pass@host/db?sslmode=require'"
  exit 1
fi

echo "Running Alembic migrations against the configured database..."
alembic upgrade head

echo "Done. Application also runs create_all + seed on cold start."
