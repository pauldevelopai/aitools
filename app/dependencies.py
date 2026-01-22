"""FastAPI dependencies for authentication."""
from typing import Optional
from fastapi import Cookie, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.auth import User
from app.services.auth import get_user_from_session


async def get_current_user(
    session_token: Optional[str] = Cookie(None, alias="session"),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user from session cookie (optional).

    Returns:
        User object if authenticated, None otherwise
    """
    if not session_token:
        return None

    user = get_user_from_session(db, session_token)
    return user


async def require_auth(
    session_token: Optional[str] = Cookie(None, alias="session"),
    db: Session = Depends(get_db)
) -> User:
    """
    Require authentication (for API endpoints).

    Returns:
        User object if authenticated

    Raises:
        HTTPException 401 if not authenticated
    """
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    user = get_user_from_session(db, session_token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )

    return user


async def require_auth_page(
    session_token: Optional[str] = Cookie(None, alias="session"),
    db: Session = Depends(get_db)
) -> User:
    """
    Require authentication for page routes (redirects to login).

    Returns:
        User object if authenticated

    Raises:
        HTTPException with redirect to login page
    """
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            detail="Redirect to login",
            headers={"Location": "/login"}
        )

    user = get_user_from_session(db, session_token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            detail="Redirect to login",
            headers={"Location": "/login"}
        )

    return user
