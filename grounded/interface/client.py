"""
GROUNDED Interface Client - Client library for civic tools to connect to GROUNDED.

Provides a simple, type-safe client for external applications to access
GROUNDED capabilities via either direct Python integration or HTTP API.
"""

import logging
from typing import Any, Dict, List, Optional
import httpx

from grounded.interface.models import (
    CapabilityType,
    RequestStatus,
    EmbeddingRequest,
    EmbeddingResponse,
    BatchEmbeddingRequest,
    BatchEmbeddingResponse,
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
    ProcessDocumentRequest,
    ProcessDocumentResponse,
    ChunkInfo,
    GovernanceStatsRequest,
    GovernanceStatsResponse,
    HealthCheckRequest,
    HealthCheckResponse,
    ComponentHealth,
    CapabilityListRequest,
    CapabilityListResponse,
    CapabilityInfo,
)

logger = logging.getLogger(__name__)


class GroundedClientError(Exception):
    """Base exception for GROUNDED client errors."""

    def __init__(self, message: str, error_code: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class GroundedConnectionError(GroundedClientError):
    """Error connecting to GROUNDED service."""
    pass


class GroundedAuthError(GroundedClientError):
    """Authentication/authorization error."""
    pass


class GroundedRateLimitError(GroundedClientError):
    """Rate limit exceeded error."""
    pass


class GroundedClient:
    """
    Client for connecting to GROUNDED from external civic tools.

    Supports two modes:
    1. Direct mode: Direct Python integration (same process)
    2. HTTP mode: Connection via HTTP API (for remote/distributed use)

    Example (Direct mode):
        client = GroundedClient.create_direct("my-civic-tool")
        await client.initialize()

        # Generate embedding
        embedding = client.create_embedding("Hello world")

        # Search knowledge
        results = client.search_knowledge("base-123", "vacation policy")

    Example (HTTP mode):
        client = GroundedClient.create_http(
            base_url="https://api.grounded.example.com",
            client_id="my-civic-tool",
            api_key="sk-xxx"
        )

        embedding = await client.create_embedding_async("Hello world")
    """

    def __init__(
        self,
        client_id: str,
        mode: str = "direct",
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize the client.

        Args:
            client_id: Unique identifier for this client
            mode: "direct" for same-process, "http" for API calls
            base_url: Base URL for HTTP mode
            api_key: API key for HTTP authentication
            timeout: Request timeout in seconds
        """
        self._client_id = client_id
        self._mode = mode
        self._base_url = base_url
        self._api_key = api_key
        self._timeout = timeout
        self._initialized = False
        self._interface = None  # For direct mode
        self._http_client: Optional[httpx.AsyncClient] = None

    @property
    def client_id(self) -> str:
        """Get the client ID."""
        return self._client_id

    @property
    def is_initialized(self) -> bool:
        """Check if the client is initialized."""
        return self._initialized

    @classmethod
    def create_direct(cls, client_id: str) -> "GroundedClient":
        """
        Create a direct-mode client for same-process integration.

        Args:
            client_id: Unique identifier for this client

        Returns:
            GroundedClient configured for direct mode
        """
        return cls(client_id=client_id, mode="direct")

    @classmethod
    def create_http(
        cls,
        base_url: str,
        client_id: str,
        api_key: str,
        timeout: float = 30.0,
    ) -> "GroundedClient":
        """
        Create an HTTP-mode client for API integration.

        Args:
            base_url: Base URL of the GROUNDED API
            client_id: Unique identifier for this client
            api_key: API key for authentication
            timeout: Request timeout in seconds

        Returns:
            GroundedClient configured for HTTP mode
        """
        return cls(
            client_id=client_id,
            mode="http",
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
        )

    async def initialize(self) -> None:
        """Initialize the client."""
        if self._initialized:
            return

        if self._mode == "direct":
            from grounded.interface.service import get_interface
            from grounded.interface.capabilities import AccessLevel

            self._interface = get_interface()
            await self._interface.initialize()
            self._interface.register_client(self._client_id, AccessLevel.AUTHENTICATED)

        elif self._mode == "http":
            self._http_client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers={
                    "X-Client-ID": self._client_id,
                    "Authorization": f"Bearer {self._api_key}",
                },
            )

        self._initialized = True
        logger.info(f"GROUNDED client initialized in {self._mode} mode")

    async def close(self) -> None:
        """Close the client and release resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Ensure the client is initialized."""
        if not self._initialized:
            import asyncio
            asyncio.get_event_loop().run_until_complete(self.initialize())

    def _check_response(self, response: Any) -> None:
        """Check response for errors and raise appropriate exceptions."""
        if hasattr(response, 'status'):
            if response.status == RequestStatus.UNAUTHORIZED:
                raise GroundedAuthError(
                    response.error_message or "Access denied",
                    response.error_code,
                )
            elif response.status == RequestStatus.RATE_LIMITED:
                raise GroundedRateLimitError(
                    response.error_message or "Rate limit exceeded",
                    response.error_code,
                )
            elif response.status == RequestStatus.FAILED:
                raise GroundedClientError(
                    response.error_message or "Request failed",
                    response.error_code,
                )

    # =========================================================================
    # AI PROCESSING
    # =========================================================================

    def create_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding for text (synchronous).

        Args:
            text: Text to embed

        Returns:
            Embedding vector

        Raises:
            GroundedClientError: If request fails
        """
        self._ensure_initialized()

        if self._mode == "direct":
            request = EmbeddingRequest(client_id=self._client_id, text=text)
            response = self._interface.create_embedding(request)
            self._check_response(response)
            return response.embedding

        raise NotImplementedError("Use create_embedding_async for HTTP mode")

    async def create_embedding_async(self, text: str) -> List[float]:
        """
        Generate an embedding for text (asynchronous).

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        await self.initialize()

        if self._mode == "direct":
            return self.create_embedding(text)

        # HTTP mode
        response = await self._http_client.post(
            "/api/v1/embeddings",
            json={"text": text},
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("success"):
            raise GroundedClientError(data.get("error_message", "Unknown error"))
        return data["embedding"]

    def create_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (synchronous).

        Args:
            texts: Texts to embed

        Returns:
            List of embedding vectors
        """
        self._ensure_initialized()

        if self._mode == "direct":
            request = BatchEmbeddingRequest(client_id=self._client_id, texts=texts)
            response = self._interface.create_batch_embeddings(request)
            self._check_response(response)
            return response.embeddings

        raise NotImplementedError("Use create_batch_embeddings_async for HTTP mode")

    # =========================================================================
    # KNOWLEDGE SYSTEM
    # =========================================================================

    def create_knowledge_base(
        self,
        name: str,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new knowledge base.

        Args:
            name: Name for the knowledge base
            description: Optional description
            metadata: Optional metadata

        Returns:
            Knowledge base ID
        """
        self._ensure_initialized()

        if self._mode == "direct":
            request = CreateKnowledgeBaseRequest(
                client_id=self._client_id,
                name=name,
                description=description,
                owner_type="client",
                owner_id=self._client_id,
                kb_metadata=metadata or {},
            )
            response = self._interface.create_knowledge_base(request)
            self._check_response(response)
            return response.base_id

        raise NotImplementedError("Use async methods for HTTP mode")

    def add_knowledge(
        self,
        base_id: str,
        source_name: str,
        content: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        generate_embedding: bool = True,
    ) -> str:
        """
        Add knowledge to a knowledge base.

        Args:
            base_id: Knowledge base ID
            source_name: Name of the source (will be created if doesn't exist)
            content: Content text
            title: Optional title
            metadata: Optional metadata
            generate_embedding: Whether to generate embedding

        Returns:
            Knowledge item ID
        """
        self._ensure_initialized()

        if self._mode == "direct":
            request = AddKnowledgeRequest(
                client_id=self._client_id,
                base_id=base_id,
                source_name=source_name,
                content=content,
                title=title,
                content_metadata=metadata or {},
                generate_embedding=generate_embedding,
            )
            response = self._interface.add_knowledge(request)
            self._check_response(response)
            return response.item_id

        raise NotImplementedError("Use async methods for HTTP mode")

    def search_knowledge(
        self,
        base_id: str,
        query: str,
        limit: int = 10,
        search_type: str = "hybrid",
    ) -> List[Dict[str, Any]]:
        """
        Search a knowledge base.

        Args:
            base_id: Knowledge base ID
            query: Search query
            limit: Maximum results
            search_type: "text", "semantic", or "hybrid"

        Returns:
            List of search results as dictionaries
        """
        self._ensure_initialized()

        if self._mode == "direct":
            request = KnowledgeSearchRequest(
                client_id=self._client_id,
                base_id=base_id,
                query=query,
                limit=limit,
                search_type=search_type,
            )
            response = self._interface.search_knowledge(request)
            self._check_response(response)
            return [r.to_dict() for r in response.results]

        raise NotImplementedError("Use async methods for HTTP mode")

    def get_answer(
        self,
        base_id: str,
        question: str,
        limit: int = 5,
    ) -> Dict[str, Any]:
        """
        Get a grounded answer from a knowledge base.

        Args:
            base_id: Knowledge base ID
            question: Question to answer
            limit: Maximum sources to use

        Returns:
            Dictionary with answer and citations
        """
        self._ensure_initialized()

        if self._mode == "direct":
            request = KnowledgeAnswerRequest(
                client_id=self._client_id,
                base_id=base_id,
                question=question,
                limit=limit,
            )
            response = self._interface.get_knowledge_answer(request)
            self._check_response(response)
            return response.to_dict()

        raise NotImplementedError("Use async methods for HTTP mode")

    # =========================================================================
    # DOCUMENT PROCESSING
    # =========================================================================

    def process_document(
        self,
        content: str,
        title: Optional[str] = None,
        document_type: str = "text",
        chunking_strategy: str = "sentence",
        chunk_size: int = 500,
        generate_embeddings: bool = True,
    ) -> Dict[str, Any]:
        """
        Process a document with chunking and embedding.

        Args:
            content: Document content
            title: Optional title
            document_type: "text" or "markdown"
            chunking_strategy: Chunking strategy
            chunk_size: Target chunk size
            generate_embeddings: Whether to generate embeddings

        Returns:
            Processing result as dictionary
        """
        self._ensure_initialized()

        if self._mode == "direct":
            request = ProcessDocumentRequest(
                client_id=self._client_id,
                content=content,
                title=title,
                document_type=document_type,
                chunking_strategy=chunking_strategy,
                chunk_size=chunk_size,
                generate_embeddings=generate_embeddings,
            )
            response = self._interface.process_document(request)
            self._check_response(response)
            return response.to_dict()

        raise NotImplementedError("Use async methods for HTTP mode")

    # =========================================================================
    # GOVERNANCE
    # =========================================================================

    def get_governance_stats(self) -> Dict[str, Any]:
        """
        Get governance statistics.

        Returns:
            Statistics as dictionary
        """
        self._ensure_initialized()

        if self._mode == "direct":
            request = GovernanceStatsRequest(client_id=self._client_id)
            response = self._interface.get_governance_stats(request)
            self._check_response(response)
            return response.to_dict()

        raise NotImplementedError("Use async methods for HTTP mode")

    # =========================================================================
    # SYSTEM
    # =========================================================================

    def health_check(self) -> Dict[str, Any]:
        """
        Check system health.

        Returns:
            Health status as dictionary
        """
        self._ensure_initialized()

        if self._mode == "direct":
            request = HealthCheckRequest(client_id=self._client_id)
            response = self._interface.health_check(request)
            return response.to_dict()

        raise NotImplementedError("Use async methods for HTTP mode")

    def list_capabilities(self) -> List[Dict[str, Any]]:
        """
        List available capabilities.

        Returns:
            List of capability info dictionaries
        """
        self._ensure_initialized()

        if self._mode == "direct":
            request = CapabilityListRequest(client_id=self._client_id)
            response = self._interface.list_capabilities(request)
            return [c.to_dict() for c in response.capabilities]

        raise NotImplementedError("Use async methods for HTTP mode")

    # =========================================================================
    # CONTEXT MANAGER
    # =========================================================================

    async def __aenter__(self) -> "GroundedClient":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
