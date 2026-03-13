"""My Toolkit router — personal tool stack with favorites."""
from typing import Optional
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.auth import User
from app.dependencies import get_current_user, require_auth
from app.templates_engine import templates
from app.products.guards import require_my_toolkit
from app.services.learning_profile import get_user_favorited_tools, toggle_favorite
from app.services.kit_loader import get_free_tools

router = APIRouter(prefix="/my-toolkit", tags=["my-toolkit"])


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def my_toolkit_index(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_my_toolkit()),
):
    """Personal tool stack page showing favorited tools."""
    requires_login = user is None
    favorited_tools = []
    clusters_covered = set()

    if user:
        favorited_slugs = get_user_favorited_tools(db, str(user.id))
        all_tools = get_free_tools()
        tool_map = {t["slug"]: t for t in all_tools}

        for slug in favorited_slugs:
            tool = tool_map.get(slug)
            if tool:
                favorited_tools.append(tool)
                cluster = tool.get("cluster_name", "")
                if cluster:
                    clusters_covered.add(cluster)

    return templates.TemplateResponse(
        "my_toolkit/index.html",
        {
            "request": request,
            "user": user,
            "favorited_tools": favorited_tools,
            "tool_count": len(favorited_tools),
            "clusters_covered": len(clusters_covered),
            "requires_login": requires_login,
            "feature_name": "My Toolkit",
            "feature_description": "Log in to build your personal AI toolkit. Save your favorite tools, track your stack, and get personalized recommendations.",
        },
    )


@router.post("/api/toggle", response_class=JSONResponse)
async def my_toolkit_toggle(
    request: Request,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _: None = Depends(require_my_toolkit()),
):
    """Toggle a tool favorite. Expects JSON body with tool_slug."""
    body = await request.json()
    tool_slug = body.get("tool_slug", "")
    if not tool_slug:
        return JSONResponse({"status": "error", "message": "tool_slug required"}, status_code=400)

    is_favorited = toggle_favorite(db, str(user.id), tool_slug)
    return JSONResponse({"status": "ok", "is_favorited": is_favorited})
