"""AI Legal Framework Builder routes.

Guided builder for creating structured AI legal compliance frameworks
with setup wizard, narrative + checklist editor, versioning, comparison,
and clean HTML export.
"""
import difflib
from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.auth import User
from app.models.legal_builder import (
    LegalFrameworkDoc, LegalFrameworkVersion,
    JURISDICTIONS, JURISDICTION_KEYS,
    SECTORS, SECTOR_KEYS,
    AI_USE_CASES, USE_CASE_KEYS,
    OBLIGATION_CATEGORIES, CATEGORY_KEYS,
    CHECKLIST_STATUSES,
)
from app.dependencies import get_current_user, require_auth
from app.templates_engine import templates
from app.products.guards import require_feature


router = APIRouter(
    prefix="/legal-builder",
    tags=["legal_builder"],
)


# -------------------------------------------------------------------------
# Helper
# -------------------------------------------------------------------------

def _get_user_framework(db: Session, framework_id: str, user: User) -> LegalFrameworkDoc:
    """Fetch a framework owned by the given user, or 404."""
    framework = db.query(LegalFrameworkDoc).filter(
        LegalFrameworkDoc.id == framework_id,
        LegalFrameworkDoc.user_id == user.id,
    ).first()
    if not framework:
        raise HTTPException(status_code=404, detail="Framework not found")
    return framework


# -------------------------------------------------------------------------
# Pages
# -------------------------------------------------------------------------

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def legal_builder_index(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _feature: None = Depends(require_feature("legal_builder")),
):
    """Index — list user frameworks or show login prompt."""
    if not user:
        return templates.TemplateResponse(
            "legal_builder/index.html",
            {
                "request": request,
                "user": None,
                "frameworks": [],
                "requires_login": True,
                "feature_name": "AI Legal Framework Builder",
                "feature_description": "Map the laws and regulations affecting your AI use and build an actionable compliance checklist.",
            },
        )

    frameworks = (
        db.query(LegalFrameworkDoc)
        .filter(LegalFrameworkDoc.user_id == user.id)
        .order_by(LegalFrameworkDoc.updated_at.desc())
        .all()
    )

    # Attach draft/published info
    for f in frameworks:
        f._draft = f.get_current_draft(db)
        f._published = (
            db.query(LegalFrameworkVersion)
            .filter(
                LegalFrameworkVersion.framework_id == f.id,
                LegalFrameworkVersion.status == "published",
            )
            .first()
        )

    return templates.TemplateResponse(
        "legal_builder/index.html",
        {
            "request": request,
            "user": user,
            "frameworks": frameworks,
            "requires_login": False,
        },
    )


@router.get("/setup", response_class=HTMLResponse)
async def setup_wizard(
    request: Request,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _feature: None = Depends(require_feature("legal_builder")),
):
    """Setup wizard page — jurisdiction/sector/use-case selection."""
    return templates.TemplateResponse(
        "legal_builder/setup.html",
        {
            "request": request,
            "user": user,
            "jurisdictions": JURISDICTIONS,
            "sectors": SECTORS,
            "use_cases": AI_USE_CASES,
        },
    )


@router.post("/create")
async def create_framework(
    request: Request,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _feature: None = Depends(require_feature("legal_builder")),
):
    """Process setup form, create framework + v1 draft, redirect to editor."""
    form = await request.form()

    title = form.get("title", "").strip() or "AI Legal Framework"
    jurisdictions = form.getlist("jurisdictions")
    sector = form.get("sector", "")
    use_cases = form.getlist("use_cases")

    # Validate
    jurisdictions = [j for j in jurisdictions if j in JURISDICTION_KEYS]
    if sector not in SECTOR_KEYS:
        sector = "other"
    use_cases = [u for u in use_cases if u in USE_CASE_KEYS]

    if not jurisdictions:
        jurisdictions = ["global"]

    framework_config = {
        "jurisdictions": jurisdictions,
        "sector": sector,
        "use_cases": use_cases,
    }

    doc = LegalFrameworkDoc.create_framework(
        db,
        user_id=user.id,
        title=title,
        framework_config=framework_config,
    )
    db.commit()
    return RedirectResponse(url=f"/legal-builder/{doc.id}/edit", status_code=303)


@router.get("/{framework_id}/edit", response_class=HTMLResponse)
async def edit_framework(
    request: Request,
    framework_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _feature: None = Depends(require_feature("legal_builder")),
):
    """Editor page — two-tab: narrative + checklist."""
    framework = _get_user_framework(db, framework_id, user)
    draft = framework.get_current_draft(db)
    if not draft:
        raise HTTPException(status_code=404, detail="No draft version found")

    return templates.TemplateResponse(
        "legal_builder/editor.html",
        {
            "request": request,
            "user": user,
            "framework": framework,
            "version": draft,
            "categories": OBLIGATION_CATEGORIES,
            "statuses": CHECKLIST_STATUSES,
        },
    )


