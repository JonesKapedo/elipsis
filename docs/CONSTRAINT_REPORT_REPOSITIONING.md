# Elipsis — Constraint Report Repositioning

Status: Phase 1 complete; Phase 2 revenue surfaces built (tests green)
Owner: Founder
Last updated: 2026-11-01

---

## 1. Thesis

Elipsis is not a platform, marketplace, or AI dashboard. It is an **Operations
Constraint Report for logistics and field operators**: score readiness, price the
main bottleneck, and leave with a 90-day plan. The paid product is a board-ready
document, not a subscription seat.

Every change must do at least one of:

1. Improve the Constraint Report.
2. Get the report paid for.
3. Get the plan implemented.

If it does none, it does not ship.

---

## 2. Decisions locked

| Area | Decision |
|---|---|
| Frontend | FastAPI + SQLAlchemy + Jinja2 only. React SPA deleted. |
| Vertical | 3PL and warehousing operators, 50–300 staff, multi-site. |
| Market | Global, English, USD. |
| Free offer | Pulse: index, band, confidence, top-3 constraint names, one sample action. |
| Core paid offer | Constraint Report, $499, perpetual document access. |
| Upsell | Facilitated, $1,900: report + review call + 3 implementer intros. |
| Recurring | Operator, $129/mo or $999/yr: actions, team, cadence. Optional. |
| Partner | $249/mo: white-label / multi-client. Phase 3. |
| Re-score | Free for report buyers. |
| Report access | Perpetual. 90 days is the plan horizon, not an expiry. |
| Payments | Paystack now (Kenya entity). Stripe later via supported entity. |
| Old SKUs | $49 report, $29/$380 subscription, $39/$119/$219 bidder plans, $24.50 switch top-up: retired. |
| Legacy data | No live paying data to preserve. Clean migration. |

---

## 3. Market and buyer

**ICP:** 3PL / contract logistics operators running two or more sites, 50–300
staff, multiple clients, WMS/TMS in place, SLAs with penalties.

**Buyer:** COO, Head of Operations, or Ops Director. Has budget authority for
$499 without procurement. Feels SLA penalties, billing leakage, labour drag, and
multi-site variance.

**Trigger events:** new client onboarding, SLA breach, WMS migration, peak-season
prep, post-merger site consolidation, board request for a costed ops plan.

**Why they pay:** the constraint is already priced in their world (credits,
penalties, overtime, rework). The report converts a feeling into a costed
operating decision.

**Explicitly not the beachhead:**

| Segment | Why not now |
|---|---|
| Haulage / trucking | Fragmented, sub-10 staff, price-sensitive, buys telematics. |
| Last-mile delivery | Thin margins, tech-forward, low willingness for a $499 document. |
| Freight forwarding | Strong second vertical; customs local, CargoWise entrenched. |
| Field service | Different buyer and vocabulary; do not split focus. |

**Validation plan (before scaling copy):** 10 calls with 3PL ops leaders, 3 free
Facilitated reports, one question: "What would you pay for this, and who signs?"
Proceed only if 5+ confirm the pain and 2+ confirm the price.

---

## 4. Offer architecture

### 4.1 SKU catalog

Single source of truth: `elipsis_api/catalog.py` (to be created). No price may be
hardcoded in a template or route.

| SKU | Name | Price | Billing | Deliverable | Access |
|---|---|---|---|---|---|
| `pulse` | Pulse | $0 | none | Index, band, confidence, top-3 constraint names, 1 sample action | Account required |
| `report` | Constraint Report | $499 | one-time | Full costed report, 36 metrics, roadmap, PDF, share link | Perpetual |
| `facilitated` | Facilitated Report | $1,900 | one-time | Report + 60–90 min review + 3 implementer intros | Perpetual |
| `operator_monthly` | Operator | $129 | monthly | Actions, team, quarterly re-score, exports | Active subscription |
| `operator_annual` | Operator (annual) | $999 | yearly | Same, 2 months free | Active subscription |
| `partner` | Partner | $249 | monthly | Multi-client, white-label, seats | Phase 3 |

