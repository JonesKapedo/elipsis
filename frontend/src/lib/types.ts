export interface PillarsP {
  code: string;
  label: string;
  weight: number;
  objective: string;
}

export interface AssessmentResult {
  orgName: string;
  index: number;
  maturity: { label: string; level: number };
  composites: Record<string, number>;
  pillars: { code: string; label: string; score: number; pillarLabel: string }[];
  confidence: number;
  roi?: {
    annualSavings: number;
    netYear1: number;
    threeYearValue: number;
    fiveYearValue: number;
    paybackMonths: number;
    roi3: number;
    roi5: number;
    currency: string;
  };
  completedAt: string;
  roadmap: { id: string; label: string; days: string; focus: string; benefit: number; investment: number }[];
}
