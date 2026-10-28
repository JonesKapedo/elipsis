# Elipsis

**Turning operational flow into business power.**

Elipsis is a business transformation intelligence platform that measures how ready an
organisation is to adopt automation — and what that readiness is worth in money.

> *Elipsis* is the three-dot mark for "and so on" — the sequence that shows the
> pattern continuing. This platform looks for exactly that: the pattern of friction
> running through an organisation, and what it will cost you next year.

---

## Status

Production path: **FastAPI + SQLAlchemy + Jinja2** (Vercel). Pure scoring engine in
`readiness.py` + declarative metrics in `constants.py`. Vertical sidebar workspace UI,
investor-facing dashboard that surfaces the seven pillars, 36 metrics, maturity bands,
and three-phase roadmap. Telegram bot remains a separate acquisition channel.

**Streamline work in progress** — see [`STREAMLINE_TODO.md`](STREAMLINE_TODO.md).

## Documentation

| Document | Purpose |
| --- | --- |
| [`docs/PLATFORM_MASTER_PLAN.md`](docs/PLATFORM_MASTER_PLAN.md) | Market, target audience, competitive position, gaps, recommendations, and feature sequence. Start here. |
| [`docs/DAILY_OPERATIONS_TRANSFORMATION.md`](docs/DAILY_OPERATIONS_TRANSFORMATION.md) | Technical specification for the daily operating layer. |
| [`docs/PLATFORM_UPGRADE_IMPLEMENTATION_GUIDE.md`](docs/PLATFORM_UPGRADE_IMPLEMENTATION_GUIDE.md) | Marketplace, entitlement, and handoff specification. |
| [`docs/COMPETITIVE_EDGE.md`](docs/COMPETITIVE_EDGE.md) | Original market read. Superseded for positioning by the master plan. |
| [`docs/SERVICE_DELIVERY_STANDARD.md`](docs/SERVICE_DELIVERY_STANDARD.md) | Published service commitments and SLAs. |
| [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md) | Pre-deploy, migration, security, and smoke-test checklist. |

## Frontend decision (locked)

| Layer | Technology | Deployed? |
| --- | --- | --- |
| **Production UI** | FastAPI + Jinja2 templates + `static/` | **Yes** (Vercel) |
| **Experimental SPA** | React + Vite under `frontend/` | **No** |

The React SPA is kept for reference only. It is **not** the deploy target and is not linked from production routes. See [`frontend/README.md`](frontend/README.md).

Do not point Vercel at the Telegram bot or at `frontend/`.

## Naming

| Layer | Name |
| --- | --- |
| Company / platform | **Elipsis** |
| Framework | Elipsis Transformation Framework |
| Flagship metric | Elipsis Index (short: *the Elipsis Score*) |
| Confidence metric | Elipsis Confidence Index |
| Maturity model | Elipsis Maturity Scale |
| Assessment instrument | ORG-001 · Elipsis Organisation Readiness Assessment |
| Assessment output | Elipsis Transformation Assessment |

All public names live in **`constants.py`** — one place to rename anything.

The neutral database/API field `readiness_index` is used deliberately so a rebrand
never requires a schema change.

---

## The seven intelligence pillars

| Code | Pillar | Weight |
| --- | --- | --- |
| OEI | Operational Efficiency Intelligence | 20% |
| ARI | Automation Readiness Intelligence | 25% |
| DMI | Digital Maturity Intelligence | 15% |
| DII | Data Intelligence & Analytics | 15% |
| AIR | AI Readiness Intelligence | 10% |
| TII | Technology & Integration Infrastructure | 5% |
| SSI | Strategic Scalability Intelligence | 10% |

Each pillar carries **three subdomains** (21 in total) and **nine questions** (63
overall), and produces its own set of **executive metrics**.

### Executive metrics

Every assessment returns **36 derived metrics**, each tagged `score` (higher is
better) or `risk` (higher is worse, built with `invert()`):

- **OEI** — Process Efficiency Score · Workflow Friction Index · Approval Complexity
  Score · Operational Waste Index · Human Dependency Ratio
- **ARI** — Repetition Index · Automation Compatibility Score · Manual Burden Score ·
  Automation Opportunity Index · Automation Urgency Index · Quick-Win Potential ·
  Estimated Automation ROI
- **DMI** — Digital Maturity Score · Software Utilization Score · Spreadsheet
  Dependency Index · Paper Reliance Index · Digital Transformation Readiness
- **DII** — Data Quality Score · Analytics Maturity Score · Reporting Effectiveness
  Score · Decision Intelligence Score · Data Trust Index
- **AIR** — AI Readiness Score · Generative AI Opportunity Index · Predictive AI
  Opportunity Index · Knowledge Automation Score · AI Value Potential
