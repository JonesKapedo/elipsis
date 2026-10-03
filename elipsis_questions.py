"""ORG-001 question bank — shared by every transport layer.

Generalised from the original finance-only FIN-001 instrument: the questions
are now organisation-wide and map onto the seven Elipsis pillars (nine
questions each), so the same assessment works for any department.

WRITING RULES for every question in this file:

1. **Plain language.** Short sentences, no jargon, no consulting words. The
   intended respondent may have no business or IT background. A question must
   be answerable by someone who has simply worked in the organisation.
2. **One idea per question.** Never ask about two things at once.
3. **`why` explains the point.** It says what this question is trying to find
   out and why the leader should care, in the same simple language.
4. **Options fit the question.** Each question names a scale in
   `constants.SCALES` — a ladder of counts, speeds or frequencies that suits
   what is being asked, rather than one universal Never->Always ladder. Every
   scale is authored so its highest option means "most ready", which is what
   lets the scoring engine treat all answers identically.

Each entry is a dict with:
    code              stable question code (Q01..Q63) referenced by reports
    scale             the answer scale this question uses (constants.SCALES),
                      chosen so the options fit what the question actually asks
    subdomain         subdomain code from constants.SUBDOMAINS
    text              the question shown to the respondent
    why               why this is being asked, and why it matters
    weight            3-5, relative importance inside the pillar
    evidence_required whether an evidence grade is asked for

The pillar is derived from the subdomain so it can never drift out of sync.
The form is presented one subdomain at a time (three questions per segment),
which keeps a 63-question form from feeling like one long chore.
"""

from typing import Any

from constants import (
    QUESTIONNAIRE_CODE,
    QUESTIONNAIRE_NAME,
    QUESTIONNAIRE_VERSION,
    SUBDOMAIN_PILLAR,
)

QUESTIONNAIRE: dict[str, Any] = dict(
    code=QUESTIONNAIRE_CODE,
    name=QUESTIONNAIRE_NAME,
    version=QUESTIONNAIRE_VERSION,
    department="Organisation",
    estimated_minutes=25,
)

