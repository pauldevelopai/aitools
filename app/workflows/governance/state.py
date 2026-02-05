"""State definitions for Governance & Tools Intelligence workflow."""
from typing import TypedDict, Optional


class EvidenceSource(TypedDict, total=False):
    """Evidence source with retrieval metadata."""
    url: str
    title: str
    retrieved_at: str  # ISO format
    excerpt: str
    content_hash: str
    fetch_status: str  # success, failed, timeout


class ExtractedFramework(TypedDict, total=False):
    """Extracted framework information."""
    name: str
    short_name: str
    framework_type: str
    jurisdiction: str
    jurisdiction_scope: str
    description: str
    summary: str
    key_provisions: list[str]
    effective_date: str
    official_url: str
    applies_to: list[str]


class ExtractedControl(TypedDict, total=False):
    """Extracted control/obligation from a framework."""
    control_id: str
    name: str
    description: str
    obligations: list[str]
    control_type: str
    risk_level: str
    applies_to_tools: bool
    applies_to_data: bool
    applies_to_content: bool


class TestResult(TypedDict, total=False):
    """Result of a tool test execution."""
    test_case_id: str
    test_name: str
    passed: bool
    score: float
    duration_ms: int
    metrics: dict
    output: str
    error_message: str
    red_flags: list[str]


class GeneratedContent(TypedDict, total=False):
    """Generated content item."""
    title: str
    slug: str
    content_markdown: str
    summary: str
    content_type: str
    section: str
    tags: list[str]
    jurisdiction: str
    audience: list[str]
    sources: list[EvidenceSource]


# =============================================================================
# FRAMEWORK RESEARCH WORKFLOW STATE
# =============================================================================

class FrameworkResearchState(TypedDict, total=False):
    """State for framework research workflow."""
    # Input
    target_id: str
    target_name: str
    target_description: str
    jurisdiction: str
    search_terms: list[str]
    known_urls: list[str]
    workflow_run_id: str

    # Research phase
    discovered_urls: list[str]
    fetched_pages: list[EvidenceSource]
    fetch_errors: list[str]

    # Extraction phase
    extracted_framework: ExtractedFramework
    extracted_controls: list[ExtractedControl]

    # Content generation phase
    generated_content: list[GeneratedContent]

    # Output
    framework_id: str
    content_item_ids: list[str]
    processing_notes: str
    errors: list[str]


# =============================================================================
# TOOL TESTING WORKFLOW STATE
# =============================================================================

class ToolTestingState(TypedDict, total=False):
    """State for tool testing workflow."""
    # Input
    target_id: str
    tool_id: str
    tool_name: str
    tool_url: str
    test_config: dict
    workflow_run_id: str

    # Test execution
    test_cases: list[dict]  # Test case definitions to run
    test_results: list[TestResult]
    overall_score: float
    overall_passed: bool

    # Analysis
    red_flags: list[str]
    recommendations: list[str]

    # Content generation
    generated_content: list[GeneratedContent]

    # Output
    content_item_ids: list[str]
    processing_notes: str
    errors: list[str]


# =============================================================================
# COMBINED GOVERNANCE WORKFLOW STATE
# =============================================================================

class GovernanceTargetState(TypedDict, total=False):
    """Combined state for processing governance targets."""
    # Target info
    target_id: str
    target_type: str  # framework, tool, template
    target_name: str
    target_description: str
    jurisdiction: str
    tool_id: str
    search_terms: list[str]
    known_urls: list[str]
    workflow_run_id: str

    # Processing
    current_step: str
    discovered_urls: list[str]
    fetched_pages: list[EvidenceSource]

    # Framework-specific
    extracted_framework: ExtractedFramework
    extracted_controls: list[ExtractedControl]
    framework_id: str

    # Tool-specific
    test_cases: list[dict]
    test_results: list[TestResult]
    overall_test_score: float
    red_flags: list[str]

    # Content generation
    generated_content: list[GeneratedContent]
    content_item_ids: list[str]

    # Review
    needs_review: bool
    review_reason: str

    # Output
    processing_notes: str
    errors: list[str]
