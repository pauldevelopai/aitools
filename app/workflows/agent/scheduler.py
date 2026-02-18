"""Autonomous agent scheduler.

Manages a background loop that rotates through a configurable list of
missions, running them one at a time with delays between each.  All state
is in-memory; individual runs are persisted as WorkflowRun records.
"""
import asyncio
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any

from app.db import SessionLocal
from app.workflows.agent.engine import AgentEngine
from app.workflows.agent.quality_judge import judge_mission_results
from app.workflows.rate_limit import check_workflow_rate_limit
from app.workflows.runtime import WorkflowRuntime

logger = logging.getLogger(__name__)

DEFAULT_SCHEDULE: list[dict[str, Any]] = [
    {"mission": "media_directory_research", "params": {"region": "Ireland", "focus": "digital-native outlets"}},
    {"mission": "tool_discovery", "params": {"category": "fact-checking", "focus": ""}},
    {"mission": "use_case_research", "params": {"topic": "automated reporting", "region": "Europe"}},
    {"mission": "legal_framework_research", "params": {"jurisdiction": "eu", "focus": "AI Act implications"}},
    {"mission": "ethics_policy_research", "params": {"focus": "major news agencies", "region": "Global"}},
    {"mission": "media_directory_research", "params": {"region": "United Kingdom", "focus": "national newspapers"}},
    {"mission": "tool_discovery", "params": {"category": "transcription", "focus": ""}},
    {"mission": "use_case_research", "params": {"topic": "AI fact-checking", "region": ""}},
    {"mission": "legal_framework_research", "params": {"jurisdiction": "uk", "focus": "Online Safety Act"}},
    {"mission": "ethics_policy_research", "params": {"focus": "European broadcasters", "region": "Europe"}},
    {"mission": "media_directory_research", "params": {"region": "United States", "focus": "major newspapers"}},
    {"mission": "tool_discovery", "params": {"category": "content-generation", "focus": "journalism-specific"}},
    {"mission": "use_case_research", "params": {"topic": "audience analytics", "region": "North America"}},
    {"mission": "legal_framework_research", "params": {"jurisdiction": "us_federal", "focus": ""}},
    {"mission": "ethics_policy_research", "params": {"focus": "generative AI policies", "region": ""}},
]


