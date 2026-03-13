"""Tool operation routes — let users operate locally-installed tools from Grounded."""
from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.auth import User
from app.dependencies import get_current_user, require_auth
from app.templates_engine import templates
from app.tool_adapters.registry import get_adapter, list_adapters

router = APIRouter(prefix="/apps/{slug}/operate", tags=["tool_operation"])


@router.get("", response_class=HTMLResponse)
async def tool_operate_dashboard(
    request: Request,
    slug: str,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Operation dashboard for a tool with adapter support."""
    adapter = get_adapter(slug)
    if not adapter:
        raise HTTPException(status_code=404, detail="No adapter available for this tool")

    health_check = adapter.get_health_check()
    actions = adapter.get_actions()
    install_steps = adapter.get_install_steps()

    # Serialize actions for template
    action_data = []
    for a in actions:
        action_data.append({
            "name": a.name,
            "label": a.label,
            "description": a.description,
            "parameters": a.parameters,
            "endpoint": a.endpoint,
            "method": a.method,
        })

    return templates.TemplateResponse(
        "open_source_apps/operate.html",
        {
            "request": request,
            "user": user,
            "tool_slug": slug,
            "tool_name": adapter.get_display_name(),
            "base_url": adapter.get_base_url(),
            "health_check_url": health_check.url,
            "health_check_method": health_check.method,
            "actions": action_data,
            "install_steps": install_steps,
        },
    )


@router.get("/actions", response_class=JSONResponse)
async def tool_operate_actions(slug: str):
    """JSON list of available actions from the adapter."""
    adapter = get_adapter(slug)
    if not adapter:
        raise HTTPException(status_code=404, detail="No adapter for this tool")

    actions = adapter.get_actions()
    return JSONResponse([
        {
            "name": a.name,
            "label": a.label,
            "description": a.description,
            "parameters": a.parameters,
            "endpoint": a.endpoint,
            "method": a.method,
        }
        for a in actions
    ])


@router.get("/health-check", response_class=JSONResponse)
async def tool_health_check_config(slug: str):
    """Return health check configuration for client-side checking."""
    adapter = get_adapter(slug)
    if not adapter:
        raise HTTPException(status_code=404, detail="No adapter for this tool")

    hc = adapter.get_health_check()
    return JSONResponse({
        "url": hc.url,
        "method": hc.method,
        "expected_status": hc.expected_status,
    })


@router.post("/install-status", response_class=JSONResponse)
async def update_install_status(
    request: Request,
    slug: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Update a user's installation status for a tool (called from browser)."""
    from app.models.open_source_app import OpenSourceApp
    from app.models.user_installation import UserToolInstallation
    from datetime import datetime, timezone

    body = await request.json()
    is_healthy = body.get("is_healthy", False)

    # Find the app
    app = db.query(OpenSourceApp).filter(OpenSourceApp.slug == slug).first()
    if not app:
        return JSONResponse({"status": "error", "message": "App not found"}, status_code=404)

    # Upsert installation record
    installation = db.query(UserToolInstallation).filter(
        UserToolInstallation.user_id == user.id,
        UserToolInstallation.app_id == app.id,
    ).first()

    now = datetime.now(timezone.utc)

    if installation:
        installation.is_healthy = is_healthy
        installation.last_health_check = now
        if is_healthy and installation.status != "installed":
            installation.status = "installed"
            installation.installed_at = now
    else:
        installation = UserToolInstallation(
            user_id=user.id,
            app_id=app.id,
            status="installed" if is_healthy else "not_installed",
            installed_at=now if is_healthy else None,
            is_healthy=is_healthy,
            last_health_check=now,
        )
        db.add(installation)

    db.commit()
    return JSONResponse({"status": "ok", "is_healthy": is_healthy})
