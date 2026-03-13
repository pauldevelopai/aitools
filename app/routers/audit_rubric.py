"""Audit Rubric Scorer router — community-driven tool auditing."""
from typing import Optional
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.auth import User
from app.dependencies import get_current_user, require_auth
from app.templates_engine import templates
from app.products.guards import require_audit_rubric
from app.services.audit_rubric import (
    DIMENSIONS, score_tool, get_user_scores, get_user_score_for_tool,
    get_tool_aggregate, get_all_aggregates
)
from app.services.kit_loader import get_free_tools, get_tool

router = APIRouter(prefix="/audit-rubric", tags=["audit-rubric"])


@router.get("/", response_class=HTMLResponse)
async def audit_rubric_index(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_audit_rubric()),
):
    """Index page: all tools with community audit scores."""
    tools = get_free_tools()
    aggregates = get_all_aggregates(db)

    # Build lookup by tool_slug
    agg_map = {a["tool_slug"]: a for a in aggregates}

    # Merge tools with aggregate data
    tool_list = []
    for t in tools:
        slug = t.get("slug", "")
        agg = agg_map.get(slug, {})
        tool_list.append({
            "slug": slug,
            "name": t.get("name", ""),
            "cluster_name": t.get("cluster_name", ""),
            "cdi_scores": t.get("cdi_scores", {}),
            "audit_avg_total": agg.get("avg_total"),
            "audit_count": agg.get("count", 0),
        })

    # If user is logged in, attach their scores
    user_score_map = {}
    if user:
        user_scores = get_user_scores(db, user.id)
        user_score_map = {s.tool_slug: s for s in user_scores}

    requires_login = user is None
    scored_count = len(aggregates)

    # Compute average across scored tools
    avg_score = 0
    if aggregates:
        avg_score = round(
            sum(a["avg_total"] for a in aggregates) / len(aggregates), 1
        )

    return templates.TemplateResponse(
        "audit_rubric/index.html",
        {
            "request": request,
            "user": user,
            "title": "Audit Rubric",
            "tools": tool_list,
            "total_tools": len(tools),
            "scored_count": scored_count,
            "avg_score": avg_score,
            "user_score_map": user_score_map,
            "requires_login": requires_login,
            "feature_name": "Audit Rubric Scoring",
            "feature_description": "Score tools across data sovereignty, exportability, business model, and security dimensions.",
        },
    )


@router.get("/api/aggregate/{tool_slug}", response_class=JSONResponse)
async def audit_rubric_aggregate_api(
    tool_slug: str,
    db: Session = Depends(get_db),
    _: None = Depends(require_audit_rubric()),
):
    """JSON endpoint for AJAX aggregate data."""
    aggregate = get_tool_aggregate(db, tool_slug)
    return JSONResponse(aggregate)


@router.get("/{tool_slug}", response_class=HTMLResponse)
async def audit_rubric_score_form(
    request: Request,
    tool_slug: str,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_audit_rubric()),
):
    """Score form: show 4 dimension sliders for a tool."""
    tool = get_tool(tool_slug)
    if not tool:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Tool not found")

    # Get existing user score if logged in
    existing_score = None
    if user:
        existing_score = get_user_score_for_tool(db, user.id, tool_slug)

    # Get community aggregate
    aggregate = get_tool_aggregate(db, tool_slug)

    requires_login = user is None

    return templates.TemplateResponse(
        "audit_rubric/score.html",
        {
            "request": request,
            "user": user,
            "title": f"Score {tool.get('name', '')} - Audit Rubric",
            "tool": tool,
            "dimensions": DIMENSIONS,
            "existing_score": existing_score,
            "aggregate": aggregate,
            "requires_login": requires_login,
            "feature_name": "Audit Rubric Scoring",
            "feature_description": "Log in to score this tool across data sovereignty, exportability, business model, and security.",
        },
    )


@router.post("/{tool_slug}", response_class=HTMLResponse)
async def audit_rubric_submit(
    request: Request,
    tool_slug: str,
    data_sovereignty: int = Form(...),
    exportability: int = Form(...),
    business_model: int = Form(...),
    security: int = Form(...),
    notes: str = Form(""),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _: None = Depends(require_audit_rubric()),
):
    """Submit an audit score for a tool."""
    score_tool(
        db,
        user_id=user.id,
        tool_slug=tool_slug,
        data_sovereignty=data_sovereignty,
        exportability=exportability,
        business_model=business_model,
        security=security,
        notes=notes or None,
    )
    return RedirectResponse(
        url=f"/audit-rubric/{tool_slug}", status_code=303
    )
