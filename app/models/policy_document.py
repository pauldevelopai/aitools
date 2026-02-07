"""Policy Document models with versioning, ownership and visibility controls.

Two-table versioning pattern:
- PolicyDocument: document identity, ownership, visibility, current version pointer
- PolicyDocumentVersion: immutable version snapshots with content and attribution

Document types: ETHICS_POLICY, LEGAL_FRAMEWORK (extensible via CHECK constraint)
Visibility: private (org only), shared (partners), public (library)
Status workflow: draft → published → archived
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column, String, DateTime, Text, ForeignKey, Boolean, Integer,
    CheckConstraint, Index, Date, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Session
import uuid
import re

from app.db import Base


class PolicyDocument(Base):
    """A policy or legal framework document owned by an organization.

    This is the identity record. Content lives in PolicyDocumentVersion rows.
    The current_version_id points to the latest published version (if any).
    """
    __tablename__ = "policy_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Ownership — nullable for system/internal documents
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("media_organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Classification
    doc_type = Column(String, nullable=False, index=True)  # ethics_policy, legal_framework
    subtype = Column(String, nullable=True)  # optional further classification

    # Identity
    title = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True, index=True)

    # Visibility
    visibility = Column(String, nullable=False, default="private")  # private, shared, public

    # Pointer to latest published version (set on publish)
    current_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("policy_document_versions.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )

    # Provenance
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("MediaOrganization", backref="policy_documents")
    versions = relationship(
        "PolicyDocumentVersion",
        back_populates="document",
        foreign_keys="PolicyDocumentVersion.document_id",
        cascade="all, delete-orphan",
        order_by="PolicyDocumentVersion.version_number.desc()",
    )
    current_version = relationship(
        "PolicyDocumentVersion",
        foreign_keys=[current_version_id],
        post_update=True,
    )
    creator = relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        CheckConstraint(
            "doc_type IN ('ethics_policy', 'legal_framework')",
            name="ck_policy_documents_doc_type",
        ),
        CheckConstraint(
            "visibility IN ('private', 'shared', 'public')",
            name="ck_policy_documents_visibility",
        ),
    )

    def __repr__(self):
        return f"<PolicyDocument {self.slug} type={self.doc_type} vis={self.visibility}>"

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    @classmethod
    def create_draft(
        cls,
        db: Session,
        *,
        title: str,
        doc_type: str,
        content_markdown: str,
        organization_id: Optional[uuid.UUID] = None,
        created_by: Optional[uuid.UUID] = None,
        visibility: str = "private",
        subtype: Optional[str] = None,
        summary: Optional[str] = None,
        source: Optional[str] = None,
        publisher: Optional[str] = None,
        publication_date: Optional[datetime] = None,
        jurisdiction: Optional[str] = None,
        source_url: Optional[str] = None,
        license_notes: Optional[str] = None,
    ) -> "PolicyDocument":
        """Create a new document with an initial draft version.

        Returns the PolicyDocument (with .versions[0] being the draft).
        The caller must call db.commit() after.
        """
        slug = cls._generate_slug(title)
        # Ensure slug uniqueness
        existing = db.query(cls).filter(cls.slug == slug).first()
        if existing:
            slug = f"{slug}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        doc = cls(
            title=title,
            slug=slug,
            doc_type=doc_type,
            organization_id=organization_id,
            created_by=created_by,
            visibility=visibility,
            subtype=subtype,
        )
        db.add(doc)
        db.flush()  # get doc.id

        version = PolicyDocumentVersion(
            document_id=doc.id,
            version_number=1,
            status="draft",
            title=title,
            content_markdown=content_markdown,
            summary=summary,
            source=source,
            publisher=publisher,
            publication_date=publication_date,
            jurisdiction=jurisdiction,
            source_url=source_url,
            license_notes=license_notes,
            created_by=created_by,
        )
        db.add(version)
        db.flush()

        return doc

    def new_draft(
        self,
        db: Session,
        *,
        content_markdown: str,
        title: Optional[str] = None,
        change_notes: Optional[str] = None,
        created_by: Optional[uuid.UUID] = None,
        summary: Optional[str] = None,
        source: Optional[str] = None,
        publisher: Optional[str] = None,
        publication_date: Optional[datetime] = None,
        jurisdiction: Optional[str] = None,
        source_url: Optional[str] = None,
        license_notes: Optional[str] = None,
    ) -> "PolicyDocumentVersion":
        """Create a new draft version of this document.

        Copies attribution from the latest version if not overridden.
        The caller must call db.commit() after.
        """
        latest = (
            db.query(PolicyDocumentVersion)
            .filter(PolicyDocumentVersion.document_id == self.id)
            .order_by(PolicyDocumentVersion.version_number.desc())
            .first()
        )
        next_num = (latest.version_number + 1) if latest else 1

        # Carry forward attribution from latest version when not explicitly provided
        version = PolicyDocumentVersion(
            document_id=self.id,
            version_number=next_num,
            status="draft",
            title=title or self.title,
            content_markdown=content_markdown,
            summary=summary if summary is not None else (latest.summary if latest else None),
            change_notes=change_notes,
            source=source if source is not None else (latest.source if latest else None),
            publisher=publisher if publisher is not None else (latest.publisher if latest else None),
            publication_date=publication_date if publication_date is not None else (latest.publication_date if latest else None),
            jurisdiction=jurisdiction if jurisdiction is not None else (latest.jurisdiction if latest else None),
            source_url=source_url if source_url is not None else (latest.source_url if latest else None),
            license_notes=license_notes if license_notes is not None else (latest.license_notes if latest else None),
            created_by=created_by,
        )
        db.add(version)
        db.flush()

        # Update document title if changed
        if title:
            self.title = title

        return version

    def list_versions(self, db: Session) -> list["PolicyDocumentVersion"]:
        """Return all versions ordered by version_number descending."""
        return (
            db.query(PolicyDocumentVersion)
            .filter(PolicyDocumentVersion.document_id == self.id)
            .order_by(PolicyDocumentVersion.version_number.desc())
            .all()
        )

    def revert_to_version(
        self,
        db: Session,
        version_number: int,
        *,
        created_by: Optional[uuid.UUID] = None,
    ) -> "PolicyDocumentVersion":
        """Create a new draft by copying content from a previous version.

        Does NOT delete any versions — creates a new draft with the old content
        and a change_notes annotation. The caller must call db.commit() after.

        Raises ValueError if the target version doesn't exist.
        """
        target = (
            db.query(PolicyDocumentVersion)
            .filter(
                PolicyDocumentVersion.document_id == self.id,
                PolicyDocumentVersion.version_number == version_number,
            )
            .first()
        )
        if not target:
            raise ValueError(
                f"Version {version_number} not found for document {self.slug}"
            )

        return self.new_draft(
            db,
            content_markdown=target.content_markdown,
            title=target.title,
            change_notes=f"Reverted to version {version_number}",
            created_by=created_by,
            summary=target.summary,
            source=target.source,
            publisher=target.publisher,
            publication_date=target.publication_date,
            jurisdiction=target.jurisdiction,
            source_url=target.source_url,
            license_notes=target.license_notes,
        )

    @staticmethod
    def _generate_slug(title: str) -> str:
        """Generate a URL-safe slug from a title."""
        slug = title.lower()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"[\s_]+", "-", slug)
        return slug.strip("-")[:100]


class PolicyDocumentVersion(Base):
    """Immutable snapshot of a policy document at a point in time.

    Once published, a version should not be edited — create a new version instead.
    """
    __tablename__ = "policy_document_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Parent document
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("policy_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number = Column(Integer, nullable=False)

    # Status
    status = Column(String, nullable=False, default="draft", index=True)  # draft, published, archived

    # Content
    title = Column(String, nullable=False)
    content_markdown = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    change_notes = Column(Text, nullable=True)  # what changed in this version

    # Attribution metadata
    source = Column(String, nullable=True)  # origin of the content
    publisher = Column(String, nullable=True)  # who authored/published it
    publication_date = Column(Date, nullable=True)  # original publication date
    jurisdiction = Column(String, nullable=True, index=True)  # legal jurisdiction
    source_url = Column(String, nullable=True)  # link to original
    license_notes = Column(Text, nullable=True)  # usage/license information

    # Publishing
    published_at = Column(DateTime(timezone=True), nullable=True)
    published_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Provenance
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    document = relationship(
        "PolicyDocument",
        back_populates="versions",
        foreign_keys=[document_id],
    )
    publisher_user = relationship("User", foreign_keys=[published_by])
    creator = relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_policy_doc_versions_status",
        ),
        UniqueConstraint(
            "document_id", "version_number",
            name="uq_policy_doc_versions_doc_version",
        ),
        Index("ix_policy_doc_versions_doc_status", "document_id", "status"),
    )

    def __repr__(self):
        return f"<PolicyDocumentVersion doc={self.document_id} v{self.version_number} status={self.status}>"

    def publish(
        self,
        db: Session,
        *,
        published_by: Optional[uuid.UUID] = None,
    ) -> None:
        """Publish this version and update the parent document's current pointer.

        Archives any previously published version of the same document.
        The caller must call db.commit() after.
        """
        if self.status == "published":
            return  # already published, no-op

        # Archive the currently published version (if any)
        db.query(PolicyDocumentVersion).filter(
            PolicyDocumentVersion.document_id == self.document_id,
            PolicyDocumentVersion.status == "published",
            PolicyDocumentVersion.id != self.id,
        ).update({"status": "archived"})

        # Publish this version
        self.status = "published"
        self.published_at = datetime.now(timezone.utc)
        self.published_by = published_by

        # Update parent document pointer
        self.document.current_version_id = self.id
        self.document.title = self.title

        db.flush()
