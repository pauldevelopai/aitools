"""Core agentic loop for the Grounded Brain.

Uses the native Anthropic tool_use pattern: send messages with tool
definitions, receive tool_use blocks, execute tools, return results,
and loop until the model emits end_turn.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.brain.missions import MISSIONS
from app.brain.system_prompt import BRAIN_SYSTEM_PROMPT
from app.brain.tools import (
    BrainContext,
    execute_tool,
    get_tool_schemas,
)
from app.services.completion import get_completion_client

logger = logging.getLogger(__name__)

# Safety limits
MAX_TURNS = 25


@dataclass
class BrainResult:
    """Result from a Brain run."""
    created_records: list[dict] = field(default_factory=list)
    research_notes: str = ""
    steps_taken: int = 0
    tool_calls: list[dict] = field(default_factory=list)
    tokens_used: dict[str, int] = field(default_factory=lambda: {"input": 0, "output": 0})
    error: str | None = None
    started_at: str = ""
    completed_at: str = ""


class GroundedBrain:
    """Runs a Claude-native tool_use research loop.

    Replaces the OpenAI Agents SDK AgentEngine with a direct
    Anthropic messages API loop that supports tool_use.
    """

    def __init__(self, db: Session):
        self.db = db

    async def run(self, mission_name: str, params: dict, run_id: str) -> BrainResult:
        """Execute a Brain mission.

        Args:
            mission_name: Key from MISSIONS dict
            params: Mission-specific parameters
            run_id: WorkflowRun ID for tracking

        Returns:
            BrainResult with created records and metadata
        """
        result = BrainResult(started_at=datetime.now(timezone.utc).isoformat())

        # Validate mission
        mission = MISSIONS.get(mission_name)
        if not mission:
            result.error = f"Unknown mission: {mission_name}"
            result.completed_at = datetime.now(timezone.utc).isoformat()
            return result

        # Get the Claude client
        try:
            client = get_completion_client()
        except Exception as e:
            result.error = f"Claude client not available: {e}"
            result.completed_at = datetime.now(timezone.utc).isoformat()
            return result

        # Build system prompt: core identity + mission-specific supplement
        system_prompt = BRAIN_SYSTEM_PROMPT + "\n\n" + mission["system_prompt_supplement"]

        # Append dynamic parameters to system prompt
        for param_key in ("region", "category", "topic", "jurisdiction", "focus"):
            if params.get(param_key):
                label = param_key.replace("_", " ").title()
                system_prompt += f"\n{label}: {params[param_key]}"

        # Build user message
        build_message = mission.get("build_user_message")
        if build_message:
            user_message = build_message(params)
        else:
            user_message = f"Execute mission: {mission_name} with parameters: {params}"

        # Get tool schemas for this mission
        tool_schemas = get_tool_schemas(mission["allowed_tools"])

        # Create execution context
        ctx = BrainContext(db=self.db, run_id=run_id)

        # Initialize conversation
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": user_message}
        ]

        try:
            turn = 0
            while turn < MAX_TURNS:
                turn += 1

                # Call Claude with tools
                response = await client.create_message_async(
                    messages=messages,
                    system=system_prompt,
                    max_tokens=4096,
                    temperature=0.3,
                    tools=tool_schemas,
                )

                # Track token usage
                if hasattr(response, "usage"):
                    result.tokens_used["input"] += getattr(response.usage, "input_tokens", 0)
                    result.tokens_used["output"] += getattr(response.usage, "output_tokens", 0)

                # Check if the model is done (no more tool calls)
                if response.stop_reason == "end_turn":
                    # Extract final text from the response
                    text_parts = []
                    for block in response.content:
                        if block.type == "text":
                            text_parts.append(block.text)
                    result.research_notes = "\n".join(text_parts)
                    break

                # Process tool_use blocks
                has_tool_use = False
                tool_results = []

                for block in response.content:
                    if block.type == "tool_use":
                        has_tool_use = True
                        tool_name = block.name
                        tool_input = block.input
                        tool_use_id = block.id

                        logger.info(f"Brain tool call: {tool_name}({tool_input})")

                        # Execute the tool
                        tool_result = execute_tool(ctx, tool_name, tool_input)

                        # Record the tool call for audit
                        call_record = {
                            "turn": turn,
                            "tool": tool_name,
                            "input": tool_input,
                            "output": tool_result[:500],  # Truncate for storage
                        }
                        ctx.tool_calls.append(call_record)
                        result.tool_calls.append(call_record)

                        # Build tool_result block for the next message
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": tool_result,
                        })

                if not has_tool_use:
                    # No tool calls and not end_turn — extract text and break
                    text_parts = []
                    for block in response.content:
                        if block.type == "text":
                            text_parts.append(block.text)
                    result.research_notes = "\n".join(text_parts)
                    break

                # Append assistant response + tool results to conversation
                # The assistant message must include the full content (text + tool_use blocks)
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

            else:
                # Exceeded MAX_TURNS
                logger.warning(f"Brain run {run_id} hit max turns ({MAX_TURNS})")
                result.research_notes += f"\n\n[Stopped after {MAX_TURNS} turns]"

        except Exception as e:
            result.error = f"Brain error: {e}"
            logger.exception(f"Brain error for run {run_id}")

        # Finalize result
        result.created_records = ctx.created_records
        result.steps_taken = ctx.steps_taken
        result.completed_at = datetime.now(timezone.utc).isoformat()

        return result