@router.post("/{framework_id}/autosave-narrative")
async def autosave_narrative(
    request: Request,
    framework_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """AJAX save narrative markdown."""
    framework = _get_user_framework(db, framework_id, user)
    draft = framework.get_current_draft(db)
    if not draft:
        return JSONResponse({"status": "error", "message": "No draft found"}, status_code=404)

    body = await request.json()
    content = body.get("content", "")

    draft.update_narrative(db, content)
    db.commit()

    return JSONResponse({"status": "ok"})


@router.post("/{framework_id}/autosave-checklist")
async def autosave_checklist(
    request: Request,
    framework_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """AJAX save single checklist item field."""
    framework = _get_user_framework(db, framework_id, user)
    draft = framework.get_current_draft(db)
    if not draft:
        return JSONResponse({"status": "error", "message": "No draft found"}, status_code=404)

    body = await request.json()
    item_id = body.get("item_id")
    field = body.get("field")
    value = body.get("value")

    if not item_id or not field:
        return JSONResponse({"status": "error", "message": "item_id and field required"}, status_code=400)

    allowed_fields = {"status", "notes", "evidence_links", "obligation", "description", "category"}
    if field not in allowed_fields:
        return JSONResponse({"status": "error", "message": f"Invalid field: {field}"}, status_code=400)

    if field == "status" and value not in CHECKLIST_STATUSES:
        return JSONResponse({"status": "error", "message": "Invalid status"}, status_code=400)

    draft.update_checklist_item(db, item_id, {field: value})
    db.commit()

    return JSONResponse({"status": "ok"})


@router.post("/{framework_id}/title")
async def update_title(
    request: Request,
    framework_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """AJAX title update."""
    framework = _get_user_framework(db, framework_id, user)
    body = await request.json()
    new_title = body.get("title", "").strip()
    if not new_title:
        return JSONResponse({"status": "error", "message": "Title required"}, status_code=400)

    framework.title = new_title
    db.commit()
    return JSONResponse({"status": "ok", "title": new_title})


@router.post("/{framework_id}/publish")
async def publish_framework(
    request: Request,
    framework_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _feature: None = Depends(require_feature("legal_builder")),
):
    """Publish the current draft version."""
    framework = _get_user_framework(db, framework_id, user)
    draft = framework.get_current_draft(db)
    if not draft:
        raise HTTPException(status_code=404, detail="No draft to publish")

    draft.publish(db, published_by=user.id)
    db.commit()
    return RedirectResponse(url=f"/legal-builder/{framework.id}", status_code=303)


@router.post("/{framework_id}/new-draft")
async def new_draft(
    request: Request,
    framework_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _feature: None = Depends(require_feature("legal_builder")),
):
    """Create a new draft from the latest version."""
    framework = _get_user_framework(db, framework_id, user)

    existing_draft = framework.get_current_draft(db)
    if existing_draft:
        return RedirectResponse(url=f"/legal-builder/{framework.id}/edit", status_code=303)

    framework.new_draft(db, created_by=user.id)
    db.commit()
    return RedirectResponse(url=f"/legal-builder/{framework.id}/edit", status_code=303)


@router.get("/{framework_id}", response_class=HTMLResponse)
async def view_framework(
    request: Request,
    framework_id: str,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _feature: None = Depends(require_feature("legal_builder")),
):
    """View the published framework (read-only)."""
    framework = db.query(LegalFrameworkDoc).filter(LegalFrameworkDoc.id == framework_id).first()
    if not framework:
        raise HTTPException(status_code=404, detail="Framework not found")

    version = None
    if framework.current_version_id:
        version = db.query(LegalFrameworkVersion).filter(
            LegalFrameworkVersion.id == framework.current_version_id
        ).first()

    if not version:
        version = (
            db.query(LegalFrameworkVersion)
            .filter(LegalFrameworkVersion.framework_id == framework.id)
            .order_by(LegalFrameworkVersion.version_number.desc())
            .first()
        )

    if not version:
        raise HTTPException(status_code=404, detail="No version found")

    is_owner = user and str(user.id) == str(framework.user_id)

    return templates.TemplateResponse(
        "legal_builder/view.html",
        {
            "request": request,
            "user": user,
            "framework": framework,
            "version": version,
            "categories": OBLIGATION_CATEGORIES,
            "statuses": CHECKLIST_STATUSES,
            "is_owner": is_owner,
        },
    )


@router.get("/{framework_id}/versions", response_class=HTMLResponse)
async def version_history(
    request: Request,
    framework_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _feature: None = Depends(require_feature("legal_builder")),
):
    """Version history list with compare picker."""
    framework = _get_user_framework(db, framework_id, user)
    versions = framework.list_versions(db)

    return templates.TemplateResponse(
        "legal_builder/versions.html",
        {
            "request": request,
            "user": user,
            "framework": framework,
            "versions": versions,
        },
    )


@router.get("/{framework_id}/versions/{version_num}", response_class=HTMLResponse)
async def view_version(
    request: Request,
    framework_id: str,
    version_num: int,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _feature: None = Depends(require_feature("legal_builder")),
):
    """View a specific version."""
    framework = _get_user_framework(db, framework_id, user)
    version = (
        db.query(LegalFrameworkVersion)
        .filter(
            LegalFrameworkVersion.framework_id == framework.id,
            LegalFrameworkVersion.version_number == version_num,
        )
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    return templates.TemplateResponse(
        "legal_builder/view.html",
        {
            "request": request,
            "user": user,
            "framework": framework,
            "version": version,
            "categories": OBLIGATION_CATEGORIES,
            "statuses": CHECKLIST_STATUSES,
            "is_owner": True,
        },
    )


@router.get("/{framework_id}/compare", response_class=HTMLResponse)
async def compare_versions(
    request: Request,
    framework_id: str,
    v1: int,
    v2: int,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _feature: None = Depends(require_feature("legal_builder")),
):
    """Side-by-side diff of two versions (narrative + checklist changes)."""
    framework = _get_user_framework(db, framework_id, user)

    ver1 = (
        db.query(LegalFrameworkVersion)
        .filter(LegalFrameworkVersion.framework_id == framework.id, LegalFrameworkVersion.version_number == v1)
        .first()
    )
    ver2 = (
        db.query(LegalFrameworkVersion)
        .filter(LegalFrameworkVersion.framework_id == framework.id, LegalFrameworkVersion.version_number == v2)
        .first()
    )
    if not ver1 or not ver2:
        raise HTTPException(status_code=404, detail="Version not found")

    # Narrative diff
    text1 = ver1.narrative_markdown or ""
    text2 = ver2.narrative_markdown or ""
    narrative_changed = text1 != text2
    narrative_diff = []
    if narrative_changed:
        narrative_diff = list(difflib.unified_diff(
            text1.splitlines(keepends=True),
            text2.splitlines(keepends=True),
            fromfile=f"v{v1}",
            tofile=f"v{v2}",
            lineterm="",
        ))

    # Checklist diff — match items by UUID id, report field changes
    items1 = {item["id"]: item for item in (ver1.checklist_items or [])}
    items2 = {item["id"]: item for item in (ver2.checklist_items or [])}
    all_ids = list(dict.fromkeys(list(items1.keys()) + list(items2.keys())))

    checklist_changes = []
    for item_id in all_ids:
        i1 = items1.get(item_id)
        i2 = items2.get(item_id)

        if i1 and not i2:
            checklist_changes.append({
                "type": "removed",
                "obligation": i1.get("obligation", ""),
                "details": [],
            })
        elif i2 and not i1:
            checklist_changes.append({
                "type": "added",
                "obligation": i2.get("obligation", ""),
                "details": [],
            })
        elif i1 and i2:
            changes = []
            for field in ["status", "notes", "obligation", "description", "category"]:
                if i1.get(field) != i2.get(field):
                    changes.append({
                        "field": field,
                        "old": i1.get(field, ""),
                        "new": i2.get(field, ""),
                    })
            if changes:
                checklist_changes.append({
                    "type": "changed",
                    "obligation": i2.get("obligation", ""),
                    "details": changes,
                })

    return templates.TemplateResponse(
        "legal_builder/compare.html",
        {
            "request": request,
            "user": user,
            "framework": framework,
            "ver1": ver1,
            "ver2": ver2,
            "v1": v1,
            "v2": v2,
            "narrative_changed": narrative_changed,
            "narrative_diff": narrative_diff,
            "checklist_changes": checklist_changes,
        },
    )


@router.get("/{framework_id}/export", response_class=HTMLResponse)
async def export_framework(
    request: Request,
    framework_id: str,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _feature: None = Depends(require_feature("legal_builder")),
):
    """Clean printable HTML export (standalone, no base.html)."""
    framework = db.query(LegalFrameworkDoc).filter(LegalFrameworkDoc.id == framework_id).first()
    if not framework:
        raise HTTPException(status_code=404, detail="Framework not found")

    version = None
    if framework.current_version_id:
        version = db.query(LegalFrameworkVersion).filter(
            LegalFrameworkVersion.id == framework.current_version_id
        ).first()

    if not version:
        version = (
            db.query(LegalFrameworkVersion)
            .filter(LegalFrameworkVersion.framework_id == framework.id)
            .order_by(LegalFrameworkVersion.version_number.desc())
            .first()
        )

    if not version:
        raise HTTPException(status_code=404, detail="No version found")

    # Build category map for display
    category_map = {c["key"]: c["label"] for c in OBLIGATION_CATEGORIES}

    return templates.TemplateResponse(
        "legal_builder/export.html",
        {
            "request": request,
            "user": user,
            "framework": framework,
            "version": version,
            "category_map": category_map,
        },
    )
