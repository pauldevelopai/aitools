"""Core agentic loop for the AI agent.

Uses the OpenAI Agents SDK with function tools
and web search in an autonomous research loop.
"""
import logging
import os
from dataclasses import dataclass, field

from sqlalchemy.orm import Session
from agents import Agent, Runner, WebSearchTool

from app.settings import settings

# Ensure the Agents SDK can find the API key from the environment
if settings.OPENAI_API_KEY and "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
from app.workflows.agent.missions import MISSIONS
from app.workflows.agent.tools import ALL_TOOLS, AgentContext

logger = logging.getLogger(__name__)

# Safety limits
MAX_TURNS = 25


@dataclass
class AgentResult:
    """Result from an agent run."""
    created_records: list[dict] = field(default_factory=list)
    research_notes: str = ""
    steps_taken: int = 0
    error: str | None = None


class AgentEngine:
    """Runs an OpenAI Agents SDK-powered research loop."""

    def __init__(self, db: Session):
        self.db = db

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

        # Build tool list from mission config + web search
        tools = [ALL_TOOLS[name] for name in mission["allowed_tools"] if name in ALL_TOOLS]
        tools.append(WebSearchTool())

        # Build user message
        user_message = self._build_user_message(mission_name, params)

        # Create context for tools (db session + run tracking)
        context = AgentContext(db=self.db, run_id=run_id)

        # Create the agent
        agent = Agent(
            name="Grounded Research Agent",
            instructions=system_prompt,
            model=settings.OPENAI_CHAT_MODEL,
            tools=tools,
        )

        result = AgentResult()

        try:
            run_result = await Runner.run(
                starting_agent=agent,
                input=user_message,
                context=context,
                max_turns=MAX_TURNS,
            )

            result.research_notes = run_result.final_output or ""
            result.created_records = context.created_records
            result.steps_taken = context.steps_taken

        except Exception as e:
            result.error = f"Agent error: {e}"
            result.created_records = context.created_records
            result.steps_taken = context.steps_taken
            logger.exception(f"Agent error for run {run_id}")

        return result

    def _build_user_message(self, mission_name: str, params: dict) -> str:
        """Build the initial user message based on mission and params."""
        if mission_name == "media_directory_research":
            region = params.get("region", "the specified region")
            focus = params.get("focus", "")
            msg = f"Research and catalog media organizations in {region}."
            if focus:
                msg += f" Focus on: {focus}."
            msg += (
                " Use web search to find current information about media organizations."
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
                " Use web search to find current tools and verify their URLs."
                " For each tool, first search existing records to check for duplicates, "
                "then create a record if it doesn't exist. Include accurate URLs and descriptions."
            )
            return msg

        return f"Execute mission: {mission_name} with parameters: {params}"
