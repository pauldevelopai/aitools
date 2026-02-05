"""Node implementations for Mentor Workflow."""
import json
from datetime import datetime, timezone
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.workflows.mentor.state import (
    MentorIntakeState,
    MentorPreCallState,
    MentorPostCallState,
    TaskItem,
    DecisionItem,
    KeyQuestion,
)


# LLM Configuration
MODEL = "gpt-4o-mini"


def _get_llm():
    """Get the LLM instance."""
    return ChatOpenAI(model=MODEL, temperature=0.7)


def _parse_json_response(response_text: str) -> dict:
    """Parse JSON from LLM response, handling markdown code blocks."""
    text = response_text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    return json.loads(text.strip())


# =============================================================================
# INTAKE (SESSION 0) WORKFLOW NODES
# =============================================================================

async def gather_intake_context(state: MentorIntakeState) -> dict:
    """Gather and validate context for intake."""
    errors = []

    if not state.get("journalist_name"):
        errors.append("Journalist name is required")
    if not state.get("engagement_title"):
        errors.append("Engagement title is required")

    return {
        "errors": errors,
    }


async def generate_prototype_charter(state: MentorIntakeState) -> dict:
    """Generate the Prototype Charter using LLM."""
    journalist_name = state.get("journalist_name", "the journalist")
    journalist_org = state.get("journalist_organization", "their organization")
    journalist_role = state.get("journalist_role", "")
    skill_level = state.get("journalist_skill_level", "beginner")
    engagement_title = state.get("engagement_title", "Mentoring Engagement")
    engagement_desc = state.get("engagement_description", "")
    topics = state.get("engagement_topics", [])

    # Additional context
    goals = state.get("journalist_goals", "Not specified")
    project_idea = state.get("project_idea", "Not specified")
    challenges = state.get("current_challenges", "Not specified")
    available_time = state.get("available_time", "Not specified")
    technical_comfort = state.get("technical_comfort", "Not specified")

    system_prompt = """You are an expert AI mentor helping journalists build AI prototypes for their newsrooms.

Generate a Prototype Charter document that will guide a mentoring engagement. The charter should:
1. Clearly define the prototype's purpose and scope
2. Identify success criteria
3. Outline the mentoring approach
4. Set realistic expectations given the journalist's skill level
5. Define deliverables and timeline

Output in JSON format with these fields:
{
    "title": "Charter title",
    "summary": "2-3 sentence executive summary",
    "prototype_vision": "What we're building and why",
    "success_criteria": ["criterion 1", "criterion 2", ...],
    "scope": {
        "in_scope": ["item 1", "item 2"],
        "out_of_scope": ["item 1", "item 2"]
    },
    "approach": "How we'll work together",
    "milestones": [
        {"name": "Milestone 1", "description": "...", "target_session": 1},
        ...
    ],
    "risks": ["risk 1", "risk 2"],
    "markdown_content": "Full charter in markdown format"
}"""

    user_prompt = f"""Create a Prototype Charter for this mentoring engagement:

**Journalist:** {journalist_name}
**Organization:** {journalist_org}
**Role:** {journalist_role}
**Current AI Skill Level:** {skill_level}

**Engagement:** {engagement_title}
**Description:** {engagement_desc}
**Topics:** {', '.join(topics) if topics else 'General AI for journalism'}

**Journalist's Goals:** {goals}
**Prototype Idea:** {project_idea}
**Current Challenges:** {challenges}
**Available Time:** {available_time}
**Technical Comfort:** {technical_comfort}

Generate a comprehensive but achievable charter for shipping a working prototype."""

    try:
        llm = _get_llm()
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        data = _parse_json_response(response.content)

        return {
            "charter_content": data.get("markdown_content", ""),
            "charter_structured": {
                "title": data.get("title"),
                "summary": data.get("summary"),
                "prototype_vision": data.get("prototype_vision"),
                "success_criteria": data.get("success_criteria", []),
                "scope": data.get("scope", {}),
                "approach": data.get("approach"),
                "milestones": data.get("milestones", []),
                "risks": data.get("risks", []),
            },
        }

    except Exception as e:
        return {
            "errors": [f"Failed to generate charter: {str(e)}"],
            "charter_content": "",
            "charter_structured": {},
        }


