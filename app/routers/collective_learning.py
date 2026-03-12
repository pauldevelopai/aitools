"""Collective Learning router — network intelligence dashboard."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.db import get_db
from app.dependencies import get_current_user, require_auth
from app.models.auth import User
from app.products.guards import require_feature
from app.templates_engine import templates
from app.services.collective_analytics import get_dashboard_data

router = APIRouter(prefix="/collective-learning", tags=["collective-learning"])


@router.get("/", response_class=HTMLResponse)
async def collective_learning_dashboard(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("collective_learning")),
):
    """Network dashboard with aggregated stats across the platform."""
    data = get_dashboard_data(db)

    requires_login = user is None

    return templates.TemplateResponse(
        "collective_learning/dashboard.html",
        {
            "request": request,
            "user": user,
            "title": "Collective Learning",
            "data": data,
            "requires_login": requires_login,
            "feature_name": "collective learning",
            "feature_description": "See aggregated network intelligence, tool adoption patterns, and skill growth across the platform.",
        },
    )


@router.get("/api/stats", response_class=JSONResponse)
async def collective_learning_api(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """JSON stats for AJAX widgets."""
    data = get_dashboard_data(db)
    return data
