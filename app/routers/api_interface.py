"""
GROUNDED API Interface Router - HTTP API for external civic tool integration.

Exposes GROUNDED capabilities via a RESTful API for external tools and partners.
This is the HTTP gateway to the GROUNDED interface layer.

Endpoints:
- /api/v1/health - Health check
- /api/v1/capabilities - List available capabilities
- /api/v1/embeddings - Generate embeddings
- /api/v1/embeddings/batch - Batch embeddings
- /api/v1/knowledge/bases - Create knowledge bases
- /api/v1/knowledge/items - Add knowledge items
- /api/v1/knowledge/search - Search knowledge
- /api/v1/knowledge/answer - Get grounded answers
- /api/v1/documents/process - Process documents
- /api/v1/governance/stats - Get governance statistics
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from grounded.interface import (
    get_interface,
    GroundedInterface,
    CapabilityType,
    RequestStatus,
    AccessLevel,
    EmbeddingRequest,
    BatchEmbeddingRequest,
    CreateKnowledgeBaseRequest,
    AddKnowledgeRequest,
    KnowledgeSearchRequest,
    KnowledgeAnswerRequest,
    ProcessDocumentRequest,
    GovernanceStatsRequest,
    HealthCheckRequest,
    CapabilityListRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["interface", "api"])

# Track if interface is initialized
_interface_initialized = False


# =============================================================================
# PYDANTIC MODELS FOR API
# =============================================================================


class EmbeddingRequestModel(BaseModel):
    """Request model for embedding generation."""
    text: str = Field(..., min_length=1, max_length=8000)


class BatchEmbeddingRequestModel(BaseModel):
    """Request model for batch embedding generation."""
    texts: List[str] = Field(..., min_items=1, max_items=100)


class CreateKnowledgeBaseModel(BaseModel):
    """Request model for creating a knowledge base."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=1000)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AddKnowledgeModel(BaseModel):
    """Request model for adding knowledge."""
    base_id: str
    source_name: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    title: Optional[str] = Field(default=None, max_length=255)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    generate_embedding: bool = True


class SearchKnowledgeModel(BaseModel):
    """Request model for knowledge search."""
    base_id: str
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=10, ge=1, le=100)
    source_ids: Optional[List[str]] = None
    filters: Dict[str, Any] = Field(default_factory=dict)
    search_type: str = Field(default="hybrid", pattern="^(text|semantic|hybrid)$")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)


class AnswerRequestModel(BaseModel):
    """Request model for grounded answers."""
    base_id: str
    question: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=5, ge=1, le=20)
    source_ids: Optional[List[str]] = None
    context: Optional[str] = None


class ProcessDocumentModel(BaseModel):
    """Request model for document processing."""
    content: str = Field(..., min_length=1)
    title: Optional[str] = None
    document_type: str = Field(default="text", pattern="^(text|markdown)$")
    chunking_strategy: str = Field(default="sentence", pattern="^(sentence|paragraph|fixed_size|semantic)$")
    chunk_size: int = Field(default=500, ge=100, le=2000)
    generate_embeddings: bool = True


# =============================================================================
# DEPENDENCIES
# =============================================================================


async def get_grounded_interface() -> GroundedInterface:
    """Get the initialized GROUNDED interface."""
    global _interface_initialized

    interface = get_interface()

    if not _interface_initialized:
        await interface.initialize()
        _interface_initialized = True

    return interface


def get_client_id(
    x_client_id: Optional[str] = Header(None, alias="X-Client-ID"),
) -> str:
    """
    Extract client ID from request headers.

    For now, accepts any client ID or generates a default.
    In production, this would validate against registered clients.
    """
    if x_client_id:
        return x_client_id
    return "anonymous-client"


# =============================================================================
# SYSTEM ENDPOINTS
# =============================================================================


@router.get("/health")
async def health_check(
    interface: GroundedInterface = Depends(get_grounded_interface),
    client_id: str = Depends(get_client_id),
):
    """
    Check system health and component status.

    Returns health information for all GROUNDED components.
    """
    request = HealthCheckRequest(client_id=client_id)
    response = interface.health_check(request)
    return response.to_dict()


@router.get("/capabilities")
async def list_capabilities(
    interface: GroundedInterface = Depends(get_grounded_interface),
    client_id: str = Depends(get_client_id),
):
    """
    List available capabilities.

    Returns information about what capabilities are available
    and their current status.
    """
    request = CapabilityListRequest(client_id=client_id)
    response = interface.list_capabilities(request)
    return response.to_dict()


# =============================================================================
# EMBEDDING ENDPOINTS
# =============================================================================


@router.post("/embeddings")
async def create_embedding(
    body: EmbeddingRequestModel,
    interface: GroundedInterface = Depends(get_grounded_interface),
    client_id: str = Depends(get_client_id),
):
    """
    Generate an embedding for text.

    Converts text into a high-dimensional vector representation
    for semantic similarity operations.
    """
    request = EmbeddingRequest(client_id=client_id, text=body.text)
    response = interface.create_embedding(request)

    if not response.is_success:
        raise HTTPException(
            status_code=_status_to_http_code(response.status),
            detail=response.error_message,
        )

    return response.to_dict()


@router.post("/embeddings/batch")
async def create_batch_embeddings(
    body: BatchEmbeddingRequestModel,
    interface: GroundedInterface = Depends(get_grounded_interface),
    client_id: str = Depends(get_client_id),
):
    """
    Generate embeddings for multiple texts.

    Efficiently processes multiple texts in a single request.
    """
    request = BatchEmbeddingRequest(client_id=client_id, texts=body.texts)
    response = interface.create_batch_embeddings(request)

    if not response.is_success:
        raise HTTPException(
            status_code=_status_to_http_code(response.status),
            detail=response.error_message,
        )

    return response.to_dict()


