import { SUBDOMAINS } from "./elipsis";
import { SCALES } from "./scales";

export type Question = {
  code: string;
  scale: string;
  subdomain: string;
  pillar: string;
  text: string;
  why: string;
  weight: number;
  evidence: boolean;
};

const Q = (
  code: string,
  scale: string,
  subdomain: string,
  text: string,
  why: string,
  weight: number,
  evidence = false,
): Question => {
  const sub = SUBDOMAINS.find((s) => s.code === subdomain);
  return { code, scale, subdomain, pillar: sub?.pillar ?? "OEI", text, why, weight, evidence };
};

export const QUESTIONS: Question[] = [
  Q("Q01", "coverage_more", "OPS", "Do you have written steps that show exactly how each main job is done?", "If the steps are not written down, every worker does the job differently and mistakes slip through.", 5, true),
  Q("Q02", "consistency_more", "OPS", "Is the same job done in the same way every time, by every team?", "When teams work differently, the work is harder to check and errors go unnoticed.", 4),
  Q("Q03", "ownership_more", "OPS", "Does every main job have one named person who is responsible for it?", "If nobody is responsible, a job is never improved, because no one gains from improving it.", 4),
  Q("Q04", "stepcount", "WFL", "How many separate steps does someone go through to finish one normal job?", "Every step adds waiting time and another chance for something to go wrong.", 4),
  Q("Q05", "approvals", "WFL", "How many different people must approve something before it can move on?", "Too many approvals is the most common reason work takes far longer than it should.", 5, true),
  Q("Q06", "waiting_less", "WFL", "When a job waits for the next person to act, how much of the total time is spent just waiting?", "Most delay is waiting, not working. Speeding up the work does not fix the waiting.", 5),
  Q("Q07", "idletime_less", "RSU", "How often are people sitting idle with nothing to do?", "People waiting for work are paid for nothing, while people who are overloaded make mistakes.", 4),
  Q("Q08", "overtime_less", "RSU", "How often does the business need people to work extra hours to finish the work?", "Extra hours are borrowed time. They fail exactly when you are busiest.", 4, true),
  Q("Q09", "balance_more", "RSU", "Is work spread fairly across teams, or is one team overloaded while another has nothing to do?", "The same business can be over-staffed and still be behind at the same time.", 3),
  Q("Q10", "repetition", "REP", "How many times a day or a week is the same work repeated?", "Work that repeats again and again is the cheapest and easiest work to hand to a machine.", 5),
  Q("Q11", "schedule_more", "REP", "Does that repeated work happen on a regular schedule?", "Work on a schedule can be given to software. Random work usually cannot.", 4),
  Q("Q12", "cover_less", "REP", "If the one person who does this work is away, does the work stop?", "One person doing all of it is both a chance to use software and a risk to your business.", 4),
  Q("Q13", "rules_more", "RUL", "Are the decisions your staff make written down as clear rules?", "Decisions that follow clear written rules are exactly the ones a computer can make.", 5),
  Q("Q14", "conditions_more", "RUL", "When there is a choice, are the conditions for each choice written down?", "Even simple if-this-then-that rules can be automated, once they are written down.", 4, true),
  Q("Q15", "exception_less", "RUL", "How often does normal work hit something unexpected that a person must decide?", "Too many surprises puts a limit on how much can ever be automated.", 4),
  Q("Q16", "effort_less", "MAN", "How much of the day is spent typing information into computers by hand?", "Typing the same information again and again is the easiest work to replace with software.", 5),
  Q("Q17", "copying_less", "MAN", "How often is information copied from one place and pasted into another?", "Copying and pasting is where wrong numbers quietly get in.", 5, true),
  Q("Q18", "effort_less", "MAN", "How much time is spent making reports by hand and chasing people for answers?", "Reports and chasing are big jobs, very boring, and follow the same rules every time.", 5),
  Q("Q19", "software_count", "ADO", "How many parts of the business use their own special software, rather than just general tools like Word and Excel?", "Special software is the ground that any later automation has to stand on.", 4),
  Q("Q20", "share_more", "ADO", "How much of that software is rented online, rather than installed on your own computers?", "Online software is what makes it possible to connect things and work from anywhere.", 4),
  Q("Q21", "outage_less", "ADO", "If one important system, or one important person, became unavailable, would the business stop?", "Anything the business cannot survive without is a limit on what you can change later.", 4, true),
  Q("Q22", "paper_less", "DWF", "How much of the daily work still starts or ends on paper?", "Paper means the work has not been moved into a computer at all.", 4),
  Q("Q23", "email_less", "DWF", "How much of the daily arranging and agreeing still happens over email?", "Email is a record of what was said. It does not check anything and it does no work for you.", 4),
  Q("Q24", "spreadsheet_less", "DWF", "How often is a spreadsheet the official record for an important job?", "When a spreadsheet is the official record, the business finds it hard to grow bigger.", 5, true),
  Q("Q25", "integration_more", "INM", "How many of your systems automatically pass information to each other?", "Systems must talk to each other before anything can be automated from start to finish.", 4),
  Q("Q26", "integration_more", "INM", "How many of your systems pass information to other systems on their own, without a person moving it?", "If a person has to move the information, the systems are not really connected.", 4),
  Q("Q27", "integration_more", "INM", "How many of your systems have clear, documented ways for other systems to connect to them?", "With no documented way in, there can be no connection, and so no automation.", 5, true),
  Q("Q28", "consistency_more", "COL", "Is the same information always collected in the same way?", "If it is collected differently each time, every number afterwards can be argued about.", 4),
  Q("Q29", "ownership_more", "COL", "Is it clear who is responsible for the quality of each important set of information?", "Information nobody is responsible for quietly gets worse, until someone decides using it.", 4, true),
  Q("Q30", "captured_more", "COL", "Is information recorded automatically while the work is being done?", "Information recorded at the time is complete. Information written down later is guessed.", 4),
  Q("Q31", "dataquality_less", "DQU", "How often is important information simply missing?", "Missing information becomes a blind spot in every decision made without it.", 4),
  Q("Q32", "dataquality_less", "DQU", "How often does the same customer, supplier or item appear twice as two separate records?", "Duplicates split the history and quietly make totals wrong.", 4),
  Q("Q33", "dataquality_less", "DQU", "How often are mistakes found in the numbers only after they have already been reported or acted on?", "Late mistakes mean decisions were made on numbers that were already wrong.", 5, true),
  Q("Q34", "kpi_more", "RPM", "Are a small number of agreed measures tracked the same way every time?", "What is not measured never improves, and cannot be automated either.", 4),
  Q("Q35", "dashboard_more", "RPM", "Can a manager see live results on a screen, without asking anyone for a report?", "A screen that has to be requested is just a slow report.", 4, true),
  Q("Q36", "reliability_more", "RPM", "Do management reports arrive on the same reliable day every month?", "Late reporting turns decisions into reactions.", 4),
  Q("Q37", "volume_count", "CSV", "How many customer questions or complaints do you receive in a normal week?", "The volume decides whether self-service or AI is worth building.", 4),
  Q("Q38", "coverage_more", "CSV", "Are the most common customer questions already written down with clear answers?", "A good list of common questions and answers is the cheapest AI tool you can build.", 4, true),
  Q("Q39", "repeats_count", "CSV", "How many of those questions are the same every time?", "Questions that repeat are easy to handle automatically. Difficult ones are not.", 4),
  Q("Q40", "knowledge_more", "KMA", "Is there one central place where all your written procedures and company knowledge are kept?", "Without one central place, AI has nothing reliable to read and staff keep reinventing work.", 5, true),
  Q("Q41", "coverage_more", "KMA", "Is the information in that place up to date and complete?", "Outdated instructions are worse than none, because people trust them and follow them.", 4),
  Q("Q42", "speed_more", "KMA", "How quickly can a new employee find the answer to an ordinary question?", "How fast an answer is found is the real test of whether the knowledge is useful.", 4),
  Q("Q43", "planning_more", "PRD", "How much does the business plan ahead, and how far into the future?", "Where there is no planning today, AI prediction has the most room to help.", 4),
  Q("Q44", "planning_more", "PRD", "How is future demand worked out, and how far ahead is it worked out?", "Planning only a short way ahead turns shortages into overtime and lost sales.", 5, true),
  Q("Q45", "databased_more", "PRD", "How much of sales forecasting is based on real data rather than opinion?", "A forecast built on opinion cannot be improved by a better model.", 4),
  Q("Q46", "core_system_more", "ECO", "Do you have one main computer system that holds all the official records?", "Without a main system there is nothing trustworthy for automation to sit on.", 5, true),
  Q("Q47", "software_count", "ECO", "Do you have dedicated systems for customers, sales points and operations, or only general tools?", "Very few specialist systems usually means the processes were never properly defined.", 4),
  Q("Q48", "fit_more", "ECO", "Do your current systems actually support the work they are meant to do?", "Software that is bought but never used is one of the most common hidden costs.", 4),
  Q("Q49", "integration_more", "INC", "How many of your systems let other systems connect to them through a documented method?", "A documented way in is the difference between connecting things and rebuilding everything.", 5, true),
  Q("Q50", "share_more", "INC", "How much of the information in your systems can other systems read?", "Information that cannot be reached cannot be connected, however good the records are.", 4),
  Q("Q51", "blockers_less", "INC", "How many known problems stop your systems from being connected to each other?", "Every connection problem is a permanent extra cost on all future automation.", 4),
  Q("Q52", "security_more", "SEC", "Who can get into your systems, and is that list checked and removed often?", "Automation inherits whatever access you already have, including the problems.", 5, true),
  Q("Q53", "restore_more", "SEC", "If you lost everything today, how quickly could you get working again, and have you tested that it works?", "A backup that was never tested is a hope, not a plan.", 5, true),
  Q("Q54", "security_more", "SEC", "Are the rules about who owns IT and information written down and clear?", "Clear rules stop unofficial systems from quietly becoming the real system.", 4),
  Q("Q55", "growth_more", "SCA", "When the business grows, does it produce more without hiring many more people?", "If every increase needs more staff, costs grow exactly as fast as revenue.", 5),
  Q("Q56", "headroom_more", "SCA", "How much more work could the business take on before it runs out of capacity?", "How much room is left tells you how long the current way of working will hold.", 4, true),
  Q("Q57", "outage_less", "SCA", "How well does the business cope when the work suddenly doubles?", "How the business handles a surprise shows what is strong and what is a bottleneck.", 4),
  Q("Q58", "keyperson_less", "KPD", "If one or two key people were unavailable tomorrow, could the business still run?", "Too much knowledge in too few people is both the biggest cost and the biggest risk.", 5, true),
  Q("Q59", "concentration_less", "KPD", "Are the important decisions all made by the same one or two people?", "If every decision waits for one person, growth waits for that person too.", 5),
  Q("Q60", "succession_more", "KPD", "Have other people been trained to cover the most important jobs?", "Cover turns a serious risk into a small inconvenience.", 4),
  Q("Q61", "blocker_less", "GCA", "How much does the way you work today stop the business from growing?", "Limits in daily operations are usually invisible until you hit them.", 5),
  Q("Q62", "blocker_less", "GCA", "How much do technology problems stop the business from growing?", "Technology limits are usually cheaper to fix than people expect.", 4),
  Q("Q63", "blocker_less", "GCA", "How much does the way jobs are done stop the business from growing?", "A process that cannot handle more customers will break before the technology does.", 4),
];

export const SEGMENTS = SUBDOMAINS.map((sub, i) => ({
  index: i,
  ...sub,
  questions: QUESTIONS.filter((q) => q.subdomain === sub.code),
}));

export function optionsFor(question: Question) {
  return SCALES[question.scale] ?? SCALES.share_more;
}
