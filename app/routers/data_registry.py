"""Data Asset Registry router — collective data management and licensing."""
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.db import get_db
from app.dependencies import get_current_user, require_auth, require_auth_page
from app.models.auth import User
from app.products.guards import require_feature
from app.templates_engine import templates
from app.services.data_registry import (
    get_registry,
    get_asset_by_slug,
    get_user_assets,
    create_asset,
    submit_inquiry,
    get_registry_stats,
)

router = APIRouter(prefix="/data-registry", tags=["data-registry"])


class CreateAssetRequest(BaseModel):
    name: str
    description: Optional[str] = None
    asset_type: str
    data_format: Optional[str] = None
    record_count: Optional[int] = None
    languages: Optional[list] = None
    sectors: Optional[list] = None
    tags: Optional[list] = None
    classification: str = "internal"
    is_licensable: bool = False
    licensing_terms: Optional[str] = None
    contact_email: Optional[str] = None


class InquiryRequest(BaseModel):
    message: str


@router.get("/", response_class=HTMLResponse)
async def registry_listing(
    request: Request,
    asset_type: Optional[str] = None,
    licensable: Optional[str] = None,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("data_registry")),
):
    """Registry listing with type/licensable filters."""
    is_licensable = None
    if licensable == "yes":
        is_licensable = True

    assets = get_registry(db, asset_type=asset_type, is_licensable=is_licensable)
    stats = get_registry_stats(db)

    requires_login = user is None

    return templates.TemplateResponse(
        "data_registry/registry.html",
        {
            "request": request,
            "user": user,
            "title": "Data Asset Registry",
            "assets": assets,
            "stats": stats,
            "active_type": asset_type,
            "active_licensable": licensable,
            "requires_login": requires_login,
            "feature_name": "data registry",
            "feature_description": "Register and discover data assets for collective licensing and collaboration.",
        },
    )


@router.get("/my-assets", response_class=HTMLResponse)
async def my_assets(
    request: Request,
    user: User = Depends(require_auth_page),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("data_registry")),
):
    """User's registered data assets."""
    assets = get_user_assets(db, user.id)

    return templates.TemplateResponse(
        "data_registry/my_assets.html",
        {
            "request": request,
            "user": user,
            "title": "My Data Assets",
            "assets": assets,
        },
    )


@router.get("/create", response_class=HTMLResponse)
async def create_asset_form(
    request: Request,
    user: User = Depends(require_auth_page),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("data_registry")),
):
    """Form to register a new data asset."""
    return templates.TemplateResponse(
        "data_registry/create.html",
        {
            "request": request,
            "user": user,
            "title": "Register Data Asset",
        },
    )


@router.post("/create")
async def create_asset_route(
    body: CreateAssetRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("data_registry")),
):
    """Create a new data asset (JSON endpoint)."""
    asset = create_asset(
        db,
        user_id=user.id,
        name=body.name,
        description=body.description,
        asset_type=body.asset_type,
        data_format=body.data_format,
        record_count=body.record_count,
        languages=body.languages or [],
        sectors=body.sectors or [],
        tags=body.tags or [],
        classification=body.classification,
        is_licensable=body.is_licensable,
        licensing_terms=body.licensing_terms,
        contact_email=body.contact_email,
        status="active",
    )

    return JSONResponse({
        "id": str(asset.id),
        "slug": asset.slug,
        "status": "created",
    })


@router.get("/{slug}", response_class=HTMLResponse)
async def asset_detail(
    request: Request,
    slug: str,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("data_registry")),
):
    """Asset detail page."""
    asset = get_asset_by_slug(db, slug)
    if not asset:
        raise HTTPException(status_code=404, detail="Data asset not found")

    requires_login = user is None

    return templates.TemplateResponse(
        "data_registry/detail.html",
        {
            "request": request,
            "user": user,
            "title": asset.name,
            "asset": asset,
            "requires_login": requires_login,
            "feature_name": "data registry",
            "feature_description": "View data asset details and express licensing interest.",
        },
    )


@router.post("/{slug}/inquire")
async def inquire_route(
    slug: str,
    body: InquiryRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature("data_registry")),
):
    """Submit licensing inquiry for a data asset."""
    asset = get_asset_by_slug(db, slug)
    if not asset:
        raise HTTPException(status_code=404, detail="Data asset not found")

    result = submit_inquiry(db, user.id, asset.id, body.message)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return JSONResponse(result)
