"""
GROUNDED Adapter - Integration layer between app and GROUNDED infrastructure.

Provides initialization, compatibility wrappers, and helpers for
gradually migrating the app to use GROUNDED infrastructure.
"""

import logging
from typing import Any, Dict, Optional

from grounded import __version__ as grounded_version
from grounded.ai import register_default_providers, get_embedding_provider
from grounded.core.config import get_settings as get_grounded_settings
from grounded.core.base import ComponentStatus, HealthCheckResult
from grounded.governance.audit.logger import get_audit_logger, AuditEvent, AuditEventType

logger = logging.getLogger(__name__)

# Track initialization state
_grounded_initialized = False


def initialize_grounded() -> bool:
    """
    Initialize the GROUNDED infrastructure layer.

    Call this during application startup to set up GROUNDED components
    including AI providers, governance policies, and audit logging.

    Returns:
        True if initialization successful
    """
    global _grounded_initialized

    if _grounded_initialized:
        logger.debug("GROUNDED already initialized, skipping")
        return True

    try:
        settings = get_grounded_settings()
        logger.info(f"Initializing GROUNDED infrastructure v{grounded_version}")
        logger.info(f"GROUNDED environment: {settings.env}")

        # Register default AI providers
        register_default_providers()
        logger.info("GROUNDED AI providers registered")

        # Initialize audit logging
        audit_logger = get_audit_logger()
        audit_logger.log_event(
            AuditEvent(
                event_type=AuditEventType.SYSTEM_STARTUP,
                action="grounded_initialize",
                resource="grounded_infrastructure",
                details={
                    "version": grounded_version,
                    "env": settings.env,
                    "debug": settings.debug,
                },
            )
        )

        _grounded_initialized = True
        logger.info("GROUNDED infrastructure initialized successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize GROUNDED: {e}")
        # Don't fail app startup, just log the error
        # GROUNDED features will be gracefully degraded
        return False


def shutdown_grounded() -> None:
    """
    Shutdown the GROUNDED infrastructure layer.

    Call this during application shutdown to clean up GROUNDED resources.
    """
    global _grounded_initialized

    if not _grounded_initialized:
        return

    try:
        logger.info("Shutting down GROUNDED infrastructure")

        # Log shutdown event
        audit_logger = get_audit_logger()
        audit_logger.log_event(
            AuditEvent(
                event_type=AuditEventType.SYSTEM_SHUTDOWN,
                action="grounded_shutdown",
                resource="grounded_infrastructure",
            )
        )

        _grounded_initialized = False
        logger.info("GROUNDED infrastructure shutdown complete")

    except Exception as e:
        logger.error(f"Error during GROUNDED shutdown: {e}")


def is_grounded_initialized() -> bool:
    """Check if GROUNDED is initialized."""
    return _grounded_initialized


def get_grounded_health() -> Dict[str, Any]:
    """
    Get GROUNDED infrastructure health status.

    Returns:
        Dictionary with health information for inclusion in health endpoints
    """
    if not _grounded_initialized:
        return {
            "grounded": {
                "status": "not_initialized",
                "version": grounded_version,
            }
        }

    try:
        settings = get_grounded_settings()

        # Check embedding provider
        provider_status = "healthy"
        provider_name = "unknown"
        try:
            provider = get_embedding_provider()
            provider_name = provider.name
        except Exception as e:
            provider_status = f"error: {e}"

        return {
            "grounded": {
                "status": "healthy",
                "version": grounded_version,
                "env": settings.env,
                "components": {
                    "embedding_provider": {
                        "status": provider_status,
                        "provider": provider_name,
                    },
                    "audit_logging": {
                        "status": "healthy" if settings.audit_log_enabled else "disabled",
                    },
                    "policy_engine": {
                        "status": "healthy",
                        "mode": settings.policy_enforcement_mode,
                    },
                },
            }
        }

    except Exception as e:
        return {
            "grounded": {
                "status": "error",
                "error": str(e),
                "version": grounded_version,
            }
        }


# Compatibility wrappers for gradual migration
# These allow existing code to use GROUNDED features without major refactoring


def create_embedding_compat(text: str) -> Optional[list[float]]:
    """
    Compatibility wrapper for creating embeddings via GROUNDED.

    Falls back gracefully if GROUNDED is not available.

    Args:
        text: Text to create embedding for

    Returns:
        Embedding vector or None if not available
    """
    if not _grounded_initialized:
        logger.warning("GROUNDED not initialized, embedding not available")
        return None

    try:
        provider = get_embedding_provider()
        return provider.create_embedding(text)
    except Exception as e:
        logger.error(f"Failed to create embedding via GROUNDED: {e}")
        return None


def log_audit_event_compat(
    action: str,
    actor: str = "system",
    resource: str = "",
    outcome: str = "success",
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Compatibility wrapper for audit logging via GROUNDED.

    Silently skips if GROUNDED is not available.

    Args:
        action: Action being logged
        actor: Who performed the action
        resource: What resource was affected
        outcome: Result of the action
        details: Additional context
    """
    if not _grounded_initialized:
        return

    try:
        audit_logger = get_audit_logger()
        audit_logger.log_action(
            action=action,
            actor=actor,
            resource=resource,
            outcome=outcome,
            details=details,
        )
    except Exception as e:
        logger.debug(f"Failed to log audit event: {e}")
