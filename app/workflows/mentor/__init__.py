"""Mentor Workflow package for prototype-shipped mentoring system.

This package provides three workflow entrypoints:
1. Intake (Session 0) - Generates Prototype Charter + initial task backlog
2. Pre-Call - Generates session agenda + key questions
3. Post-Call - Processes notes/transcript, updates decision log, generates Prototype Pack + next tasks
"""
from app.workflows.mentor.graph import (
    create_intake_graph,
    create_pre_call_graph,
    create_post_call_graph,
    register_mentor_workflows,
    run_intake,
    run_pre_call,
    run_post_call,
    WORKFLOW_INTAKE,
    WORKFLOW_PRE_CALL,
    WORKFLOW_POST_CALL,
)
from app.workflows.mentor.state import (
    MentorIntakeState,
    MentorPreCallState,
    MentorPostCallState,
    TaskItem,
    DecisionItem,
    KeyQuestion,
)

__all__ = [
    # Graph creators
    "create_intake_graph",
    "create_pre_call_graph",
    "create_post_call_graph",
    "register_mentor_workflows",
    # Convenience runners
    "run_intake",
    "run_pre_call",
    "run_post_call",
    # Workflow names
    "WORKFLOW_INTAKE",
    "WORKFLOW_PRE_CALL",
    "WORKFLOW_POST_CALL",
    # State types
    "MentorIntakeState",
    "MentorPreCallState",
    "MentorPostCallState",
    "TaskItem",
    "DecisionItem",
    "KeyQuestion",
]
