"""Export/Report Generation router."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_auth_page
from app.models.auth import User
from app.products.guards import require_feature
from app.templates_engine import templates
from app.services.export_report import get_report_sections, get_available_sections_summary

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/", response_class=HTMLResponse)
async def export_landing(
    request: Request,
    user: User = Depends(require_auth_page),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("export_reports")),
):
    """Export landing page showing available report sections."""
    available = get_available_sections_summary(db, user.id)
    has_content = any(s["available"] for s in available if s["key"] != "progress")

    return templates.TemplateResponse(
        "export/index.html",
        {
            "request": request,
            "user": user,
            "title": "Export Report",
            "sections": available,
            "has_content": has_content,
        },
    )


@router.get("/preview", response_class=HTMLResponse)
async def export_preview(
    request: Request,
    user: User = Depends(require_auth_page),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("export_reports")),
):
    """HTML preview of the full report."""
    sections = get_report_sections(db, user.id)

    return templates.TemplateResponse(
        "export/report_preview.html",
        {
            "request": request,
            "user": user,
            "title": "Report Preview",
            "sections": sections,
            "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        },
    )


@router.get("/download", response_class=HTMLResponse)
async def export_download(
    request: Request,
    user: User = Depends(require_auth_page),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("export_reports")),
):
    """Generate and serve a print-ready HTML report for download/printing."""
    sections = get_report_sections(db, user.id)
    from datetime import datetime, timezone

    return templates.TemplateResponse(
        "export/report_download.html",
        {
            "request": request,
            "user": user,
            "title": "AI Implementation Report",
            "sections": sections,
            "generated_at": datetime.now(timezone.utc),
        },
    )
