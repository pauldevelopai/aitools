"""LangGraph workflow definition for Partner Intelligence."""
from typing import Literal
from langgraph.graph import StateGraph, END

from app.workflows.partner_intelligence.state import PartnerIntelligenceState
from app.workflows.partner_intelligence.nodes import (
    identify_pages,
    fetch_pages,
    extract_fields,
    detect_conflicts,
    upsert_enrichment,
    save_evidence,
    compile_output,
)
from app.workflows.runtime import WorkflowRuntime


WORKFLOW_NAME = "partner_intelligence"
WORKFLOW_VERSION = "1.0.0"


def create_partner_intelligence_graph(db_session=None):
    """Create the Partner Intelligence LangGraph workflow.

    The workflow follows these steps:
    1. identify_pages - Discover key pages on the organization's website
    2. fetch_pages - Fetch and store page content
    3. extract_fields - Use LLM to extract structured data
    4. detect_conflicts - Check for conflicts with existing data
    5. route_review - Conditional routing based on confidence/conflicts
    6a. upsert_enrichment - Apply changes (if no review needed)
    6b. [END needs_review] - Stop for human review
    7. save_evidence - Store evidence sources
    8. compile_output - Prepare final output

    Args:
        db_session: SQLAlchemy database session for persistence

    Returns:
        Compiled LangGraph workflow
    """
    # Create workflow builder
    workflow = StateGraph(PartnerIntelligenceState)

    # Create node wrappers that inject db_session
    async def fetch_pages_with_db(state):
        return await fetch_pages(state, db_session)

    async def upsert_enrichment_with_db(state):
        return await upsert_enrichment(state, db_session)

    async def save_evidence_with_db(state):
        return await save_evidence(state, db_session)

    # Add nodes
    workflow.add_node("identify_pages", identify_pages)
    workflow.add_node("fetch_pages", fetch_pages_with_db)
    workflow.add_node("extract_fields", extract_fields)
    workflow.add_node("detect_conflicts", detect_conflicts)
    workflow.add_node("upsert_enrichment", upsert_enrichment_with_db)
    workflow.add_node("save_evidence", save_evidence_with_db)
    workflow.add_node("compile_output", compile_output)

    # Define routing function
    def route_after_conflicts(state: PartnerIntelligenceState) -> Literal["upsert_enrichment", "compile_output"]:
        """Route based on whether review is needed."""
        if state.get("needs_review"):
            # Skip upsert, go directly to compile output
            return "compile_output"
        return "upsert_enrichment"

    # Add edges
    workflow.set_entry_point("identify_pages")
    workflow.add_edge("identify_pages", "fetch_pages")
    workflow.add_edge("fetch_pages", "extract_fields")
    workflow.add_edge("extract_fields", "detect_conflicts")

    # Conditional routing after conflict detection
    workflow.add_conditional_edges(
        "detect_conflicts",
        route_after_conflicts,
        {
            "upsert_enrichment": "upsert_enrichment",
            "compile_output": "compile_output",
        }
    )

    workflow.add_edge("upsert_enrichment", "save_evidence")
    workflow.add_edge("save_evidence", "compile_output")
    workflow.add_edge("compile_output", END)

    # Compile the graph
    return workflow.compile()


def register_partner_intelligence_workflow():
    """Register the Partner Intelligence workflow with the runtime.

    This should be called during application startup.
    """
    # We register a factory function that creates the graph with a db session
    WorkflowRuntime.register_workflow(
        name=WORKFLOW_NAME,
        workflow=create_partner_intelligence_graph,
        version=WORKFLOW_VERSION,
    )


async def run_partner_intelligence(
    organization_id: str,
    organization_name: str,
    website_url: str,
    current_description: str | None = None,
    current_notes: str | None = None,
    db_session=None,
    workflow_run_id: str | None = None,
) -> PartnerIntelligenceState:
    """Execute the Partner Intelligence workflow directly.

    This is a convenience function for running the workflow without
    going through the WorkflowRuntime.

    Args:
        organization_id: UUID of the organization to enrich
        organization_name: Name of the organization
        website_url: Website URL to analyze
        current_description: Current description (for conflict detection)
        current_notes: Current notes
        db_session: SQLAlchemy database session
        workflow_run_id: Optional workflow run ID for tracking

    Returns:
        Final workflow state with results
    """
    # Create the graph with the database session
    graph = create_partner_intelligence_graph(db_session)

    # Prepare initial state
    initial_state: PartnerIntelligenceState = {
        "organization_id": organization_id,
        "organization_name": organization_name,
        "website_url": website_url,
        "current_description": current_description,
        "current_notes": current_notes,
        "workflow_run_id": workflow_run_id,
        "discovered_pages": [],
        "snapshot_ids": [],
        "fetch_errors": [],
        "extracted_fields": [],
        "extraction_errors": [],
        "enrichment": {},
        "conflicts": [],
        "has_conflicts": False,
        "needs_review": False,
        "low_confidence_fields": [],
        "evidence_source_ids": [],
        "enrichment_applied": False,
        "errors": [],
    }

    # Execute the workflow
    result = await graph.ainvoke(initial_state)

    return result
