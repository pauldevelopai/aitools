"""Glossary router — searchable AI & journalism glossary."""
from typing import Optional
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.models.auth import User
from app.dependencies import get_current_user
from app.templates_engine import templates
from app.products.guards import require_glossary
from app.services.kit_loader import get_glossary_terms

router = APIRouter(prefix="/glossary", tags=["glossary"])


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def glossary_index(
    request: Request,
    q: Optional[str] = None,
    user: Optional[User] = Depends(get_current_user),
    _: None = Depends(require_glossary()),
):
    """Searchable glossary page with alphabet quick-jump."""
    import json as json_mod

    terms = get_glossary_terms()

    # Sort alphabetically
    terms.sort(key=lambda t: t.get("term", "").lower())

    # Build alphabet list from available first letters
    letters = sorted(set(
        t["term"][0].upper() for t in terms if t.get("term")
    ))

    # Prepare terms JSON for tooltip component
    terms_json = json_mod.dumps([
        {"term": t["term"], "definition": t["definition"], "slug": t["slug"]}
        for t in terms
    ])

    return templates.TemplateResponse(
        "glossary/index.html",
        {
            "request": request,
            "user": user,
            "terms": terms,
            "total_terms": len(terms),
            "letters": letters,
            "terms_json": terms_json,
            "q": q or "",
        },
    )
