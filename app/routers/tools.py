"""Tool listing, detail, and finder routes."""
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


@router.get("/finder", response_class=HTMLResponse)
async def tool_finder(
    request: Request,
    need: Optional[str] = None,
    user: Optional[User] = Depends(get_current_user),
):
    """Interactive tool finder to help journalists choose the right tool."""
    clusters = get_all_clusters()
    all_tools_list = get_all_tools()

    # Pre-defined journalism needs mapped to use case groups
    needs_map = {
        "transcribe": {"label": "Transcribe interviews or audio", "use_cases": ["transcription"], "clusters": ["transcription-translation"]},
        "translate": {"label": "Translate content between languages", "use_cases": ["translation"], "clusters": ["transcription-translation"]},
        "verify": {"label": "Verify images, video or claims", "use_cases": ["verification"], "clusters": ["verification-investigations"]},
        "investigate": {"label": "Investigate documents or data", "use_cases": ["document-research", "network-analysis"], "clusters": ["verification-investigations"]},
        "monitor": {"label": "Monitor websites for changes", "use_cases": ["web-monitoring"], "clusters": ["verification-investigations"]},
        "write": {"label": "Draft, edit or summarise text", "use_cases": ["llm-writing", "text-editing"], "clusters": ["writing-analysis"]},
        "data": {"label": "Analyse data or documents", "use_cases": ["data-analysis"], "clusters": ["writing-analysis"]},
        "video": {"label": "Create or edit video content", "use_cases": ["video-production"], "clusters": ["audio-video-social"]},
        "audio": {"label": "Create audio or voice content", "use_cases": ["audio-voice"], "clusters": ["audio-video-social"]},
        "images": {"label": "Generate or edit images", "use_cases": ["image-generation"], "clusters": ["audio-video-social"]},
        "social": {"label": "Manage social media", "use_cases": ["social-media"], "clusters": ["audio-video-social"]},
        "security": {"label": "Protect sources and data", "use_cases": ["security-privacy"], "clusters": ["security-challenges"]},
        "build": {"label": "Build custom tools or apps", "use_cases": ["coding-building"], "clusters": ["building-your-own-tools"]},
        "automate": {"label": "Automate workflows", "use_cases": ["automation"], "clusters": ["ai-agents-automated-workflows"]},
        "sovereign": {"label": "Use only sovereign/local tools", "use_cases": ["local-ai"], "clusters": []},
    }

    recommended = []
    selected_need = None

    if need and need in needs_map:
        selected_need = needs_map[need]
        target_use_cases = set(selected_need["use_cases"])
        target_clusters = set(selected_need["clusters"])

        for tool in all_tools_list:
            cr = tool.get("cross_references", {})
            tool_use_cases = set(cr.get("use_cases", []))

            # Match by use case or cluster
            if tool_use_cases & target_use_cases:
                recommended.append(tool)
            elif tool.get("cluster_slug") in target_clusters and tool not in recommended:
                recommended.append(tool)

        # Special case: sovereign filter
        if need == "sovereign":
            recommended = [t for t in all_tools_list if t.get("cdi_scores", {}).get("invasiveness", 10) == 0]

        # Sort: lower total CDI score first (easier, cheaper, less invasive)
        recommended.sort(key=lambda t: (
            t["cdi_scores"]["cost"] + t["cdi_scores"]["difficulty"] + t["cdi_scores"]["invasiveness"]
        ))

    return templates.TemplateResponse(
        "tools/finder.html",
        {
            "request": request,
            "user": user,
            "needs": needs_map,
            "selected_need": need,
            "selected_need_info": selected_need,
            "recommended": recommended,
            "clusters": clusters,
        }
    )


@router.get("/cdi", response_class=HTMLResponse)
async def cdi_explorer(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
):
    """Interactive CDI score explorer — scatter chart, sliders, comparisons."""
    import json as json_mod
    all_tools_list = get_all_tools()
    clusters = get_all_clusters()

    # Prepare tools data for client-side JS
    tools_json = json_mod.dumps([
        {
            "slug": t["slug"],
            "name": t["name"],
            "cluster_name": t.get("cluster_name", ""),
            "cluster_slug": t.get("cluster_slug", ""),
            "cost": t["cdi_scores"]["cost"],
            "difficulty": t["cdi_scores"]["difficulty"],
            "invasiveness": t["cdi_scores"]["invasiveness"],
            "total": t["cdi_scores"]["cost"] + t["cdi_scores"]["difficulty"] + t["cdi_scores"]["invasiveness"],
            "purpose": t.get("purpose", ""),
            "tags": t.get("tags", []),
        }
        for t in all_tools_list
    ])

    return templates.TemplateResponse(
        "tools/cdi.html",
        {
            "request": request,
            "user": user,
            "tools_json": tools_json,
            "tool_count": len(all_tools_list),
            "clusters": clusters,
        }
    )


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
    """Show individual tool detail page with cross-references."""
    tool = get_tool(slug)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    # Get related tools from same cluster
    related = [
        t for t in get_cluster_tools(tool.get("cluster_slug", ""))
        if t["slug"] != slug
    ]

    # Resolve cross-references
    cross_refs = tool.get("cross_references", {})

    # Sovereign alternative (if this tool has one)
    sovereign_alt = None
    sov_slug = cross_refs.get("sovereign_alternative")
    if sov_slug:
        sovereign_alt = get_tool(sov_slug)

    # Tools this is a sovereign alternative FOR
    sovereign_for_tools = []
    for s in cross_refs.get("sovereign_alternative_for", []):
        t = get_tool(s)
        if t:
            sovereign_for_tools.append(t)

    # Similar tools
    similar_tools = []
    for s in cross_refs.get("similar_tools", []):
        t = get_tool(s)
        if t:
            similar_tools.append(t)

    return templates.TemplateResponse(
        "tools/detail.html",
        {
            "request": request,
            "user": user,
            "tool": tool,
            "related_tools": related,
            "sovereign_alt": sovereign_alt,
            "sovereign_for_tools": sovereign_for_tools,
            "similar_tools": similar_tools,
        }
    )