- **TII** — Technology Readiness Score · Integration Complexity Index · Security
  Readiness Score · Automation Deployment Readiness
- **SSI** — Scalability Score · Growth Constraint Index · Key Person Risk Score ·
  Organizational Resilience Score · Future Readiness Index

Metric formulas live in `constants.METRIC_FORMULAS` as short declarative strings and
are evaluated by a **restricted AST interpreter** in `readiness.py`. Only names,
numbers, arithmetic and whitelisted helpers are permitted, so a typo fails loudly at
import time rather than quietly producing a wrong number.

### Implementation roadmap

Recommendations are grouped into three phases:

| Phase | Horizon | Focus |
| --- | --- | --- |
| 1 · Quick Wins | 0–90 days | Low-complexity automation on repetitive work |
| 2 · Process Automation | 3–12 months | Structural change: approvals, integrations, controls |
| 3 · AI Enablement | 12–24 months | Predictive and generative AI on a clean base |

---

## Products & pricing (summary)

| Offer | Price | What you get |
| --- | --- | --- |
| Free diagnostic | $0 | 63-question diagnostic, Elipsis Index, top constraints, sample plan |
| Full Assessment | $49 once | Full 36-metric report, costed constraints, board pack, 3 partner intros |
| Operator subscription | $29 / mo (or $380 / yr) | Unlimited assessments, exports, team collaboration, switches |
| Marketplace | Partner plans from $39 / mo | Clients publish briefs; verified implementers bid (no commission taken by Elipsis) |

See `/pricing` on the live site for the full commercial story.

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt          # FastAPI platform (what Vercel deploys)
pip install -r requirements-bot.txt      # Telegram bot (aiogram)
cp .env.example .env
```

### Run the web platform

```bash
python run_api.py            # -> http://127.0.0.1:8001
python run_api.py --reload   # auto-reload during development
```

Open **<http://127.0.0.1:8001>** and sign in.

The first administrator is created from `ELIPSIS_ADMIN_EMAIL` and
`ELIPSIS_ADMIN_PASSWORD` (defaults: `admin@elipsis.local` / `elipsis`, with a
startup warning while the default password is in use). **Set both before
exposing an instance** — the sign-in page deliberately does not display them.

Interactive API docs: **<http://127.0.0.1:8001/docs>**

Change the port with `ELIPSIS_PORT=8080 python run_api.py`.

> The FastAPI stack lives in **`.venv`**. The Telegram bot needs `aiogram`, which is
> only in `requirements-bot.txt`.

### Run the Telegram bot

```bash
python -m telegram_bot.bot
```

### Database migrations

```bash
export ELIPSIS_DATABASE_URL='postgresql://…'
./scripts/migrate.sh          # or: alembic upgrade head
```

Without a Postgres URL the app falls back to ephemeral SQLite under `/tmp` (**dev only** — data is lost on cold starts).

### Deploy to Vercel

See **DEPLOY.md**. Production UI is the FastAPI + Jinja2 app.

---

## Architecture

The platform is **FastAPI + SQLAlchemy + Jinja2**, served by Uvicorn. Business logic
lives in `readiness.py` (pure functions, no web dependency) so it is reusable from
the bot, the API and future workers.

```text
constants.py           # ALL brand names, pillars, subdomains, metric formulas
readiness.py           # scoring engine: index, 36 metrics, pain points, roadmap
elipsis_questions.py   # ORG-001 questionnaire (63 questions, 7 pillars)

run_api.py             # FastAPI launcher          -> http://127.0.0.1:8001
elipsis_api/
  main.py              # app factory, static mount, startup seeding
  config.py            # env-driven settings (SQLite / PostgreSQL)
  database.py          # SQLAlchemy engine, session, Base
  models.py            # organizations, departments, questionnaires, questions,
                       # assessments, answers, pillar/subdomain/metric scores,
                       # pain points, recommendations, financial model
  schemas.py           # Pydantic request/response models
  services.py          # persistence, segments, dashboard, live scoring
  security.py          # PBKDF2 password hashing, session tokens
  deps.py              # Jinja templates, current-user dependency
  routers/api.py       # JSON API  (/api/v1)
  routers/pages.py     # HTML pages (server-rendered)
  templates/           # base, login, dashboard, start, step, results,
                       # report, assessments, methodology, …
static/                # design system + app shell (vertical sidebar)

telegram_bot/
  bot.py                 # bot entry point (aiogram)
  handlers.py            # conversation flow
  scoring.py             # preliminary scoring + savings estimate
```

## Workspace UI

Signed-in users get a **vertical sidebar** (Workspace · Commercial · Account) with a
mobile drawer. The dashboard surfaces the measurement model for operators and
investors: KPI strip, framework summary, latest result with pillar bars, pillar
portfolio, maturity spread, and assessment table.
