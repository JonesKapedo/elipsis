import { HORIZONS, MATURITY, PILLARS, SUBDOMAINS, maturityFor } from "./elipsis";
import { QUESTIONS, optionsFor } from "./questions";
import { scoreFromIndex } from "./scales";

export type Answers = Record<string, number>;

export type OrgProfile = {
  name: string;
  industry: string;
  region: string;
  sizeBand: string;
  headcount: number;
  annualRevenue: number;
  hourlyRate: number;
  currency: string;
};

export type PainPoint = {
  code: string;
  title: string;
  problem: string;
  impact: string;
  solution: string;
  automation: string;
  severity: "Critical" | "High" | "Medium";
  complexity: "Low" | "Medium" | "High";
  priority: number;
  horizon: (typeof HORIZONS)[number]["id"];
  weeklyHours: number;
  annualSavings: number;
  investment: number;
  roi: number;
  kpis: string[];
};

export type MetricRow = {
  code: string;
  pillar: string;
  label: string;
  kind: "score" | "risk";
  value: number;
  reading: string;
};

export type AssessmentResult = {
  index: number;
  confidence: number;
  maturity: { level: number; label: string; reading: string };
  pillars: {
    code: string;
    label: string;
    short: string;
    weight: number;
    score: number;
    subdomains: { code: string; label: string; score: number }[];
  }[];
  composites: {
    currentState: number;
    futureReadiness: number;
    risk: number;
    opportunity: number;
    efficiency: number;
    automationPotential: number;
    aiAdoption: number;
    dataMaturity: number;
    techMaturity: number;
    transformationIndex: number;
  };
  metrics: MetricRow[];
  answered: number;
  total: number;
  painPoints: PainPoint[];
  roadmap: {
    id: string;
    label: string;
    days: number;
    focus: string;
    items: PainPoint[];
    benefit: number;
    investment: number;
  }[];
  roi: {
    currency: string;
    payroll: number;
    annualSavings: number;
    investment: number;
    netYear1: number;
    paybackMonths: number;
    roi3: number;
    roi5: number;
    productivityGain: number;
    revenueLift: number;
    threeYearValue: number;
    fiveYearValue: number;
    working: string[];
  };
  benchmarks: {
    industry: string;
    sizeBand: string;
    industryAvg: number;
    sizeAvg: number;
    digitalAvg: number;
    automationAvg: number;
    aiAvg: number;
    percentile: number;
    pillarBench: { code: string; you: number; industry: number; peers: number }[];
  };
};

const clamp = (n: number, a = 0, b = 100) => Math.max(a, Math.min(b, n));
const avg = (xs: number[]) => (xs.length ? xs.reduce((s, x) => s + x, 0) / xs.length : 0);
const invert = (x: number) => 100 - x;
const mix = (...xs: number[]) => avg(xs);
const blend = (a: number, b: number, wa: number, wb: number) => (wa + wb ? (a * wa + b * wb) / (wa + wb) : 0);

type Catalog = {
  code: string;
  title: string;
  problem: string;
  impact: string;
  solution: string;
  automation: string;
  severity: PainPoint["severity"];
  complexity: PainPoint["complexity"];
  horizon: PainPoint["horizon"];
  weeklyHours: number;
  share: number;
  investment: number;
  kpis: string[];
};

