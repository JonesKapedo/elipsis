"""Shared questionnaire collect + company assess/share routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from elipsis_api import models, services
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user, login_redirect, templates

router = APIRouter()


def _new_token() -> str:
    from elipsis_api import security
    return security.new_token()


def _campaign_open(c: models.CollectCampaign) -> bool:
    if c is None or c.status not in ("collecting",):
        return False
    if c.deadline:
        from datetime import datetime
        try:
            end = datetime.fromisoformat(c.deadline.replace("Z", ""))
            if datetime.utcnow() > end:
                return False
        except Exception:
            pass
    return True


def _count_completed(db: Session, token: str) -> int:
    return int(db.scalar(select(func.count()).select_from(models.CollectResponse).where(
        models.CollectResponse.campaign_token == token,
        models.CollectResponse.status == "completed")) or 0)


def _maybe_finalize_campaign(db: Session, campaign: models.CollectCampaign):
    if campaign.status == "reported" and campaign.master_assessment_id:
        return campaign.master_assessment_id
    completed = _count_completed(db, campaign.token)
    if completed < (campaign.min_respondents or 1):
        return None
    rows = list(db.scalars(select(models.CollectResponse).where(
        models.CollectResponse.campaign_token == campaign.token,
        models.CollectResponse.status == "completed")))
    if not rows:
        return None
    from collections import defaultdict
    score_sum: dict[int, list[int]] = defaultdict(list)
    evidence_pick: dict[int, str] = {}
    for r in rows:
        for ans in db.scalars(select(models.Answer).where(
                models.Answer.assessment_id == r.assessment_id)):
            if ans.score is not None:
                score_sum[ans.question_id].append(int(ans.score))
                evidence_pick.setdefault(ans.question_id, ans.evidence or "none")
    bank = services.get_bank(db)
    if bank is None:
        return None
    from elipsis_api.services_core import _now
    master = models.Assessment(
        organization_id=campaign.organization_id,
        department_id=campaign.department_id,
        questionnaire_id=bank.id,
        respondent=f"Team aggregate ({completed} responses)",
        status="in_progress",
        started_at=_now(),
    )
    db.add(master)
    db.flush()
    from elipsis_api import schemas as _schemas
    answers = []
    for qid, scores in score_sum.items():
        avg = int(round(sum(scores) / len(scores)))
        avg = max(0, min(5, avg))
        answers.append(_schemas.AnswerIn(
            question_id=qid, score=avg, evidence=evidence_pick.get(qid, "none")))
    services.submit(db, master.id, answers)
    campaign.master_assessment_id = master.id
    campaign.status = "reported"
    db.commit()
    return master.id


@router.post("/company/{organization_id}/assess")
def company_assess(organization_id: int, request: Request,
                   department: str = Form("Organisation-wide"),
                   respondent: str = Form(""),
                   user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not services.can_access_org(db, user, organization_id):
        return RedirectResponse("/company", status_code=303)
    from elipsis_api import schemas
    dept = (department or "Organisation-wide").strip() or "Organisation-wide"
    payload = schemas.AssessmentIn(
        organization_id=organization_id,
        department=dept,
        respondent=(respondent or "").strip() or (user.name or user.email),
    )
    assessment = services.create_assessment(db, payload)
    services.claim_org(db, user.id, organization_id)
    return RedirectResponse(f"/assessment/{assessment.id}/step/1", status_code=303)


@router.post("/company/{organization_id}/share")
def company_share(organization_id: int, request: Request,
                  department: str = Form("Organisation-wide"),
                  deadline_date: str = Form(...),
                  deadline_time: str = Form("17:00"),
                  min_respondents: int = Form(5),
                  allow_anonymous: str = Form(""),
                  note: str = Form(""),
                  user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not services.can_access_org(db, user, organization_id):
        return RedirectResponse("/company", status_code=303)
    org = db.get(models.Organization, organization_id)
    dept_name = (department or "Organisation-wide").strip()
    dept = db.scalar(select(models.Department).where(
        models.Department.organization_id == organization_id,
        models.Department.name == dept_name))
    if dept is None and dept_name:
        dept = models.Department(organization_id=organization_id, name=dept_name)
        db.add(dept)
        db.flush()
    deadline = f"{deadline_date.strip()}T{(deadline_time or '17:00').strip()}"
    token = _new_token()[:24]
    camp = models.CollectCampaign(
        token=token,
        organization_id=organization_id,
        department_id=dept.id if dept else None,
        created_by=user.id,
        title=f"{org.name} readiness questionnaire",
        deadline=deadline,
        min_respondents=max(1, min(500, int(min_respondents or 5))),
        allow_anonymous=1 if allow_anonymous else 0,
        status="collecting",
        note=(note or "").strip()[:2000] or None,
    )
    db.add(camp)
    db.commit()
    return RedirectResponse(f"/company/campaign/{token}", status_code=303)


@router.get("/company/campaign/{token}")
def campaign_status(token: str, request: Request,
                    user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    camp = db.get(models.CollectCampaign, token)
    if camp is None or not services.can_access_org(db, user, camp.organization_id):
        return RedirectResponse("/company", status_code=303)
    org = db.get(models.Organization, camp.organization_id)
    dept = db.get(models.Department, camp.department_id) if camp.department_id else None
    responses = list(db.scalars(select(models.CollectResponse).where(
        models.CollectResponse.campaign_token == token).order_by(models.CollectResponse.id.desc())))
    completed = sum(1 for r in responses if r.status == "completed")
    in_progress = sum(1 for r in responses if r.status == "in_progress")
    if completed >= (camp.min_respondents or 1) and camp.status == "collecting":
        _maybe_finalize_campaign(db, camp)
        db.refresh(camp)
    share_url = str(request.base_url).rstrip("/") + f"/q/{token}"
    return templates.TemplateResponse(request, "campaign_status.html", {
        "user": user, "campaign": camp, "org": org, "dept": dept,
        "responses": responses, "completed": completed, "in_progress": in_progress,
        "share_url": share_url,
    })


@router.get("/company/campaign/{token}/finalize")
def campaign_finalize(token: str, request: Request,
                      user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    camp = db.get(models.CollectCampaign, token)
    if camp is None or not services.can_access_org(db, user, camp.organization_id):
        return RedirectResponse("/company", status_code=303)
    mid = _maybe_finalize_campaign(db, camp)
    if mid:
        return RedirectResponse(f"/assessment/{mid}/results", status_code=303)
    return RedirectResponse(f"/company/campaign/{token}", status_code=303)


@router.get("/q/{token}")
def collect_landing(token: str, request: Request, db: Session = Depends(get_db)):
    camp = db.get(models.CollectCampaign, token)
    if camp is None:
        return templates.TemplateResponse(request, "404.html", {"user": None}, status_code=404)
    org = db.get(models.Organization, camp.organization_id)
    dept = db.get(models.Department, camp.department_id) if camp.department_id else None
    closed = not _campaign_open(camp)
    return templates.TemplateResponse(request, "collect_landing.html", {
        "user": None, "campaign": camp, "org": org, "dept": dept, "closed": closed,
    })


@router.post("/q/{token}/start")
def collect_start(token: str, request: Request,
                  name: str = Form(""), email: str = Form(""),
                  anonymous: str = Form(""),
                  db: Session = Depends(get_db)):
    camp = db.get(models.CollectCampaign, token)
    if camp is None or not _campaign_open(camp):
        return RedirectResponse(f"/q/{token}", status_code=303)
    is_anon = bool(anonymous) and bool(camp.allow_anonymous)
    if not is_anon and not camp.allow_anonymous:
        if not (name or "").strip() and not (email or "").strip():
            return RedirectResponse(f"/q/{token}", status_code=303)
    from elipsis_api import schemas
    dept = db.get(models.Department, camp.department_id) if camp.department_id else None
    dept_name = dept.name if dept else "Organisation-wide"
    respondent = "Anonymous" if is_anon else ((name or "").strip() or (email or "").strip() or "Respondent")
    payload = schemas.AssessmentIn(
        organization_id=camp.organization_id,
        department=dept_name,
        respondent=respondent,
    )
    assessment = services.create_assessment(db, payload)
    resp = models.CollectResponse(
        campaign_token=token,
        assessment_id=assessment.id,
        respondent_name=None if is_anon else ((name or "").strip()[:120] or None),
        respondent_email=None if is_anon else ((email or "").strip()[:160] or None),
        is_anonymous=1 if is_anon else 0,
        status="in_progress",
    )
    db.add(resp)
    db.commit()
    return RedirectResponse(f"/q/{token}/a/{assessment.id}/step/1", status_code=303)


def _collect_owned(db: Session, token: str, assessment_id: int):
    camp = db.get(models.CollectCampaign, token)
    if camp is None:
        return None, None, None
    row = db.scalar(select(models.CollectResponse).where(
        models.CollectResponse.campaign_token == token,
        models.CollectResponse.assessment_id == assessment_id))
    if row is None:
        return camp, None, None
    assessment = db.get(models.Assessment, assessment_id)
    return camp, row, assessment


@router.get("/q/{token}/a/{assessment_id}/step/{number}")
def collect_step(token: str, assessment_id: int, number: int, request: Request,
                 db: Session = Depends(get_db)):
    camp, row, assessment = _collect_owned(db, token, assessment_id)
    if camp is None or row is None or assessment is None:
        return templates.TemplateResponse(request, "404.html", {"user": None}, status_code=404)
    if row.status == "completed":
        return RedirectResponse(f"/q/{token}/done", status_code=303)
    org = db.get(models.Organization, camp.organization_id)
    steps = services.build_segments(db, assessment_id)
    if not steps:
        return templates.TemplateResponse(request, "404.html", {"user": None}, status_code=404)
    number = max(1, min(number, len(steps)))
    step = steps[number - 1]
    answers = services.answers_map(db, assessment_id)
    return templates.TemplateResponse(request, "collect_step.html", {
        "user": None, "campaign": camp, "org": org, "assessment": assessment,
        "step": step, "steps": steps, "total_steps": len(steps),
        "answers": answers, "is_last": number >= len(steps),
    })


@router.post("/q/{token}/a/{assessment_id}/live")
async def collect_live(token: str, assessment_id: int, request: Request,
                       db: Session = Depends(get_db)):
    camp, row, assessment = _collect_owned(db, token, assessment_id)
    if camp is None or row is None or assessment is None or row.status == "completed":
        return JSONResponse({"error": "closed"}, status_code=400)
    body = await request.json()
    items = body.get("answers") or []
    clean = []
    for it in items:
        try:
            clean.append({
                "question_id": int(it["question_id"]),
                "score": int(it["score"]),
                "evidence": it.get("evidence") or "none",
            })
        except Exception:
            continue
    services.save_answers(db, assessment_id, clean)
    live = services.live_scores(db, assessment_id, body.get("segment") or "") or {}
    return JSONResponse(live)


@router.post("/q/{token}/a/{assessment_id}/submit")
async def collect_submit(token: str, assessment_id: int, request: Request,
                         db: Session = Depends(get_db)):
    camp, row, assessment = _collect_owned(db, token, assessment_id)
    if camp is None or row is None or assessment is None:
        return RedirectResponse(f"/q/{token}", status_code=303)
    form = await request.form()
    from elipsis_api import schemas
    answers = []
    for question in services.get_questions(db, assessment.questionnaire_id):
        raw = form.get(f"q{question.id}")
        if not isinstance(raw, str) or raw == "":
            continue
        try:
            score = max(0, min(5, int(raw)))
        except ValueError:
            continue
        evidence = form.get(f"e{question.id}")
        answers.append(schemas.AnswerIn(
            question_id=question.id, score=score,
            evidence=evidence if isinstance(evidence, str) else "none"))
    existing = services.answers_map(db, assessment_id)
    have = {a.question_id for a in answers}
    for qid, data in existing.items():
        if qid not in have and data.get("score") is not None:
            answers.append(schemas.AnswerIn(
                question_id=qid, score=int(data["score"]),
                evidence=data.get("evidence") or "none"))
    services.submit(db, assessment_id, answers)
    from datetime import datetime
    row.status = "completed"
    row.submitted_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    db.commit()
    _maybe_finalize_campaign(db, camp)
    return RedirectResponse(f"/q/{token}/done", status_code=303)


@router.get("/q/{token}/done")
def collect_done(token: str, request: Request, db: Session = Depends(get_db)):
    camp = db.get(models.CollectCampaign, token)
    org = db.get(models.Organization, camp.organization_id) if camp else None
    return templates.TemplateResponse(request, "collect_done.html", {
        "user": None, "org": org or type("O", (), {"name": "your company"})(),
    })