### 4.2 Retired

| Old item | Old price | Replacement |
|---|---|---|
| Unlock Full Assessment | $49 | Constraint Report $499 |
| Pro monthly / annual | $29 / $380 | Operator $129 / $999 |
| Bidder Starter / Pro / Elite | $39 / $119 / $219 | Partner $249 (Phase 3) |
| Switch top-up | $24.50 | Removed |

### 4.3 Access split

- **Report document:** perpetual after payment.
- **Interactive layer** (action board, team seats, tracking, cadence): 90 days
  included with report; continues under Operator.
- **Report is never gated by subscription.** Operator is optional.

### 4.4 Re-score mechanics

- Free for anyone who bought a report.
- Day-75 reminder (email) with a pre-filled re-score link.
- Re-score shows movement against the original report.
- Cadence beyond the first re-score is an Operator feature, but the report owner
  may always re-score free once per 90-day cycle.

---

## 5. Entitlement matrix

| Capability | Pulse | Report | Facilitated | Operator | Partner |
|---|---|---|---|---|---|
| Readiness index | yes | yes | yes | yes | yes |
| Maturity band | yes | yes | yes | yes | yes |
| Confidence index | yes | yes | yes | yes | yes |
| Top-3 constraint names | yes | yes | yes | yes | yes |
| One sample action | yes | yes | yes | yes | yes |
| Constraint narrative | no | yes | yes | yes | yes |
| Costed $ model | no | yes | yes | yes | yes |
| 36 executive metrics | no | yes | yes | yes | yes |
| Pillars and lanes | no | yes | yes | yes | yes |
| 90-day roadmap | no | yes | yes | yes | yes |
| PDF board pack | no | yes | yes | yes | yes |
| Share link | no | yes | yes | yes | yes |
| Review call | no | no | yes | yes | yes |
| 3 implementer intros | no | no | yes | yes | yes |
| Action board / owners | no | 90 days | 90 days | yes | yes |
| Team seats | no | 90 days | 90 days | yes | yes |
| Re-score | yes | free | free | yes | yes |
| White-label / multi-client | no | no | no | no | yes |

---

## 6. Free boundary spec

Free (Pulse) shows exactly:

1. Readiness index (one number).
2. Maturity band.
3. Confidence index and band.
4. Top-three constraint **names** (no cost).
5. One sample action.

Free must **not** show: costed $ exposure, the full 36 metrics, pillar bars with
scores, the roadmap, benchmarks, assumptions, PDF, share link, or team tools.

Upgrade panel: one primary button (`Get the Constraint Report · $499`) and one
secondary text link (`See a sample report`). No dead end, no second checkout
price.

---

## 7. Payments

### 7.1 Provider decision

Stripe does not onboard Kenya-registered businesses. Therefore:

- **Launch:** Paystack (already integrated; accepts international cards; USD
  payout; a Stripe company).
- **Later:** add Stripe only if a US/UK entity exists (e.g. Stripe Atlas).
- **Code:** payment layer behind a `PaymentProvider` interface. Checkout,
  webhook, and refund call the interface, not Paystack directly.

### 7.2 Stripe reference (if added later)

- No setup, monthly, or closure fee.
- 2.9% + $0.30 per successful domestic card.
- +1.5% cross-border, +1% currency conversion for global USD.
- Billing add-on 0.7% on recurring volume.
- Expected net on $499: about $484 domestic, $472 international + FX.

### 7.3 Paystack launch checklist

- Registered Kenyan business and KYC approved before first live charge.
- Confirm USD charging and payout on the account.
- Production keys in environment; dummy mode disabled.
- Webhook signature verification and idempotency by provider reference.
- Reconciliation: provider reference -> order -> entitlement.

### 7.4 Refunds and disputes

