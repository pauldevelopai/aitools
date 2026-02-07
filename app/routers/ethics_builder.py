"""AI Ethics Policy Builder routes.

Guided builder for creating structured AI ethics policies with
autosave, versioning, comparison, and clean HTML export.
"""
import difflib
from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.auth import User
from app.models.ethics_builder import (
    EthicsPolicy, EthicsPolicyVersion,
    ETHICS_SECTIONS, SECTION_MAP, SECTION_KEYS,
    compile_sections_to_markdown,
)
from app.dependencies import get_current_user, require_auth
from app.templates_engine import templates
from app.products.guards import require_feature


router = APIRouter(
    prefix="/ethics-builder",
    tags=["ethics_builder"],
)


# -------------------------------------------------------------------------
# Helper
# -------------------------------------------------------------------------

def _get_user_policy(db: Session, policy_id: str, user: User) -> EthicsPolicy:
    """Fetch a policy owned by the given user, or 404."""
    policy = db.query(EthicsPolicy).filter(
        EthicsPolicy.id == policy_id,
        EthicsPolicy.user_id == user.id,
    ).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


# -------------------------------------------------------------------------
# Pages
# -------------------------------------------------------------------------

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def ethics_builder_index(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _feature: None = Depends(require_feature("ethics_builder")),
):
    """Index — list user policies or show login prompt."""
    if not user:
        return templates.TemplateResponse(
            "ethics_builder/index.html",
            {
                "request": request,
                "user": None,
                "policies": [],
                "requires_login": True,
                "feature_name": "AI Ethics Policy Builder",
                "feature_description": "Build a structured AI ethics policy for your organisation, section by section.",
            },
        )

    policies = (
        db.query(EthicsPolicy)
        .filter(EthicsPolicy.user_id == user.id)
        .order_by(EthicsPolicy.updated_at.desc())
        .all()
    )

    # Attach draft/published info to each policy
    for p in policies:
        p._draft = p.get_current_draft(db)
        p._published = (
            db.query(EthicsPolicyVersion)
            .filter(
                EthicsPolicyVersion.policy_id == p.id,
                EthicsPolicyVersion.status == "published",
            )
            .first()
        )

    return templates.TemplateResponse(
        "ethics_builder/index.html",
        {
            "request": request,
            "user": user,
            "policies": policies,
            "requires_login": False,
        },
    )


@router.post("/new")
async def create_policy(
    request: Request,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _feature: None = Depends(require_feature("ethics_builder")),
):
    """Create a new policy with starter content, redirect to editor."""
    policy = EthicsPolicy.create_policy(
        db,
        user_id=user.id,
        title="AI Ethics Policy",
    )
    db.commit()
    return RedirectResponse(url=f"/ethics-builder/{policy.id}/edit", status_code=303)


@router.get("/{policy_id}/edit", response_class=HTMLResponse)
async def edit_policy(
    request: Request,
    policy_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _feature: None = Depends(require_feature("ethics_builder")),
):
    """Editor page — sidebar sections + textarea + autosave JS."""
    policy = _get_user_policy(db, policy_id, user)
    draft = policy.get_current_draft(db)
    if not draft:
        raise HTTPException(status_code=404, detail="No draft version found")

    return templates.TemplateResponse(
        "ethics_builder/editor.html",
        {
            "request": request,
            "user": user,
            "policy": policy,
            "version": draft,
            "sections": ETHICS_SECTIONS,
            "section_map": SECTION_MAP,
        },
    )