async def generate_initial_backlog(state: MentorIntakeState) -> dict:
    """Generate initial task backlog based on the charter."""
    charter = state.get("charter_structured", {})
    journalist_name = state.get("journalist_name", "Journalist")
    skill_level = state.get("journalist_skill_level", "beginner")

    system_prompt = """You are an expert AI mentor. Based on a Prototype Charter, generate an initial task backlog.

Each task should be actionable and appropriate for the journalist's skill level.
Mix tasks for both the journalist and mentor.

Output JSON array of tasks:
[
    {
        "title": "Task title",
        "description": "Detailed description",
        "task_type": "action|decision|learning|deliverable",
        "priority": 1-5 (1=highest),
        "assigned_to": "journalist|mentor"
    },
    ...
]

Generate 5-10 tasks that form a logical progression toward the prototype."""

    user_prompt = f"""Generate initial backlog for:

**Charter Summary:** {charter.get('summary', 'Not available')}
**Prototype Vision:** {charter.get('prototype_vision', 'Not available')}
**Milestones:** {json.dumps(charter.get('milestones', []))}
**Skill Level:** {skill_level}

Create tasks that will help {journalist_name} ship their prototype."""

    try:
        llm = _get_llm()
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        tasks = _parse_json_response(response.content)
        if not isinstance(tasks, list):
            tasks = []

        return {
            "initial_tasks": tasks,
        }

    except Exception as e:
        return {
            "errors": [f"Failed to generate backlog: {str(e)}"],
            "initial_tasks": [],
        }


async def finalize_intake(state: MentorIntakeState) -> dict:
    """Finalize intake outputs."""
    charter_content = state.get("charter_content", "")
    tasks = state.get("initial_tasks", [])
    errors = state.get("errors", [])

    if charter_content and tasks:
        summary = f"Generated Prototype Charter and {len(tasks)} initial tasks"
    elif charter_content:
        summary = "Generated Prototype Charter (no tasks created)"
    else:
        summary = "Intake incomplete - check errors"

    return {
        "summary": summary,
        "errors": errors,
    }


# =============================================================================
# PRE-CALL WORKFLOW NODES
# =============================================================================

async def gather_session_context(state: MentorPreCallState) -> dict:
    """Gather context for the upcoming session."""
    session_number = state.get("session_number", 1)
    open_tasks = state.get("open_tasks", [])
    completed_tasks = state.get("completed_tasks", [])

    context_summary = f"Session {session_number}: {len(open_tasks)} open tasks, {len(completed_tasks)} completed"

    return {
        "summary": context_summary,
    }


async def generate_session_agenda(state: MentorPreCallState) -> dict:
    """Generate agenda and key questions for the session."""
    session_number = state.get("session_number", 1)
    journalist_name = state.get("journalist_name", "the journalist")
    charter_content = state.get("charter_content", "")
    previous_decisions = state.get("previous_decisions", [])
    open_tasks = state.get("open_tasks", [])
    previous_notes = state.get("previous_session_notes", "")
    session_focus = state.get("session_focus", "")

    system_prompt = """You are an expert AI mentor preparing for a mentoring session.

Generate a structured agenda with key questions to drive the session productively.

Output JSON:
{
    "agenda_markdown": "Full agenda in markdown format",
    "key_questions": [
        {"question": "...", "context": "why this matters", "priority": 1-3}
    ],
    "suggested_topics": ["topic 1", "topic 2"],
    "time_allocations": {
        "Check-in": 5,
        "Progress review": 15,
        "Main topic": 25,
        "Next steps": 10,
        "Buffer": 5
    }
}"""

    user_prompt = f"""Prepare agenda for Session {session_number} with {journalist_name}:

**Charter Summary:**
{charter_content[:1000] if charter_content else 'Not available'}

**Previous Decisions:**
{json.dumps(previous_decisions[:5]) if previous_decisions else 'None yet'}

**Open Tasks:**
{json.dumps(open_tasks[:10]) if open_tasks else 'None'}

**Notes from Last Session:**
{previous_notes[:500] if previous_notes else 'First session or no notes'}

**Session Focus:** {session_focus if session_focus else 'General progress review'}

Generate an agenda that keeps us on track toward shipping the prototype."""

    try:
        llm = _get_llm()
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        data = _parse_json_response(response.content)

        return {
            "agenda_content": data.get("agenda_markdown", ""),
            "key_questions": data.get("key_questions", []),
            "suggested_topics": data.get("suggested_topics", []),
            "time_allocations": data.get("time_allocations", {}),
        }

    except Exception as e:
        return {
            "errors": [f"Failed to generate agenda: {str(e)}"],
            "agenda_content": "",
            "key_questions": [],
        }


