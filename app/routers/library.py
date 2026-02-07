"""Public Library router — browse, search, and copy reference documents."""
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.db import get_db
from app.dependencies import get_current_user, require_auth
from app.models.auth import User
from app.models.library_item import (
    LibraryItem,
    DOCUMENT_TYPES,
    DOCUMENT_TYPE_MAP,
)
from app.models.legal_builder import JURISDICTIONS, JURISDICTION_MAP
from app.products.guards import require_library
from app.templates_engine import templates

router = APIRouter(prefix="/library", tags=["library"])

PER_PAGE = 20


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def library_index(
    request: Request,
    jurisdiction: Optional[str] = Query(None),
    document_type: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    user: Optional[User] = Depends(get_current_user),
    _feature: None = Depends(require_library()),
    db: Session = Depends(get_db),
):
    """Browse published library items with filters and search."""
    query = db.query(LibraryItem).filter(LibraryItem.is_published == True)

    if jurisdiction:
        query = query.filter(LibraryItem.jurisdiction == jurisdiction)

    if document_type:
        query = query.filter(LibraryItem.document_type == document_type)

    if q and q.strip():
        search = f"%{q.strip()}%"
        query = query.filter(
            LibraryItem.title.ilike(search)
            | LibraryItem.summary.ilike(search)
            | LibraryItem.content_markdown.ilike(search)
        )

    total = query.count()
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = min(page, total_pages)
    offset = (page - 1) * PER_PAGE

    items = query.order_by(LibraryItem.title).offset(offset).limit(PER_PAGE).all()

    return templates.TemplateResponse(
        "library/index.html",
        {
            "request": request,
            "user": user,
            "items": items,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "jurisdiction": jurisdiction or "",
            "document_type": document_type or "",
            "q": q or "",
            "document_types": DOCUMENT_TYPES,
            "jurisdictions": JURISDICTIONS,
            "document_type_map": DOCUMENT_TYPE_MAP,
            "jurisdiction_map": JURISDICTION_MAP,
        },
    )


@router.get("/{slug}", response_class=HTMLResponse)
async def library_detail(
    slug: str,
    request: Request,
    user: Optional[User] = Depends(get_current_user),
    _feature: None = Depends(require_library()),
    db: Session = Depends(get_db),
):
    """View a published library item."""
    item = db.query(LibraryItem).filter(
        LibraryItem.slug == slug,
        LibraryItem.is_published == True,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Document not found")

    requires_login = user is None

    return templates.TemplateResponse(
        "library/detail.html",
        {
            "request": request,
            "user": user,
            "item": item,
            "requires_login": requires_login,
            "feature_name": "Copy to Draft",
            "feature_description": "Log in to copy this document into your own Ethics Policy or Legal Framework draft.",
            "document_type_map": DOCUMENT_TYPE_MAP,
            "jurisdiction_map": JURISDICTION_MAP,
        },
    )


@router.post("/{slug}/copy-to-ethics")
async def copy_to_ethics(
    slug: str,
    user: User = Depends(require_auth),
    _feature: None = Depends(require_library()),
    db: Session = Depends(get_db),
):
    """Create an EthicsPolicy draft from a library item."""
    from app.models.ethics_builder import EthicsPolicy

    item = db.query(LibraryItem).filter(
        LibraryItem.slug == slug,
        LibraryItem.is_published == True,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Document not found")

    # Create a new ethics policy with starter content
    policy = EthicsPolicy.create_policy(
        db,
        user_id=user.id,
        title=f"{item.title} (Copy)",
    )
    db.flush()

    # Get the draft version and override principles content with library item content
    draft = policy.versions[0]

    # Build attribution header
    attribution_parts = [f"*Source: {item.title}*"]
    if item.publisher:
        attribution_parts.append(f"*Publisher: {item.publisher}*")
    if item.source_url:
        attribution_parts.append(f"*URL: {item.source_url}*")
    attribution = "\n\n".join(attribution_parts)

    # Override the principles section with library content
    sections_data = draft.sections_data
    if sections_data and "principles" in sections_data:
        sections_data["principles"]["content"] = f"{attribution}\n\n---\n\n{item.content_markdown}"
        flag_modified(draft, "sections_data")

    draft.content_markdown = f"{attribution}\n\n---\n\n{item.content_markdown}"

    db.commit()

    return JSONResponse({"redirect_url": f"/ethics-builder/{policy.id}/edit"})


@router.post("/{slug}/copy-to-legal")
async def copy_to_legal(
    slug: str,
    user: User = Depends(require_auth),
    _feature: None = Depends(require_library()),
    db: Session = Depends(get_db),
):
    """Create a LegalFrameworkDoc draft from a library item."""
    from app.models.legal_builder import LegalFrameworkDoc

    item = db.query(LibraryItem).filter(
        LibraryItem.slug == slug,
        LibraryItem.is_published == True,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Document not found")

    # Build framework config with attribution
    framework_config = {
        "jurisdiction": item.jurisdiction or "global",
        "source_attribution": {
            "title": item.title,
            "publisher": item.publisher,
            "source_url": item.source_url,
            "jurisdiction": item.jurisdiction,
        },
    }

    doc = LegalFrameworkDoc.create_framework(
        db,
        user_id=user.id,
        title=f"{item.title} (Copy)",
        framework_config=framework_config,
    )
    db.flush()

    # Override narrative with library item content + attribution
    draft = doc.versions[0]

    attribution_parts = [f"*Source: {item.title}*"]
    if item.publisher:
        attribution_parts.append(f"*Publisher: {item.publisher}*")
    if item.source_url:
        attribution_parts.append(f"*URL: {item.source_url}*")
    attribution = "\n\n".join(attribution_parts)

    draft.narrative_markdown = f"{attribution}\n\n---\n\n{item.content_markdown}"

    db.commit()

    return JSONResponse({"redirect_url": f"/legal-builder/{doc.id}/edit"})