# =============================================================================
# KNOWLEDGE ENDPOINTS
# =============================================================================


@router.post("/knowledge/bases")
async def create_knowledge_base(
    body: CreateKnowledgeBaseModel,
    interface: GroundedInterface = Depends(get_grounded_interface),
    client_id: str = Depends(get_client_id),
):
    """
    Create a new knowledge base.

    Creates an isolated knowledge container for storing and
    retrieving information.
    """
    request = CreateKnowledgeBaseRequest(
        client_id=client_id,
        name=body.name,
        description=body.description,
        owner_type="client",
        owner_id=client_id,
        kb_metadata=body.metadata,
    )
    response = interface.create_knowledge_base(request)

    if not response.is_success:
        raise HTTPException(
            status_code=_status_to_http_code(response.status),
            detail=response.error_message,
        )

    return response.to_dict()


@router.post("/knowledge/items")
async def add_knowledge(
    body: AddKnowledgeModel,
    interface: GroundedInterface = Depends(get_grounded_interface),
    client_id: str = Depends(get_client_id),
):
    """
    Add knowledge to a knowledge base.

    Stores content with optional embedding generation for
    semantic search.
    """
    request = AddKnowledgeRequest(
        client_id=client_id,
        base_id=body.base_id,
        source_name=body.source_name,
        content=body.content,
        title=body.title,
        content_metadata=body.metadata,
        generate_embedding=body.generate_embedding,
    )
    response = interface.add_knowledge(request)

    if not response.is_success:
        raise HTTPException(
            status_code=_status_to_http_code(response.status),
            detail=response.error_message,
        )

    return response.to_dict()


@router.post("/knowledge/search")
async def search_knowledge(
    body: SearchKnowledgeModel,
    interface: GroundedInterface = Depends(get_grounded_interface),
    client_id: str = Depends(get_client_id),
):
    """
    Search a knowledge base.

    Performs text, semantic, or hybrid search to find
    relevant knowledge items.
    """
    request = KnowledgeSearchRequest(
        client_id=client_id,
        base_id=body.base_id,
        query=body.query,
        limit=body.limit,
        source_ids=body.source_ids,
        filters=body.filters,
        search_type=body.search_type,
        min_score=body.min_score,
    )
    response = interface.search_knowledge(request)

    if not response.is_success:
        raise HTTPException(
            status_code=_status_to_http_code(response.status),
            detail=response.error_message,
        )

    return response.to_dict()


@router.post("/knowledge/answer")
async def get_knowledge_answer(
    body: AnswerRequestModel,
    interface: GroundedInterface = Depends(get_grounded_interface),
    client_id: str = Depends(get_client_id),
):
    """
    Get a grounded answer from a knowledge base.

    Retrieves relevant knowledge and generates an answer
    with citations for verification.
    """
    request = KnowledgeAnswerRequest(
        client_id=client_id,
        base_id=body.base_id,
        question=body.question,
        limit=body.limit,
        source_ids=body.source_ids,
        context=body.context,
    )
    response = interface.get_knowledge_answer(request)

    if not response.is_success:
        raise HTTPException(
            status_code=_status_to_http_code(response.status),
            detail=response.error_message,
        )

    return response.to_dict()


# =============================================================================
# DOCUMENT ENDPOINTS
# =============================================================================


@router.post("/documents/process")
async def process_document(
    body: ProcessDocumentModel,
    interface: GroundedInterface = Depends(get_grounded_interface),
    client_id: str = Depends(get_client_id),
):
    """
    Process a document.

    Extracts text, chunks content, and optionally generates
    embeddings for each chunk.
    """
    request = ProcessDocumentRequest(
        client_id=client_id,
        content=body.content,
        title=body.title,
        document_type=body.document_type,
        chunking_strategy=body.chunking_strategy,
        chunk_size=body.chunk_size,
        generate_embeddings=body.generate_embeddings,
    )
    response = interface.process_document(request)

    if not response.is_success:
        raise HTTPException(
            status_code=_status_to_http_code(response.status),
            detail=response.error_message,
        )

    return response.to_dict()


# =============================================================================
# GOVERNANCE ENDPOINTS
# =============================================================================


@router.get("/governance/stats")
async def get_governance_stats(
    include_by_type: bool = True,
    include_by_provider: bool = True,
    interface: GroundedInterface = Depends(get_grounded_interface),
    client_id: str = Depends(get_client_id),
):
    """
    Get AI governance statistics.

    Returns usage metrics and statistics for AI operations.
    """
    request = GovernanceStatsRequest(
        client_id=client_id,
        include_by_type=include_by_type,
        include_by_provider=include_by_provider,
    )
    response = interface.get_governance_stats(request)

    if not response.is_success:
        raise HTTPException(
            status_code=_status_to_http_code(response.status),
            detail=response.error_message,
        )

    return response.to_dict()


# =============================================================================
# HELPERS
# =============================================================================


def _status_to_http_code(status: RequestStatus) -> int:
    """Convert request status to HTTP status code."""
    mapping = {
        RequestStatus.COMPLETED: 200,
        RequestStatus.FAILED: 500,
        RequestStatus.UNAUTHORIZED: 403,
        RequestStatus.RATE_LIMITED: 429,
        RequestStatus.PENDING: 202,
        RequestStatus.PROCESSING: 202,
    }
    return mapping.get(status, 500)