async def finalize_pre_call(state: MentorPreCallState) -> dict:
    """Finalize pre-call outputs."""
    agenda = state.get("agenda_content", "")
    questions = state.get("key_questions", [])

    if agenda:
        summary = f"Generated agenda with {len(questions)} key questions"
    else:
        summary = "Failed to generate agenda"

    return {
        "summary": summary,
    }


# =============================================================================
# POST-CALL WORKFLOW NODES
# =============================================================================

async def process_session_notes(state: MentorPostCallState) -> dict:
    """Process session notes/transcript to extract key information."""
    session_notes = state.get("session_notes", "")
    session_transcript = state.get("session_transcript", "")
    current_tasks = state.get("current_tasks", [])

    content = session_transcript if session_transcript else session_notes

    if not content:
        return {
            "errors": ["No session notes or transcript provided"],
        }

    system_prompt = """You are an expert AI mentor analyzing session notes.

Extract key information from the session notes/transcript:
1. Decisions made during the session
2. Tasks that were completed or discussed
3. New blockers or challenges identified
4. Key insights or learnings
5. Action items for next steps

Output JSON:
{
    "decisions": [
        {"topic": "...", "decision": "...", "rationale": "..."}
    ],
    "completed_task_titles": ["task 1", "task 2"],
    "blockers": ["blocker 1"],
    "insights": ["insight 1", "insight 2"],
    "action_items": ["action 1", "action 2"],
    "skill_observations": "Notes on journalist's skill progression",
    "session_summary": "2-3 sentence summary of the session"
}"""

    user_prompt = f"""Analyze these session notes:

{content[:5000]}

**Current Tasks for Context:**
{json.dumps([t.get('title') for t in current_tasks[:10]]) if current_tasks else 'None'}

Extract the key information from this session."""

    try:
        llm = _get_llm()
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        data = _parse_json_response(response.content)

        return {
            "new_decisions": data.get("decisions", []),
            "completed_task_ids": data.get("completed_task_titles", []),
            "blocked_tasks": data.get("blockers", []),
            "new_insights": data.get("insights", []),
            "skill_progression_notes": data.get("skill_observations", ""),
            "session_summary": data.get("session_summary", ""),
        }

    except Exception as e:
        return {
            "errors": [f"Failed to process notes: {str(e)}"],
        }


async def update_decision_log(state: MentorPostCallState) -> dict:
    """Update the decision log with new decisions."""
    new_decisions = state.get("new_decisions", [])
    previous_decisions = state.get("previous_decisions", [])
    session_number = state.get("session_number", 1)

    if not new_decisions:
        return {
            "decision_log_update": "",
        }

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Format decision log entry
    log_entries = [f"## Session {session_number} Decisions ({today})\n"]

    for decision in new_decisions:
        log_entries.append(f"### {decision.get('topic', 'Untitled Decision')}")
        log_entries.append(f"**Decision:** {decision.get('decision', 'Not specified')}")
        if decision.get('rationale'):
            log_entries.append(f"**Rationale:** {decision.get('rationale')}")
        log_entries.append("")

    return {
        "decision_log_update": "\n".join(log_entries),
    }


