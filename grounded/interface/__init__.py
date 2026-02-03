"""
GROUNDED Interface - Structured interface layer for civic tool integration.

Provides a controlled, unified interface for external civic tools to access
GROUNDED's AI processing, knowledge systems, document handling, and governance
capabilities.

This module is designed with future partners in mind, providing:
- Clean request/response models for all operations
- Capability-based access control with rate limiting
- Both direct Python integration and HTTP API support
- Usage tracking and governance compliance

Usage (Direct Integration):
    from grounded.interface import GroundedClient

    # Create and initialize client
    client = GroundedClient.create_direct("my-civic-tool")
    await client.initialize()

    # Use GROUNDED capabilities
    embedding = client.create_embedding("Hello world")

    # Create knowledge base
    base_id = client.create_knowledge_base("My Knowledge")
    client.add_knowledge(base_id, "docs", "Content here...", title="Doc 1")

    # Search and get answers
    results = client.search_knowledge(base_id, "query")
    answer = client.get_answer(base_id, "What is...?")

Usage (HTTP API - for future distributed use):
    from grounded.interface import GroundedClient

    client = GroundedClient.create_http(
        base_url="https://api.grounded.example.com",
        client_id="my-civic-tool",
        api_key="sk-xxx"
    )

    async with client:
        embedding = await client.create_embedding_async("Hello")

Service Usage (for app integration):
    from grounded.interface import get_interface, GroundedInterface

    interface = get_interface()
    await interface.initialize()

    # Register a partner
    interface.register_client("partner-123", AccessLevel.PARTNER)
"""

# Models
from grounded.interface.models import (
    # Enums
    InterfaceVersion,
    CapabilityType,
    RequestStatus,
    # Base
    InterfaceRequest,
    InterfaceResponse,
    # AI Processing
    EmbeddingRequest,
    EmbeddingResponse,
    BatchEmbeddingRequest,
    BatchEmbeddingResponse,
    # Knowledge
    CreateKnowledgeBaseRequest,
    CreateKnowledgeBaseResponse,
    AddKnowledgeRequest,
    AddKnowledgeResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    SearchResultItem,
    KnowledgeAnswerRequest,
    KnowledgeAnswerResponse,
    CitationItem,
    # Documents
    ProcessDocumentRequest,
    ProcessDocumentResponse,
    ChunkInfo,
    # Governance
    GovernanceStatsRequest,
    GovernanceStatsResponse,
    # System
    HealthCheckRequest,
    HealthCheckResponse,
    ComponentHealth,
    CapabilityListRequest,
    CapabilityListResponse,
    CapabilityInfo,
)

# Capabilities
from grounded.interface.capabilities import (
    AccessLevel,
    CapabilityDefinition,
    CapabilityRegistry,
    get_capability_registry,
)

# Service
from grounded.interface.service import (
    GroundedInterface,
    get_interface,
)

# Client
from grounded.interface.client import (
    GroundedClient,
    GroundedClientError,
    GroundedConnectionError,
    GroundedAuthError,
    GroundedRateLimitError,
)

__all__ = [
    # Enums
    "InterfaceVersion",
    "CapabilityType",
    "RequestStatus",
    "AccessLevel",
    # Base models
    "InterfaceRequest",
    "InterfaceResponse",
    # AI Processing models
    "EmbeddingRequest",
    "EmbeddingResponse",
    "BatchEmbeddingRequest",
    "BatchEmbeddingResponse",
    # Knowledge models
    "CreateKnowledgeBaseRequest",
    "CreateKnowledgeBaseResponse",
    "AddKnowledgeRequest",
    "AddKnowledgeResponse",
    "KnowledgeSearchRequest",
    "KnowledgeSearchResponse",
    "SearchResultItem",
    "KnowledgeAnswerRequest",
    "KnowledgeAnswerResponse",
    "CitationItem",
    # Document models
    "ProcessDocumentRequest",
    "ProcessDocumentResponse",
    "ChunkInfo",
    # Governance models
    "GovernanceStatsRequest",
    "GovernanceStatsResponse",
    # System models
    "HealthCheckRequest",
    "HealthCheckResponse",
    "ComponentHealth",
    "CapabilityListRequest",
    "CapabilityListResponse",
    "CapabilityInfo",
    # Capabilities
    "CapabilityDefinition",
    "CapabilityRegistry",
    "get_capability_registry",
    # Service
    "GroundedInterface",
    "get_interface",
    # Client
    "GroundedClient",
    "GroundedClientError",
    "GroundedConnectionError",
    "GroundedAuthError",
    "GroundedRateLimitError",
]