const CATALOG: Catalog[] = [
  { code: "Q01", title: "Tribal knowledge risk", problem: "Core jobs live in people's heads, not in written steps.", impact: "Quality varies by who is on shift. Onboarding is slow. Errors repeat.", solution: "Document the core processes and stand up a searchable SOP library.", automation: "Knowledge base with owned SOPs and retrieval.", severity: "High", complexity: "Low", horizon: "30d", weeklyHours: 28, share: 0.1, investment: 18000, kpis: ["SOP coverage %", "Time to find an answer"] },
  { code: "Q03", title: "Unowned processes", problem: "Main jobs have no named owner.", impact: "Nothing is improved because nobody is accountable.", solution: "Assign a named process owner and a review cadence.", automation: "Process register with ownership and SLA.", severity: "Medium", complexity: "Low", horizon: "30d", weeklyHours: 14, share: 0.06, investment: 9000, kpis: ["% processes with owner"] },
  { code: "Q05", title: "Approval bottleneck", problem: "Routine work waits on too many people.", impact: "Cycle time inflates. Customers wait. Staff chase signatures.", solution: "Collapse approval layers and auto-route low-value requests.", automation: "Workflow engine with approval rules.", severity: "High", complexity: "Medium", horizon: "6m", weeklyHours: 16, share: 0.08, investment: 42000, kpis: ["Approval cycle time", "Layers per request"] },
  { code: "Q06", title: "Cycle-time drag", problem: "Most of the elapsed time is waiting, not working.", impact: "Capacity is paid for but idle. Promises slip.", solution: "Re-engineer the flow to remove queue time between steps.", automation: "Process redesign plus workflow automation.", severity: "High", complexity: "Medium", horizon: "6m", weeklyHours: 24, share: 0.12, investment: 54000, kpis: ["End-to-end cycle time"] },
  { code: "Q08", title: "Overtime dependency", problem: "The operation only finishes with extra hours.", impact: "Cost spikes exactly when demand is highest. Burnout follows.", solution: "Rebalance capacity against measured demand.", automation: "Capacity planning and scheduling.", severity: "Medium", complexity: "Medium", horizon: "90d", weeklyHours: 20, share: 0.1, investment: 28000, kpis: ["Overtime hours", "On-time completion"] },
  { code: "Q10", title: "High-frequency repetitive work", problem: "The same tasks run all day, by hand.", impact: "Payroll is spent on work a machine can do tonight.", solution: "Automate the highest-frequency recurring tasks first.", automation: "RPA / workflow automation on the top 3 tasks.", severity: "High", complexity: "Low", horizon: "90d", weeklyHours: 45, share: 0.15, investment: 48000, kpis: ["Hours automated / week"] },
  { code: "Q13", title: "Unwritten decision rules", problem: "Staff decide by feel. Rules are not encoded.", impact: "Inconsistent outcomes. Automation cannot start.", solution: "Encode fixed decision rules into a decision service.", automation: "Rules engine for the top decision paths.", severity: "High", complexity: "Medium", horizon: "90d", weeklyHours: 32, share: 0.12, investment: 36000, kpis: ["% decisions with written rules"] },
  { code: "Q16", title: "Manual data entry", problem: "Hours each day are spent typing information in by hand.", impact: "Cost, delay, and quiet error.", solution: "Capture at source and transfer by API.", automation: "Form capture / OCR / API integration.", severity: "High", complexity: "Low", horizon: "90d", weeklyHours: 38, share: 0.14, investment: 32000, kpis: ["Manual keystrokes removed"] },
  { code: "Q17", title: "Copy-paste dependency", problem: "Information is re-keyed between systems.", impact: "Wrong numbers enter the official record.", solution: "Connect the systems so data moves once.", automation: "API / iPaaS between systems of record.", severity: "Critical", complexity: "Medium", horizon: "6m", weeklyHours: 40, share: 0.13, investment: 62000, kpis: ["Re-key events / week"] },
  { code: "Q18", title: "Manual reporting and chasing", problem: "Reports and follow-ups are assembled by hand.", impact: "Managers wait. Staff lose days to status.", solution: "Automate recurring reporting and exception chasing.", automation: "BI suite with scheduled packs and alerts.", severity: "High", complexity: "Low", horizon: "90d", weeklyHours: 42, share: 0.15, investment: 26000, kpis: ["Report cycle time"] },
  { code: "Q22", title: "Paper reliance", problem: "Daily work still starts or ends on paper.", impact: "Nothing downstream can be automated until capture is digital.", solution: "Digitise intake at the point of work.", automation: "Digital forms and document capture.", severity: "Medium", complexity: "Medium", horizon: "6m", weeklyHours: 18, share: 0.1, investment: 38000, kpis: ["% paper-free transactions"] },
  { code: "Q24", title: "Spreadsheet as system of record", problem: "Official jobs live in spreadsheets.", impact: "Growth, audit, and automation all stall.", solution: "Move spreadsheet systems of record into a governed platform.", automation: "Operational database + BI.", severity: "High", complexity: "Medium", horizon: "12m", weeklyHours: 35, share: 0.12, investment: 72000, kpis: ["Jobs off spreadsheet"] },
  { code: "Q27", title: "Integration constraint", problem: "Systems have no documented way to connect.", impact: "Every automation project pays a rebuild tax.", solution: "Expose documented APIs and an integration layer.", automation: "iPaaS / API middleware.", severity: "High", complexity: "High", horizon: "12m", weeklyHours: 26, share: 0.08, investment: 110000, kpis: ["Documented APIs"] },
  { code: "Q29", title: "Unowned critical data", problem: "Nobody owns data quality.", impact: "Numbers quietly rot until a decision is made on them.", solution: "Publish data ownership and quality standards.", automation: "Data ownership register.", severity: "Medium", complexity: "Low", horizon: "30d", weeklyHours: 14, share: 0.05, investment: 12000, kpis: ["Datasets with an owner"] },
  { code: "Q33", title: "Late data errors", problem: "Mistakes appear after they have already been acted on.", impact: "Wrong decisions, rework, and lost trust.", solution: "Validate at the point of capture.", automation: "Validation rules / data-quality tooling.", severity: "High", complexity: "Medium", horizon: "6m", weeklyHours: 28, share: 0.1, investment: 44000, kpis: ["Error detection lag"] },
  { code: "Q35", title: "Absent decision dashboard", problem: "Managers must ask for a report.", impact: "The organisation steers in the rear-view mirror.", solution: "Publish a live KPI dashboard from systems of record.", automation: "BI dashboard layer.", severity: "Medium", complexity: "Medium", horizon: "12m", weeklyHours: 22, share: 0.08, investment: 34000, kpis: ["Live KPI coverage"] },
  { code: "Q38", title: "Support knowledge deficit", problem: "Common customer questions are not written down.", impact: "Every ticket is treated as unique. Cost scales with volume.", solution: "Write the FAQ and put it behind self-service.", automation: "Knowledge base + deflection / assistant.", severity: "Medium", complexity: "Low", horizon: "90d", weeklyHours: 20, share: 0.08, investment: 22000, kpis: ["Deflection rate"] },
  { code: "Q40", title: "Scattered institutional knowledge", problem: "There is no central place for procedures.", impact: "AI has nothing reliable to read. Staff reinvent work.", solution: "Stand up one searchable knowledge base with owners.", automation: "Knowledge platform with retrieval.", severity: "High", complexity: "Medium", horizon: "12m", weeklyHours: 24, share: 0.09, investment: 48000, kpis: ["Time to first answer"] },
  { code: "Q44", title: "Short-horizon planning", problem: "Demand is worked out too late.", impact: "Shortages become overtime and lost sales.", solution: "Build a data-based demand plan on a longer horizon.", automation: "Forecasting model on sales and operations data.", severity: "High", complexity: "High", horizon: "24m", weeklyHours: 18, share: 0.07, investment: 86000, kpis: ["Forecast accuracy"] },
  { code: "Q46", title: "No system of record", problem: "Official records are not in one trusted system.", impact: "Automation has nowhere trustworthy to sit.", solution: "Designate and enforce one system of record per domain.", automation: "ERP / operations core.", severity: "Critical", complexity: "High", horizon: "12m", weeklyHours: 30, share: 0.1, investment: 140000, kpis: ["Domains with a system of record"] },
  { code: "Q52", title: "Weak access control", problem: "Who can get into systems is not reviewed.", impact: "Automation inherits the holes.", solution: "Own, review, and audit access lists.", automation: "Identity governance.", severity: "High", complexity: "Medium", horizon: "6m", weeklyHours: 8, share: 0.03, investment: 28000, kpis: ["Access review cadence"] },
  { code: "Q53", title: "Untested recovery", problem: "Backup exists as a hope, not a plan.", impact: "A single incident can freeze the transformation programme.", solution: "Test restore. Time it. Own it.", automation: "Documented restore runbook, regularly tested.", severity: "High", complexity: "Medium", horizon: "30d", weeklyHours: 6, share: 0.02, investment: 16000, kpis: ["Last successful restore test"] },
  { code: "Q55", title: "Linear staffing growth", problem: "Every increase in work needs more people.", impact: "Margin cannot improve with scale.", solution: "Automate the volume-sensitive path first.", automation: "Straight-through processing on the growth path.", severity: "High", complexity: "Medium", horizon: "12m", weeklyHours: 22, share: 0.1, investment: 64000, kpis: ["Revenue per FTE"] },
  { code: "Q58", title: "Key-person concentration", problem: "The business would stall without one or two people.", impact: "Growth, holiday, and succession are all the same risk.", solution: "Document, train cover, and encode the work.", automation: "SOP + cover roster + encoded rules.", severity: "Critical", complexity: "Low", horizon: "30d", weeklyHours: 16, share: 0.08, investment: 14000, kpis: ["Roles with trained cover"] },
  { code: "Q61", title: "Operating model blocks growth", problem: "The current way of working is the ceiling.", impact: "New customers make the operation worse, not richer.", solution: "Redesign the constrained flow before adding volume.", automation: "Process automation on the constrained path.", severity: "High", complexity: "Medium", horizon: "24m", weeklyHours: 20, share: 0.09, investment: 78000, kpis: ["Throughput without extra FTE"] },
];

