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
Experimental React SPA under `frontend/` is not the deploy target.

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

### Deploy to Vercel

See **DEPLOY.md**. Production UI is the FastAPI + Jinja2 app. Do not point Vercel at
the Telegram bot or the experimental React SPA under `frontend/`.

**Storage:** set `ELIPSIS_DATABASE_URL` to a managed PostgreSQL URL. Without it the
app uses ephemeral SQLite under `/tmp` and data is lost on cold starts.

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

Signed-in users get a **vertical sidebar** (Command · Intelligence · Account) with a
mobile drawer. The old diamond dropdown is retired. The dashboard surfaces the
measurement model for operators and investors: KPI strip, framework summary, latest
result with pillar bars, pillar portfolio, maturity spread, and assessment table.
