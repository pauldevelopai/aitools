"""Core agentic loop for the AI agent.

Uses OpenAI's Chat Completions API with function calling
and database tools in an iterative tool-use loop.
"""
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field

from openai import OpenAI, APIError

from sqlalchemy.orm import Session

from app.settings import settings
from app.workflows.agent.missions import MISSIONS
from app.workflows.agent.tools import ALL_TOOL_SCHEMAS, TOOL_HANDLERS

logger = logging.getLogger(__name__)

# Safety limits
MAX_ITERATIONS = 25
TIMEOUT_SECONDS = 300  # 5 minutes


@dataclass
class AgentResult:
    """Result from an agent run."""
    created_records: list[dict] = field(default_factory=list)
    research_notes: str = ""
    steps_taken: int = 0
    error: str | None = None


class AgentEngine:
    """Runs an OpenAI-powered agentic loop with function calling."""

    def __init__(self, db: Session):
        self.db = db
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    async def run(self, mission_name: str, params: dict, run_id: str) -> AgentResult:
        """Execute an agent mission.

        Args:
            mission_name: Key from MISSIONS dict
            params: Mission-specific parameters
            run_id: WorkflowRun ID for tracking

        Returns:
            AgentResult with created records and metadata
        """
        mission = MISSIONS.get(mission_name)
        if not mission:
            return AgentResult(error=f"Unknown mission: {mission_name}")

        # Build system prompt with mission context + parameters
        system_prompt = mission["system_prompt"]
        if params.get("region"):
            system_prompt += f"\nTarget region: {params['region']}"
        if params.get("category"):
            system_prompt += f"\nTarget category: {params['category']}"
        if params.get("focus"):
            system_prompt += f"\nFocus: {params['focus']}"

        # Build tool list for OpenAI function calling
        tools = self._build_tools(mission["allowed_tools"])

        # Initial user message
        user_message = self._build_user_message(mission_name, params)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        result = AgentResult()
        start_time = time.time()

        try:
            for iteration in range(MAX_ITERATIONS):
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > TIMEOUT_SECONDS:
                    result.research_notes += f"\n[Stopped: timeout after {int(elapsed)}s]"
                    break

                # Call OpenAI
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=settings.OPENAI_CHAT_MODEL,
                    max_tokens=4096,
                    tools=tools,
                    messages=messages,
                )

                choice = response.choices[0]
                message = choice.message
                result.steps_taken = iteration + 1

                # If model stopped without tool calls, we're done
                if choice.finish_reason != "tool_calls":
                    if message.content:
                        result.research_notes += message.content
                    break

                # Append assistant message (with tool_calls) to conversation
                messages.append(message)

                # Process each tool call
                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        fn_name = tool_call.function.name
                        try:
                            fn_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            fn_args = {}

                        tool_result = await self._execute_client_tool(
                            fn_name, fn_args, run_id, result
                        )

                        # Feed tool result back as a tool message
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_result,
                        })

        except APIError as e:
            result.error = f"OpenAI API error: {e}"
            logger.error(f"Agent API error for run {run_id}: {e}")
        except Exception as e:
            result.error = f"Agent error: {e}"
            logger.exception(f"Agent error for run {run_id}")

        return result

    def _build_tools(self, allowed_tool_names: list[str]) -> list[dict]:
        """Build the tools list for the OpenAI function calling API."""
        tools = []

        for name in allowed_tool_names:
            schema = ALL_TOOL_SCHEMAS.get(name)
            if schema:
                tools.append({
                    "type": "function",
                    "function": schema,
                })

        return tools

    def _build_user_message(self, mission_name: str, params: dict) -> str:
        """Build the initial user message based on mission and params."""
        if mission_name == "media_directory_research":
            region = params.get("region", "the specified region")
            focus = params.get("focus", "")
            msg = f"Research and catalog media organizations in {region}."
            if focus:
                msg += f" Focus on: {focus}."
            msg += (
                " For each organization, first search existing records to check for duplicates, "
                "then create a record if it doesn't exist. Aim for the major established outlets."
            )
            return msg

        elif mission_name == "tool_discovery":
            category = params.get("category", "the specified category")
            focus = params.get("focus", "")
            msg = f"Discover AI tools relevant to journalism in the '{category}' category."
            if focus:
                msg += f" Focus on: {focus}."
            msg += (
                " For each tool, first search existing records to check for duplicates, "
                "then create a record if it doesn't exist. Include accurate URLs and descriptions."
            )
            return msg

        return f"Execute mission: {mission_name} with parameters: {params}"

    async def _execute_client_tool(
        self,
        tool_name: str,
        tool_input: dict,
        run_id: str,
        result: AgentResult,
    ) -> str:
        """Execute a client-side tool and return the result string."""
        handler = TOOL_HANDLERS.get(tool_name)
        if not handler:
            return f"Error: unknown tool '{tool_name}'."

        try:
            # Tools that create records need run_id
            if tool_name in ("create_media_organization", "create_discovered_tool"):
                output = await handler(self.db, tool_input, run_id)
                # Track created records
                if output.startswith("Created"):
                    result.created_records.append({
                        "tool": tool_name,
                        "name": tool_input.get("name", ""),
                        "output": output,
                    })
            else:
                output = await handler(self.db, tool_input)

            return output

        except Exception as e:
            logger.error(f"Tool {tool_name} error: {e}")
            return f"Error executing {tool_name}: {e}"
