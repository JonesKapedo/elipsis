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
4. **The same answer scale everywhere** — see `constants.ANSWER_SCALE`.

Each entry is a dict with:
    code              stable question code (Q01..Q63) referenced by reports
    subdomain         subdomain code from constants.SUBDOMAINS
    text              the question shown to the respondent
    why               why this is being asked, and why it matters
    weight            3-5, relative importance inside the pillar
    evidence_required whether an evidence grade is asked for

The pillar is derived from the subdomain so it can never drift out of sync.
The form is presented one subdomain at a time (three questions per segment),
which keeps a 63-question form from feeling like one long chore.
"""

from constants import (
    QUESTIONNAIRE_CODE,
    QUESTIONNAIRE_NAME,
    QUESTIONNAIRE_VERSION,
    SUBDOMAIN_PILLAR,
)

QUESTIONNAIRE = dict(
    code=QUESTIONNAIRE_CODE,
    name=QUESTIONNAIRE_NAME,
    version=QUESTIONNAIRE_VERSION,
    department="Organisation",
    estimated_minutes=25,
)

QUESTIONS = [
    # --- Pillar 1: Operational Efficiency Intelligence ----------------------
    # Process Standardisation
    dict(code="Q01", subdomain="OPS",
         text="Do you have written steps that show exactly how each main job is done?",
         why="If the steps are not written down, every worker does the job differently "
             "and mistakes slip through.",
         weight=5, evidence_required=True),
    dict(code="Q02", subdomain="OPS",
         text="Is the same job done in the same way every time, by every team?",
         why="When teams work differently, the work is harder to check and errors go unnoticed.",
         weight=4, evidence_required=False),
    dict(code="Q03", subdomain="OPS",
         text="Does every main job have one named person who is responsible for it?",
         why="If nobody is responsible, a job is never improved, because no one gains "
             "from improving it.",
         weight=4, evidence_required=False),
    # Workflow Efficiency
    dict(code="Q04", subdomain="WFL",
         text="How many separate steps does someone go through to finish one normal job?",
         why="Every step adds waiting time and another chance for something to go wrong.",
         weight=4, evidence_required=False),
    dict(code="Q05", subdomain="WFL",
         text="How many different people must approve something before it can move on?",
         why="Too many approvals is the most common reason work takes far longer than it should.",
         weight=5, evidence_required=True),
    dict(code="Q06", subdomain="WFL",
         text="When a job waits for the next person to act, how much of the total time "
              "is spent just waiting?",
         why="Most delay is waiting, not working. Speeding up the work does not fix the waiting.",
         weight=5, evidence_required=False),
    # Resource Utilisation
    dict(code="Q07", subdomain="RSU",
         text="Are your people busy for most of the working day?",
         why="People waiting for work are paid for nothing, while people who are overloaded make mistakes.",
         weight=4, evidence_required=False),
    dict(code="Q08", subdomain="RSU",
         text="Does the business depend on people working extra hours to finish the work?",
         why="Extra hours are borrowed time. They fail exactly when you are busiest.",
         weight=4, evidence_required=True),
    dict(code="Q09", subdomain="RSU",
         text="Is work spread fairly across teams, or is one team overloaded while another has nothing to do?",
         why="The same business can be over-staffed and still be behind at the same time.",
         weight=3, evidence_required=False),

    # --- Pillar 2: Automation Readiness Intelligence -----------------------
    # Repetition Analysis
    dict(code="Q10", subdomain="REP",
         text="How many times a day or a week is the same work repeated?",
         why="Work that repeats again and again is the cheapest and easiest work to hand to a machine.",
         weight=5, evidence_required=False),
    dict(code="Q11", subdomain="REP",
         text="Does that repeated work happen on a regular schedule?",
         why="Work on a schedule can be given to software. Random work usually cannot.",
         weight=4, evidence_required=False),
    dict(code="Q12", subdomain="REP",
         text="Is that repeated work done by only one person?",
         why="One person doing all of it is both a chance to use software and a risk to your business.",
         weight=4, evidence_required=False),
    # Rule-Based Decision Analysis
    dict(code="Q13", subdomain="RUL",
         text="Are the decisions your staff make written down as clear rules?",
         why="Decisions that follow clear written rules are exactly the ones a computer can make.",
         weight=5, evidence_required=False),
    dict(code="Q14", subdomain="RUL",
         text="When there is a choice, are the conditions for each choice written down?",
         why="Even 'if this then that' rules can be automated, once they are written down.",
         weight=4, evidence_required=True),
    dict(code="Q15", subdomain="RUL",
         text="How often does normal work hit something unexpected that a person must decide?",
         why="Too many surprises puts a limit on how much can ever be automated.",
         weight=4, evidence_required=False),
    # Manual Effort Analysis
    dict(code="Q16", subdomain="MAN",
         text="How much of the day is spent typing information into computers by hand?",
         why="Typing the same information again and again is the easiest work to replace with software.",
         weight=5, evidence_required=False),
    dict(code="Q17", subdomain="MAN",
         text="How often is information copied from one place and pasted into another?",
         why="Copying and pasting is where wrong numbers quietly get in.",
         weight=5, evidence_required=True),
    dict(code="Q18", subdomain="MAN",
         text="How much time is spent making reports by hand and chasing people for answers?",
         why="Reports and chasing are big jobs, very boring, and follow the same rules every time.",
         weight=5, evidence_required=False),
    # --- Pillar 3: Digital Maturity Intelligence ---------------------------
    # Technology Adoption
    dict(code="Q19", subdomain="ADO",
         text="How many parts of the business use their own special software, rather than "
              "just general tools like Word and Excel?",
         why="Special software is the ground that any later automation has to stand on.",
         weight=4, evidence_required=False),
    dict(code="Q20", subdomain="ADO",
         text="How much of that software is rented online, rather than installed on your own computers?",
         why="Online software is what makes it possible to connect things and work from anywhere.",
         weight=4, evidence_required=False),
    dict(code="Q21", subdomain="ADO",
         text="If one important system, or one important person, became unavailable, would the business stop?",
         why="Anything the business cannot survive without is a limit on what you can change later.",
         weight=4, evidence_required=True),
    # Digital Workflow Adoption
    dict(code="Q22", subdomain="DWF",
         text="How much of the daily work still starts or ends on paper?",
         why="Paper means the work has not been moved into a computer at all.",
         weight=4, evidence_required=False),
    dict(code="Q23", subdomain="DWF",
         text="How much of the daily arranging and agreeing still happens over email?",
         why="Email is a record of what was said. It does not check anything and it does no work for you.",
         weight=4, evidence_required=False),
    dict(code="Q24", subdomain="DWF",
         text="How often is a spreadsheet the official record for an important job?",
         why="When a spreadsheet is the official record, the business finds it hard to grow bigger.",
         weight=5, evidence_required=True),
    # Integration Maturity
    dict(code="Q25", subdomain="INM",
         text="How many of your systems automatically pass information to each other?",
         why="Systems must talk to each other before anything can be automated from start to finish.",
         weight=4, evidence_required=False),
    dict(code="Q26", subdomain="INM",
         text="Does information move between systems without someone typing it or copying a file?",
         why="If a person has to move the information, the systems are not really connected.",
         weight=4, evidence_required=False),
    dict(code="Q27", subdomain="INM",
         text="Can your systems talk to each other through clear, documented connections?",
         why="With no documented way in, there can be no connection, and so no automation.",
         weight=5, evidence_required=True),

    # --- Pillar 4: Data Intelligence & Analytics ---------------------------
    # Data Collection
    dict(code="Q28", subdomain="COL",
         text="Is the same information always collected in the same way?",
         why="If it is collected differently each time, every number afterwards can be argued about.",
         weight=4, evidence_required=False),
    dict(code="Q29", subdomain="COL",
         text="Is it clear who is responsible for the quality of each important set of information?",
         why="Information nobody is responsible for quietly gets worse, until someone decides using it.",
         weight=4, evidence_required=True),
    dict(code="Q30", subdomain="COL",
         text="Is information recorded automatically while the work is being done?",
         why="Information recorded at the time is complete. Information written down later is guessed.",
         weight=4, evidence_required=False),
    # Data Quality
    dict(code="Q31", subdomain="DQU",
         text="How often is important information simply missing?",
         why="Missing information becomes a blind spot in every decision made without it.",
         weight=4, evidence_required=False),
    dict(code="Q32", subdomain="DQU",
         text="How often does the same customer, supplier or item appear twice as two separate records?",
         why="Duplicates split the history and quietly make totals wrong.",
         weight=4, evidence_required=False),
    dict(code="Q33", subdomain="DQU",
         text="How often are mistakes found in the numbers only after they have already been "
              "reported or acted on?",
         why="Late mistakes mean decisions were made on numbers that were already wrong.",
         weight=5, evidence_required=True),
    # Reporting Maturity
    dict(code="Q34", subdomain="RPM",
         text="Are a small number of agreed measures tracked the same way every time?",
         why="What is not measured never improves, and cannot be automated either.",
         weight=4, evidence_required=False),
    dict(code="Q35", subdomain="RPM",
         text="Can a manager see live results on a screen, without asking anyone for a report?",
         why="A screen that has to be requested is just a slow report.",
         weight=4, evidence_required=True),
    dict(code="Q36", subdomain="RPM",
         text="Do management reports arrive on the same reliable day every month?",
         why="Late reporting turns decisions into reactions.",
         weight=4, evidence_required=False),
    # --- Pillar 5: AI Readiness Intelligence -------------------------------
    # Customer Service Assessment
    dict(code="Q37", subdomain="CSV",
         text="How many customer questions or complaints do you receive in a normal week?",
         why="The volume decides whether self-service or AI is worth building.",
         weight=4, evidence_required=False),
    dict(code="Q38", subdomain="CSV",
         text="Are the most common customer questions already written down with clear answers?",
         why="A good list of common questions and answers is the cheapest AI tool you can build.",
         weight=4, evidence_required=True),
    dict(code="Q39", subdomain="CSV",
         text="How many of those questions are the same every time?",
         why="Questions that repeat are easy to handle automatically. Difficult ones are not.",
         weight=4, evidence_required=False),
    # Knowledge Management
    dict(code="Q40", subdomain="KMA",
         text="Is there one central place where all your SOPs and company knowledge are kept?",
         why="Without one central place, AI has nothing reliable to read and staff keep reinventing work.",
         weight=5, evidence_required=True),
    dict(code="Q41", subdomain="KMA",
         text="Is the information in that place up to date and complete?",
         why="Outdated instructions are worse than none, because people trust them and follow them.",
         weight=4, evidence_required=False),
    dict(code="Q42", subdomain="KMA",
         text="How quickly can a new employee find the answer to an ordinary question?",
         why="How fast an answer is found is the real test of whether the knowledge is useful.",
         weight=4, evidence_required=False),
    # Predictive Opportunity
    dict(code="Q43", subdomain="PRD",
         text="How much does the business plan ahead, and how far into the future?",
         why="Where there is no planning today, AI prediction has the most room to help.",
         weight=4, evidence_required=False),
    dict(code="Q44", subdomain="PRD",
         text="How is future demand worked out, and how far ahead is it worked out?",
         why="Planning only a short way ahead turns shortages into overtime and lost sales.",
         weight=5, evidence_required=True),
    dict(code="Q45", subdomain="PRD",
         text="How much of sales forecasting is based on real data rather than opinion?",
         why="A forecast built on opinion cannot be improved by a better model.",
         weight=4, evidence_required=False),

    # --- Pillar 6: Technology & Integration Infrastructure -----------------
    # Software Ecosystem
    dict(code="Q46", subdomain="ECO",
         text="Do you have one main system that holds the official records, such as an ERP system?",
         why="Without a main system there is nothing trustworthy for automation to sit on.",
         weight=5, evidence_required=True),
    dict(code="Q47", subdomain="ECO",
         text="Do you have dedicated systems for customers, sales points and operations, "
              "or only general tools?",
         why="Very few specialist systems usually means the processes were never properly defined.",
         weight=4, evidence_required=False),
    dict(code="Q48", subdomain="ECO",
         text="Do your current systems actually support the work they are meant to do?",
         why="Software that is bought but never used is one of the most common hidden costs.",
         weight=4, evidence_required=False),
    # Integration Capability
    dict(code="Q49", subdomain="INC",
         text="How many of your systems let other systems connect to them through a "
              "documented method?",
         why="A documented way in is the difference between connecting things and rebuilding everything.",
         weight=5, evidence_required=True),
    dict(code="Q50", subdomain="INC",
         text="Can information inside your systems be reached by your other systems?",
         why="Information that cannot be reached cannot be connected, however good the records are.",
         weight=4, evidence_required=False),
    dict(code="Q51", subdomain="INC",
         text="How many known problems stop your systems from being connected to each other?",
         why="Every connection problem is a permanent extra cost on all future automation.",
         weight=4, evidence_required=False),
    # Security Readiness
    dict(code="Q52", subdomain="SEC",
         text="Who can get into your systems, and is that list checked and removed often?",
         why="Automation inherits whatever access you already have, including the problems.",
         weight=5, evidence_required=True),
    dict(code="Q53", subdomain="SEC",
         text="Are your backups up to date, and has anyone recently restored from one successfully?",
         why="A backup that was never tested is a hope, not a plan.",
         weight=5, evidence_required=True),
    dict(code="Q54", subdomain="SEC",
         text="Are the rules about who owns IT and information written down and clear?",
         why="Clear rules stop unofficial systems from quietly becoming the real system.",
         weight=4, evidence_required=False),
    # --- Pillar 7: Strategic Scalability Intelligence ----------------------
    # Scalability Assessment
    dict(code="Q55", subdomain="SCA",
         text="When the business grows, does it produce more without hiring many more people?",
         why="If every increase needs more staff, costs grow exactly as fast as revenue.",
         weight=5, evidence_required=False),
    dict(code="Q56", subdomain="SCA",
         text="How much more work can the business take on before it runs out of capacity?",
         why="How much room is left tells you how long the current way of working will hold.",
         weight=4, evidence_required=True),
    dict(code="Q57", subdomain="SCA",
         text="How well does the business cope when the work suddenly doubles?",
         why="How the business handles a surprise shows what is strong and what is a bottleneck.",
         weight=4, evidence_required=False),
    # Key Person Dependency
    dict(code="Q58", subdomain="KPD",
         text="If one or two key people were unavailable tomorrow, could the business still run?",
         why="Too much knowledge in too few people is both the biggest cost and the biggest risk.",
         weight=5, evidence_required=True),
    dict(code="Q59", subdomain="KPD",
         text="Are the important decisions all made by the same one or two people?",
         why="If every decision waits for one person, growth waits for that person too.",
         weight=5, evidence_required=False),
    dict(code="Q60", subdomain="KPD",
         text="Have other people been trained to cover the most important jobs?",
         why="Cover turns a serious risk into a small inconvenience.",
         weight=4, evidence_required=False),
    # Growth Constraint Analysis
    dict(code="Q61", subdomain="GCA",
         text="How much does the way you work today stop the business from growing?",
         why="Limits in daily operations are usually invisible until you hit them.",
         weight=5, evidence_required=False),
    dict(code="Q62", subdomain="GCA",
         text="How much do technology problems stop the business from growing?",
         why="Technology limits are usually cheaper to fix than people expect.",
         weight=4, evidence_required=False),
    dict(code="Q63", subdomain="GCA",
         text="How much does the way jobs are done stop the business from growing?",
         why="A process that cannot handle more customers will break before the technology does.",
         weight=4, evidence_required=False),
]


def as_dicts():
    """Return the bank as dicts with a 1-based position, for seeding."""
    return [
        dict(code=q["code"], subdomain=q["subdomain"],
             pillar=SUBDOMAIN_PILLAR[q["subdomain"]], text=q["text"],
             why=q["why"], weight=q["weight"],
             evidence_required=bool(q["evidence_required"]), position=pos)
        for pos, q in enumerate(QUESTIONS, start=1)
    ]


def segments():
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
