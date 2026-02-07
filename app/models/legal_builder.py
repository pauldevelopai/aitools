"""AI Legal Framework Builder models with versioning and compliance checklist.

Two-table versioning pattern:
- LegalFrameworkDoc: per-user framework identity, current version pointer
- LegalFrameworkVersion: immutable version snapshots with JSONB config + checklist

Status workflow: draft -> published -> archived
Outputs: narrative_markdown (editable summary) + checklist_items (JSONB array)
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column, String, DateTime, Text, ForeignKey, Integer,
    CheckConstraint, UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Session
from sqlalchemy.orm.attributes import flag_modified
import uuid

from app.db import Base


# =============================================================================
# CONSTANTS
# =============================================================================

JURISDICTIONS = [
    {
        "key": "eu",
        "label": "European Union",
        "description": "EU AI Act, GDPR, and related EU regulations",
        "frameworks": ["EU AI Act", "GDPR", "EU Copyright Directive"],
    },
    {
        "key": "uk",
        "label": "United Kingdom",
        "description": "UK data protection, ICO guidance, and AI regulation",
        "frameworks": ["UK GDPR", "Data Protection Act 2018", "ICO AI Guidance", "UK Online Safety Act"],
    },
    {
        "key": "us_federal",
        "label": "US Federal",
        "description": "Federal AI guidance, FTC rules, and executive orders",
        "frameworks": ["NIST AI RMF", "FTC AI Guidance", "Executive Order on AI"],
    },
    {
        "key": "us_state",
        "label": "US State",
        "description": "State-level AI laws (Colorado, California, Illinois, etc.)",
        "frameworks": ["Colorado AI Act", "California CPRA", "Illinois BIPA", "NYC Local Law 144"],
    },
    {
        "key": "ireland",
        "label": "Ireland",
        "description": "Irish Data Protection Commission guidance and national AI strategy",
        "frameworks": ["DPC Guidance", "National AI Strategy", "GDPR (as applied by DPC)"],
    },
    {
        "key": "global",
        "label": "Global / International",
        "description": "OECD AI Principles, UNESCO, ISO standards",
        "frameworks": ["OECD AI Principles", "UNESCO AI Ethics", "ISO/IEC 42001"],
    },
]

JURISDICTION_KEYS = [j["key"] for j in JURISDICTIONS]
JURISDICTION_MAP = {j["key"]: j for j in JURISDICTIONS}

SECTORS = [
    {"key": "newsroom", "label": "Newsroom / Media"},
    {"key": "ngo", "label": "NGO / Non-Profit"},
    {"key": "academic", "label": "Academic / Research"},
    {"key": "government", "label": "Government / Public Sector"},
    {"key": "freelance", "label": "Freelance / Independent"},
    {"key": "other", "label": "Other"},
]

SECTOR_KEYS = [s["key"] for s in SECTORS]
SECTOR_MAP = {s["key"]: s for s in SECTORS}

AI_USE_CASES = [
    {"key": "content_generation", "label": "Content Generation", "description": "Using AI to draft articles, reports, or other written content"},
    {"key": "research", "label": "Research & Analysis", "description": "AI-assisted research, fact-checking, and background analysis"},
    {"key": "translation", "label": "Translation", "description": "Automated translation of content between languages"},
    {"key": "transcription", "label": "Transcription", "description": "Converting audio or video recordings to text"},
    {"key": "image_video", "label": "Image / Video Generation", "description": "Creating or editing visual content with AI"},
    {"key": "data_analysis", "label": "Data Analysis", "description": "Processing and analysing datasets to identify patterns"},
    {"key": "audience_targeting", "label": "Audience Targeting", "description": "Using AI for audience segmentation and content personalisation"},
    {"key": "content_moderation", "label": "Content Moderation", "description": "Automated review and filtering of user-generated content"},
    {"key": "chatbot", "label": "Chatbot / Conversational AI", "description": "Deploying AI-powered chat interfaces for users"},
]

USE_CASE_KEYS = [u["key"] for u in AI_USE_CASES]
USE_CASE_MAP = {u["key"]: u for u in AI_USE_CASES}

OBLIGATION_CATEGORIES = [
    {"key": "transparency", "label": "Transparency"},
    {"key": "data_protection", "label": "Data Protection"},
    {"key": "accountability", "label": "Accountability"},
    {"key": "human_oversight", "label": "Human Oversight"},
    {"key": "risk_management", "label": "Risk Management"},
    {"key": "ip_copyright", "label": "IP & Copyright"},
    {"key": "content_labelling", "label": "Content Labelling"},
    {"key": "safety", "label": "Safety"},
    {"key": "record_keeping", "label": "Record Keeping"},
    {"key": "other", "label": "Other"},
]

CATEGORY_KEYS = [c["key"] for c in OBLIGATION_CATEGORIES]

CHECKLIST_STATUSES = ["not_applicable", "planned", "implemented"]

# =============================================================================
# STARTER CHECKLIST ITEMS — keyed by jurisdiction
# =============================================================================

STARTER_CHECKLIST_ITEMS = {
    "eu": [
        {
            "category": "risk_management",
            "obligation": "Classify AI systems by risk level under the EU AI Act",
            "description": "Determine whether your AI use cases fall under unacceptable, high, limited, or minimal risk categories as defined by the EU AI Act.",
            "framework_ref": "EU AI Act, Title III",
        },
        {
            "category": "data_protection",
            "obligation": "Conduct Data Protection Impact Assessment (DPIA) for high-risk AI processing",
            "description": "Under GDPR Article 35, carry out a DPIA where AI processing is likely to result in high risk to individuals' rights and freedoms.",
            "framework_ref": "GDPR Article 35",
        },
        {
            "category": "transparency",
            "obligation": "Inform users when they are interacting with an AI system",
            "description": "The EU AI Act requires that persons be notified they are interacting with an AI system, unless this is obvious from the circumstances.",
            "framework_ref": "EU AI Act, Article 52",
        },
        {
            "category": "accountability",
            "obligation": "Maintain technical documentation for high-risk AI systems",
            "description": "High-risk AI systems must have technical documentation demonstrating compliance, kept up to date throughout the system lifecycle.",
            "framework_ref": "EU AI Act, Article 11",
        },
        {
            "category": "human_oversight",
            "obligation": "Ensure human oversight mechanisms for high-risk AI",
            "description": "High-risk AI systems must be designed to allow effective human oversight, including the ability to intervene or override.",
            "framework_ref": "EU AI Act, Article 14",
        },
        {
            "category": "ip_copyright",
            "obligation": "Comply with copyright obligations for training data",
            "description": "Under the EU Copyright Directive, ensure AI training data usage complies with text and data mining exceptions and rights holder opt-outs.",
            "framework_ref": "EU Copyright Directive, Articles 3-4",
        },
        {
            "category": "content_labelling",
            "obligation": "Label AI-generated content including deepfakes",
            "description": "Content that is artificially generated or manipulated (deepfakes) must be disclosed as such to recipients.",
            "framework_ref": "EU AI Act, Article 52(3)",
        },
    ],
    "uk": [
        {
            "category": "data_protection",
            "obligation": "Register AI processing activities with the ICO",
            "description": "Ensure your organisation's AI data processing is covered by your ICO registration and data protection fee payment.",
            "framework_ref": "Data Protection Act 2018, Part 3",
        },
        {
            "category": "transparency",
            "obligation": "Provide clear privacy notices for AI processing",
            "description": "ICO guidance requires organisations to be transparent about how AI processes personal data, including in privacy notices.",
            "framework_ref": "ICO AI Guidance, Principle 1",
        },
        {
            "category": "accountability",
            "obligation": "Document AI decision-making processes",
            "description": "Maintain records of how AI systems make or support decisions, especially those affecting individuals.",
            "framework_ref": "ICO Accountability Framework",
        },
        {
            "category": "data_protection",
            "obligation": "Establish lawful basis for AI personal data processing",
            "description": "Identify and document the lawful basis (consent, legitimate interest, etc.) for processing personal data through AI systems.",
            "framework_ref": "UK GDPR, Article 6",
        },
        {
            "category": "risk_management",
            "obligation": "Apply proportionate governance to AI systems",
            "description": "Follow the UK's pro-innovation, principles-based approach to AI regulation with proportionate risk management.",
            "framework_ref": "UK AI Regulation White Paper",
        },
        {
            "category": "safety",
            "obligation": "Assess AI systems for online safety compliance",
            "description": "If deploying AI in user-facing services, assess obligations under the Online Safety Act regarding harmful content.",
            "framework_ref": "UK Online Safety Act 2023",
        },
    ],
    "us_federal": [
        {
            "category": "risk_management",
            "obligation": "Align with NIST AI Risk Management Framework",
            "description": "Map your AI governance to the NIST AI RMF functions: Govern, Map, Measure, and Manage.",
            "framework_ref": "NIST AI RMF 1.0",
        },
        {
            "category": "transparency",
            "obligation": "Follow FTC guidance on AI transparency",
            "description": "The FTC has signalled that deceptive AI practices may violate Section 5 of the FTC Act. Ensure AI use is transparent and non-deceptive.",
            "framework_ref": "FTC Act, Section 5",
        },
        {
            "category": "accountability",
            "obligation": "Implement AI governance per Executive Order requirements",
            "description": "Follow the Executive Order on Safe, Secure, and Trustworthy AI, including safety testing and reporting requirements.",
            "framework_ref": "Executive Order 14110",
        },
        {
            "category": "data_protection",
            "obligation": "Assess AI systems for consumer privacy impacts",
            "description": "Evaluate how AI systems collect, use, and share consumer data. Consider privacy-by-design principles.",
            "framework_ref": "FTC Privacy Guidance",
        },
        {
            "category": "human_oversight",
            "obligation": "Ensure meaningful human review for consequential AI decisions",
            "description": "Federal guidance emphasises that AI should not make consequential decisions about individuals without meaningful human review.",
            "framework_ref": "Blueprint for an AI Bill of Rights",
        },
    ],
    "us_state": [
        {
            "category": "risk_management",
            "obligation": "Comply with Colorado AI Act requirements for high-risk systems",
            "description": "If operating in Colorado, assess whether AI systems are 'high-risk' and implement required impact assessments and disclosures.",
            "framework_ref": "Colorado AI Act (SB 24-205)",
        },
        {
            "category": "data_protection",
            "obligation": "Honour consumer data rights under CPRA",
            "description": "California's CPRA gives consumers rights over automated decision-making. Provide opt-out mechanisms for AI profiling.",
            "framework_ref": "California CPRA",
        },
        {
            "category": "transparency",
            "obligation": "Disclose use of automated employment decision tools",
            "description": "NYC Local Law 144 requires bias audits and disclosure for automated employment decision tools.",
            "framework_ref": "NYC Local Law 144",
        },
        {
            "category": "data_protection",
            "obligation": "Comply with biometric data requirements",
            "description": "If using AI with biometric data (face recognition, voice analysis), comply with Illinois BIPA consent and notice requirements.",
            "framework_ref": "Illinois BIPA",
        },
        {
            "category": "accountability",
            "obligation": "Conduct algorithmic impact assessments where required",
            "description": "Several state laws require impact assessments for high-risk AI systems affecting consumers.",
            "framework_ref": "Various state AI laws",
        },
    ],
    "ireland": [
        {
            "category": "data_protection",
            "obligation": "Follow DPC guidance on AI and data protection",
            "description": "The Irish Data Protection Commission has published specific guidance on AI and automated decision-making under GDPR.",
            "framework_ref": "DPC AI Guidance",
        },
        {
            "category": "accountability",
            "obligation": "Align with Ireland's National AI Strategy",
            "description": "Consider the principles and objectives outlined in AI – Here for Good, Ireland's national AI strategy.",
            "framework_ref": "AI – Here for Good (National AI Strategy)",
        },
        {
            "category": "transparency",
            "obligation": "Provide information about automated decision-making",
            "description": "Under GDPR as enforced by the DPC, provide meaningful information about the logic involved in automated decision-making.",
            "framework_ref": "GDPR Article 22, DPC guidance",
        },
        {
            "category": "data_protection",
            "obligation": "Ensure cross-border data transfer compliance for AI services",
            "description": "When using AI services hosted outside the EU/EEA, ensure appropriate data transfer mechanisms are in place.",
            "framework_ref": "GDPR Chapter V, DPC guidance",
        },
        {
            "category": "risk_management",
            "obligation": "Prepare for EU AI Act implementation via Irish regulatory bodies",
            "description": "As an EU member state, Ireland will designate national competent authorities for AI Act enforcement. Monitor and prepare.",
            "framework_ref": "EU AI Act, National Implementation",
        },
    ],
    "global": [
        {
            "category": "accountability",
            "obligation": "Align with OECD AI Principles",
            "description": "The OECD AI Principles promote trustworthy AI that is innovative, respects human rights, and is transparent.",
            "framework_ref": "OECD AI Principles (2019)",
        },
        {
            "category": "human_oversight",
            "obligation": "Apply UNESCO Recommendation on AI Ethics",
            "description": "UNESCO's recommendation covers proportionality, safety, fairness, sustainability, privacy, and human oversight of AI.",
            "framework_ref": "UNESCO Recommendation on the Ethics of AI",
        },
        {
            "category": "risk_management",
            "obligation": "Consider ISO/IEC 42001 AI Management System certification",
            "description": "ISO/IEC 42001 provides a framework for establishing, implementing, and improving an AI management system.",
            "framework_ref": "ISO/IEC 42001:2023",
        },
        {
            "category": "record_keeping",
            "obligation": "Maintain AI system inventory and documentation",
            "description": "International best practice recommends maintaining a register of AI systems in use, their purposes, and risk assessments.",
            "framework_ref": "OECD AI Policy Observatory",
        },
        {
            "category": "transparency",
            "obligation": "Publish an organisational AI use statement",
            "description": "International norms encourage organisations to publicly state their approach to AI use, governance, and ethical principles.",
            "framework_ref": "OECD AI Principles, UNESCO Recommendation",
        },
    ],
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def build_starter_narrative(framework_config: dict) -> str:
    """Generate a starter narrative markdown document from user selections."""
    jurisdictions = framework_config.get("jurisdictions", [])
    sector = framework_config.get("sector", "")
    use_cases = framework_config.get("use_cases", [])

    sector_label = SECTOR_MAP.get(sector, {}).get("label", sector)
    jurisdiction_labels = [JURISDICTION_MAP[j]["label"] for j in jurisdictions if j in JURISDICTION_MAP]
    use_case_labels = [USE_CASE_MAP[u]["label"] for u in use_cases if u in USE_CASE_MAP]

    parts = []
    parts.append("## Our Legal Obligations for AI Use\n")
    parts.append(
        f"This framework maps the legal and regulatory obligations affecting our use of "
        f"artificial intelligence as a **{sector_label}** organisation.\n"
    )

    if jurisdiction_labels:
        parts.append("### Jurisdictions\n")
        parts.append("We operate under or are affected by regulations in the following jurisdictions:\n")
        for label in jurisdiction_labels:
            parts.append(f"- **{label}**")
        parts.append("")

        # Add framework references
        parts.append("### Key Regulatory Frameworks\n")
        for j_key in jurisdictions:
            j = JURISDICTION_MAP.get(j_key)
            if j:
                frameworks = ", ".join(j["frameworks"])
                parts.append(f"- **{j['label']}**: {frameworks}")
        parts.append("")

    if use_case_labels:
        parts.append("### AI Use Cases in Scope\n")
        parts.append("The following AI use cases are covered by this framework:\n")
        for label in use_case_labels:
            parts.append(f"- {label}")
        parts.append("")

    parts.append("### Compliance Approach\n")
    parts.append(
        "We take a risk-based approach to AI compliance, prioritising obligations "
        "that have the greatest impact on individuals and our organisation. "
        "Each obligation in our checklist is tracked with its current implementation "
        "status and supporting evidence.\n"
    )

    parts.append("### Review Schedule\n")
    parts.append(
        "This framework is reviewed quarterly and updated when relevant laws or "
        "regulations change. The compliance checklist is maintained as a living "
        "document by the designated compliance lead.\n"
    )

    return "\n".join(parts)


def build_starter_checklist(framework_config: dict) -> list[dict]:
    """Generate checklist items from selected jurisdictions."""
    jurisdictions = framework_config.get("jurisdictions", [])
    items = []
    order = 1

    for j_key in jurisdictions:
        starter_items = STARTER_CHECKLIST_ITEMS.get(j_key, [])
        for item_template in starter_items:
            items.append({
                "id": str(uuid.uuid4()),
                "category": item_template["category"],
                "obligation": item_template["obligation"],
                "description": item_template["description"],
                "framework_ref": item_template["framework_ref"],
                "status": "planned",
                "evidence_links": [],
                "notes": "",
                "order": order,
            })
            order += 1

    return items


# =============================================================================
# MODELS
# =============================================================================

class LegalFrameworkDoc(Base):
    """Per-user AI Legal Framework — the identity record.

    Content lives in LegalFrameworkVersion rows.
    The current_version_id points to the latest published version (if any).
    """
    __tablename__ = "legal_framework_docs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Owner
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional org link
    organization_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organization_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )

    title = Column(String, nullable=False)

    # Pointer to latest published version
    current_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("legal_framework_versions.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    organization_profile = relationship("OrganizationProfile", foreign_keys=[organization_profile_id])
    versions = relationship(
        "LegalFrameworkVersion",
        back_populates="framework",
        foreign_keys="LegalFrameworkVersion.framework_id",
        cascade="all, delete-orphan",
        order_by="LegalFrameworkVersion.version_number.desc()",
    )
    current_version = relationship(
        "LegalFrameworkVersion",
        foreign_keys=[current_version_id],
        post_update=True,
    )

    def __repr__(self):
        return f"<LegalFrameworkDoc {self.id} user={self.user_id} title={self.title!r}>"

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    @classmethod
    def create_framework(
        cls,
        db: Session,
        *,
        user_id: uuid.UUID,
        title: str,
        framework_config: dict,
        organization_profile_id: Optional[uuid.UUID] = None,
    ) -> "LegalFrameworkDoc":
        """Create a new framework with a v1 draft containing generated content.

        Returns the LegalFrameworkDoc. Caller must call db.commit().
        """
        doc = cls(
            user_id=user_id,
            title=title,
            organization_profile_id=organization_profile_id,
        )
        db.add(doc)
        db.flush()

        narrative = build_starter_narrative(framework_config)
        checklist = build_starter_checklist(framework_config)

        version = LegalFrameworkVersion(
            framework_id=doc.id,
            version_number=1,
            status="draft",
            framework_config=framework_config,
            narrative_markdown=narrative,
            checklist_items=checklist,
        )
        db.add(version)
        db.flush()

        return doc

    def new_draft(self, db: Session, *, created_by: Optional[uuid.UUID] = None) -> "LegalFrameworkVersion":
        """Create a new draft version from the latest version.

        Caller must call db.commit().
        """
        latest = (
            db.query(LegalFrameworkVersion)
            .filter(LegalFrameworkVersion.framework_id == self.id)
            .order_by(LegalFrameworkVersion.version_number.desc())
            .first()
        )
        next_num = (latest.version_number + 1) if latest else 1
        framework_config = dict(latest.framework_config) if latest and latest.framework_config else {}
        narrative = latest.narrative_markdown if latest else ""
        checklist = list(latest.checklist_items) if latest and latest.checklist_items else []

        version = LegalFrameworkVersion(
            framework_id=self.id,
            version_number=next_num,
            status="draft",
            framework_config=framework_config,
            narrative_markdown=narrative,
            checklist_items=checklist,
        )
        db.add(version)
        db.flush()
        return version

    def get_current_draft(self, db: Session) -> Optional["LegalFrameworkVersion"]:
        """Return the current draft version if one exists."""
        return (
            db.query(LegalFrameworkVersion)
            .filter(
                LegalFrameworkVersion.framework_id == self.id,
                LegalFrameworkVersion.status == "draft",
            )
            .order_by(LegalFrameworkVersion.version_number.desc())
            .first()
        )

    def list_versions(self, db: Session) -> list["LegalFrameworkVersion"]:
        """Return all versions ordered by version_number descending."""
        return (
            db.query(LegalFrameworkVersion)
            .filter(LegalFrameworkVersion.framework_id == self.id)
            .order_by(LegalFrameworkVersion.version_number.desc())
            .all()
        )


class LegalFrameworkVersion(Base):
    """Immutable snapshot of a legal framework at a point in time.

    Contains framework_config (user selections), narrative_markdown,
    and checklist_items (JSONB array). Once published, create a new version to edit.
    """
    __tablename__ = "legal_framework_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Parent framework
    framework_id = Column(
        UUID(as_uuid=True),
        ForeignKey("legal_framework_docs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number = Column(Integer, nullable=False)

    # Status
    status = Column(String, nullable=False, default="draft", index=True)

    # User selections for this version
    framework_config = Column(JSONB, nullable=True)

    # Narrative summary (editable markdown)
    narrative_markdown = Column(Text, nullable=True)

    # Checklist items (JSONB array)
    checklist_items = Column(JSONB, nullable=True)

    # Version metadata
    change_notes = Column(Text, nullable=True)

    # Publishing
    published_at = Column(DateTime(timezone=True), nullable=True)
    published_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    framework = relationship(
        "LegalFrameworkDoc",
        back_populates="versions",
        foreign_keys=[framework_id],
    )
    publisher_user = relationship("User", foreign_keys=[published_by])

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_legal_framework_versions_status",
        ),
        UniqueConstraint(
            "framework_id", "version_number",
            name="uq_legal_framework_versions_framework_version",
        ),
        Index("ix_legal_framework_versions_framework_status", "framework_id", "status"),
    )

    def __repr__(self):
        return f"<LegalFrameworkVersion framework={self.framework_id} v{self.version_number} status={self.status}>"

    def publish(self, db: Session, *, published_by: Optional[uuid.UUID] = None) -> None:
        """Publish this version, archiving any previously published version.

        Updates the parent framework's current_version_id pointer.
        Caller must call db.commit().
        """
        if self.status == "published":
            return

        # Archive previously published versions
        db.query(LegalFrameworkVersion).filter(
            LegalFrameworkVersion.framework_id == self.framework_id,
            LegalFrameworkVersion.status == "published",
            LegalFrameworkVersion.id != self.id,
        ).update({"status": "archived"})

        self.status = "published"
        self.published_at = datetime.now(timezone.utc)
        self.published_by = published_by

        # Update parent framework pointer
        self.framework.current_version_id = self.id

        db.flush()

    def update_narrative(self, db: Session, content: str) -> None:
        """Update the narrative markdown.

        Caller must call db.commit().
        """
        self.narrative_markdown = content
        db.flush()

    def update_checklist_item(self, db: Session, item_id: str, updates: dict) -> None:
        """Update a single item in the checklist_items JSONB array.

        Uses flag_modified() for SQLAlchemy JSONB change detection.
        Caller must call db.commit().
        """
        if not self.checklist_items:
            return

        for item in self.checklist_items:
            if item.get("id") == item_id:
                for key, value in updates.items():
                    if key != "id":  # Don't allow changing the id
                        item[key] = value
                break

        flag_modified(self, "checklist_items")
        db.flush()
