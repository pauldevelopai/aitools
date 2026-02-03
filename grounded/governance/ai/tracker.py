"""
GROUNDED AI Governance Tracker - Core tracking service for AI operations.

The AIGovernanceTracker is the central service for recording and querying
AI operation audit records. It maintains an audit trail of all AI usage
across the GROUNDED infrastructure.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Callable, Dict, List, Optional

from grounded.core.base import ComponentStatus, GroundedComponent, HealthCheckResult
from grounded.core.config import get_settings
from grounded.governance.ai.models import (
    AIAuditRecord,
    AIDataType,
    AIGovernanceStats,
    AIOperationContext,
    AIOperationStatus,
    AIOperationType,
)

logger = logging.getLogger(__name__)


class AIGovernanceTracker(GroundedComponent):
    """
    Central tracker for AI governance and audit.

    Records all AI operations across the GROUNDED infrastructure,
    providing a queryable audit trail for transparency and compliance.

    Features:
    - Automatic operation tracking with before/after hooks
    - In-memory audit storage (configurable backends in future)
    - Statistics and aggregation
    - Event callbacks for real-time monitoring

    Example:
        tracker = AIGovernanceTracker()

        # Start tracking an operation
        record = tracker.start_operation(
            operation_type=AIOperationType.EMBEDDING,
            source_component="DocumentProcessor",
            provider_name="openai"
        )

        # Complete it when done
        tracker.complete_operation(record.record_id, output_size=1536)

        # Query the audit trail
        records = tracker.get_records(
            operation_type=AIOperationType.EMBEDDING,
            limit=100
        )
    """

    def __init__(
        self,
        max_records: int = 10000,
        enable_logging: bool = True,
    ):
        """
        Initialize the governance tracker.

        Args:
            max_records: Maximum records to keep in memory (FIFO eviction)
            enable_logging: Whether to log operations to Python logging
        """
        self._max_records = max_records
        self._enable_logging = enable_logging

        # Storage
        self._records: List[AIAuditRecord] = []
        self._records_by_id: Dict[str, AIAuditRecord] = {}
        self._lock = Lock()

        # Callbacks for real-time monitoring
        self._on_operation_start: List[Callable[[AIAuditRecord], None]] = []
        self._on_operation_complete: List[Callable[[AIAuditRecord], None]] = []

        # Settings
        self._settings = get_settings()
        self._enabled = True

    @property
    def name(self) -> str:
        return "ai_governance_tracker"

    @property
    def enabled(self) -> bool:
        """Check if tracking is enabled."""
        return self._enabled

    def enable(self) -> None:
        """Enable tracking."""
        self._enabled = True
        logger.info("AI governance tracking enabled")

    def disable(self) -> None:
        """Disable tracking."""
        self._enabled = False
        logger.info("AI governance tracking disabled")

    async def health_check(self) -> HealthCheckResult:
        """Check tracker health."""
        return HealthCheckResult(
            status=ComponentStatus.HEALTHY,
            component_name=self.name,
            message="AI governance tracker operational",
            details={
                "enabled": self._enabled,
                "records_count": len(self._records),
                "max_records": self._max_records,
            },
        )

    # =========================================================================
    # Operation Tracking
    # =========================================================================

    def start_operation(
        self,
        operation_type: AIOperationType,
        source_module: str = "",
        source_function: str = "",
        source_component: str = "",
        provider_name: str = "",
        model_name: str = "",
        input_data_type: AIDataType = AIDataType.UNKNOWN,
        input_size: int = 0,
        input_count: int = 1,
        actor_type: str = "system",
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        parent_operation_id: Optional[str] = None,
        tokens_input: int = 0,
        **metadata: Any,
    ) -> AIAuditRecord:
        """
        Start tracking a new AI operation.

        Args:
            operation_type: Type of AI operation
            source_module: Module that triggered the operation
            source_function: Function that triggered the operation
            source_component: Component name (e.g., "DocumentProcessor")
            provider_name: AI provider being used
            model_name: Model being used
            input_data_type: Type of input data
            input_size: Size of input data
            input_count: Number of input items
            actor_type: Who triggered it (system, user, api)
            actor_id: ID of the actor
            correlation_id: For tracking related operations
            parent_operation_id: Parent operation if nested
            tokens_input: Input token count (if known)
            **metadata: Additional metadata

        Returns:
            AIAuditRecord for tracking completion
        """
        if not self._enabled:
            # Return a minimal record that won't be stored
            return AIAuditRecord(
                context=AIOperationContext(operation_type=operation_type),
                status=AIOperationStatus.IN_PROGRESS,
            )

        context = AIOperationContext(
            operation_type=operation_type,
            source_module=source_module,
            source_function=source_function,
            source_component=source_component,
            provider_name=provider_name,
            model_name=model_name,
            input_data_type=input_data_type,
            input_size=input_size,
            input_count=input_count,
            actor_type=actor_type,
            actor_id=actor_id,
            correlation_id=correlation_id,
            parent_operation_id=parent_operation_id,
            metadata=metadata,
        )

        record = AIAuditRecord(
            context=context,
            status=AIOperationStatus.IN_PROGRESS,
            tokens_input=tokens_input,
        )

        with self._lock:
            self._records.append(record)
            self._records_by_id[record.record_id] = record
            self._evict_if_needed()

        # Notify callbacks
        for callback in self._on_operation_start:
            try:
                callback(record)
            except Exception as e:
                logger.warning(f"Operation start callback error: {e}")

        if self._enable_logging:
            logger.debug(
                f"AI operation started: {operation_type.value} "
                f"provider={provider_name} source={source_component or source_module}"
            )

        return record

    def complete_operation(
        self,
        record_id: str,
        output_size: int = 0,
        output_count: int = 0,
        output_data_type: AIDataType = AIDataType.UNKNOWN,
        tokens_output: int = 0,
        estimated_cost_usd: float = 0.0,
        **result_metadata: Any,
    ) -> Optional[AIAuditRecord]:
        """
        Mark an operation as completed successfully.

        Args:
            record_id: ID of the operation to complete
            output_size: Size of output data
            output_count: Number of output items
            output_data_type: Type of output data
            tokens_output: Output token count
            estimated_cost_usd: Estimated cost in USD
            **result_metadata: Additional result metadata

        Returns:
            Updated AIAuditRecord or None if not found
        """
        if not self._enabled:
            return None

        with self._lock:
            record = self._records_by_id.get(record_id)
            if not record:
                return None

            record.complete(
                output_size=output_size,
                output_count=output_count,
                tokens_output=tokens_output,
                **result_metadata,
            )
            record.output_data_type = output_data_type
            record.estimated_cost_usd = estimated_cost_usd

        # Notify callbacks
        for callback in self._on_operation_complete:
            try:
                callback(record)
            except Exception as e:
                logger.warning(f"Operation complete callback error: {e}")

        if self._enable_logging:
            logger.info(record.to_log_string())

        return record

    def fail_operation(
        self,
        record_id: str,
        error_message: str,
        error_type: Optional[str] = None,
    ) -> Optional[AIAuditRecord]:
        """
        Mark an operation as failed.

        Args:
            record_id: ID of the operation
            error_message: Error message
            error_type: Type of error

        Returns:
            Updated AIAuditRecord or None if not found
        """
        if not self._enabled:
            return None

        with self._lock:
            record = self._records_by_id.get(record_id)
            if not record:
                return None

            record.fail(error_message, error_type)

        # Notify callbacks
        for callback in self._on_operation_complete:
            try:
                callback(record)
            except Exception as e:
                logger.warning(f"Operation complete callback error: {e}")

        if self._enable_logging:
            logger.warning(
                f"AI operation failed: {record.operation_type.value} "
                f"error={error_message}"
            )

        return record

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_record(self, record_id: str) -> Optional[AIAuditRecord]:
        """Get a specific audit record by ID."""
        with self._lock:
            return self._records_by_id.get(record_id)

    def get_records(
        self,
        operation_type: Optional[AIOperationType] = None,
        provider_name: Optional[str] = None,
        source_component: Optional[str] = None,
        status: Optional[AIOperationStatus] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AIAuditRecord]:
        """
        Query audit records with filters.

        Args:
            operation_type: Filter by operation type
            provider_name: Filter by provider
            source_component: Filter by source component
            status: Filter by status
            since: Only records after this time
            until: Only records before this time
            actor_id: Filter by actor
            correlation_id: Filter by correlation ID
            limit: Maximum records to return
            offset: Skip first N records

        Returns:
            List of matching AIAuditRecord
        """
        with self._lock:
            results = []
            for record in reversed(self._records):  # Most recent first
                # Apply filters
                if operation_type and record.operation_type != operation_type:
                    continue
                if provider_name and record.context.provider_name != provider_name:
                    continue
                if source_component and record.context.source_component != source_component:
                    continue
                if status and record.status != status:
                    continue
                if since and record.started_at < since:
                    continue
                if until and record.started_at > until:
                    continue
                if actor_id and record.context.actor_id != actor_id:
                    continue
                if correlation_id and record.context.correlation_id != correlation_id:
                    continue

                results.append(record)

            # Apply pagination
            return results[offset : offset + limit]

    def get_recent_records(self, limit: int = 50) -> List[AIAuditRecord]:
        """Get the most recent audit records."""
        with self._lock:
            return list(reversed(self._records[-limit:]))

    def count_records(
        self,
        operation_type: Optional[AIOperationType] = None,
        since: Optional[datetime] = None,
    ) -> int:
        """Count records matching filters."""
        with self._lock:
            count = 0
            for record in self._records:
                if operation_type and record.operation_type != operation_type:
                    continue
                if since and record.started_at < since:
                    continue
                count += 1
            return count

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> AIGovernanceStats:
        """
        Get aggregated statistics for AI operations.

        Args:
            since: Start of period (default: all time)
            until: End of period (default: now)

        Returns:
            AIGovernanceStats with aggregated metrics
        """
        stats = AIGovernanceStats(
            period_start=since,
            period_end=until or datetime.utcnow(),
        )

        durations = []

        with self._lock:
            for record in self._records:
                # Apply time filter
                if since and record.started_at < since:
                    continue
                if until and record.started_at > until:
                    continue

                stats.total_operations += 1

                if record.is_success:
                    stats.successful_operations += 1
                elif record.status == AIOperationStatus.FAILED:
                    stats.failed_operations += 1

                # By type
                type_key = record.operation_type.value
                stats.operations_by_type[type_key] = (
                    stats.operations_by_type.get(type_key, 0) + 1
                )

                # By provider
                provider = record.context.provider_name or "unknown"
                stats.operations_by_provider[provider] = (
                    stats.operations_by_provider.get(provider, 0) + 1
                )

                # By source
                source = record.context.source_component or record.context.source_module or "unknown"
                stats.operations_by_source[source] = (
                    stats.operations_by_source.get(source, 0) + 1
                )

                # Timing
                if record.is_complete:
                    stats.total_duration_ms += record.duration_ms
                    durations.append(record.duration_ms)

                # Tokens
                stats.total_input_tokens += record.tokens_input
                stats.total_output_tokens += record.tokens_output
                stats.total_tokens += record.tokens_total

                # Cost
                stats.total_estimated_cost_usd += record.estimated_cost_usd

        # Calculate averages
        if durations:
            stats.avg_duration_ms = stats.total_duration_ms / len(durations)
            stats.min_duration_ms = min(durations)
            stats.max_duration_ms = max(durations)

        return stats

    def get_stats_by_hour(
        self,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """
        Get statistics broken down by hour.

        Args:
            hours: Number of hours to look back

        Returns:
            List of hourly stat dictionaries
        """
        now = datetime.utcnow()
        hourly_stats = []

        for h in range(hours):
            hour_start = now - timedelta(hours=h + 1)
            hour_end = now - timedelta(hours=h)

            stats = self.get_stats(since=hour_start, until=hour_end)
            hourly_stats.append({
                "hour": hour_start.strftime("%Y-%m-%d %H:00"),
                "operations": stats.total_operations,
                "successful": stats.successful_operations,
                "failed": stats.failed_operations,
                "avg_duration_ms": stats.avg_duration_ms,
                "total_tokens": stats.total_tokens,
            })

        return list(reversed(hourly_stats))

    # =========================================================================
    # Callbacks
    # =========================================================================

    def on_operation_start(self, callback: Callable[[AIAuditRecord], None]) -> None:
        """Register a callback for operation start events."""
        self._on_operation_start.append(callback)

    def on_operation_complete(self, callback: Callable[[AIAuditRecord], None]) -> None:
        """Register a callback for operation completion events."""
        self._on_operation_complete.append(callback)

    # =========================================================================
    # Maintenance
    # =========================================================================

    def clear(self) -> None:
        """Clear all audit records."""
        with self._lock:
            self._records.clear()
            self._records_by_id.clear()
        logger.info("AI governance audit records cleared")

    def _evict_if_needed(self) -> None:
        """Evict old records if over capacity (must be called with lock)."""
        while len(self._records) > self._max_records:
            old_record = self._records.pop(0)
            self._records_by_id.pop(old_record.record_id, None)


# Global tracker instance
_global_tracker: Optional[AIGovernanceTracker] = None


def get_governance_tracker() -> AIGovernanceTracker:
    """
    Get the global AI governance tracker instance.

    Returns:
        AIGovernanceTracker instance (creates one if needed)
    """
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = AIGovernanceTracker()
    return _global_tracker


def set_governance_tracker(tracker: AIGovernanceTracker) -> None:
    """
    Set the global AI governance tracker instance.

    Args:
        tracker: The tracker to use globally
    """
    global _global_tracker
    _global_tracker = tracker
