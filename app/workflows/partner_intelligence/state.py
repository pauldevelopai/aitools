"""State definitions for Partner Intelligence workflow."""
from typing import TypedDict, Optional, Any
from uuid import UUID


class PageInfo(TypedDict, total=False):
    """Information about a discovered page."""
    url: str
    page_type: str  # homepage, about, team, contact, news, programs
    priority: int  # 1=highest priority
    fetched: bool
    status_code: Optional[int]
    error: Optional[str]


class ExtractedField(TypedDict, total=False):
    """A single extracted field with confidence."""
    field_name: str
    value: Any
    confidence: float  # 0.0-1.0
    source_url: str
    extraction_method: str
    needs_review: bool
    review_reason: Optional[str]


class ConflictInfo(TypedDict, total=False):
    """Information about a detected conflict."""
    field_name: str
    current_value: Any
    new_value: Any
    confidence: float
    resolution: Optional[str]  # "keep_current", "use_new", "manual"


class PartnerIntelligenceState(TypedDict, total=False):
    """State for the Partner Intelligence workflow.

    This state is passed through all workflow nodes and contains:
    - Input data (organization info)
    - Discovered pages and their content
    - Extracted fields with confidence scores
    - Conflict detection results
    - Final enrichment results
    """

    # Input
    organization_id: str
    organization_name: str
    website_url: str
    current_description: Optional[str]
    current_notes: Optional[str]

    # Page discovery
    discovered_pages: list[PageInfo]
    canonical_url: Optional[str]

    # Fetched content (stored separately in WebPageSnapshot, IDs here)
    snapshot_ids: list[str]
    fetch_errors: list[str]

    # Extraction results
    extracted_fields: list[ExtractedField]
    extraction_errors: list[str]

    # Structured enrichment data
    enrichment: dict[str, Any]
    # Expected keys: description, focus_areas, countries_served, key_people, programs

    # Conflict detection
    conflicts: list[ConflictInfo]
    has_conflicts: bool

    # Review routing
    needs_review: bool
    review_reason: Optional[str]
    low_confidence_fields: list[str]

    # Evidence tracking
    evidence_source_ids: list[str]

    # Final output
    enrichment_applied: bool
    summary: str
    errors: list[str]

    # Workflow metadata
    __state__: dict  # For needs_review flag passthrough
