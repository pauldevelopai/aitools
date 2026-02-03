"""
GROUNDED Governance Audit Logger - Audit event logging.

Provides structured audit logging for tracking actions, policy
evaluations, and significant events across the GROUNDED infrastructure.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from grounded.core.base import GroundedComponent
from grounded.core.config import get_settings


class AuditEventType(Enum):
    """Types of audit events."""

    # Access events
    ACCESS = "access"
    ACCESS_DENIED = "access_denied"

    # Action events
    ACTION = "action"
    ACTION_STARTED = "action_started"
    ACTION_COMPLETED = "action_completed"
    ACTION_FAILED = "action_failed"

    # Policy events
    POLICY_EVALUATED = "policy_evaluated"
    POLICY_VIOLATION = "policy_violation"

    # System events
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    COMPONENT_INITIALIZED = "component_initialized"

    # Data events
    DATA_READ = "data_read"
    DATA_WRITE = "data_write"
    DATA_DELETE = "data_delete"

    # Integration events
    INTEGRATION_CALL = "integration_call"
    INTEGRATION_ERROR = "integration_error"


@dataclass
class AuditEvent:
    """
    A structured audit event.

    Captures all relevant information about an auditable action
    in the GROUNDED infrastructure.
    """

    event_type: AuditEventType
    action: str
    actor: str = "system"
    resource: str = ""
    outcome: str = "success"
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "event_type": self.event_type.value,
            "action": self.action,
            "actor": self.actor,
            "resource": self.resource,
            "outcome": self.outcome,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


# Type for audit event handlers
AuditHandler = Callable[[AuditEvent], None]


class AuditLogger(GroundedComponent):
    """
    Centralized audit logger for GROUNDED infrastructure.

    Provides structured audit logging with multiple output handlers,
    correlation tracking, and configurable filtering.

    Example:
        logger = AuditLogger()
        logger.log_event(AuditEvent(
            event_type=AuditEventType.ACTION,
            action="create_embedding",
            actor="user@example.com",
            resource="embedding_provider",
            details={"text_length": 100}
        ))
    """

    def __init__(
        self,
        name: str = "grounded_audit",
        enabled: Optional[bool] = None,
    ):
        """
        Initialize the audit logger.

        Args:
            name: Logger name for Python logging integration
            enabled: Override settings for audit logging enabled
        """
        self._name = name
        self._settings = get_settings()
        self._enabled = enabled if enabled is not None else self._settings.audit_log_enabled
        self._handlers: List[AuditHandler] = []
        self._logger = logging.getLogger(name)

        # Set up default console handler
        self._setup_default_handler()

    def _setup_default_handler(self) -> None:
        """Set up the default logging handler."""
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [AUDIT] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)

    @property
    def name(self) -> str:
        return self._name

    @property
    def enabled(self) -> bool:
        """Check if audit logging is enabled."""
        return self._enabled

    def enable(self) -> None:
        """Enable audit logging."""
        self._enabled = True

    def disable(self) -> None:
        """Disable audit logging."""
        self._enabled = False

    def add_handler(self, handler: AuditHandler) -> None:
        """
        Add a custom audit event handler.

        Handlers are called for each audit event after the default
        Python logging handler.

        Args:
            handler: Callable that receives AuditEvent
        """
        self._handlers.append(handler)

    def remove_handler(self, handler: AuditHandler) -> bool:
        """
        Remove a custom audit event handler.

        Args:
            handler: The handler to remove

        Returns:
            True if handler was found and removed
        """
        try:
            self._handlers.remove(handler)
            return True
        except ValueError:
            return False

    def log_event(self, event: AuditEvent) -> None:
        """
        Log an audit event.

        Args:
            event: The audit event to log
        """
        if not self._enabled:
            return

        # Log to Python logging
        log_message = (
            f"{event.event_type.value} | "
            f"action={event.action} | "
            f"actor={event.actor} | "
            f"resource={event.resource} | "
            f"outcome={event.outcome}"
        )
        if event.correlation_id:
            log_message += f" | correlation_id={event.correlation_id}"

        self._logger.info(log_message)

        # Call custom handlers
        for handler in self._handlers:
            try:
                handler(event)
            except Exception as e:
                self._logger.error(f"Audit handler error: {e}")

    def log_action(
        self,
        action: str,
        actor: str = "system",
        resource: str = "",
        outcome: str = "success",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        """
        Convenience method to log an action event.

        Args:
            action: The action being performed
            actor: Who performed the action
            resource: What resource was affected
            outcome: Result of the action
            details: Additional context
            correlation_id: Optional correlation ID
        """
        event = AuditEvent(
            event_type=AuditEventType.ACTION,
            action=action,
            actor=actor,
            resource=resource,
            outcome=outcome,
            details=details or {},
            correlation_id=correlation_id,
        )
        self.log_event(event)

    def log_access(
        self,
        resource: str,
        actor: str,
        granted: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Convenience method to log an access event.

        Args:
            resource: The resource being accessed
            actor: Who is accessing
            granted: Whether access was granted
            details: Additional context
        """
        event = AuditEvent(
            event_type=AuditEventType.ACCESS if granted else AuditEventType.ACCESS_DENIED,
            action="access",
            actor=actor,
            resource=resource,
            outcome="granted" if granted else "denied",
            details=details or {},
        )
        self.log_event(event)

    def log_policy_evaluation(
        self,
        policy_name: str,
        action: str,
        decision: str,
        actor: str = "system",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log a policy evaluation event.

        Args:
            policy_name: Name of the policy
            action: Action being evaluated
            decision: Policy decision (allow/deny/warn)
            actor: Who triggered the evaluation
            details: Additional context
        """
        event_type = (
            AuditEventType.POLICY_VIOLATION
            if decision == "deny"
            else AuditEventType.POLICY_EVALUATED
        )
        event = AuditEvent(
            event_type=event_type,
            action=action,
            actor=actor,
            resource=policy_name,
            outcome=decision,
            details=details or {},
        )
        self.log_event(event)


# Global audit logger instance
_global_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """
    Get the global audit logger instance.

    Returns:
        AuditLogger instance (creates one if needed)
    """
    global _global_audit_logger
    if _global_audit_logger is None:
        _global_audit_logger = AuditLogger()
    return _global_audit_logger


def set_audit_logger(logger: AuditLogger) -> None:
    """
    Set the global audit logger instance.

    Args:
        logger: The audit logger to use globally
    """
    global _global_audit_logger
    _global_audit_logger = logger