@router.post("/{policy_id}/autosave")
async def autosave_section(
    request: Request,
    policy_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """AJAX autosave — update a single section in the current draft."""
    policy = _get_user_policy(db, policy_id, user)
    draft = policy.get_current_draft(db)
    if not draft:
        return JSONResponse({"status": "error", "message": "No draft found"}, status_code=404)

    body = await request.json()
    section_key = body.get("section_key")
    content = body.get("content", "")

    if section_key not in SECTION_KEYS:
        return JSONResponse({"status": "error", "message": "Invalid section"}, status_code=400)

    draft.update_section(db, section_key, content)
    db.commit()

    return JSONResponse({
        "status": "ok",
        "saved_at": draft.sections_data[section_key]["updated_at"],
    })


@router.post("/{policy_id}/title")
async def update_title(
    request: Request,
    policy_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """AJAX title update."""
    policy = _get_user_policy(db, policy_id, user)
    body = await request.json()
    new_title = body.get("title", "").strip()
    if not new_title:
        return JSONResponse({"status": "error", "message": "Title required"}, status_code=400)

    policy.title = new_title
    db.commit()
    return JSONResponse({"status": "ok", "title": new_title})


@router.post("/{policy_id}/publish")
async def publish_policy(
    request: Request,
    policy_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _feature: None = Depends(require_feature("ethics_builder")),
):
    """Publish the current draft version."""
    policy = _get_user_policy(db, policy_id, user)
    draft = policy.get_current_draft(db)
    if not draft:
        raise HTTPException(status_code=404, detail="No draft to publish")

    draft.publish(db, published_by=user.id)
    db.commit()
    return RedirectResponse(url=f"/ethics-builder/{policy.id}", status_code=303)


@router.post("/{policy_id}/new-draft")
async def new_draft(
    request: Request,
    policy_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _feature: None = Depends(require_feature("ethics_builder")),
):
    """Create a new draft from the latest version."""
    policy = _get_user_policy(db, policy_id, user)

    # Don't create a new draft if one already exists
    existing_draft = policy.get_current_draft(db)
    if existing_draft:
        return RedirectResponse(url=f"/ethics-builder/{policy.id}/edit", status_code=303)

    policy.new_draft(db, created_by=user.id)
    db.commit()
    return RedirectResponse(url=f"/ethics-builder/{policy.id}/edit", status_code=303)


@router.get("/{policy_id}", response_class=HTMLResponse)
async def view_policy(
    request: Request,
    policy_id: str,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _feature: None = Depends(require_feature("ethics_builder")),
):
    """View the published policy (read-only)."""
    policy = db.query(EthicsPolicy).filter(EthicsPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    # Show published version if available, otherwise latest version
    version = None
    if policy.current_version_id:
        version = db.query(EthicsPolicyVersion).filter(
            EthicsPolicyVersion.id == policy.current_version_id
        ).first()

    if not version:
        # Fall back to latest version of any status
        version = (
            db.query(EthicsPolicyVersion)
            .filter(EthicsPolicyVersion.policy_id == policy.id)
            .order_by(EthicsPolicyVersion.version_number.desc())
            .first()
        )

    if not version:
        raise HTTPException(status_code=404, detail="No version found")

    is_owner = user and str(user.id) == str(policy.user_id)

    return templates.TemplateResponse(
        "ethics_builder/view.html",
        {
            "request": request,
            "user": user,
            "policy": policy,
            "version": version,
            "sections": ETHICS_SECTIONS,
            "section_map": SECTION_MAP,
            "is_owner": is_owner,
        },
    )


@router.get("/{policy_id}/versions", response_class=HTMLResponse)
async def version_history(
    request: Request,
    policy_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _feature: None = Depends(require_feature("ethics_builder")),
):
    """Version history list with compare picker."""
    policy = _get_user_policy(db, policy_id, user)
    versions = policy.list_versions(db)

    return templates.TemplateResponse(
        "ethics_builder/versions.html",
        {
            "request": request,
            "user": user,
            "policy": policy,
            "versions": versions,
        },
    )


@router.get("/{policy_id}/versions/{version_num}", response_class=HTMLResponse)
async def view_version(
    request: Request,
    policy_id: str,
    version_num: int,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _feature: None = Depends(require_feature("ethics_builder")),
):
    """View a specific version."""
    policy = _get_user_policy(db, policy_id, user)
    version = (
        db.query(EthicsPolicyVersion)
        .filter(
            EthicsPolicyVersion.policy_id == policy.id,
            EthicsPolicyVersion.version_number == version_num,
        )
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    return templates.TemplateResponse(
        "ethics_builder/view.html",
        {
            "request": request,
            "user": user,
            "policy": policy,
            "version": version,
            "sections": ETHICS_SECTIONS,
            "section_map": SECTION_MAP,
            "is_owner": True,
        },
    )


@router.get("/{policy_id}/compare", response_class=HTMLResponse)
async def compare_versions(
    request: Request,
    policy_id: str,
    v1: int,
    v2: int,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    _feature: None = Depends(require_feature("ethics_builder")),
):
    """Side-by-side diff of two versions."""
    policy = _get_user_policy(db, policy_id, user)

    ver1 = (
        db.query(EthicsPolicyVersion)
        .filter(EthicsPolicyVersion.policy_id == policy.id, EthicsPolicyVersion.version_number == v1)
        .first()
    )
    ver2 = (
        db.query(EthicsPolicyVersion)
        .filter(EthicsPolicyVersion.policy_id == policy.id, EthicsPolicyVersion.version_number == v2)
        .first()
    )
    if not ver1 or not ver2:
        raise HTTPException(status_code=404, detail="Version not found")

    # Build per-section diffs
    section_diffs = []
    for s in ETHICS_SECTIONS:
        key = s["key"]
        content1 = (ver1.sections_data or {}).get(key, {}).get("content", "")
        content2 = (ver2.sections_data or {}).get(key, {}).get("content", "")

        if content1 == content2:
            section_diffs.append({
                "key": key,
                "title": s["title"],
                "changed": False,
                "diff_lines": [],
            })
        else:
            diff = list(difflib.unified_diff(
                content1.splitlines(keepends=True),
                content2.splitlines(keepends=True),
                fromfile=f"v{v1}",
                tofile=f"v{v2}",
                lineterm="",
            ))
            section_diffs.append({
                "key": key,
                "title": s["title"],
                "changed": True,
                "diff_lines": diff,
            })

    return templates.TemplateResponse(
        "ethics_builder/compare.html",
        {
            "request": request,
            "user": user,
            "policy": policy,
            "ver1": ver1,
            "ver2": ver2,
            "v1": v1,
            "v2": v2,
            "section_diffs": section_diffs,
        },
    )


@router.get("/{policy_id}/export", response_class=HTMLResponse)
async def export_policy(
    request: Request,
    policy_id: str,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _feature: None = Depends(require_feature("ethics_builder")),
):
    """Clean printable HTML export (standalone, no base.html)."""
    policy = db.query(EthicsPolicy).filter(EthicsPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    # Use published version if available, otherwise latest
    version = None
    if policy.current_version_id:
        version = db.query(EthicsPolicyVersion).filter(
            EthicsPolicyVersion.id == policy.current_version_id
        ).first()

    if not version:
        version = (
            db.query(EthicsPolicyVersion)
            .filter(EthicsPolicyVersion.policy_id == policy.id)
            .order_by(EthicsPolicyVersion.version_number.desc())
            .first()
        )

    if not version:
        raise HTTPException(status_code=404, detail="No version found")

    return templates.TemplateResponse(
        "ethics_builder/export.html",
        {
            "request": request,
            "user": user,
            "policy": policy,
            "version": version,
            "sections": ETHICS_SECTIONS,
            "section_map": SECTION_MAP,
        },
    )