QUESTIONS: list[dict[str, Any]] = [
    # --- Pillar 1: Operational Efficiency Intelligence ----------------------
    # Process Standardisation
    dict(code="Q01", scale="coverage_more", subdomain="OPS",
         text="Do you have written steps that show exactly how each main job is done?",
         why="If the steps are not written down, every worker does the job differently "
             "and mistakes slip through.",
         weight=5, evidence_required=True),
    dict(code="Q02", scale="consistency_more", subdomain="OPS",
         text="Is the same job done in the same way every time, by every team?",
         why="When teams work differently, the work is harder to check and errors go unnoticed.",
         weight=4, evidence_required=False),
    dict(code="Q03", scale="ownership_more", subdomain="OPS",
         text="Does every main job have one named person who is responsible for it?",
         why="If nobody is responsible, a job is never improved, because no one gains "
             "from improving it.",
         weight=4, evidence_required=False),
    # Workflow Efficiency
    dict(code="Q04", scale="stepcount", subdomain="WFL",
         text="How many separate steps does someone go through to finish one normal job?",
         why="Every step adds waiting time and another chance for something to go wrong.",
         weight=4, evidence_required=False),
    dict(code="Q05", scale="approvals", subdomain="WFL",
         text="How many different people must approve something before it can move on?",
         why="Too many approvals is the most common reason work takes far longer than it should.",
         weight=5, evidence_required=True),
    dict(code="Q06", scale="waiting_less", subdomain="WFL",
         text="When a job waits for the next person to act, how much of the total time "
              "is spent just waiting?",
         why="Most delay is waiting, not working. Speeding up the work does not fix the waiting.",
         weight=5, evidence_required=False),
    # Resource Utilisation
    dict(code="Q07", scale="idletime_less", subdomain="RSU",
         text="How often are people sitting idle with nothing to do?",
         why="People waiting for work are paid for nothing, while people who are overloaded make mistakes.",
         weight=4, evidence_required=False),
    dict(code="Q08", scale="overtime_less", subdomain="RSU",
         text="How often does the business need people to work extra hours to finish the work?",
         why="Extra hours are borrowed time. They fail exactly when you are busiest.",
         weight=4, evidence_required=True),
    dict(code="Q09", scale="balance_more", subdomain="RSU",
         text="Is work spread fairly across teams, or is one team overloaded while another has nothing to do?",
         why="The same business can be over-staffed and still be behind at the same time.",
         weight=3, evidence_required=False),

    # --- Pillar 2: Automation Readiness Intelligence -----------------------
    # Repetition Analysis
    dict(code="Q10", scale="repetition", subdomain="REP",
         text="How many times a day or a week is the same work repeated?",
         why="Work that repeats again and again is the cheapest and easiest work to hand to a machine.",
         weight=5, evidence_required=False),
    dict(code="Q11", scale="schedule_more", subdomain="REP",
         text="Does that repeated work happen on a regular schedule?",
         why="Work on a schedule can be given to software. Random work usually cannot.",
         weight=4, evidence_required=False),
    dict(code="Q12", scale="cover_less", subdomain="REP",
         text="If the one person who does this work is away, does the work stop?",
         why="One person doing all of it is both a chance to use software and a risk to your business.",
         weight=4, evidence_required=False),
    # Rule-Based Decision Analysis
    dict(code="Q13", scale="rules_more", subdomain="RUL",
         text="Are the decisions your staff make written down as clear rules?",
         why="Decisions that follow clear written rules are exactly the ones a computer can make.",
         weight=5, evidence_required=False),
    dict(code="Q14", scale="conditions_more", subdomain="RUL",
         text="When there is a choice, are the conditions for each choice written down?",
         why="Even 'if this then that' rules can be automated, once they are written down.",
         weight=4, evidence_required=True),
    dict(code="Q15", scale="exception_less", subdomain="RUL",
         text="How often does normal work hit something unexpected that a person must decide?",
         why="Too many surprises puts a limit on how much can ever be automated.",
         weight=4, evidence_required=False),
    # Manual Effort Analysis
    dict(code="Q16", scale="effort_less", subdomain="MAN",
         text="How much of the day is spent typing information into computers by hand?",
         why="Typing the same information again and again is the easiest work to replace with software.",
         weight=5, evidence_required=False),
    dict(code="Q17", scale="copying_less", subdomain="MAN",
         text="How often is information copied from one place and pasted into another?",
         why="Copying and pasting is where wrong numbers quietly get in.",
         weight=5, evidence_required=True),
    dict(code="Q18", scale="effort_less", subdomain="MAN",
         text="How much time is spent making reports by hand and chasing people for answers?",
         why="Reports and chasing are big jobs, very boring, and follow the same rules every time.",
         weight=5, evidence_required=False),
    # --- Pillar 3: Digital Maturity Intelligence ---------------------------
    # Technology Adoption
    dict(code="Q19", scale="software_count", subdomain="ADO",
         text="How many parts of the business use their own special software, rather than "
              "just general tools like Word and Excel?",
         why="Special software is the ground that any later automation has to stand on.",
         weight=4, evidence_required=False),
    dict(code="Q20", scale="share_more", subdomain="ADO",
         text="How much of that software is rented online, rather than installed on your own computers?",
         why="Online software is what makes it possible to connect things and work from anywhere.",
         weight=4, evidence_required=False),
    dict(code="Q21", scale="outage_less", subdomain="ADO",
         text="If one important system, or one important person, became unavailable, would the business stop?",
         why="Anything the business cannot survive without is a limit on what you can change later.",
         weight=4, evidence_required=True),
    # Digital Workflow Adoption
    dict(code="Q22", scale="paper_less", subdomain="DWF",
         text="How much of the daily work still starts or ends on paper?",
         why="Paper means the work has not been moved into a computer at all.",
         weight=4, evidence_required=False),
    dict(code="Q23", scale="email_less", subdomain="DWF",
         text="How much of the daily arranging and agreeing still happens over email?",
         why="Email is a record of what was said. It does not check anything and it does no work for you.",
         weight=4, evidence_required=False),
    dict(code="Q24", scale="spreadsheet_less", subdomain="DWF",
         text="How often is a spreadsheet the official record for an important job?",
         why="When a spreadsheet is the official record, the business finds it hard to grow bigger.",
         weight=5, evidence_required=True),
    # Integration Maturity
    dict(code="Q25", scale="integration_more", subdomain="INM",
         text="How many of your systems automatically pass information to each other?",
         why="Systems must talk to each other before anything can be automated from start to finish.",
         weight=4, evidence_required=False),
    dict(code="Q26", scale="integration_more", subdomain="INM",
         text="How many of your systems pass information to other systems on their own, without a person moving it?",
         why="If a person has to move the information, the systems are not really connected.",
         weight=4, evidence_required=False),
    dict(code="Q27", scale="integration_more", subdomain="INM",
         text="How many of your systems have clear, documented ways for other systems to connect to them?",
         why="With no documented way in, there can be no connection, and so no automation.",
         weight=5, evidence_required=True),

    # --- Pillar 4: Data Intelligence & Analytics ---------------------------
    # Data Collection
    dict(code="Q28", scale="consistency_more", subdomain="COL",
         text="Is the same information always collected in the same way?",
         why="If it is collected differently each time, every number afterwards can be argued about.",
         weight=4, evidence_required=False),
    dict(code="Q29", scale="ownership_more", subdomain="COL",
         text="Is it clear who is responsible for the quality of each important set of information?",
         why="Information nobody is responsible for quietly gets worse, until someone decides using it.",
         weight=4, evidence_required=True),
    dict(code="Q30", scale="captured_more", subdomain="COL",
         text="Is information recorded automatically while the work is being done?",
         why="Information recorded at the time is complete. Information written down later is guessed.",
         weight=4, evidence_required=False),
    # Data Quality
    dict(code="Q31", scale="dataquality_less", subdomain="DQU",
         text="How often is important information simply missing?",
         why="Missing information becomes a blind spot in every decision made without it.",
         weight=4, evidence_required=False),
    dict(code="Q32", scale="dataquality_less", subdomain="DQU",
         text="How often does the same customer, supplier or item appear twice as two separate records?",
         why="Duplicates split the history and quietly make totals wrong.",
         weight=4, evidence_required=False),
    dict(code="Q33", scale="dataquality_less", subdomain="DQU",
         text="How often are mistakes found in the numbers only after they have already been "
              "reported or acted on?",
         why="Late mistakes mean decisions were made on numbers that were already wrong.",
         weight=5, evidence_required=True),
    # Reporting Maturity
    dict(code="Q34", scale="kpi_more", subdomain="RPM",
         text="Are a small number of agreed measures tracked the same way every time?",
         why="What is not measured never improves, and cannot be automated either.",
         weight=4, evidence_required=False),
    dict(code="Q35", scale="dashboard_more", subdomain="RPM",
         text="Can a manager see live results on a screen, without asking anyone for a report?",
         why="A screen that has to be requested is just a slow report.",
         weight=4, evidence_required=True),
    dict(code="Q36", scale="reliability_more", subdomain="RPM",
         text="Do management reports arrive on the same reliable day every month?",
         why="Late reporting turns decisions into reactions.",
         weight=4, evidence_required=False),
    # --- Pillar 5: AI Readiness Intelligence -------------------------------
    # Customer Service Assessment
    dict(code="Q37", scale="volume_count", subdomain="CSV",
         text="How many customer questions or complaints do you receive in a normal week?",
         why="The volume decides whether self-service or AI is worth building.",
         weight=4, evidence_required=False),
    dict(code="Q38", scale="coverage_more", subdomain="CSV",
         text="Are the most common customer questions already written down with clear answers?",
         why="A good list of common questions and answers is the cheapest AI tool you can build.",
         weight=4, evidence_required=True),
    dict(code="Q39", scale="repeats_count", subdomain="CSV",
         text="How many of those questions are the same every time?",
         why="Questions that repeat are easy to handle automatically. Difficult ones are not.",
         weight=4, evidence_required=False),
    # Knowledge Management
    dict(code="Q40", scale="knowledge_more", subdomain="KMA",
         text="Is there one central place where all your written procedures and company knowledge are kept?",
         why="Without one central place, AI has nothing reliable to read and staff keep reinventing work.",
         weight=5, evidence_required=True),
    dict(code="Q41", scale="coverage_more", subdomain="KMA",
         text="Is the information in that place up to date and complete?",
         why="Outdated instructions are worse than none, because people trust them and follow them.",
         weight=4, evidence_required=False),
    dict(code="Q42", scale="speed_more", subdomain="KMA",
         text="How quickly can a new employee find the answer to an ordinary question?",
         why="How fast an answer is found is the real test of whether the knowledge is useful.",
         weight=4, evidence_required=False),
    # Predictive Opportunity
    dict(code="Q43", scale="planning_more", subdomain="PRD",
         text="How much does the business plan ahead, and how far into the future?",
         why="Where there is no planning today, AI prediction has the most room to help.",
         weight=4, evidence_required=False),
    dict(code="Q44", scale="planning_more", subdomain="PRD",
         text="How is future demand worked out, and how far ahead is it worked out?",
         why="Planning only a short way ahead turns shortages into overtime and lost sales.",
         weight=5, evidence_required=True),
    dict(code="Q45", scale="databased_more", subdomain="PRD",
         text="How much of sales forecasting is based on real data rather than opinion?",
         why="A forecast built on opinion cannot be improved by a better model.",
         weight=4, evidence_required=False),

    # --- Pillar 6: Technology & Integration Infrastructure -----------------
    # Software Ecosystem
    dict(code="Q46", scale="core_system_more", subdomain="ECO",
         text="Do you have one main computer system that holds all the official records?",
         why="Without a main system there is nothing trustworthy for automation to sit on.",
         weight=5, evidence_required=True),
    dict(code="Q47", scale="software_count", subdomain="ECO",
         text="Do you have dedicated systems for customers, sales points and operations, "
              "or only general tools?",
         why="Very few specialist systems usually means the processes were never properly defined.",
         weight=4, evidence_required=False),
    dict(code="Q48", scale="fit_more", subdomain="ECO",
         text="Do your current systems actually support the work they are meant to do?",
         why="Software that is bought but never used is one of the most common hidden costs.",
         weight=4, evidence_required=False),
    # Integration Capability
    dict(code="Q49", scale="integration_more", subdomain="INC",
         text="How many of your systems let other systems connect to them through a "
              "documented method?",
         why="A documented way in is the difference between connecting things and rebuilding everything.",
         weight=5, evidence_required=True),
    dict(code="Q50", scale="share_more", subdomain="INC",
         text="How much of the information in your systems can other systems read?",
         why="Information that cannot be reached cannot be connected, however good the records are.",
         weight=4, evidence_required=False),
    dict(code="Q51", scale="blockers_less", subdomain="INC",
         text="How many known problems stop your systems from being connected to each other?",
         why="Every connection problem is a permanent extra cost on all future automation.",
         weight=4, evidence_required=False),
    # Security Readiness
    dict(code="Q52", scale="security_more", subdomain="SEC",
         text="Who can get into your systems, and is that list checked and removed often?",
         why="Automation inherits whatever access you already have, including the problems.",
         weight=5, evidence_required=True),
    dict(code="Q53", scale="restore_more", subdomain="SEC",
         text="If you lost everything today, how quickly could you get working again, and have you tested that it works?",
         why="A backup that was never tested is a hope, not a plan.",
         weight=5, evidence_required=True),
    dict(code="Q54", scale="security_more", subdomain="SEC",
         text="Are the rules about who owns IT and information written down and clear?",
         why="Clear rules stop unofficial systems from quietly becoming the real system.",
         weight=4, evidence_required=False),
    # --- Pillar 7: Strategic Scalability Intelligence ----------------------
    # Scalability Assessment
    dict(code="Q55", scale="growth_more", subdomain="SCA",
         text="When the business grows, does it produce more without hiring many more people?",
         why="If every increase needs more staff, costs grow exactly as fast as revenue.",
         weight=5, evidence_required=False),
    dict(code="Q56", scale="headroom_more", subdomain="SCA",
         text="How much more work could the business take on before it runs out of capacity?",
         why="How much room is left tells you how long the current way of working will hold.",
         weight=4, evidence_required=True),
    dict(code="Q57", scale="outage_less", subdomain="SCA",
         text="How well does the business cope when the work suddenly doubles?",
         why="How the business handles a surprise shows what is strong and what is a bottleneck.",
         weight=4, evidence_required=False),
    # Key Person Dependency
    dict(code="Q58", scale="keyperson_less", subdomain="KPD",
         text="If one or two key people were unavailable tomorrow, could the business still run?",
         why="Too much knowledge in too few people is both the biggest cost and the biggest risk.",
         weight=5, evidence_required=True),
    dict(code="Q59", scale="concentration_less", subdomain="KPD",
         text="Are the important decisions all made by the same one or two people?",
         why="If every decision waits for one person, growth waits for that person too.",
         weight=5, evidence_required=False),
    dict(code="Q60", scale="succession_more", subdomain="KPD",
         text="Have other people been trained to cover the most important jobs?",
         why="Cover turns a serious risk into a small inconvenience.",
         weight=4, evidence_required=False),
    # Growth Constraint Analysis
    dict(code="Q61", scale="blocker_less", subdomain="GCA",
         text="How much does the way you work today stop the business from growing?",
         why="Limits in daily operations are usually invisible until you hit them.",
         weight=5, evidence_required=False),
    dict(code="Q62", scale="blocker_less", subdomain="GCA",
         text="How much do technology problems stop the business from growing?",
         why="Technology limits are usually cheaper to fix than people expect.",
         weight=4, evidence_required=False),
    dict(code="Q63", scale="blocker_less", subdomain="GCA",
         text="How much does the way jobs are done stop the business from growing?",
         why="A process that cannot handle more customers will break before the technology does.",
         weight=4, evidence_required=False),
]


def as_dicts() -> list[dict[str, Any]]:
    """Return the bank as dicts with a 1-based position, for seeding."""
    return [
        dict(code=q["code"], scale=q["scale"], subdomain=q["subdomain"],
             pillar=SUBDOMAIN_PILLAR[q["subdomain"]], text=q["text"],
             why=q["why"], weight=q["weight"],
             evidence_required=bool(q["evidence_required"]), position=pos)
        for pos, q in enumerate(QUESTIONS, start=1)
    ]


def segments() -> list[dict[str, Any]]:
    """Group the bank into short segments, one per subdomain (3 questions each).

    A 63-question form in one page is intimidating and boring. Presenting one
    subdomain at a time turns it into 21 short steps, each with its own live
    score, so the respondent sees progress and immediate feedback.

    Returns a list of dicts in instrument order.
    """
    order = []
    buckets = {}
    for q in QUESTIONS:
        code = q["subdomain"]
        if code not in buckets:
            buckets[code] = []
            order.append(code)
        buckets[code].append(q)
    return [
        dict(subdomain=code, pillar=SUBDOMAIN_PILLAR[code], questions=buckets[code])
        for code in order
    ]
