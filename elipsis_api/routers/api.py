"""JSON API router (/api/v1) — the primary programmatic interface."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from constants import BRAND_NAME, INDEX_NAME, scale_options
from elipsis_api import schemas, services
from elipsis_api.config import DATABASE_URL
from elipsis_api.database import get_db

router = APIRouter(prefix="/api/v1", tags=["api"])


def _assessment_out(a):
    return schemas.AssessmentOut(
        id=a.id, organization_id=a.organization_id, department_id=a.department_id,
        questionnaire_id=a.questionnaire_id, respondent=a.respondent, status=a.status,
        readiness_index=a.readiness_index, maturity_band=a.maturity_band,
        confidence_index=a.confidence_index)


@router.get("/health", response_model=schemas.HealthOut)
def health():
    return schemas.HealthOut(status="ok", brand=BRAND_NAME, index=INDEX_NAME,
                             database=DATABASE_URL.split("://", 1)[0])


@router.get("/questionnaire", response_model=list[schemas.QuestionOut])
def questionnaire(db: Session = Depends(get_db)):
    bank = services.get_bank(db)
    if bank is None:
        raise HTTPException(status_code=404, detail="questionnaire not seeded")
    return [schemas.QuestionOut(
                id=q.id, code=q.code, scale=q.scale,
                options=[schemas.OptionOut(score=s, emoji=e, label=label, help=h)
                         for s, e, label, h in (scale_options(q.scale or "") or ())],
                subdomain=q.subdomain, pillar=q.pillar,
                text=q.text, why=q.why, weight=q.weight or 0,
                evidence_required=bool(q.evidence_required))
            for q in services.get_questions(db, bank.id)]


@router.get("/assessments")
def list_assessments(db: Session = Depends(get_db)):
    return services.list_assessments(db)


@router.post("/assessments", response_model=schemas.AssessmentOut, status_code=201)
def create_assessment(payload: schemas.AssessmentIn, db: Session = Depends(get_db)):
    try:
        return _assessment_out(services.create_assessment(db, payload))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/assessments/{assessment_id}", response_model=schemas.ResultOut)
def assessment_result(assessment_id: int, db: Session = Depends(get_db)):
    _, result = services.compute(db, assessment_id)
    if result is None:
        raise HTTPException(status_code=404, detail="assessment not found")
    return result


@router.post("/assessments/{assessment_id}/submit", response_model=schemas.ResultOut)
def assessment_submit(assessment_id: int, payload: schemas.SubmitIn,
                      db: Session = Depends(get_db)):
    _, result = services.submit(db, assessment_id, payload.answers)
    if result is None:
        raise HTTPException(status_code=404, detail="assessment not found")
    return result