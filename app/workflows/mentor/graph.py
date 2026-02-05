"""LangGraph workflow definitions for Mentor Workflow."""
from langgraph.graph import StateGraph, END

from app.workflows.mentor.state import (
    MentorIntakeState,
    MentorPreCallState,
    MentorPostCallState,
)
from app.workflows.mentor.nodes import (
    # Intake nodes
    gather_intake_context,
    generate_prototype_charter,
    generate_initial_backlog,
    finalize_intake,
    # Pre-call nodes
    gather_session_context,
    generate_session_agenda,
    finalize_pre_call,
    # Post-call nodes
    process_session_notes,
    update_decision_log,
    generate_prototype_pack,
    generate_next_tasks,
    finalize_post_call,
)
from app.workflows.runtime import WorkflowRuntime


# Workflow names
WORKFLOW_INTAKE = "mentor_intake"
WORKFLOW_PRE_CALL = "mentor_pre_call"
WORKFLOW_POST_CALL = "mentor_post_call"
WORKFLOW_VERSION = "1.0.0"


# =============================================================================
# INTAKE (SESSION 0) WORKFLOW
# =============================================================================

def create_intake_graph():
    """Create the Intake (Session 0) workflow.

    Outputs: Prototype Charter + initial task backlog
    """
    workflow = StateGraph(MentorIntakeState)

    # Add nodes
    workflow.add_node("gather_context", gather_intake_context)
    workflow.add_node("generate_charter", generate_prototype_charter)
    workflow.add_node("generate_backlog", generate_initial_backlog)
    workflow.add_node("finalize", finalize_intake)

    # Add edges
    workflow.set_entry_point("gather_context")
    workflow.add_edge("gather_context", "generate_charter")
    workflow.add_edge("generate_charter", "generate_backlog")
    workflow.add_edge("generate_backlog", "finalize")
    workflow.add_edge("finalize", END)

    return workflow.compile()


# =============================================================================
# PRE-CALL WORKFLOW
# =============================================================================

def create_pre_call_graph():
    """Create the Pre-Call workflow.

    Outputs: Session agenda + key questions
    """
    workflow = StateGraph(MentorPreCallState)

    # Add nodes
    workflow.add_node("gather_context", gather_session_context)
    workflow.add_node("generate_agenda", generate_session_agenda)
    workflow.add_node("finalize", finalize_pre_call)

    # Add edges
    workflow.set_entry_point("gather_context")
    workflow.add_edge("gather_context", "generate_agenda")
    workflow.add_edge("generate_agenda", "finalize")
    workflow.add_edge("finalize", END)

    return workflow.compile()


# =============================================================================
# POST-CALL WORKFLOW
# =============================================================================

def create_post_call_graph():
    """Create the Post-Call workflow.

    Takes: transcript/notes upload
    Outputs: Decision log update, Prototype Pack, next tasks
    """
    workflow = StateGraph(MentorPostCallState)

    # Add nodes
    workflow.add_node("process_notes", process_session_notes)
    workflow.add_node("update_decisions", update_decision_log)
    workflow.add_node("generate_pack", generate_prototype_pack)
    workflow.add_node("generate_tasks", generate_next_tasks)
    workflow.add_node("finalize", finalize_post_call)

    # Add edges
    workflow.set_entry_point("process_notes")
    workflow.add_edge("process_notes", "update_decisions")
    workflow.add_edge("update_decisions", "generate_pack")
    workflow.add_edge("generate_pack", "generate_tasks")
    workflow.add_edge("generate_tasks", "finalize")
    workflow.add_edge("finalize", END)

    return workflow.compile()


# =============================================================================
# REGISTRATION
# =============================================================================

def register_mentor_workflows():
    """Register all mentor workflows with the runtime."""
    WorkflowRuntime.register_workflow(
        name=WORKFLOW_INTAKE,
        workflow=create_intake_graph,
        version=WORKFLOW_VERSION,
    )
    WorkflowRuntime.register_workflow(
        name=WORKFLOW_PRE_CALL,
        workflow=create_pre_call_graph,
        version=WORKFLOW_VERSION,
    )
    WorkflowRuntime.register_workflow(
        name=WORKFLOW_POST_CALL,
        workflow=create_post_call_graph,
        version=WORKFLOW_VERSION,
    )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def run_intake(
    engagement_id: str,
    journalist_name: str,
    journalist_role: str = "",
    journalist_organization: str = "",
    journalist_skill_level: str = "beginner",
    engagement_title: str = "",
    engagement_description: str = "",
    engagement_topics: list[str] | None = None,
    journalist_goals: str = "",
    project_idea: str = "",
    current_challenges: str = "",
    available_time: str = "",
    technical_comfort: str = "",
    workflow_run_id: str | None = None,
) -> MentorIntakeState:
    """Run the Intake workflow directly."""
    graph = create_intake_graph()

    initial_state: MentorIntakeState = {
        "engagement_id": engagement_id,
        "journalist_name": journalist_name,
        "journalist_role": journalist_role,
        "journalist_organization": journalist_organization,
        "journalist_skill_level": journalist_skill_level,
        "engagement_title": engagement_title,
        "engagement_description": engagement_description,
        "engagement_topics": engagement_topics or [],
        "journalist_goals": journalist_goals,
        "project_idea": project_idea,
        "current_challenges": current_challenges,
        "available_time": available_time,
        "technical_comfort": technical_comfort,
        "workflow_run_id": workflow_run_id,
        "errors": [],
    }

    return await graph.ainvoke(initial_state)


async def run_pre_call(
    engagement_id: str,
    session_number: int,
    journalist_name: str,
    journalist_organization: str = "",
    charter_content: str = "",
    previous_decisions: list | None = None,
    open_tasks: list | None = None,
    completed_tasks: list | None = None,
    previous_session_notes: str = "",
    session_focus: str = "",
    workflow_run_id: str | None = None,
) -> MentorPreCallState:
    """Run the Pre-Call workflow directly."""
    graph = create_pre_call_graph()

    initial_state: MentorPreCallState = {
        "engagement_id": engagement_id,
        "session_number": session_number,
        "journalist_name": journalist_name,
        "journalist_organization": journalist_organization,
        "charter_content": charter_content,
        "previous_decisions": previous_decisions or [],
        "open_tasks": open_tasks or [],
        "completed_tasks": completed_tasks or [],
        "previous_session_notes": previous_session_notes,
        "session_focus": session_focus,
        "workflow_run_id": workflow_run_id,
        "errors": [],
    }

    return await graph.ainvoke(initial_state)


async def run_post_call(
    engagement_id: str,
    session_number: int,
    journalist_name: str,
    journalist_organization: str = "",
    session_notes: str = "",
    session_transcript: str = "",
    session_duration: int = 60,
    charter_content: str = "",
    previous_decisions: list | None = None,
    current_tasks: list | None = None,
    workflow_run_id: str | None = None,
) -> MentorPostCallState:
    """Run the Post-Call workflow directly."""
    graph = create_post_call_graph()

    initial_state: MentorPostCallState = {
        "engagement_id": engagement_id,
        "session_number": session_number,
        "journalist_name": journalist_name,
        "journalist_organization": journalist_organization,
        "session_notes": session_notes,
        "session_transcript": session_transcript,
        "session_duration": session_duration,
        "charter_content": charter_content,
        "previous_decisions": previous_decisions or [],
        "current_tasks": current_tasks or [],
        "workflow_run_id": workflow_run_id,
        "errors": [],
    }

    return await graph.ainvoke(initial_state)