async def generate_prototype_pack(state: MentorPostCallState) -> dict:
    """Generate/update the Prototype Pack."""
    journalist_name = state.get("journalist_name", "the journalist")
    session_number = state.get("session_number", 1)
    charter_content = state.get("charter_content", "")
    all_decisions = state.get("previous_decisions", []) + state.get("new_decisions", [])
    insights = state.get("new_insights", [])
    session_summary = state.get("session_summary", "")

    system_prompt = """You are an expert AI mentor creating a Prototype Pack.

The Prototype Pack is a living document that captures:
1. Current state of the prototype
2. Key decisions and rationale
3. Learnings and insights
4. Next steps and recommendations
5. Resources and references

Output JSON:
{
    "prototype_pack_markdown": "Full pack in markdown format",
    "structured_data": {
        "status": "in_progress|near_complete|complete",
        "completion_percentage": 0-100,
        "key_achievements": ["achievement 1"],
        "next_priorities": ["priority 1"],
        "recommended_resources": ["resource 1"]
    }
}"""

    user_prompt = f"""Generate Prototype Pack for {journalist_name} after Session {session_number}:

**Charter:**
{charter_content[:1500] if charter_content else 'Not available'}

**Session Summary:**
{session_summary}

**Key Decisions Made:**
{json.dumps(all_decisions[:10]) if all_decisions else 'None yet'}

**Insights Gained:**
{json.dumps(insights) if insights else 'None recorded'}

Create a comprehensive Prototype Pack that helps the journalist continue making progress."""

    try:
        llm = _get_llm()
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        data = _parse_json_response(response.content)

        return {
            "prototype_pack_content": data.get("prototype_pack_markdown", ""),
            "prototype_pack_structured": data.get("structured_data", {}),
        }

    except Exception as e:
        return {
            "errors": [f"Failed to generate prototype pack: {str(e)}"],
            "prototype_pack_content": "",
            "prototype_pack_structured": {},
        }


async def generate_next_tasks(state: MentorPostCallState) -> dict:
    """Generate next tasks based on session outcomes."""
    session_summary = state.get("session_summary", "")
    blocked_tasks = state.get("blocked_tasks", [])
    insights = state.get("new_insights", [])
    prototype_pack = state.get("prototype_pack_structured", {})

    next_priorities = prototype_pack.get("next_priorities", [])

    system_prompt = """You are an expert AI mentor generating next action items.

Based on the session outcomes, generate concrete next tasks.
Tasks should be actionable, specific, and appropriate for the current stage.

Output JSON array:
[
    {
        "title": "Task title",
        "description": "Detailed description",
        "task_type": "action|decision|blocker|learning|deliverable",
        "priority": 1-5,
        "assigned_to": "journalist|mentor"
    }
]

Generate 3-5 tasks for the next sprint."""

    user_prompt = f"""Generate next tasks based on:

**Session Summary:** {session_summary}

**Blockers Identified:** {json.dumps(blocked_tasks) if blocked_tasks else 'None'}

**New Insights:** {json.dumps(insights) if insights else 'None'}

**Next Priorities:** {json.dumps(next_priorities) if next_priorities else 'Continue progress'}

Create actionable tasks for the next phase."""

    try:
        llm = _get_llm()
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        tasks = _parse_json_response(response.content)
        if not isinstance(tasks, list):
            tasks = []

        return {
            "next_tasks": tasks,
        }

    except Exception as e:
        return {
            "errors": [f"Failed to generate next tasks: {str(e)}"],
            "next_tasks": [],
        }


async def finalize_post_call(state: MentorPostCallState) -> dict:
    """Finalize post-call outputs."""
    prototype_pack = state.get("prototype_pack_content", "")
    next_tasks = state.get("next_tasks", [])
    new_decisions = state.get("new_decisions", [])
    errors = state.get("errors", [])

    parts = []
    if prototype_pack:
        parts.append("Prototype Pack")
    if next_tasks:
        parts.append(f"{len(next_tasks)} new tasks")
    if new_decisions:
        parts.append(f"{len(new_decisions)} decisions logged")

    if parts:
        summary = f"Generated: {', '.join(parts)}"
    else:
        summary = "Post-call processing incomplete - check errors"

    return {
        "summary": summary,
        "errors": errors,
    }
