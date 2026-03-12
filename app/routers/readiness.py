"""AI Readiness Assessment router."""
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models.auth import User
from app.products.guards import require_feature
from app.templates_engine import templates
from app.services.readiness_assessment import (
    ASSESSMENT_QUESTIONS,
    calculate_scores,
    determine_maturity_level,
    generate_recommendations,
    save_assessment,
)

router = APIRouter(prefix="/readiness", tags=["readiness"])


@router.get("/", response_class=HTMLResponse)
async def readiness_landing(
    request: Request,
    user: User = Depends(get_current_user),
    _: None = Depends(require_feature("readiness_assessment")),
):
    """Assessment landing / start page."""
    return templates.TemplateResponse(
        "readiness/assessment.html",
        {
            "request": request,
            "user": user,
            "title": "AI Readiness Assessment",
            "questions": ASSESSMENT_QUESTIONS,
        },
    )


@router.post("/submit")
async def submit_assessment(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("readiness_assessment")),
):
    """Process submitted assessment answers."""
    form_data = await request.form()

    # Extract answers: form fields named q_{question_id}
    answers = {}
    for q in ASSESSMENT_QUESTIONS:
        val = form_data.get(f"q_{q['id']}")
        if val is not None:
            answers[q["id"]] = int(val)

    if len(answers) < len(ASSESSMENT_QUESTIONS):
        # Not all questions answered — redirect back
        return RedirectResponse(url="/readiness/", status_code=303)

    # Calculate scores
    scores = calculate_scores(answers)
    overall = scores.pop("overall")
    level = determine_maturity_level(overall)

    # Generate recommendations
    org_type = user.organisation_type if user else None
    recs = generate_recommendations(scores, level["name"], org_type)

    # Save
    assessment = save_assessment(
        db=db,
        answers=answers,
        dimension_scores=scores,
        overall_score=overall,
        maturity_level=level["name"],
        recommendations=recs,
        user_id=user.id if user else None,
        organisation_type=org_type,
    )

    return RedirectResponse(url=f"/readiness/results/{assessment.id}", status_code=303)


@router.get("/results/{assessment_id}", response_class=HTMLResponse)
async def readiness_results(
    request: Request,
    assessment_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("readiness_assessment")),
):
    """Display assessment results."""
    from app.models.readiness import ReadinessAssessment
    import uuid

    assessment = (
        db.query(ReadinessAssessment)
        .filter(ReadinessAssessment.id == uuid.UUID(assessment_id))
        .first()
    )
    if not assessment:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Assessment not found")

    level = determine_maturity_level(assessment.overall_score)

    return templates.TemplateResponse(
        "readiness/results.html",
        {
            "request": request,
            "user": user,
            "title": "Your AI Readiness Results",
            "assessment": assessment,
            "level": level,
        },
    )