- 14-day refund if the report has not been generated/downloaded.
- No refund after download; offer one free re-run instead.
- Facilitated: one free reschedule; refund only if the call is not delivered.
- Chargebacks: respond with delivery evidence (report access log, download log).

### 7.5 Tax and invoicing

- Prices are exclusive of taxes.
- Kenya VAT (16%) and eTIMS apply once VAT-registered; confirm with accountant.
- Global digital-services tax (EU VAT, UK VAT, US state) is out of scope for
  launch; disclose and revisit at volume.
- B2B invoice must carry company name, address, tax ID, and line items.

---

## 8. Legal and compliance

Must exist before the first $499:

- Terms of service (report sale, not SaaS seat).
- Privacy policy and data processing addendum.
- **Disclaimer on every $ claim:** "Indicative model based on your inputs, not an
  audited saving. No guarantee of results."
- Limitation of liability capped at the amount paid.
- IP: buyer receives a licence to the report; Elipsis retains methodology,
  benchmark, and scoring IP.
- Data retention and deletion policy (global buyers, GDPR/UK GDPR adjacent).
- Governing law: Kenya.
- Kenyan entity registration and tax registration.

---

## 9. Data model and migration

### 9.1 New model

`Order` (or `Entitlement`):

| Field | Purpose |
|---|---|
| `id` | primary key |
| `organization_id` | buyer org |
| `assessment_id` | nullable; report scope |
| `sku` | catalog key |
| `amount_minor` | integer, provider minor units |
| `currency` | `USD` |
| `tax_minor` | nullable |
| `status` | `pending`, `paid`, `refunded`, `failed` |
| `provider` | `paystack`, `stripe` |
| `provider_reference` | unique, idempotency |
| `purchased_at` | timestamp |
| `expires_at` | null for report; set for workspace/operator |

`AssessmentPurchase` is unique on `assessment_id` and cannot hold multiple SKUs.
Migrate to `Order` and keep a compatibility read.

### 9.2 Gating fix (blocker)

`report_routes.py` now gates on `company_is_pro` OR an active `report`
entitlement OR the compatibility `AssessmentPurchase`, so a paid report is
reachable without a subscription.

### 9.3 Free/paid template

`results.html` gates the appendix with a `report_unlocked` conditional. The page is
now ordered summary strip -> money -> constraint narrative -> index -> lanes ->
90-day plan -> PDF rail. Free users see the index, band, confidence, and top-3
names only.

### 9.4 Studio router

`elipsis_api/routers/studio.py` is now a normal 900-line module. The
base64/gzip part files have been removed, so billing and entitlements are
readable and editable directly.

---

## 10. UI / UX implementation guide

### 10.1 Ownership

- `static/tokens.css` is the single source of truth, loaded first.
- No other stylesheet may declare a light-mode `:root`.
- Dark overrides remain in `theme.css` under `html[data-theme="dark"]`.
- Per-element vars (`--i`, `--pct`, `--pulse`, `--room-accent`,
  `--report-accent`) are set inline and are not global tokens.

### 10.2 Cascade order (base.html)

```
tokens.css
style.css
app-shell.css
extras.css
motion.css
app.css
premium.css
design.css
contrast-fix.css
theme.css
logistics-ui.css
brand-scale.css
```

Retire `contrast-fix.css` and `brand-scale.css` after visual verification; they
are patches for cascade fights that no longer exist.

### 10.3 Page-by-page

**Landing (`landing.html`)**

1. Hero: constraint + money + 90 days.
2. Two CTAs: `Start free assessment` (primary), `See a sample report` (secondary).
3. Static product mock: Index + constraint + exposure. No marketplace chrome.
4. Proof strip: questions, metrics, 90-day plan.
5. How it works: Diagnose -> Price -> Act.
6. Sample report strip.
7. Pricing: Pulse -> Constraint Report (featured) -> Facilitated -> Operator.
8. Secondary link: For consultants and implementers.
9. Trust row: ~25 min, assumptions printed, no consultants required.

