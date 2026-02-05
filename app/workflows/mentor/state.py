"""State definitions for Mentor Workflow."""
from typing import TypedDict, Optional, Any


class TaskItem(TypedDict, total=False):
    """A task item for the mentor backlog."""
    title: str
    description: str
    task_type: str  # action, decision, blocker, learning, deliverable
    priority: int  # 1-5
    assigned_to: str  # "journalist", "mentor", or specific name
    due_date: Optional[str]


class DecisionItem(TypedDict, total=False):
    """A decision logged during mentoring."""
    topic: str
    decision: str
    rationale: str
    date: str


class KeyQuestion(TypedDict, total=False):
    """A key question for the session agenda."""
    question: str
    context: str
    priority: int


class MentorIntakeState(TypedDict, total=False):
    """State for the Intake (Session 0) workflow.

    Outputs: Prototype Charter + initial task backlog
    """
    # Input
    engagement_id: str
    journalist_name: str
    journalist_role: str
    journalist_organization: str
    journalist_skill_level: str
    engagement_title: str
    engagement_description: str
    engagement_topics: list[str]

    # Context gathering
    journalist_goals: str  # What they want to achieve
    project_idea: str  # Initial prototype concept
    current_challenges: str  # Pain points
    available_time: str  # How much time they can commit
    technical_comfort: str  # Comfort with technical tools

    # Outputs
    charter_content: str  # Markdown content for Prototype Charter
    charter_structured: dict  # Structured data
    initial_tasks: list[TaskItem]

    # Workflow tracking
    workflow_run_id: Optional[str]
    errors: list[str]
    summary: str


class MentorPreCallState(TypedDict, total=False):
    """State for the Pre-Call workflow.

    Outputs: Session agenda + key questions
    """
    # Input
    engagement_id: str
    session_number: int
    journalist_name: str
    journalist_organization: str

    # Context from previous sessions
    charter_content: str
    previous_decisions: list[DecisionItem]
    open_tasks: list[TaskItem]
    completed_tasks: list[TaskItem]
    previous_session_notes: str

    # Focus for this session
    session_focus: str  # Optional focus area

    # Outputs
    agenda_content: str  # Markdown agenda
    key_questions: list[KeyQuestion]
    suggested_topics: list[str]
    time_allocations: dict[str, int]  # topic -> minutes

    # Workflow tracking
    workflow_run_id: Optional[str]
    errors: list[str]
    summary: str


class MentorPostCallState(TypedDict, total=False):
    """State for the Post-Call workflow.

    Takes: transcript/notes upload
    Outputs: Updated decision log, Prototype Pack, next tasks
    """
    # Input
    engagement_id: str
    session_number: int
    journalist_name: str
    journalist_organization: str

    # Session input
    session_notes: str  # Raw notes or transcript
    session_transcript: str  # Full transcript if available
    session_duration: int  # Minutes

    # Context
    charter_content: str
    previous_decisions: list[DecisionItem]
    current_tasks: list[TaskItem]

    # Extracted from notes
    new_decisions: list[DecisionItem]
    completed_task_ids: list[str]
    blocked_tasks: list[str]
    new_insights: list[str]

    # Outputs
    decision_log_update: str  # Markdown for decision log
    prototype_pack_content: str  # Markdown for Prototype Pack
    prototype_pack_structured: dict  # Structured data
    next_tasks: list[TaskItem]
    session_summary: str  # Brief summary of the session

    # Skill assessment
    skill_progression_notes: str
    recommended_skill_level: str

    # Workflow tracking
    workflow_run_id: Optional[str]
    errors: list[str]
    summary: str
