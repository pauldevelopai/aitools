"""Admin-only Google Drive integration router."""
import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_admin
from app.models.auth import User
from app.models.google_drive import GoogleConnection, GoogleSyncItem
from app.models.organization_profile import OrganizationProfile
from app.settings import settings
from app.templates_engine import templates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/google", tags=["google-drive"])


# ── Helpers ─────────────────────────────────────────────────────────────────

def _get_connection(db: Session, user: User) -> Optional[GoogleConnection]:
    return db.query(GoogleConnection).filter(
        GoogleConnection.user_id == user.id,
        GoogleConnection.is_active == True,
    ).first()


def _callback_uri(request: Request) -> str:
    """Build the OAuth callback URI from the current request."""
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.url.netloc)
    return f"{scheme}://{host}/admin/google/callback"


# ── Dashboard ───────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def google_dashboard(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Google Drive connection dashboard."""
    connection = _get_connection(db, user)

    sync_items = []
    if connection:
        sync_items = db.query(GoogleSyncItem).filter(
            GoogleSyncItem.connection_id == connection.id
        ).order_by(GoogleSyncItem.created_at.desc()).all()

    organizations = db.query(OrganizationProfile).order_by(OrganizationProfile.name).all()

    google_configured = bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)

    return templates.TemplateResponse(
        "admin/google_drive.html",
        {
            "request": request,
            "user": user,
            "active_admin_page": "google_drive",
            "connection": connection,
            "sync_items": sync_items,
            "organizations": organizations,
            "google_configured": google_configured,
        },
    )


# ── OAuth flow ──────────────────────────────────────────────────────────────

@router.get("/connect")
async def google_connect(
    request: Request,
    user: User = Depends(require_admin),
):
    """Redirect admin to Google OAuth consent screen."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(400, "Google API credentials not configured")

    from app.services.google_auth import get_auth_url

    redirect_uri = _callback_uri(request)
    url = get_auth_url(redirect_uri)
    return RedirectResponse(url)


@router.get("/callback")
async def google_callback(
    request: Request,
    code: str = Query(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Handle Google OAuth callback, store encrypted tokens."""
    from app.services.google_auth import exchange_code

    redirect_uri = _callback_uri(request)

    try:
        creds = exchange_code(code, redirect_uri)
    except Exception as e:
        logger.error(f"Google OAuth exchange failed: {e}")
        raise HTTPException(400, f"OAuth exchange failed: {e}")

    # Upsert connection
    connection = db.query(GoogleConnection).filter(
        GoogleConnection.user_id == user.id
    ).first()

    if connection:
        connection.set_tokens(creds["access_token"], creds["refresh_token"])
        connection.token_expiry = creds["expiry"]
        connection.google_email = creds["email"]
        connection.scopes = creds["scopes"]
        connection.is_active = True
    else:
        connection = GoogleConnection(user_id=user.id)
        connection.set_tokens(creds["access_token"], creds["refresh_token"])
        connection.token_expiry = creds["expiry"]
        connection.google_email = creds["email"]
        connection.scopes = creds["scopes"]
        db.add(connection)

    db.commit()
    logger.info(f"Google connected for admin {user.email} ({creds['email']})")

    return RedirectResponse("/admin/google", status_code=303)


# ── Disconnect ──────────────────────────────────────────────────────────────

