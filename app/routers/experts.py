"""Expert Directory router — curated list of AI & journalism experts."""
from typing import Optional
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.models.auth import User
from app.dependencies import get_current_user
from app.templates_engine import templates
from app.products.guards import require_experts
from app.services.kit_loader import get_experts

router = APIRouter(prefix="/experts", tags=["experts"])


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def experts_index(
    request: Request,
    q: Optional[str] = None,
    user: Optional[User] = Depends(get_current_user),
    _: None = Depends(require_experts()),
):
    """Expert directory page with optional search filtering."""
    experts = get_experts()

    # Server-side filtering if query provided
    filtered = experts
    if q:
        q_lower = q.lower()
        filtered = [
            e for e in experts
            if q_lower in e.get("name", "").lower()
            or q_lower in e.get("description", "").lower()
        ]

    return templates.TemplateResponse(
        "experts/index.html",
        {
            "request": request,
            "user": user,
            "experts": filtered,
            "total_experts": len(experts),
            "q": q or "",
        },
    )
