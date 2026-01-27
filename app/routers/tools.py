"""Tool listing and detail routes."""
from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.auth import User
from app.dependencies import get_current_user
from app.services.kit_loader import (
    get_all_tools, get_tool, get_all_clusters,
    get_cluster_tools, search_tools
)


router = APIRouter(prefix="/tools", tags=["tools"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def tools_index(
    request: Request,
    cluster: Optional[str] = None,
    q: Optional[str] = None,
    max_cost: Optional[int] = Query(None, ge=0, le=10),
    max_difficulty: Optional[int] = Query(None, ge=0, le=10),
    max_invasiveness: Optional[int] = Query(None, ge=0, le=10),
    user: Optional[User] = Depends(get_current_user),
):
    """List all tools with optional filtering."""
    clusters = get_all_clusters()

    tools = search_tools(
        query=q or "",
        cluster_slug=cluster,
        max_cost=max_cost,
        max_difficulty=max_difficulty,
        max_invasiveness=max_invasiveness,
    )

    return templates.TemplateResponse(
        "tools/index.html",
        {
            "request": request,
            "user": user,
            "tools": tools,
            "clusters": clusters,
            "cluster": cluster,
            "q": q or "",
            "max_cost": max_cost,
            "max_difficulty": max_difficulty,
            "max_invasiveness": max_invasiveness,
            "total_tools": len(get_all_tools()),
        }
    )


@router.get("/{slug}", response_class=HTMLResponse)
async def tool_detail(
    request: Request,
    slug: str,
    user: Optional[User] = Depends(get_current_user),
):
    """Show individual tool detail page."""
    tool = get_tool(slug)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    # Get related tools from same cluster
    related = [
        t for t in get_cluster_tools(tool.get("cluster_slug", ""))
        if t["slug"] != slug
    ]

    return templates.TemplateResponse(
        "tools/detail.html",
        {
            "request": request,
            "user": user,
            "tool": tool,
            "related_tools": related,
        }
    )
