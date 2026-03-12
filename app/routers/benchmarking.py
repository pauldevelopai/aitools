"""Benchmarking router."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_auth, require_auth_page
from app.models.auth import User
from app.products.guards import require_feature
from app.templates_engine import templates
from app.services.benchmarking import get_peer_comparison

router = APIRouter(prefix="/benchmarking", tags=["benchmarking"])


@router.get("/", response_class=HTMLResponse)
async def benchmarking_dashboard(
    request: Request,
    user: User = Depends(require_auth_page),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("benchmarking")),
):
    """Benchmarking dashboard showing user's position vs peers."""
    comparison = get_peer_comparison(db, user.id)

    return templates.TemplateResponse(
        "benchmarking/dashboard.html",
        {
            "request": request,
            "user": user,
            "title": "Benchmarking",
            "comparison": comparison,
        },
    )


@router.get("/api/my-position", response_class=JSONResponse)
async def benchmarking_api(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """JSON endpoint for user's benchmark position."""
    comparison = get_peer_comparison(db, user.id)
    return comparison