function questionScore(answers: Answers, code: string) {
  const q = QUESTIONS.find((x) => x.code === code);
  if (!q || answers[code] === undefined) return null;
  return scoreFromIndex(answers[code], optionsFor(q).length);
}

function subdomainScore(answers: Answers, code: string) {
  const qs = QUESTIONS.filter((q) => q.subdomain === code);
  const weighted = qs
    .map((q) => {
      const s = questionScore(answers, q.code);
      return s === null ? null : { s, w: q.weight };
    })
    .filter((x): x is { s: number; w: number } => x !== null);
  if (!weighted.length) return 0;
  return weighted.reduce((a, x) => a + x.s * x.w, 0) / weighted.reduce((a, x) => a + x.w, 0);
}

const INDUSTRY_BASE: Record<string, number> = {
  Logistics: 41,
  "Financial Services": 54,
  Manufacturing: 46,
  Healthcare: 44,
  Retail: 48,
  "Professional Services": 52,
  Telecommunications: 57,
  Energy: 45,
  "Public Sector": 38,
  Technology: 62,
  Agriculture: 36,
  Hospitality: 40,
};

export function computeResult(answers: Answers, org: OrgProfile): AssessmentResult {
  const answered = QUESTIONS.filter((q) => answers[q.code] !== undefined).length;
  const subScores: Record<string, number> = {};
  for (const s of SUBDOMAINS) subScores[s.code] = subdomainScore(answers, s.code);

  const pillars = PILLARS.map((p) => {
    const subs = SUBDOMAINS.filter((s) => s.pillar === p.code).map((s) => ({
      code: s.code,
      label: s.label,
      score: Math.round(subScores[s.code]),
    }));
    return {
      code: p.code,
      label: p.label,
      short: p.short,
      weight: p.weight,
      score: Math.round(avg(subs.map((s) => s.score))),
      subdomains: subs,
    };
  });

  const p = Object.fromEntries(pillars.map((x) => [x.code, x.score])) as Record<string, number>;
  const q = (code: string) => questionScore(answers, code) ?? 0;
  const s = subScores;

  const index = clamp(PILLARS.reduce((sum, x) => sum + (p[x.code] ?? 0) * x.weight, 0));
  const maturity = maturityFor(index);

  const metrics: MetricRow[] = [
    { code: "PES", pillar: "OEI", label: "Process Efficiency Score", kind: "score", value: mix(s.OPS, s.WFL), reading: "How efficiently work is documented and sequenced." },
    { code: "WFI", pillar: "OEI", label: "Workflow Friction Index", kind: "risk", value: invert(s.WFL), reading: "Step count, approvals and waiting time in the operating flow." },
    { code: "ACS", pillar: "OEI", label: "Approval Complexity Score", kind: "risk", value: invert(blend(q("Q05"), q("Q04"), 0.6, 0.4)), reading: "How many layers and steps a routine transaction must clear." },
    { code: "OWI", pillar: "OEI", label: "Operational Waste Index", kind: "risk", value: invert(blend(s.RSU, mix(q("Q06"), q("Q07")), 0.5, 0.5)), reading: "Idle capacity, overtime and elapsed time paid for but not worked." },
    { code: "HDR", pillar: "OEI", label: "Human Dependency Ratio", kind: "risk", value: invert(blend(mix(q("Q03"), q("Q12")), s.KPD, 0.5, 0.5)), reading: "How much of the operation only works because a person knows how." },
    { code: "RPI", pillar: "ARI", label: "Repetition Index", kind: "score", value: s.REP, reading: "How much of the work is frequent, regular and single-owner." },
    { code: "ACMS", pillar: "ARI", label: "Automation Compatibility Score", kind: "score", value: mix(s.REP, s.RUL), reading: "Whether the work follows rules a machine could follow." },
    { code: "MBS", pillar: "ARI", label: "Manual Burden Score", kind: "risk", value: invert(s.MAN), reading: "Entry, copying, reporting and chasing done by hand." },
    { code: "AOI", pillar: "ARI", label: "Automation Opportunity Index", kind: "score", value: blend(mix(s.REP, s.RUL), invert(s.MAN), 0.6, 0.4), reading: "Combined size of the automatable workload." },
    { code: "DMS", pillar: "DMI", label: "Digital Maturity Score", kind: "score", value: mix(s.ADO, s.DWF, s.INM), reading: "Software adoption, workflow digitisation and integration depth." },
    { code: "SDI", pillar: "DMI", label: "Spreadsheet Dependency Index", kind: "risk", value: invert(q("Q24")), reading: "Where a spreadsheet is still the system of record." },
    { code: "PRI", pillar: "DMI", label: "Paper Reliance Index", kind: "risk", value: invert(q("Q22")), reading: "Work that still begins or ends on paper." },
    { code: "DQS", pillar: "DII", label: "Data Quality Score", kind: "score", value: s.DQU, reading: "Missing, duplicated and erroneous data in operational records." },
    { code: "AMS", pillar: "DII", label: "Analytics Maturity Score", kind: "score", value: s.RPM, reading: "KPI discipline, dashboards and decision reporting." },
    { code: "DIS", pillar: "DII", label: "Decision Intelligence Score", kind: "score", value: mix(s.RPM, s.DQU, s.COL), reading: "How far decisions rest on facts rather than assumption." },
    { code: "ARS", pillar: "AIR", label: "AI Readiness Score", kind: "score", value: mix(s.CSV, s.KMA, s.PRD), reading: "Whether the organisation can absorb AI at all." },
    { code: "GAOI", pillar: "AIR", label: "Generative AI Opportunity Index", kind: "score", value: mix(s.KMA, s.CSV), reading: "Scope for generative AI in support and knowledge work." },
    { code: "PAOI", pillar: "AIR", label: "Predictive AI Opportunity Index", kind: "score", value: s.PRD, reading: "Scope for forecasting and predictive work." },
    { code: "TRS", pillar: "TII", label: "Technology Readiness Score", kind: "score", value: s.ECO, reading: "Whether the software estate can host new capability." },
    { code: "ICI", pillar: "TII", label: "Integration Complexity Index", kind: "risk", value: invert(s.INC), reading: "How hard systems are to connect and data to move." },
    { code: "SRS", pillar: "TII", label: "Security Readiness Score", kind: "score", value: s.SEC, reading: "Access control, recovery and governance strength." },
    { code: "SCS", pillar: "SSI", label: "Scalability Score", kind: "score", value: s.SCA, reading: "Whether growth requires proportional headcount." },
    { code: "GCI", pillar: "SSI", label: "Growth Constraint Index", kind: "risk", value: invert(s.GCA), reading: "Blockers that will slow the next stage of growth." },
    { code: "KPR", pillar: "SSI", label: "Key Person Risk Score", kind: "risk", value: invert(s.KPD), reading: "Concentration of knowledge and decisions in few people." },
  ].map((m) => ({ ...m, value: Math.round(clamp(m.value)) })) as MetricRow[];

  const aoi = metrics.find((m) => m.code === "AOI")?.value ?? 50;
  const riskAvg = avg(metrics.filter((m) => m.kind === "risk").map((m) => m.value));
  const composites = {
    currentState: Math.round(index),
    futureReadiness: Math.round(mix(p.SSI, p.AIR, p.TII)),
    risk: Math.round(riskAvg),
    opportunity: Math.round(aoi),
    efficiency: Math.round(p.OEI),
    automationPotential: Math.round(p.ARI),
    aiAdoption: Math.round(p.AIR),
    dataMaturity: Math.round(p.DII),
    techMaturity: Math.round(p.TII),
    transformationIndex: Math.round(index),
  };

  const sizeFactor = Math.max(0.45, Math.min(2.8, org.headcount / 140));
  const rate = org.hourlyRate;
  const payroll = org.headcount * rate * 2080;

  const painPoints: PainPoint[] = CATALOG.map((c) => {
    const score = questionScore(answers, c.code);
    if (score === null || score > 40) return null;
    const gap = (40 - score) / 40;
    const weekly = c.weeklyHours * (0.55 + gap * 0.7) * sizeFactor;
    const annual = weekly * 52 * rate * (0.35 + c.share);
    const investment = c.investment * sizeFactor;
    const roi = investment ? (annual - investment * 0.15) / investment : 0;
    const priority = Math.round(clamp((c.severity === "Critical" ? 30 : c.severity === "High" ? 18 : 8) + gap * 40 + (100 - score) * 0.2));
    return {
      code: c.code,
      title: c.title,
      problem: c.problem,
      impact: c.impact,
      solution: c.solution,
      automation: c.automation,
      severity: c.severity,
      complexity: c.complexity,
      priority,
      horizon: c.horizon,
      weeklyHours: Math.round(weekly),
      annualSavings: Math.round(annual),
      investment: Math.round(investment),
      roi,
      kpis: c.kpis,
    };
  })
    .filter((x): x is PainPoint => x !== null)
    .sort((a, b) => b.priority - a.priority);

  const gross = painPoints.reduce((s, x) => s + x.annualSavings, 0);
  const annualSavings = Math.min(gross, payroll * 0.22);
  const scale = gross > 0 ? annualSavings / gross : 1;
  for (const pnt of painPoints) pnt.annualSavings = Math.round(pnt.annualSavings * scale);

  const investment = painPoints.reduce((s, x) => s + x.investment, 0);
  const paybackMonths = annualSavings > 0 ? (investment / annualSavings) * 12 : 36;
  const roi3 = investment ? ((annualSavings * 3 - investment) / investment) * 100 : 0;
  const roi5 = investment ? ((annualSavings * 5 - investment) / investment) * 100 : 0;
  const productivityGain = clamp((aoi * 0.18 + invert(p.ARI ?? 50) * 0.12) / 2);
  const revenueLift = Math.round(org.annualRevenue * (0.012 + (100 - index) * 0.00035));

  const roadmap = HORIZONS.map((h) => {
    const items = painPoints.filter((x) => x.horizon === h.id);
    return {
      id: h.id,
      label: h.label,
      days: h.days,
      focus: h.focus,
      items,
      benefit: items.reduce((s, x) => s + x.annualSavings, 0),
      investment: items.reduce((s, x) => s + x.investment, 0),
    };
  });

  const industryAvg = INDUSTRY_BASE[org.industry] ?? 46;
  const sizeAdj = org.headcount < 30 ? -4 : org.headcount < 80 ? -1 : org.headcount < 300 ? 2 : 5;
  const sizeAvg = industryAvg + sizeAdj;
  const digitalAvg = industryAvg + 3;
  const automationAvg = industryAvg - 2;
  const aiAvg = industryAvg - 8;
  const percentile = clamp(Math.round(18 + (index - industryAvg) * 2.1 + 32));

  const pillarBench = pillars.map((pl, i) => ({
    code: pl.code,
    you: pl.score,
    industry: clamp(Math.round(industryAvg + [-2, 1, 3, 2, -6, 4, 0][i])),
    peers: clamp(Math.round(sizeAvg + [-1, 0, 2, 1, -5, 3, 1][i])),
  }));

  const confidence = clamp(55 + (answered / QUESTIONS.length) * 35 - (painPoints.filter((x) => x.severity === "Critical").length > 2 ? 8 : 0));

  return {
    index: Math.round(index),
    confidence: Math.round(confidence),
    maturity: { level: maturity.level, label: maturity.label, reading: maturity.reading },
    pillars,
    composites,
    metrics,
    answered,
    total: QUESTIONS.length,
    painPoints,
    roadmap,
    roi: {
      currency: org.currency,
      payroll: Math.round(payroll),
      annualSavings: Math.round(annualSavings),
      investment: Math.round(investment),
      netYear1: Math.round(annualSavings - investment),
      paybackMonths: Math.round(paybackMonths * 10) / 10,
      roi3: Math.round(roi3),
      roi5: Math.round(roi5),
      productivityGain: Math.round(productivityGain),
      revenueLift,
      threeYearValue: Math.round(annualSavings * 3 - investment),
      fiveYearValue: Math.round(annualSavings * 5 - investment),
      working: [
        `Headcount ${org.headcount} × ${org.currency} ${rate}/hour × 2,080 hours = payroll.`,
        `Triggered pain points produce modelled hours; savings are capped at 22% of payroll so the figure stays conservative.`,
        `Investment is the sum of recommended programmes, scaled to organisation size.`,
        `Payback is investment divided by annual savings. 3- and 5-year ROI compound the same savings with no heroic growth assumption.`,
      ],
    },
    benchmarks: {
      industry: org.industry,
      sizeBand: org.sizeBand,
      industryAvg,
      sizeAvg,
      digitalAvg,
      automationAvg,
      aiAvg,
      percentile,
      pillarBench,
    },
  };
}

export function livePartial(answers: Answers) {
  const org: OrgProfile = {
    name: "Live",
    industry: "Logistics",
    region: "Global",
    sizeBand: "mid",
    headcount: 140,
    annualRevenue: 12000000,
    hourlyRate: 18,
    currency: "USD",
  };
  return computeResult(answers, org);
}

export { MATURITY };
