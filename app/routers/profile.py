"""User profile routes."""
from typing import Optional
from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.auth import User
from app.dependencies import require_auth_page
from app.middleware.csrf import CSRFProtectionMiddleware


router = APIRouter(tags=["profile"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    response: Response,
    success: Optional[str] = None,
    user: User = Depends(require_auth_page),
):
    """Profile page."""
    csrf_token = CSRFProtectionMiddleware.generate_token()
    template_response = templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": user,
            "csrf_token": csrf_token,
            "success": success,
        }
    )
    CSRFProtectionMiddleware.set_csrf_cookie(template_response, csrf_token)
    return template_response


@router.post("/profile/update")
async def update_profile(
    request: Request,
    display_name: Optional[str] = Form(None),
    organisation: Optional[str] = Form(None),
    organisation_type: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    interests: Optional[str] = Form(None),
    ai_experience_level: Optional[str] = Form(None),
    user: User = Depends(require_auth_page),
    db: Session = Depends(get_db),
):
    """Update user profile."""
    user.display_name = display_name.strip() if display_name else None
    user.organisation = organisation.strip() if organisation else None
    user.organisation_type = organisation_type if organisation_type else None
    user.role = role.strip() if role else None
    user.country = country.strip() if country else None
    user.interests = interests.strip() if interests else None
    user.ai_experience_level = ai_experience_level if ai_experience_level else None

    db.commit()

    return RedirectResponse(url="/profile?success=1", status_code=303)
