export const BRAND = {
  name: "Elipsis",
  mark: "⋯",
  tagline: "Measure. Transform. Scale.",
  long: "Turning operational flow into business power.",
};

export const PILLARS = [
  { code: "OEI", label: "Operational Efficiency", short: "Efficiency", weight: 0.2, objective: "Where work actually flows — and where it stalls." },
  { code: "ARI", label: "Automation Readiness", short: "Automation", weight: 0.25, objective: "What can be automated now, versus later, and at what return." },
  { code: "DMI", label: "Digital Maturity", short: "Digital", weight: 0.15, objective: "How digitally evolved the organisation actually is." },
  { code: "DII", label: "Data Intelligence", short: "Data", weight: 0.15, objective: "Whether decisions rest on facts or on assumptions." },
  { code: "AIR", label: "AI Readiness", short: "AI", weight: 0.1, objective: "Whether AI can create measurable business value." },
  { code: "TII", label: "Technology Infrastructure", short: "Technology", weight: 0.05, objective: "Whether the environment can host automation at all." },
  { code: "SSI", label: "Strategic Scalability", short: "Scale", weight: 0.1, objective: "Whether the business can grow without operational collapse." },
] as const;

export type PillarCode = (typeof PILLARS)[number]["code"];

export const SUBDOMAINS = [
  { code: "OPS", pillar: "OEI", label: "Process Standardisation" },
  { code: "WFL", pillar: "OEI", label: "Workflow Efficiency" },
  { code: "RSU", pillar: "OEI", label: "Resource Utilisation" },
  { code: "REP", pillar: "ARI", label: "Repetition Analysis" },
  { code: "RUL", pillar: "ARI", label: "Rule-Based Decisions" },
  { code: "MAN", pillar: "ARI", label: "Manual Effort" },
  { code: "ADO", pillar: "DMI", label: "Technology Adoption" },
  { code: "DWF", pillar: "DMI", label: "Digital Workflows" },
  { code: "INM", pillar: "DMI", label: "Integration Maturity" },
  { code: "COL", pillar: "DII", label: "Data Collection" },
  { code: "DQU", pillar: "DII", label: "Data Quality" },
  { code: "RPM", pillar: "DII", label: "Reporting Maturity" },
  { code: "CSV", pillar: "AIR", label: "Customer Service" },
  { code: "KMA", pillar: "AIR", label: "Knowledge Management" },
  { code: "PRD", pillar: "AIR", label: "Predictive Opportunity" },
  { code: "ECO", pillar: "TII", label: "Software Ecosystem" },
  { code: "INC", pillar: "TII", label: "Integration Capability" },
  { code: "SEC", pillar: "TII", label: "Security Readiness" },
  { code: "SCA", pillar: "SSI", label: "Scalability" },
  { code: "KPD", pillar: "SSI", label: "Key Person Dependency" },
  { code: "GCA", pillar: "SSI", label: "Growth Constraints" },
] as const;

export const MATURITY = [
  { level: 1, min: 0, max: 21, label: "Reactive", reading: "Work is firefighting. Process lives in people, not systems." },
  { level: 2, min: 21, max: 41, label: "Developing", reading: "Some structure exists, but it is uneven and easily broken." },
  { level: 3, min: 41, max: 61, label: "Structured", reading: "Core processes are defined. Automation can land without chaos." },
  { level: 4, min: 61, max: 81, label: "Optimized", reading: "Operations are measured and improving. Ready for scale automation." },
  { level: 5, min: 81, max: 101, label: "Transformative", reading: "The organisation can absorb AI and grow without proportional headcount." },
] as const;

export function maturityFor(score: number) {
  const s = Number.isFinite(score) ? score : 0;
  return MATURITY.find((b) => s >= b.min && s < b.max) ?? MATURITY[0];
}

export const HORIZONS = [
  { id: "30d", label: "30-Day Plan", days: 30, focus: "Stabilise and capture obvious waste." },
  { id: "90d", label: "90-Day Plan", days: 90, focus: "Automate repetitive, rule-based work." },
  { id: "6m", label: "6-Month Plan", days: 180, focus: "Rebuild the operating flow: approvals, integrations, controls." },
  { id: "12m", label: "12-Month Plan", days: 365, focus: "Institutionalise process automation across departments." },
  { id: "24m", label: "24-Month Plan", days: 730, focus: "Deploy predictive and generative AI on a clean base." },
] as const;

export const DEPARTMENTS = [
  "Operations",
  "Finance",
  "Human Resources",
  "Sales",
  "Marketing",
  "Customer Service",
  "Procurement",
  "Manufacturing",
  "Logistics",
  "IT",
  "Executive Leadership",
  "Compliance",
  "Data & Analytics",
  "Research & Development",
] as const;

export const INDUSTRIES = [
  "Logistics",
  "Financial Services",
  "Manufacturing",
  "Healthcare",
  "Retail",
  "Professional Services",
  "Telecommunications",
  "Energy",
  "Public Sector",
  "Technology",
  "Agriculture",
  "Hospitality",
] as const;

export const SIZE_BANDS = [
  { id: "micro", label: "1–20 people", headcount: 12 },
  { id: "small", label: "21–75 people", headcount: 45 },
  { id: "mid", label: "76–250 people", headcount: 140 },
  { id: "upper", label: "251–1,000 people", headcount: 420 },
  { id: "enterprise", label: "1,000+ people", headcount: 1800 },
] as const;

export const REGIONS = ["East Africa", "West Africa", "Southern Africa", "Europe", "North America", "Middle East", "Asia Pacific", "Global"] as const;

export const PLANS = [
  {
    id: "starter",
    name: "Starter",
    price: 0,
    blurb: "One organisation. One assessment. Executive snapshot.",
    features: ["ORG-001 instrument", "Elipsis Index", "3-phase snapshot", "Sample benchmarking"],
  },
  {
    id: "professional",
    name: "Professional",
    price: 2400,
    blurb: "Full intelligence chain for a single mid-market company.",
    features: ["Unlimited assessments", "Departmental analysis", "ROI forecast", "Roadmap + automation discovery", "Boardroom reports"],
  },
  {
    id: "business",
    name: "Business",
    price: 7800,
    blurb: "Multi-department programmes with comparison and advisor.",
    features: ["Everything in Professional", "AI Transformation Advisor", "Industry & size benchmarks", "Investment priority ranking", "Excel & print export"],
  },
  {
    id: "enterprise",
    name: "Enterprise",
    price: 24000,
    blurb: "Portfolio, white-label, and custom frameworks.",
    features: ["Multi-company assessments", "White-label reporting", "Custom frameworks", "API access", "Dedicated advisor context"],
  },
] as const;
