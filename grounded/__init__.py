"""
GROUNDED - Civic AI Infrastructure Layer.

A foundational infrastructure layer providing shared services for civic AI applications.
This platform layer offers AI providers, governance policies, partner integrations,
document intelligence, knowledge management, and trust frameworks that can be consumed
by applications.

Usage:
    from grounded import __version__
    from grounded.ai import get_embedding_provider
    from grounded.governance import PolicyEngine
    from grounded.documents import DocumentProcessor, Document
    from grounded.knowledge import KnowledgeService
"""

__version__ = "0.1.0"
__author__ = "Grounded Team"

from grounded.core.base import GroundedComponent, Registry, ComponentStatus, HealthCheckResult
from grounded.core.config import GroundedSettings
from grounded.core.exceptions import (
    GroundedException,
    ProviderNotFoundError,
    PolicyViolationError,
    ConfigurationError,
)

__all__ = [
    "__version__",
    "__author__",
    # Core
    "GroundedComponent",
    "Registry",
    "ComponentStatus",
    "HealthCheckResult",
    "GroundedSettings",
    # Exceptions
    "GroundedException",
    "ProviderNotFoundError",
    "PolicyViolationError",
    "ConfigurationError",
]
