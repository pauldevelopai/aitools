"""Google Drive connection and sync item models."""
import hashlib
import base64
import uuid
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from sqlalchemy import (
    Column, String, DateTime, Text, Boolean,
    ForeignKey, CheckConstraint, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db import Base
from app.settings import settings


def _get_fernet() -> Fernet:
    """Derive a Fernet key from the app SECRET_KEY."""
    key = base64.urlsafe_b64encode(
        hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    )
    return Fernet(key)


def encrypt_token(plaintext: str) -> str:
    """Encrypt a token string using Fernet."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted token string."""
    return _get_fernet().decrypt(ciphertext.encode()).decode()


class GoogleConnection(Base):
    """OAuth connection to a Google account (one per admin)."""

    __tablename__ = "google_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    access_token_encrypted = Column(Text, nullable=False)
    refresh_token_encrypted = Column(Text, nullable=False)
    token_expiry = Column(DateTime(timezone=True), nullable=True)

    google_email = Column(String, nullable=True)
    scopes = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def set_tokens(self, access_token: str, refresh_token: str):
        """Encrypt and store OAuth tokens."""
        self.access_token_encrypted = encrypt_token(access_token)
        self.refresh_token_encrypted = encrypt_token(refresh_token)

    def get_access_token(self) -> str:
        """Decrypt and return the access token."""
        return decrypt_token(self.access_token_encrypted)

    def get_refresh_token(self) -> str:
        """Decrypt and return the refresh token."""
        return decrypt_token(self.refresh_token_encrypted)

    def __repr__(self):
        return f"<GoogleConnection user_id={self.user_id} email={self.google_email}>"


class GoogleSyncItem(Base):
    """Tracks a synced Google Drive file."""

    __tablename__ = "google_sync_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("google_connections.id", ondelete="CASCADE"),
        nullable=False,
    )

    google_file_id = Column(String, nullable=False, index=True)
    google_file_name = Column(String, nullable=False)
    google_mime_type = Column(String, nullable=True)
    google_parent_id = Column(String, nullable=True)

    target_type = Column(String, nullable=False)
    target_id = Column(UUID(as_uuid=True), nullable=True)

    sync_status = Column(String, nullable=False, default="pending")
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    content_hash = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)

    library_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("library_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    toolkit_document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("toolkit_documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("connection_id", "google_file_id", name="uq_sync_connection_file"),
        CheckConstraint(
            "target_type IN ('library', 'organization')",
            name="ck_sync_items_target_type",
        ),
        CheckConstraint(
            "sync_status IN ('pending', 'syncing', 'synced', 'error')",
            name="ck_sync_items_sync_status",
        ),
    )

    def __repr__(self):
        return f"<GoogleSyncItem {self.google_file_name} status={self.sync_status}>"
