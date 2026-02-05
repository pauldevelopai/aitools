"""LangGraph workflow definitions for Governance & Tools Intelligence."""
from langgraph.graph import StateGraph, END

from app.workflows.governance.state import GovernanceTargetState
from app.workflows.governance.nodes import (
    # Research nodes
    discover_urls,
    fetch_pages,
    # Framework nodes
    extract_framework_info,
    extract_controls,
    save_framework,
    generate_framework_content,
    # Tool testing nodes
    load_test_cases,
    run_tool_tests,
    save_test_results,
    generate_tool_content,
    # Common nodes
    save_content_items,
    check_needs_review,
    finalize_target,
    route_by_target_type,
)
from app.workflows.runtime import WorkflowRuntime


# Workflow names
WORKFLOW_GOVERNANCE = "governance_intelligence"
WORKFLOW_VERSION = "1.0.0"


def create_governance_graph():
    """Create the Governance & Tools Intelligence workflow.

    This workflow:
    1. Routes based on target type (framework, tool, template)
    2. For frameworks: researches, extracts info, generates content
    3. For tools: runs tests, generates assessment content
    4. Saves all outputs and routes to review
    """
    workflow = StateGraph(GovernanceTargetState)

    # ==========================================================================
    # Add nodes
    # ==========================================================================

    # Research nodes
    workflow.add_node("discover_urls", discover_urls)
    workflow.add_node("fetch_pages", fetch_pages)

    # Framework-specific nodes
    workflow.add_node("extract_framework", extract_framework_info)
    workflow.add_node("extract_controls", extract_controls)
    workflow.add_node("save_framework", save_framework)
    workflow.add_node("generate_framework_content", generate_framework_content)

    # Tool-specific nodes
    workflow.add_node("load_test_cases", load_test_cases)
    workflow.add_node("run_tests", run_tool_tests)
    workflow.add_node("save_test_results", save_test_results)
    workflow.add_node("generate_tool_content", generate_tool_content)

    # Common nodes
    workflow.add_node("save_content", save_content_items)
    workflow.add_node("check_review", check_needs_review)
    workflow.add_node("finalize", finalize_target)

    # ==========================================================================
    # Entry and routing
    # ==========================================================================

    workflow.set_entry_point("discover_urls")

    # After URL discovery, route based on target type
    def route_after_discovery(state: GovernanceTargetState) -> str:
        target_type = state.get("target_type", "framework")
        if target_type == "tool":
            return "load_test_cases"
        else:  # framework or template
            return "fetch_pages"

    workflow.add_conditional_edges(
        "discover_urls",
        route_after_discovery,
        {
            "fetch_pages": "fetch_pages",
            "load_test_cases": "load_test_cases",
        }
    )

    # ==========================================================================
    # Framework flow
    # ==========================================================================

    workflow.add_edge("fetch_pages", "extract_framework")
    workflow.add_edge("extract_framework", "extract_controls")
    workflow.add_edge("extract_controls", "save_framework")
    workflow.add_edge("save_framework", "generate_framework_content")
    workflow.add_edge("generate_framework_content", "save_content")

    # ==========================================================================
    # Tool flow
    # ==========================================================================

    workflow.add_edge("load_test_cases", "run_tests")
    workflow.add_edge("run_tests", "save_test_results")
    workflow.add_edge("save_test_results", "generate_tool_content")
    workflow.add_edge("generate_tool_content", "save_content")

    # ==========================================================================
    # Common ending
    # ==========================================================================

    workflow.add_edge("save_content", "check_review")
    workflow.add_edge("check_review", "finalize")
    workflow.add_edge("finalize", END)

    return workflow.compile()


def register_governance_workflows():
    """Register governance workflows with the runtime."""
    WorkflowRuntime.register_workflow(
        name=WORKFLOW_GOVERNANCE,
        workflow=create_governance_graph,
        version=WORKFLOW_VERSION,
    )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def run_governance_workflow(
    target_id: str,
    target_type: str,
    target_name: str,
    target_description: str = "",
    jurisdiction: str = "",
    tool_id: str = "",
    tool_url: str = "",
    search_terms: list[str] | None = None,
    known_urls: list[str] | None = None,
    workflow_run_id: str | None = None,
) -> GovernanceTargetState:
    """Run the governance workflow directly.

    Args:
        target_id: ID of the GovernanceTarget
        target_type: "framework", "tool", or "template"
        target_name: Name of the target (e.g., "EU AI Act", "ChatGPT")
        target_description: Optional description
        jurisdiction: For frameworks, the jurisdiction (e.g., "EU", "US")
        tool_id: For tools, the ToolsCatalogEntry ID
        tool_url: For tools, the URL to test
        search_terms: Keywords to search for
        known_urls: URLs to fetch directly
        workflow_run_id: Optional workflow run ID for tracking
    """
    graph = create_governance_graph()

    initial_state: GovernanceTargetState = {
        "target_id": target_id,
        "target_type": target_type,
        "target_name": target_name,
        "target_description": target_description,
        "jurisdiction": jurisdiction,
        "tool_id": tool_id,
        "tool_url": tool_url,
        "search_terms": search_terms or [],
        "known_urls": known_urls or [],
        "workflow_run_id": workflow_run_id,
        "errors": [],
    }

    return await graph.ainvoke(initial_state)


async def run_framework_research(
    target_name: str,
    jurisdiction: str,
    known_urls: list[str] | None = None,
    search_terms: list[str] | None = None,
    workflow_run_id: str | None = None,
) -> GovernanceTargetState:
    """Convenience function to run framework research."""
    return await run_governance_workflow(
        target_id="",
        target_type="framework",
        target_name=target_name,
        jurisdiction=jurisdiction,
        known_urls=known_urls,
        search_terms=search_terms,
        workflow_run_id=workflow_run_id,
    )


async def run_tool_testing(
    tool_id: str,
    tool_name: str,
    tool_url: str,
    workflow_run_id: str | None = None,
) -> GovernanceTargetState:
    """Convenience function to run tool testing."""
    return await run_governance_workflow(
        target_id="",
        target_type="tool",
        target_name=tool_name,
        tool_id=tool_id,
        tool_url=tool_url,
        workflow_run_id=workflow_run_id,
    )
