import type { Answers, OrgProfile } from "./engine";
import { QUESTIONS } from "./questions";

export const SAMPLE_ORG: OrgProfile = {
  name: "Meridian Logistics Group",
  industry: "Logistics",
  region: "East Africa",
  sizeBand: "mid",
  headcount: 186,
  annualRevenue: 14200000,
  hourlyRate: 16,
  currency: "USD",
};

/** Mid-market operator: strong people, weak systems. Plenty of automation ROI. */
export const SAMPLE_ANSWERS: Answers = {
  Q01: 1, Q02: 2, Q03: 1, Q04: 1, Q05: 1, Q06: 1, Q07: 2, Q08: 1, Q09: 2,
  Q10: 4, Q11: 3, Q12: 1, Q13: 1, Q14: 1, Q15: 2, Q16: 1, Q17: 0, Q18: 1,
  Q19: 2, Q20: 2, Q21: 1, Q22: 1, Q23: 1, Q24: 0, Q25: 1, Q26: 1, Q27: 0,
  Q28: 2, Q29: 1, Q30: 1, Q31: 2, Q32: 2, Q33: 1, Q34: 2, Q35: 1, Q36: 2,
  Q37: 4, Q38: 1, Q39: 4, Q40: 1, Q41: 1, Q42: 1, Q43: 2, Q44: 1, Q45: 1,
  Q46: 2, Q47: 2, Q48: 2, Q49: 1, Q50: 1, Q51: 1, Q52: 2, Q53: 1, Q54: 2,
  Q55: 1, Q56: 1, Q57: 2, Q58: 1, Q59: 1, Q60: 1, Q61: 1, Q62: 2, Q63: 1,
};

export function fillMissing(answers: Answers): Answers {
  const next = { ...answers };
  for (const q of QUESTIONS) {
    if (next[q.code] === undefined) next[q.code] = 2;
  }
  return next;
}