Proof line under the $499 card: "Comparable on-site diagnostics often start at
$2,000+; Elipsis delivers the structured report layer in hours, not a week on
site."

Remove: marketplace-first story, long platform feature grids, competing primary
buttons.

**Pricing (`pricing.html`)**

- Four cards; Constraint Report featured with `--amber-soft` wash and amber
  border.
- Mono/tabular prices.
- Short bullets only.
- Facilitated presented as "with review".
- Operator secondary.
- Disclaimer: "Indicative model based on your inputs."

**Results (`results.html`) — the product**

Strict order:

1. Summary strip, max 4 cells: Index · Constraint · Exposure · Confidence.
   Free: Index · Band · Confidence, no exposure cell.
2. Money: largest indicative constraint $ with mono disclaimer
   "indicative / based on your inputs".
3. Constraint narrative: 2–4 plain sentences.
4. Index and maturity band: one big number.
5. Pillars/lanes: compact bars; weakest in amber.
6. 90-day plan: top actions with owner and date when available.
7. Primary CTA: `Download board pack` (solid, always visible).
8. Secondary: Share, Request implementer intros.

Layout: summary strip full width; main column = story + plan; right rail = PDF,
share, intros.

Free: teaser only; blurred/truncated $ model and plan; single upgrade panel.

Paid: full clarity; PDF dominant.

**App shell (`base.html`)**

- Dark asphalt sidebar.
- Nav groups: Diagnose · Plan · Account.
- Marketplace hidden from client nav (flag + IA).
- Active nav: amber left border (already in design.css).
- Thin white top bar; org switcher; no decorative search.

**Dashboard**

- Max 4 KPIs.
- "This week's actions from last report".
- No chart wall, no module grid as hero.

**Assessment**

- Progress by pillar in left rail.
- One question focus, calm type, clear options.
- Mono autosave indicator.
- Footer: Back / Continue only.
- Mobile: full-width options, sticky progress, large tap targets.

**Intros**

- After results: simple "Request implementer intros" form.
- No marketplace browser for clients.
- Partner/admin surfaces stay dense but use the same tokens.

### 10.4 Featured $499 card

- `border: 1px solid var(--amber)`.
- Header wash `var(--amber-soft)`.
- Mono price at 36–40px with `font-variant-numeric: tabular-nums`.
- One primary amber button.
- Small "most operators start here" label in mono uppercase.
- No gradient, no shadow stack.

### 10.5 PDF CTA and disclaimer

- Solid amber button in the results right rail and at the end of the plan.
- Label: `Download board pack (PDF)`.
- Directly below: mono, 11px, muted:
  `indicative / based on your inputs`.
- Button remains visible on mobile (sticky bottom bar acceptable).

### 10.6 Visual QA checklist

Desktop and mobile:

- [ ] Hierarchy: money before index on paid; index before everything on free.
- [ ] One primary CTA color per screen (amber only).
- [ ] Contrast: amber never used for body text; amber buttons use amber-ink.
- [ ] Free vs paid: free shows exactly the five allowed items.
- [ ] Paid: PDF button visible without scrolling past the plan.
- [ ] Type: Plex Sans for UI, Plex Mono for scores/money/eyebrows.
- [ ] Radius: 5–8px; no 999px pills except status dots.
- [ ] Borders over shadows; no decorative gradients.
- [ ] Nav: no Marketplace in client path.
- [ ] Mobile: CTA, PDF, and answer options usable at 375px.

---

## 11. Facilitated delivery runbook

1. Order paid -> booking link (Cal.com) -> 60–90 min call.
2. Call agenda: confirm inputs, one constraint deep-dive, agree top actions.
3. Deliverable: revised report + 3 intro options within 5 business days.
4. QA before send: numbers reconcile, assumptions printed, disclaimer present.
5. Intros: consent from both sides, tracked in `IntroRequest`, success fee
   documented.
6. Capacity: founder delivers first 10; max 3 per week.

---

## 12. Go-to-market

