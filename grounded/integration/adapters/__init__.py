"""
GROUNDED Integration Adapters - Framework-specific adapters.

Contains adapters for integrating GROUNDED with various web
frameworks and external services.
"""

from grounded.integration.adapters.fastapi import (
    audit_endpoint,
    get_grounded_settings,
    get_audit_logger_dep,
    require_policy,
)

__all__ = [
    "audit_endpoint",
    "get_grounded_settings",
    "get_audit_logger_dep",
    "require_policy",
]
