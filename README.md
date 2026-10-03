# Elipsis

**Turning operational flow into business power.**

Elipsis is a business transformation intelligence platform that measures how ready an
organisation is to adopt automation — and what that readiness is worth in money.

> *Elipsis* is the three-dot mark for "and so on" — the sequence that shows the
> pattern continuing. This platform looks for exactly that: the pattern of friction
> running through an organisation, and what it will cost you next year.

---

## Status

Early implementation. A **FastAPI + SQLAlchemy + Jinja2** web platform backed by a pure
scoring engine, plus a **Telegram bot** used as a client-acquisition channel.

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

Open **<http://127.0.0.1:8001>** and sign in with
**<admin@elipsis.local> / elipsis**.

Interactive API docs: **<http://127.0.0.1:8001/docs>**

Change the port with `ELIPSIS_PORT=8080 python run_api.py`.

> The FastAPI stack lives in **`.venv`**. The Telegram bot needs `aiogram`, which is
> only in `requirements-bot.txt`.

### Run the Telegram bot

```bash
python -m telegram_bot.bot
```

### Deploy to Vercel

The web platform is declared explicitly, because the repository root also
contains the Telegram bot and Vercel would otherwise try to deploy that:

```toml
# pyproject.toml
[tool.vercel]
entrypoint = "elipsis_api.main:app"
```

The bot lives in the **`telegram_bot/`** package, not the repository root. Vercel
scans the root for `app.py / index.py / server.py / main.py / wsgi.py / asgi.py`
and deploys whatever it finds there, so keeping aiogram code out of the root
means the only thing it can build is the web platform.

Vercel installs the root **`requirements.txt`**, which is why that file holds
the FastAPI stack rather than the bot's `aiogram` (those live in
`requirements-bot.txt`).

**Storage — read this before going live.** Vercel mounts the deployment bundle
read-only, so the local `turbinez.db` SQLite file cannot be used there. Without a
database URL the app falls back to SQLite under `/tmp`, which is **ephemeral**:
every assessment is lost when the instance recycles, and each cold start reseeds
an empty database. For a real deployment set a managed PostgreSQL URL in the
Vercel project's environment variables:

| Variable | Example |
| --- | --- |
| `ELIPSIS_DATABASE_URL` | `postgresql://user:pass@host:5432/db?sslmode=require` |
| `ELIPSIS_TELEGRAM_TOKEN` | *(only needed for the bot)* |
| `ELIPSIS_SECRET_KEY` | *(only needed for the bot)* |

`psycopg[binary]` is already listed in `requirements.txt`, so a `postgres://` URL
is honoured as-is. `ELIPSIS_SECRET_KEY` is only read by the Telegram bot; the web
platform's sessions use a random token in a cookie.

Sign in at **`/login`** with **<admin@elipsis.local> / elipsis** (seeded on first
request), or create your own user row in the `users` table.

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
                       # report, assessments, 404
static/style.css       # dark design system + white print stylesheet

telegram_bot/
  bot.py                 # bot entry point (aiogram) — python -m telegram_bot.bot
  handlers.py            # bot: conversation flow
  scoring.py             # bot: preliminary scoring + savings estimate (KES)
