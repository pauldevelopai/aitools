"""Locale middleware.

Sets request.state.locale based on user preference or Accept-Language header.
Makes the translation function available to templates.
"""
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.services.i18n import get_locale, DEFAULT_LANGUAGE


class LocaleMiddleware(BaseHTTPMiddleware):
    """Middleware to set locale on each request."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = logging.getLogger("app.locale")

    async def dispatch(self, request, call_next):
        """Set locale on request state."""
        # Determine locale (will check user pref + Accept-Language)
        request.state.locale = get_locale(request)
        return await call_next(request)
