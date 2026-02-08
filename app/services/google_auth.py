"""Google OAuth2 authentication and API client helpers."""
import logging
from datetime import datetime, timezone, timedelta

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.models.google_drive import GoogleConnection, encrypt_token
from app.settings import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
]


def _client_config() -> dict:
    """Build the OAuth2 client config dict from settings."""
    return {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def get_auth_url(redirect_uri: str) -> str:
    """Build the Google OAuth2 consent URL."""
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES)
    flow.redirect_uri = redirect_uri
    url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return url


def exchange_code(code: str, redirect_uri: str) -> dict:
    """Exchange an authorization code for credentials.

    Returns dict with keys: access_token, refresh_token, expiry, email, scopes.
    """
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES)
    flow.redirect_uri = redirect_uri
    flow.fetch_token(code=code)

    creds = flow.credentials
    # Fetch the connected Google email
    service = build("oauth2", "v2", credentials=creds)
    user_info = service.userinfo().get().execute()

    return {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "expiry": creds.expiry,
        "email": user_info.get("email", ""),
        "scopes": " ".join(creds.scopes or SCOPES),
    }


def _credentials_from_connection(connection: GoogleConnection) -> Credentials:
    """Build a google.oauth2.credentials.Credentials from a stored connection."""
    return Credentials(
        token=connection.get_access_token(),
        refresh_token=connection.get_refresh_token(),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=connection.scopes.split() if connection.scopes else SCOPES,
    )


def refresh_token_if_needed(db: Session, connection: GoogleConnection) -> Credentials:
    """Return valid credentials, refreshing the access token if expired."""
    creds = _credentials_from_connection(connection)

    # Check if token is expired or will expire in the next 5 minutes
    needs_refresh = False
    if connection.token_expiry:
        if connection.token_expiry <= datetime.now(timezone.utc) + timedelta(minutes=5):
            needs_refresh = True
    else:
        needs_refresh = True

    if needs_refresh and creds.refresh_token:
        from google.auth.transport.requests import Request
        creds.refresh(Request())

        # Update stored tokens
        connection.access_token_encrypted = encrypt_token(creds.token)
        connection.token_expiry = creds.expiry
        db.commit()
        logger.info(f"Refreshed Google access token for {connection.google_email}")

    return creds


def get_drive_service(db: Session, connection: GoogleConnection):
    """Return an authenticated Google Drive API v3 client."""
    creds = refresh_token_if_needed(db, connection)
    return build("drive", "v3", credentials=creds)


def get_docs_service(db: Session, connection: GoogleConnection):
    """Return an authenticated Google Docs API v1 client."""
    creds = refresh_token_if_needed(db, connection)
    return build("docs", "v1", credentials=creds)