```

> The Python package was renamed `turbinez_api` -> `elipsis_api` with the rebrand. The
> SQLite file is still `turbinez.db` for the same reason: renaming a local file is
> churn with no benefit.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Service status |
| `GET` | `/api/v1/questionnaire` | ORG-001 question bank (63 questions) |
| `GET` | `/api/v1/assessments` | List assessments |
| `POST` | `/api/v1/assessments` | Create an assessment |
| `GET` | `/api/v1/assessments/{id}` | Full computed result as JSON |
| `POST` | `/api/v1/assessments/{id}/submit` | Submit answers, compute result |

The result payload includes `metrics` (36 values), `metric_rows` (labelled, with a
one-line reading each), `metrics_by_pillar`, and `roadmap` (the three phases).

## Environment

| Variable | Purpose |
| --- | --- |
| `ELIPSIS_ENV` | `development` / `production` |
| `ELIPSIS_TELEGRAM_TOKEN` | Bot token from @BotFather |
| `ELIPSIS_DATABASE_URL` | PostgreSQL DSN (SQLite when absent) |
| `ELIPSIS_REDIS_URL` | Redis (for FSM storage/caching) |
| `ELIPSIS_SECRET_KEY` | Application secret |

> **Compatibility:** the pre-rebrand `TURBINEZ_*` names are still read as a fallback,
> so an existing `.env` keeps working.

> **Security:** rotate the Telegram token if `.env` has ever been shared or committed.

## How the form works

A 63-question form on one page is intimidating, so the assessment is presented as
**21 short segments of three questions** — one subdomain at a time. Each step shows:

- a plain-English heading and what the section is checking,
- **three questions only**, each with a "Why we ask" line,
- a **live score panel** that updates after every answer, showing the running
  {{ INDEX_SHORT }}, the section score, the pillar score, and the executive metrics
  that the section feeds,
- a clickable stepper so any step can be revisited.

Answers save automatically as you go, so a half-finished assessment survives a refresh.
A metric only shows a number once every input its formula needs has a real answer;
until then it shows a dash rather than a misleading figure.

### Answer scales — tailored per question

There is no single universal ladder. Each question names a scale in
`constants.SCALES` built for what it actually asks, so a question about
approval layers offers counts of people, a question about retrieval speed
offers times, and a question about volume offers counts per week.

| Question | Scale | Options run from |
| --- | --- | --- |
| How many separate steps to finish a job? | `stepcount` | More than 10 steps → One step |
| How many people must approve something? | `approvals` | Five or more people → Never needs approval |
| How quickly can a new hire find an answer? | `speed_more` | They must ask someone → Straight away |
| How many customer questions per week? | `volume_count` | None → More than 100 a week |
| How often is information copied and pasted? | `copying_less` | All day, every day → Never |

**Invariant:** the highest-scoring option of *every* scale means "most ready".
"Ladders for questions where less is better are written in reverse at authoring
time, so the scoring engine and all 36 metric formulas need no knowledge of
polarity. `tests/test_questions.py` enforces this.

### Writing rules for questions

Questions are written so that someone with no business or IT background can answer
them from their own experience: short sentences, no jargon, one idea per question, and
a "why" that says what is being checked and why it matters.

---

## Roadmap

1. ✅ Naming system, pillar framework and confidence model
2. ✅ Bot input validation + error handling
3. ✅ Scoring engine: Elipsis Index, confidence index, pain points, recommendations
4. ✅ Financial model (KES): cost, ROI, payback
5. ✅ FastAPI + SQLAlchemy platform: dashboard, printable report, REST API, OpenAPI docs
6. ✅ Generalised ORG-001 instrument: 63 questions, seven pillars, 36 executive metrics
7. ✅ Three-phase implementation roadmap (Quick Wins → Process Automation → AI)
8. ✅ Segmented form (21 steps) with live per-section scoring and autosave
9. ✅ Command-centre dashboard, plain-English instrument, icon-led design system
10. ✅ Per-question answer scales (48 named scales) replacing the universal ladder
11. ✅ Test suite (63 tests) covering the engine, instrument, financial model and API
12. ✅ Financial impact sized by the organisation, with a ceiling and a shown working
13. ✅ Dashboard "clear demo data" control
14. Next: evidence uploads, multi-respondent alignment index, assessment
    comparison view, further verticals, Level 3–6 report tiers

## Tests

```bash
pip install -e '.[dev]'
python -m pytest
```

| File | Covers |
| --- | --- |
| `tests/test_questions.py` | 63 unique codes, 9 per pillar, 21 segments, plain-English wording, scale integrity and direction |
| `tests/test_readiness.py` | Metric bounds, evaluator safety (rejects `__import__`, attribute access, lambdas), readiness gating, maturity band edges, partial/empty forms, roadmap coverage |
| `tests/test_financial.py` | Savings scale with company size, wage tiers, the 12% ceiling, and arithmetic that reconciles |
| `tests/test_api.py` | Full round trip: create → answer 21 segments live → submit → results/report/dashboard |

## The financial model

Annual savings are sized by the organisation being assessed:

```text
affected staff = staff x share of workforce the pain touches
annual hours   = affected staff x hours per person per year x severity
current cost   = annual hours x blended hourly rate
recoverable    = current cost x efficiency(complexity)

total savings  = capped at 12% of the labour line
```

The blended hourly rate rises with organisation size (KES 250 → 900), and the
report prints the whole working — staff count, rate, labour line, ceiling and
hours freed — so a client can check the arithmetic instead of taking it on
trust.