@router.post("/disconnect")
async def google_disconnect(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Remove Google connection and all sync items."""
    connection = _get_connection(db, user)
    if not connection:
        raise HTTPException(404, "No active Google connection")

    # Delete sync items first (CASCADE should handle, but be explicit)
    db.query(GoogleSyncItem).filter(
        GoogleSyncItem.connection_id == connection.id
    ).delete()
    db.delete(connection)
    db.commit()

    logger.info(f"Google disconnected for admin {user.email}")
    return RedirectResponse("/admin/google", status_code=303)


# ── Browse Drive files (AJAX) ──────────────────────────────────────────────

@router.get("/browse", response_class=JSONResponse)
async def browse_drive(
    request: Request,
    folder_id: Optional[str] = Query(None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List files in a Drive folder (JSON for AJAX)."""
    connection = _get_connection(db, user)
    if not connection:
        raise HTTPException(400, "Not connected to Google Drive")

    from app.services.google_ingest import list_drive_files

    try:
        files = list_drive_files(db, connection, folder_id)
    except Exception as e:
        logger.error(f"Drive browse failed: {e}")
        raise HTTPException(500, f"Failed to list files: {e}")

    return {"files": files, "folder_id": folder_id}


# ── Ingest selected files ──────────────────────────────────────────────────

@router.post("/ingest", response_class=JSONResponse)
async def ingest_files(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Ingest selected Google Drive files into the chosen target."""
    connection = _get_connection(db, user)
    if not connection:
        raise HTTPException(400, "Not connected to Google Drive")

    body = await request.json()
    files: List[dict] = body.get("files", [])
    target_type: str = body.get("target_type", "library")
    target_id: Optional[str] = body.get("target_id")

    if not files:
        raise HTTPException(400, "No files selected")

    if target_type not in ("library", "organization"):
        raise HTTPException(400, "Invalid target_type")

    if target_type == "organization" and not target_id:
        raise HTTPException(400, "target_id required for organization target")

    from app.services.google_ingest import ingest_google_file

    results = []

    for f in files:
        file_id = f.get("id")
        file_name = f.get("name", "Unknown")
        mime_type = f.get("mimeType", "")

        # Skip folders
        if mime_type == "application/vnd.google-apps.folder":
            continue

        # Create or find sync item
        existing = db.query(GoogleSyncItem).filter(
            GoogleSyncItem.connection_id == connection.id,
            GoogleSyncItem.google_file_id == file_id,
        ).first()

        if existing:
            sync_item = existing
            sync_item.target_type = target_type
            sync_item.target_id = target_id if target_id else None
        else:
            sync_item = GoogleSyncItem(
                connection_id=connection.id,
                google_file_id=file_id,
                google_file_name=file_name,
                google_mime_type=mime_type,
                target_type=target_type,
                target_id=target_id if target_id else None,
            )
            db.add(sync_item)
            db.flush()

        ingest_google_file(db, sync_item, connection)

        results.append({
            "file_name": file_name,
            "status": sync_item.sync_status,
            "error": sync_item.error_message,
        })

    return {"results": results}


# ── Re-sync single item ────────────────────────────────────────────────────

@router.post("/sync/{item_id}", response_class=JSONResponse)
async def sync_single(
    item_id: UUID,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Re-sync a single Google Drive file."""
    connection = _get_connection(db, user)
    if not connection:
        raise HTTPException(400, "Not connected")

    sync_item = db.query(GoogleSyncItem).filter(
        GoogleSyncItem.id == item_id,
        GoogleSyncItem.connection_id == connection.id,
    ).first()

    if not sync_item:
        raise HTTPException(404, "Sync item not found")

    from app.services.google_ingest import ingest_google_file
    ingest_google_file(db, sync_item, connection)

    return {
        "status": sync_item.sync_status,
        "error": sync_item.error_message,
        "last_synced_at": str(sync_item.last_synced_at) if sync_item.last_synced_at else None,
    }


# ── Re-sync all ────────────────────────────────────────────────────────────

@router.post("/sync-all", response_class=JSONResponse)
async def sync_all(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Re-sync all items for the current connection."""
    connection = _get_connection(db, user)
    if not connection:
        raise HTTPException(400, "Not connected")

    from app.services.google_ingest import sync_all_items
    stats = sync_all_items(db, connection)

    return stats


# ── Delete sync item ───────────────────────────────────────────────────────

@router.post("/delete/{item_id}", response_class=JSONResponse)
async def delete_sync_item(
    item_id: UUID,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Remove a sync item (does not delete the ingested content)."""
    connection = _get_connection(db, user)
    if not connection:
        raise HTTPException(400, "Not connected")

    sync_item = db.query(GoogleSyncItem).filter(
        GoogleSyncItem.id == item_id,
        GoogleSyncItem.connection_id == connection.id,
    ).first()

    if not sync_item:
        raise HTTPException(404, "Sync item not found")

    db.delete(sync_item)
    db.commit()

    return {"deleted": True}
