"""Source citation routes (grounded link extracts from batch PDFs)."""
from typing import Optional
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse

from app.models.auth import User
from app.dependencies import get_current_user
from app.services.kit_loader import (
    get_all_sources, get_source_batch, search_sources
)
from app.templates_engine import templates


router = APIRouter(prefix="/sources", tags=["sources"])


def infer_source_type(url: str) -> str:
    """Infer source type from URL."""
    url_lower = (url or "").lower()
    if any(x in url_lower for x in ['.pdf', 'oecd.org', 'linuxfoundation.org', 'unesco.org', 'artificialintelligenceact.eu']):
        return 'report'
    elif any(x in url_lower for x in ['researchgate.net', 'arxiv.org', 'doi.org', 'academic', 'journal', 'springer', 'wiley']):
        return 'study'
    return 'article'


@router.get("", response_class=HTMLResponse)
async def sources_index(
    request: Request,
    batch: Optional[str] = Query(None),
    q: Optional[str] = None,
    source_type: Optional[str] = Query(None),
    user: Optional[User] = Depends(get_current_user),
):
    """List all grounded citation sources with optional batch/search/type filter."""
    # Convert batch to int if provided (handle empty string)
    batch_num = None
    if batch and batch.strip():
        try:
            batch_num = int(batch)
            if batch_num < 1 or batch_num > 12:
                batch_num = None
        except ValueError:
            batch_num = None

    all_data = get_all_sources()

    if q:
        entries = search_sources(q)
    elif batch_num:
        batch_data = get_source_batch(batch_num)
        entries = batch_data["entries"] if batch_data else []
    else:
        entries = all_data.get("entries", [])

    # Filter by source type if specified
    if source_type and source_type in ('article', 'report', 'study'):
        entries = [e for e in entries if infer_source_type(e.get("url", "")) == source_type]

    return templates.TemplateResponse(
        "sources/index.html",
        {
            "request": request,
            "user": user,
            "entries": entries,
            "batches": all_data.get("batches", []),
            "total_entries": all_data.get("total_entries", 0),
            "selected_batch": batch_num,
            "source_type": source_type or "",
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
