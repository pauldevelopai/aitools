"""Admin routes for Open Source Apps CRUD."""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_admin
from app.models.auth import User
from app.models.open_source_app import OpenSourceApp
from app.templates_engine import templates
from app.products.admin_context import get_admin_context_dict

router = APIRouter(prefix="/admin/apps", tags=["admin_apps"])


@router.get("", response_class=HTMLResponse)
async def list_apps(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all open source apps."""
    admin_context = get_admin_context_dict(request)
    apps = db.query(OpenSourceApp).order_by(OpenSourceApp.created_at.desc()).all()

    return templates.TemplateResponse(
        "admin/apps/list.html",
        {
            "request": request,
            "user": user,
            "apps": apps,
            **admin_context,
            "active_admin_page": "apps",
        }
    )


@router.get("/create", response_class=HTMLResponse)
async def create_app_form(
    request: Request,
    user: User = Depends(require_admin),
):
    """Show app creation form."""
    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/apps/form.html",
        {
            "request": request,
            "user": user,
            **admin_context,
            "active_admin_page": "apps",
        }
    )


@router.post("/create")
async def create_app(
    name: str = Form(...),
    github_url: str = Form(...),
    website_url: str = Form(None),
    docs_url: str = Form(None),
    description: str = Form(None),
    license_type: str = Form("MIT"),
    deployment_type: str = Form("self_hosted"),
    installation_guide: str = Form(None),
    system_requirements: str = Form(None),
    platforms: str = Form(None),
    difficulty: str = Form("beginner"),
    pricing_model: str = Form("free"),
    categories: str = Form(None),
    tags: str = Form(None),
    sectors: str = Form(None),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new open source app."""
    slug = OpenSourceApp.generate_slug(name)
    existing = db.query(OpenSourceApp).filter(OpenSourceApp.slug == slug).first()
    if existing:
        slug = f"{slug}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    # Parse comma-separated fields into lists
    categories_list = None
    if categories and categories.strip():
        categories_list = [c.strip() for c in categories.split(",") if c.strip()]

    tags_list = None
    if tags and tags.strip():
        tags_list = [t.strip() for t in tags.split(",") if t.strip()]

    sectors_list = None
    if sectors and sectors.strip():
        sectors_list = [s.strip() for s in sectors.split(",") if s.strip()]

    platforms_list = None
    if platforms and platforms.strip():
        platforms_list = [p.strip() for p in platforms.split(",") if p.strip()]

    app_item = OpenSourceApp(
        name=name,
        slug=slug,
        github_url=github_url,
        website_url=website_url or None,
        docs_url=docs_url or None,
        description=description or None,
        license_type=license_type,
        deployment_type=deployment_type,
        installation_guide=installation_guide or None,
        system_requirements=system_requirements or None,
        platforms=platforms_list,
        difficulty=difficulty,
        pricing_model=pricing_model,
        categories=categories_list,
        tags=tags_list,
        sectors=sectors_list,
        created_by=admin_user.id,
        status="draft",
    )
    db.add(app_item)
    db.commit()

    return RedirectResponse(url=f"/admin/apps/{app_item.id}", status_code=303)


@router.get("/{app_id}", response_class=HTMLResponse)
async def app_detail(
    app_id: str,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """App detail / edit form."""
    app_item = db.query(OpenSourceApp).filter(OpenSourceApp.id == app_id).first()
    if not app_item:
        raise HTTPException(status_code=404, detail="App not found")

    # Prepare JSONB lists as comma-separated strings for the form
    categories_str = ", ".join(app_item.categories) if app_item.categories else ""
    tags_str = ", ".join(app_item.tags) if app_item.tags else ""
    sectors_str = ", ".join(app_item.sectors) if app_item.sectors else ""
    platforms_str = ", ".join(app_item.platforms) if app_item.platforms else ""

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/apps/form.html",
        {
            "request": request,
            "user": admin_user,
            "app_item": app_item,
            "categories_str": categories_str,
            "tags_str": tags_str,
            "sectors_str": sectors_str,
            "platforms_str": platforms_str,
            **admin_context,
            "active_admin_page": "apps",
        }
    )


@router.post("/{app_id}/edit")
async def edit_app(
    app_id: str,
    name: str = Form(...),
    github_url: str = Form(...),
    website_url: str = Form(None),
    docs_url: str = Form(None),
    description: str = Form(None),
    license_type: str = Form("MIT"),
    deployment_type: str = Form("self_hosted"),
    installation_guide: str = Form(None),
    system_requirements: str = Form(None),
    platforms: str = Form(None),
    difficulty: str = Form("beginner"),
    pricing_model: str = Form("free"),
    categories: str = Form(None),
    tags: str = Form(None),
    sectors: str = Form(None),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update an open source app."""
    app_item = db.query(OpenSourceApp).filter(OpenSourceApp.id == app_id).first()
    if not app_item:
        raise HTTPException(status_code=404, detail="App not found")

    app_item.name = name
    app_item.github_url = github_url
    app_item.website_url = website_url or None
    app_item.docs_url = docs_url or None
    app_item.description = description or None
    app_item.license_type = license_type
    app_item.deployment_type = deployment_type
    app_item.installation_guide = installation_guide or None
    app_item.system_requirements = system_requirements or None
    app_item.difficulty = difficulty
    app_item.pricing_model = pricing_model

    # Parse comma-separated fields
    if categories and categories.strip():
        app_item.categories = [c.strip() for c in categories.split(",") if c.strip()]
    else:
        app_item.categories = None

    if tags and tags.strip():
        app_item.tags = [t.strip() for t in tags.split(",") if t.strip()]
    else:
        app_item.tags = None

    if sectors and sectors.strip():
        app_item.sectors = [s.strip() for s in sectors.split(",") if s.strip()]
    else:
        app_item.sectors = None

    if platforms and platforms.strip():
        app_item.platforms = [p.strip() for p in platforms.split(",") if p.strip()]
    else:
        app_item.platforms = None

    db.commit()

    return RedirectResponse(url=f"/admin/apps/{app_id}", status_code=303)


@router.post("/{app_id}/toggle-publish")
async def toggle_app_publish(
    app_id: str,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Toggle publish status of an app."""
    app_item = db.query(OpenSourceApp).filter(OpenSourceApp.id == app_id).first()
    if not app_item:
        raise HTTPException(status_code=404, detail="App not found")

    app_item.status = "published" if app_item.status == "draft" else "draft"
    db.commit()

    return RedirectResponse(url="/admin/apps", status_code=303)


@router.post("/{app_id}/delete")
async def delete_app(
    app_id: str,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete an open source app."""
    app_item = db.query(OpenSourceApp).filter(OpenSourceApp.id == app_id).first()
    if not app_item:
        raise HTTPException(status_code=404, detail="App not found")

    db.delete(app_item)
    db.commit()

    return RedirectResponse(url="/admin/apps", status_code=303)