- One-liner: "Find the bottleneck costing your operation. Price it. Fix it in 90
  days."
- Assets needed: anonymized sample report (PDF), methodology page, pricing page,
  FAQ, one vertical landing page.
- Channels: 3PL associations, WMS/ops implementers, LinkedIn ops groups, targeted
  outbound to 50 named accounts.
- Design partner offer: first 10 reports free or at cost in exchange for a case
  study and a testimonial.
- Objection handling: "we already know our bottleneck" -> cost it; "we have
  consultants" -> this is the pre-consultant layer; "is this AI?" -> it is a
  structured diagnostic, not a chatbot.

---

## 13. Metrics

- North star: percentage of reports re-scored at day 90.
- Funnel: visitor -> Pulse start -> Pulse complete -> report purchase ->
  facilitated -> Operator -> re-score.
- Targets for first 90 days: 300 Pulse completes, 20 reports, 5 facilitated,
  3 Operator, 50% re-score rate.

---

## 14. Phase plan

### Phase 1 — Build (test mode)

| # | Task | Acceptance |
|---|---|---|
| 1 | `tokens.css` canonical + strip competing roots | One `:root`; pages render |
| 2 | Create `catalog.py` SKU source | No price literals in templates |
| 3 | `Order` model + migration | Paid order creates entitlement |
| 4 | Fix `report_routes.py` gating | Paid report downloads |
| 5 | Reprice landing, pricing, results | No `$49`/`$29`/`$380` in UI |
| 6 | Results reorder + free teaser | Matches section 10.3 |
| 7 | Hide marketplace from client nav | Flag on; admin bypass intact |
| 8 | Intros CTA after results | Form submits, admin sees request |
| 9 | De-obfuscate studio router | Normal module, tests pass |
| 10 | Re-score flow + day-75 tick | Reminder sends, re-score works |
| 11 | Tests green | Payment, gating, pricing covered |

### Phase 2 — Revenue

Built:

- Facilitated Report checkout ($1,900), booking workspace, and report entitlement bundle.
- Billing history, printable receipts, entitlement list, and subscription renewal cancellation.
- Operator page rewritten around execution, with renewal terms and billing links.
- Public refund policy; trust nav, footer, robots, and sitemap updated.
- Receipt and checkout copy state USD pricing and tax treatment.

External gates:

- Entity registered, Paystack KYC, first live $499 charge end-to-end.
- 10 design-partner calls; 3 facilitated delivered.
- Tax/VAT/eTIMS confirmation before first Kenyan invoice.

### Phase 3 — Scale

- Operator and Partner surfaces.
- Stripe via supported entity if volume justifies.
- Benchmark cohort once sample is sufficient.
- Case studies and partner channel.

---

## 15. Go-live gates

Do not publish $499 until all are true:

- [ ] Business registered; Paystack KYC approved.
- [ ] Real test charge produces a downloadable report.
- [ ] PDF matches on-screen order and includes the disclaimer.
- [x] Refund and chargeback policy published.
- [ ] ToS, privacy, DPA reviewed.
- [ ] Paid report is not redirected to `/pro`.
- [ ] Marketplace absent from client nav.
- [ ] Test suite green.
- [ ] Sample report approved.
- [ ] Support inbox monitored.

---

## 16. Risks

| Risk | Mitigation |
|---|---|
| One-time revenue lumpiness | Operator and Partner attach; re-score loop |
| Report credibility | Methodology page, assumptions printed, no guaranteed savings |
| Kenya entity / Stripe gap | Paystack now; provider interface; Stripe later |
| Tax/VAT/eTIMS | Accountant engaged before first Kenyan invoice |
| Benchmark thinness | Suppress peer comparisons until minimum sample |
| Facilitated capacity | Cap at 3/week; founder delivers first 10 |
| Chargebacks | Delivery evidence, clear refund policy |
| Scope creep | Three-question test in section 1 |
| Marketplace distraction | Hidden from client IA; partner-only |
