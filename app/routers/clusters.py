"""Cluster listing and detail routes."""
from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.models.auth import User
from app.dependencies import get_current_user
from app.services.kit_loader import (
    get_all_clusters, get_cluster, get_cluster_tools
)


router = APIRouter(prefix="/clusters", tags=["clusters"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def clusters_index(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """List all tool clusters."""
    clusters = get_all_clusters()

    # Enrich each cluster with its tool count and tools
    enriched = []
    for c in clusters:
        tools = get_cluster_tools(c["slug"])
        enriched.append({
            **c,
            "tools": tools,
            "tool_count": len(tools),
            "avg_cost": round(sum(t["cdi_scores"]["cost"] for t in tools) / len(tools), 1) if tools else 0,
            "avg_difficulty": round(sum(t["cdi_scores"]["difficulty"] for t in tools) / len(tools), 1) if tools else 0,
            "avg_invasiveness": round(sum(t["cdi_scores"]["invasiveness"] for t in tools) / len(tools), 1) if tools else 0,
        })

    return templates.TemplateResponse(
        "clusters/index.html",
        {
            "request": request,
            "user": user,
            "clusters": enriched,
        }
    )


@router.get("/{slug}", response_class=HTMLResponse)
async def cluster_detail(
    request: Request,
    slug: str,
    user: Optional[User] = Depends(get_current_user),
):
    """Show cluster detail with its tools."""
    cluster = get_cluster(slug)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    tools = get_cluster_tools(slug)

    return templates.TemplateResponse(
        "clusters/detail.html",
        {
            "request": request,
            "user": user,
            "cluster": cluster,
            "tools": tools,
        }
    )
