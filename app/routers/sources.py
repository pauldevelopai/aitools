"""Source citation routes (grounded link extracts from batch PDFs)."""
from typing import Optional
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.models.auth import User
from app.dependencies import get_current_user
from app.services.kit_loader import (
    get_all_sources, get_source_batch, search_sources
)


router = APIRouter(prefix="/sources", tags=["sources"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def sources_index(
    request: Request,
    batch: Optional[int] = Query(None, ge=1, le=12),
    q: Optional[str] = None,
    user: Optional[User] = Depends(get_current_user),
):
    """List all grounded citation sources with optional batch/search filter."""
    all_data = get_all_sources()

    if q:
        entries = search_sources(q)
    elif batch:
        batch_data = get_source_batch(batch)
        entries = batch_data["entries"] if batch_data else []
    else:
        entries = all_data.get("entries", [])

    return templates.TemplateResponse(
        "sources/index.html",
        {
            "request": request,
            "user": user,
            "entries": entries,
            "batches": all_data.get("batches", []),
            "total_entries": all_data.get("total_entries", 0),
            "selected_batch": batch,
            "q": q or "",
        }
    )


@router.get("/batch/{batch_num}", response_class=HTMLResponse)
async def source_batch_detail(
    request: Request,
    batch_num: int,
    user: Optional[User] = Depends(get_current_user),
):
    """Show all entries from a specific batch."""
    batch_data = get_source_batch(batch_num)
    all_data = get_all_sources()

    return templates.TemplateResponse(
        "sources/batch.html",
        {
            "request": request,
            "user": user,
            "batch": batch_data,
            "batch_num": batch_num,
            "batches": all_data.get("batches", []),
        }
    )
