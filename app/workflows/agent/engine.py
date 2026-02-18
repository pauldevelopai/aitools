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
        if not settings.OPENAI_API_KEY:
            return AgentResult(error="OPENAI_API_KEY is not configured. Set it in .env to run agent missions.")

        mission = MISSIONS.get(mission_name)
        if not mission:
            return AgentResult(error=f"Unknown mission: {mission_name}")

        # Build system prompt with mission context + parameters
        system_prompt = mission["system_prompt"]
        for param_key in ("region", "category", "topic", "jurisdiction", "focus"):
            if params.get(param_key):
                label = param_key.replace("_", " ").title()
                system_prompt += f"\n{label}: {params[param_key]}"

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

        elif mission_name == "use_case_research":
            topic = params.get("topic", "AI in journalism")
            region = params.get("region", "")
            msg = f"Research real-world AI use cases in journalism related to '{topic}'."
            if region:
                msg += f" Focus on organizations in {region}."
            msg += (
                " Use web search to find documented case studies from sources like JournalismAI, "
                "Nieman Lab, Reuters Institute, and news org tech blogs."
                " For each use case, first search existing records (record_type='use_case') "
                "to check for duplicates, then create a record with the challenge, solution, and outcome."
            )
            return msg

        elif mission_name == "legal_framework_research":
            jurisdiction = params.get("jurisdiction", "the specified jurisdiction")
            focus = params.get("focus", "")
            msg = f"Research AI regulations and legal frameworks in the '{jurisdiction}' jurisdiction that are relevant to journalism and media organizations."
            if focus:
                msg += f" Focus on: {focus}."
            msg += (
                " Use web search to find current regulatory information."
                " For each regulation, first search existing records (record_type='content') "
                "to check for duplicates, then create a content item with a clear explanation "
                "of requirements and implications for newsrooms."
            )
            return msg

        elif mission_name == "ethics_policy_research":
            focus = params.get("focus", "AI ethics in journalism")
            region = params.get("region", "")
            msg = f"Research published AI ethics policies and guidelines related to '{focus}'."
            if region:
                msg += f" Focus on organizations in {region}."
            msg += (
                " Use web search to find current published policies from news organizations "
                "and journalism bodies."
                " For each policy, first search existing records (record_type='content') "
                "to check for duplicates, then create a content item documenting the key "
                "principles, allowed uses, and disclosure requirements."
            )
            return msg

        return f"Execute mission: {mission_name} with parameters: {params}"
