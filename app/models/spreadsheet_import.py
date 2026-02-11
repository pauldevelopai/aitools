"""Spreadsheet import session tracking model."""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db import Base


class SpreadsheetImport(Base):
    """Tracks a spreadsheet import session through its lifecycle."""

    __tablename__ = "spreadsheet_imports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_type = Column(String(10), nullable=False)  # csv, xlsx, xls
    row_count = Column(Integer, default=0)
    raw_headers = Column(JSONB, default=list)
    sample_rows = Column(JSONB, default=list)
    column_mapping = Column(JSONB, default=dict)  # {spreadsheet_col: target_field}
    field_defaults = Column(JSONB, default=dict)  # {field: default_value} from chat
    row_overrides = Column(JSONB, default=dict)  # {row_index: {field: value}} per-row AI classifications
    chat_history = Column(JSONB, default=list)  # [{role, content}]
    status = Column(
        String(20), nullable=False, default="uploaded"
    )  # uploaded, mapped, chatting, ready, importing, completed, failed
    records_created = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_skipped = Column(Integer, default=0)
    import_errors = Column(JSONB, default=list)

    # Relationships
    uploaded_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("organization_profiles.id", ondelete="SET NULL"), nullable=True, index=True)

    uploaded_by = relationship("User")
    client = relationship("OrganizationProfile")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
