"""Directory models for journalist and media organization tracking."""
from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class MediaOrganization(Base):
    """Media organization (BBC, The Guardian, etc.)."""

    __tablename__ = "media_organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    org_type = Column(String(50), nullable=False)  # newspaper, broadcaster, digital, agency, freelance_collective
    country = Column(String(100))
    website = Column(String(500))
    logo_url = Column(String(500))
    description = Column(Text)
    notes = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    departments = relationship("Department", back_populates="organization", cascade="all, delete-orphan")
    journalists = relationship("Journalist", back_populates="organization")


class Department(Base):
    """Department within a media organization (News, Sports, Features, etc.)."""

    __tablename__ = "departments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("media_organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    organization = relationship("MediaOrganization", back_populates="departments")
    teams = relationship("Team", back_populates="department", cascade="all, delete-orphan")
    journalists = relationship("Journalist", back_populates="department")


class Team(Base):
    """Team within a department."""

    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    department = relationship("Department", back_populates="teams")
    journalists = relationship("Journalist", back_populates="team")


class Journalist(Base):
    """Journalist contact record."""

    __tablename__ = "journalists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("media_organizations.id", ondelete="SET NULL"), nullable=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True)
    phone = Column(String(50))
    role = Column(String(100))  # Job title
    beat = Column(String(255))  # Coverage area (politics, tech, etc.)
    bio = Column(Text)
    photo_url = Column(String(500))

    # Social handles
    twitter = Column(String(100))
    linkedin = Column(String(255))
    website = Column(String(500))

    # AI learning status
    ai_skill_level = Column(String(20), default="none")  # none, beginner, intermediate, advanced
    areas_of_interest = Column(JSONB, default=list)  # AI topics interested in

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("MediaOrganization", back_populates="journalists")
    department = relationship("Department", back_populates="journalists")
    team = relationship("Team", back_populates="journalists")
    engagements = relationship("Engagement", back_populates="journalist", cascade="all, delete-orphan")
    notes = relationship("JournalistNote", back_populates="journalist", cascade="all, delete-orphan")

    @property
    def full_name(self):
        """Return full name."""
        return f"{self.first_name} {self.last_name}"


class Engagement(Base):
    """Training engagement with a journalist."""

    __tablename__ = "engagements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    journalist_id = Column(UUID(as_uuid=True), ForeignKey("journalists.id", ondelete="CASCADE"), nullable=False)

    engagement_type = Column(String(50), nullable=False)  # training, mentoring, workshop, presentation, consultation, follow_up
    title = Column(String(255), nullable=False)
    description = Column(Text)
    date = Column(Date, nullable=False)
    duration_minutes = Column(Integer)
    location = Column(String(255))  # in-person/virtual/venue name

    topics_covered = Column(JSONB, default=list)
    materials_used = Column(JSONB, default=list)

    outcomes = Column(Text)
    follow_up_actions = Column(Text)
    follow_up_date = Column(Date)

    skill_before = Column(String(20))  # Skill level before engagement
    skill_after = Column(String(20))   # Skill level after engagement

    notes = Column(Text)  # Private notes
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    journalist = relationship("Journalist", back_populates="engagements")
    documents = relationship("EngagementDocument", back_populates="engagement", cascade="all, delete-orphan")


class JournalistNote(Base):
    """Freeform notes about a journalist."""

    __tablename__ = "journalist_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    journalist_id = Column(UUID(as_uuid=True), ForeignKey("journalists.id", ondelete="CASCADE"), nullable=False)

    note_type = Column(String(50), default="general")  # general, feedback, observation, reminder
    content = Column(Text, nullable=False)
    is_private = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    journalist = relationship("Journalist", back_populates="notes")


class EngagementDocument(Base):
    """Document or material associated with an engagement."""

    __tablename__ = "engagement_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engagement_id = Column(UUID(as_uuid=True), ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False)

    title = Column(String(255), nullable=False)
    doc_type = Column(String(50), nullable=False)  # presentation, handout, guide, recording, link
    url = Column(String(500))
    notes = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    engagement = relationship("Engagement", back_populates="documents")