class AgentScheduler:
    """Singleton scheduler that autonomously runs agent missions."""

    def __init__(self) -> None:
        self.state: str = "stopped"  # running | paused | stopped
        self.current_run_id: str | None = None
        self.current_mission: str | None = None
        self.schedule: list[dict[str, Any]] = list(DEFAULT_SCHEDULE)
        self.schedule_index: int = 0
        self.delay_between_missions: int = 120  # seconds
        self.stats: dict[str, Any] = {
            "missions_completed_today": 0,
            "records_created_today": 0,
            "records_rejected_today": 0,
            "started_at": None,
            "errors_today": 0,
        }
        self.activity_log: deque[dict[str, Any]] = deque(maxlen=100)
        self._task: asyncio.Task | None = None
        self._current_mission_start: datetime | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self) -> None:
        if self.state == "running":
            return
        self.state = "running"
        self._reset_daily_stats()
        self._log("Scheduler started", "info")
        self._task = asyncio.create_task(self._run_loop())

    def stop(self) -> None:
        if self.state == "stopped":
            return
        self.state = "stopped"
        self._log("Scheduler stopping (will finish current mission)", "info")

    def pause(self) -> None:
        if self.state == "running":
            self.state = "paused"
            self._log("Scheduler paused", "info")

    def resume(self) -> None:
        if self.state == "paused":
            self.state = "running"
            self._log("Scheduler resumed", "info")

    def update_schedule(self, new_schedule: list[dict[str, Any]], delay: int | None = None) -> None:
        self.schedule = new_schedule
        if delay is not None:
            self.delay_between_missions = delay
        self.schedule_index = 0
        self._log(f"Schedule updated ({len(new_schedule)} missions, delay={self.delay_between_missions}s)", "info")

    def get_status(self) -> dict[str, Any]:
        elapsed = None
        if self._current_mission_start and self.current_run_id:
            elapsed = int((datetime.now(timezone.utc) - self._current_mission_start).total_seconds())
        next_mission = None
        if self.schedule:
            next_idx = (self.schedule_index + 1) % len(self.schedule) if self.current_run_id else self.schedule_index
            if self.state != "stopped":
                next_mission = self.schedule[next_idx % len(self.schedule)]
        return {
            "state": self.state,
            "current_run_id": self.current_run_id,
            "current_mission": self.current_mission,
            "current_elapsed_seconds": elapsed,
            "schedule_index": self.schedule_index,
            "schedule_total": len(self.schedule),
            "delay_between_missions": self.delay_between_missions,
            "stats": dict(self.stats),
            "next_mission": next_mission,
            "schedule": self.schedule,
        }

    def get_activity(self) -> list[dict[str, Any]]:
        return list(self.activity_log)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _reset_daily_stats(self) -> None:
        self.stats = {
            "missions_completed_today": 0,
            "records_created_today": 0,
            "records_rejected_today": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "errors_today": 0,
        }
        self._stats_date = datetime.now(timezone.utc).date()

    def _check_day_rollover(self) -> None:
        today = datetime.now(timezone.utc).date()
        if hasattr(self, "_stats_date") and self._stats_date != today:
            self._log("New day detected, resetting daily stats")
            self._reset_daily_stats()

    def _log(self, message: str, level: str = "info") -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": message,
            "level": level,
        }
        self.activity_log.appendleft(entry)
        getattr(logger, level, logger.info)(f"[Scheduler] {message}")

    async def _run_loop(self) -> None:
        try:
            while self.state != "stopped":
                self._check_day_rollover()

                if self.state == "paused":
                    await asyncio.sleep(2)
                    continue

                if not self.schedule:
                    self._log("No missions in schedule, stopping", "warning")
                    self.state = "stopped"
                    break

                mission_entry = self.schedule[self.schedule_index % len(self.schedule)]
                mission_name = mission_entry["mission"]
                params = mission_entry.get("params", {})

                self._log(f"Starting mission: {mission_name} ({_summarise_params(params)})")
                self.current_mission = mission_name

                try:
                    await self._run_single_mission(mission_name, params)
                except Exception as e:
                    self._log(f"Mission error: {e}", "error")
                    self.stats["errors_today"] += 1

                self.current_run_id = None
                self.current_mission = None
                self._current_mission_start = None

                # Advance schedule
                self.schedule_index = (self.schedule_index + 1) % len(self.schedule)

                if self.state == "stopped":
                    break

                # Delay between missions
                self._log(f"Waiting {self.delay_between_missions}s before next mission...")
                for _ in range(self.delay_between_missions):
                    if self.state == "stopped":
                        break
                    await asyncio.sleep(1)

        except asyncio.CancelledError:
            self._log("Scheduler task cancelled", "warning")
        except Exception as e:
            self._log(f"Scheduler loop crashed: {e}", "error")
            self.state = "stopped"

    async def _run_single_mission(self, mission_name: str, params: dict) -> None:
        db = SessionLocal()
        try:
            # Rate limit check (use the auto profile)
            allowed, retry_after, reason = check_workflow_rate_limit(
                "agent_mission_auto", "scheduler"
            )
            if not allowed:
                self._log(f"Rate limited ({reason}), waiting {retry_after}s", "warning")
                await asyncio.sleep(retry_after)

            # Create workflow run
            runtime = WorkflowRuntime(db)
            run = runtime.create_run(
                workflow_name="agent_mission",
                inputs={"mission": mission_name, "params": params},
                triggered_by=None,
                tags=["agent", "scheduler", mission_name],
            )
            self.current_run_id = str(run.id)
            self._current_mission_start = datetime.now(timezone.utc)

            runtime.update_status(run, status="running")

            engine = AgentEngine(db)
            result = await engine.run(mission_name, params, str(run.id))

            # Quality judging
            quality_report = None
            if result.created_records:
                try:
                    quality_report = await judge_mission_results(
                        db, str(run.id), result.created_records
                    )
                    self._log(
                        f"Quality: {quality_report['high_quality']} high, "
                        f"{quality_report['medium_quality']} med, "
                        f"{quality_report['low_quality']} low, "
                        f"{quality_report['auto_rejected']} rejected"
                    )
                    self.stats["records_rejected_today"] += quality_report["auto_rejected"]
                except Exception as e:
                    self._log(f"Quality judging error: {e}", "error")

            if result.error:
                runtime.update_status(
                    run,
                    status="failed",
                    error_message=result.error,
                    outputs={
                        "created_records": result.created_records,
                        "steps_taken": result.steps_taken,
                        "quality_report": quality_report,
                    },
                )
                self._log(f"Mission failed: {result.error}", "error")
                self.stats["errors_today"] += 1
            else:
                status = "needs_review" if result.created_records else "completed"
                outputs: dict[str, Any] = {
                    "created_records": result.created_records,
                    "research_notes": result.research_notes[:5000],
                    "steps_taken": result.steps_taken,
                }
                if quality_report:
                    outputs["quality_report"] = quality_report
                runtime.update_status(
                    run,
                    status=status,
                    outputs=outputs,
                    review_required="Approve agent-created records" if result.created_records else None,
                )
                record_count = len(result.created_records)
                self.stats["missions_completed_today"] += 1
                self.stats["records_created_today"] += record_count
                self._log(
                    f"Completed {mission_name} -- "
                    f"{record_count} record(s) created, {result.steps_taken} steps"
                )

        finally:
            db.close()


def _summarise_params(params: dict) -> str:
    parts = []
    for key in ("region", "category", "topic", "jurisdiction", "focus"):
        val = params.get(key)
        if val:
            parts.append(val)
    return ", ".join(parts) or "default"


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_scheduler: AgentScheduler | None = None


def get_scheduler() -> AgentScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AgentScheduler()
    return _scheduler
