"""Report HTML pack + server-side PDF download routes."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from constants import (
    BRAND_NAME, BRAND_TAGLINE, CURRENCY, INDEX_NAME, INDEX_SHORT, PILLAR_LABELS,
)
from elipsis_api import models, services
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user, login_redirect, templates

router = APIRouter()


def _not_found(request, user):
    return templates.TemplateResponse(request, "404.html", {"user": user}, status_code=404)


@router.get("/assessment/{assessment_id}/report")
def assessment_report(assessment_id: int, request: Request,
                      user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    assessment, result = services.compute(db, assessment_id)
    if assessment is None or result is None:
        return _not_found(request, user)
    org = db.get(models.Organization, assessment.organization_id)
    comparison_rows, comparison_average = [], None
    if org is not None:
        try:
            data = services.department_comparison(db, org.id)
            comparison_rows = data.get("rows") or []
            comparison_average = data.get("average")
        except Exception:  # noqa: BLE001
            pass
    return templates.TemplateResponse(request, "report.html", {
        "user": user, "result": result, "assessment": assessment,
        "organization": org,
        "department": db.get(models.Department, assessment.department_id)
        if assessment.department_id else None,
        "comparison_rows": comparison_rows,
        "comparison_average": comparison_average,
    })


@router.get("/assessment/{assessment_id}/report.pdf")
def assessment_report_pdf(assessment_id: int, request: Request,
                          user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Server-side board-pack PDF (reportlab)."""
    from elipsis_api.report_pdf import build_pdf

    if user is None:
        return login_redirect()
    assessment, result = services.compute(db, assessment_id)
    if assessment is None or result is None:
        return _not_found(request, user)
    org = db.get(models.Organization, assessment.organization_id)
    dept = (db.get(models.Department, assessment.department_id)
            if assessment.department_id else None)
    comparison_rows = []
    if org is not None:
        try:
            comparison_rows = (services.department_comparison(db, org.id).get("rows") or [])
        except Exception:  # noqa: BLE001
            pass
    try:
        pdf_bytes = build_pdf(
            brand_name=BRAND_NAME, brand_tagline=BRAND_TAGLINE,
            index_name=INDEX_NAME, index_short=INDEX_SHORT, currency=CURRENCY,
            organization=org, department=dept, assessment=assessment, result=result,
            pillar_labels=PILLAR_LABELS, comparison_rows=comparison_rows or None,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[elipsis] PDF build failed: {exc}", flush=True)
        return RedirectResponse(f"/assessment/{assessment_id}/report", status_code=303)
    filename = f"elipsis-report-{assessment_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
