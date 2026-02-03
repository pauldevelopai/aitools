"""
GROUNDED Interface Service - Main orchestrator for external tool integration.

Provides a unified interface for civic tools to access GROUNDED capabilities
including AI processing, knowledge systems, document handling, and governance.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from grounded import __version__ as grounded_version
from grounded.ai import get_embedding_provider, register_default_providers
from grounded.documents import Document, DocumentProcessor, ProcessorConfig, ChunkingStrategy
from grounded.governance.ai import get_governance_tracker
from grounded.knowledge import KnowledgeService

from grounded.interface.models import (
    CapabilityType,
    RequestStatus,
    InterfaceRequest,
    InterfaceResponse,
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
)
from grounded.interface.capabilities import (
    CapabilityRegistry,
    get_capability_registry,
    AccessLevel,
)

logger = logging.getLogger(__name__)


class GroundedInterface:
    """
    Main interface service for external civic tool integration.

    Provides a controlled, unified interface for tools to access GROUNDED
    capabilities. Handles authentication, authorization, rate limiting,
    and request processing.

    Example:
        interface = GroundedInterface()
        await interface.initialize()

        # Register a client
        interface.register_client("civic-tool-123", AccessLevel.PARTNER)

        # Process a request
        request = EmbeddingRequest(
            client_id="civic-tool-123",
            text="Hello world"
        )
        response = interface.create_embedding(request)
    """

    def __init__(self):
        """Initialize the interface service."""
        self._registry = get_capability_registry()
        self._knowledge_service: Optional[KnowledgeService] = None
        self._document_processor: Optional[DocumentProcessor] = None
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if the interface is initialized."""
        return self._initialized

    @property
    def registry(self) -> CapabilityRegistry:
        """Get the capability registry."""
        return self._registry

    async def initialize(self) -> None:
        """
        Initialize the interface and its dependencies.

        Sets up AI providers, knowledge service, and document processor.
        """
        if self._initialized:
            return

        logger.info("Initializing GROUNDED Interface")

        try:
            # Ensure AI providers are registered
            register_default_providers()

            # Initialize knowledge service
            self._knowledge_service = KnowledgeService()
            await self._knowledge_service.initialize()

            # Initialize document processor
            config = ProcessorConfig(
                chunking_strategy=ChunkingStrategy.SENTENCE,
                chunk_size=500,
                generate_embeddings=True,
            )
            self._document_processor = DocumentProcessor(config)
            await self._document_processor.initialize()

            self._initialized = True
            logger.info("GROUNDED Interface initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize interface: {e}")
            raise

    def _ensure_initialized(self) -> None:
        """Ensure the interface is initialized."""
        if not self._initialized:
            import asyncio
            asyncio.get_event_loop().run_until_complete(self.initialize())

    def _check_access(
        self,
        request: InterfaceRequest,
    ) -> Optional[InterfaceResponse]:
        """
        Check if client has access to the requested capability.

        Returns an error response if access is denied, None if allowed.
        """
        allowed, reason = self._registry.can_use_capability(
            request.client_id,
            request.capability,
        )

        if not allowed:
            return InterfaceResponse(
                request_id=request.request_id,
                status=RequestStatus.UNAUTHORIZED,
                error_message=reason,
                error_code="ACCESS_DENIED",
            )

        return None

    def _record_and_respond(
        self,
        request: InterfaceRequest,
        response: InterfaceResponse,
        start_time: float,
    ) -> InterfaceResponse:
        """Record usage and finalize response timing."""
        response.processing_time_ms = (time.time() - start_time) * 1000

        if response.is_success:
            self._registry.record_usage(request.client_id, request.capability)

        return response

    # =========================================================================
    # CLIENT MANAGEMENT
    # =========================================================================

    def register_client(
        self,
        client_id: str,
        access_level: AccessLevel = AccessLevel.AUTHENTICATED,
        allowed_capabilities: Optional[set] = None,
    ) -> None:
        """
        Register a client for interface access.

        Args:
            client_id: Unique client identifier
            access_level: Access level to grant
            allowed_capabilities: Specific capabilities to allow
        """
        self._registry.register_client(client_id, access_level, allowed_capabilities)
        logger.info(f"Registered client {client_id} with access level {access_level.value}")

    # =========================================================================
    # AI PROCESSING
    # =========================================================================

    def create_embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Generate an embedding for text.

        Args:
            request: Embedding request with text

        Returns:
            EmbeddingResponse with vector or error
        """
        start_time = time.time()

        # Check access
        error = self._check_access(request)
        if error:
            return EmbeddingResponse(
                request_id=request.request_id,
                status=error.status,
                error_message=error.error_message,
                error_code=error.error_code,
            )

        try:
            self._ensure_initialized()
            provider = get_embedding_provider()
            embedding = provider.create_embedding(request.text)

            response = EmbeddingResponse(
                request_id=request.request_id,
                status=RequestStatus.COMPLETED,
                embedding=embedding,
                dimensions=len(embedding),
                provider=provider.name,
                model=provider.model if hasattr(provider, 'model') else "unknown",
            )

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            response = EmbeddingResponse(
                request_id=request.request_id,
                status=RequestStatus.FAILED,
                error_message=str(e),
                error_code="EMBEDDING_ERROR",
            )

        return self._record_and_respond(request, response, start_time)

    def create_batch_embeddings(self, request: BatchEmbeddingRequest) -> BatchEmbeddingResponse:
        """
        Generate embeddings for multiple texts.

        Args:
            request: Batch embedding request with texts

        Returns:
            BatchEmbeddingResponse with vectors or error
        """
        start_time = time.time()

        # Check access
        error = self._check_access(request)
        if error:
            return BatchEmbeddingResponse(
                request_id=request.request_id,
                status=error.status,
                error_message=error.error_message,
                error_code=error.error_code,
            )

        try:
            self._ensure_initialized()
            provider = get_embedding_provider()
            embeddings = provider.create_embeddings(request.texts)

            response = BatchEmbeddingResponse(
                request_id=request.request_id,
                status=RequestStatus.COMPLETED,
                embeddings=embeddings,
                count=len(embeddings),
                dimensions=len(embeddings[0]) if embeddings else 0,
                provider=provider.name,
                model=provider.model if hasattr(provider, 'model') else "unknown",
            )

        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            response = BatchEmbeddingResponse(
                request_id=request.request_id,
                status=RequestStatus.FAILED,
                error_message=str(e),
                error_code="BATCH_EMBEDDING_ERROR",
            )

        return self._record_and_respond(request, response, start_time)

    # =========================================================================
    # KNOWLEDGE SYSTEM
    # =========================================================================

    def create_knowledge_base(self, request: CreateKnowledgeBaseRequest) -> CreateKnowledgeBaseResponse:
        """
        Create a new knowledge base.

        Args:
            request: Knowledge base creation request

        Returns:
            CreateKnowledgeBaseResponse with base ID or error
        """
        start_time = time.time()

        # Check access
        error = self._check_access(request)
        if error:
            return CreateKnowledgeBaseResponse(
                request_id=request.request_id,
                status=error.status,
                error_message=error.error_message,
                error_code=error.error_code,
            )

        try:
            self._ensure_initialized()
            base = self._knowledge_service.create_knowledge_base(
                name=request.name,
                owner_type=request.owner_type,
                owner_id=request.owner_id,
                description=request.description,
                metadata=request.kb_metadata,
            )

            response = CreateKnowledgeBaseResponse(
                request_id=request.request_id,
                status=RequestStatus.COMPLETED,
                base_id=base.base_id,
                name=base.name,
                owner_type=base.owner_type,
                owner_id=base.owner_id,
            )

        except Exception as e:
            logger.error(f"Knowledge base creation failed: {e}")
            response = CreateKnowledgeBaseResponse(
                request_id=request.request_id,
                status=RequestStatus.FAILED,
                error_message=str(e),
                error_code="KNOWLEDGE_BASE_ERROR",
            )

        return self._record_and_respond(request, response, start_time)

    def add_knowledge(self, request: AddKnowledgeRequest) -> AddKnowledgeResponse:
        """
        Add knowledge to a knowledge base.

        Args:
            request: Add knowledge request

        Returns:
            AddKnowledgeResponse with item ID or error
        """
        start_time = time.time()

        # Check access
        error = self._check_access(request)
        if error:
            return AddKnowledgeResponse(
                request_id=request.request_id,
                status=error.status,
                error_message=error.error_message,
                error_code=error.error_code,
            )

        try:
            self._ensure_initialized()

            # Get or create source
            sources = self._knowledge_service.list_sources(request.base_id)
            source = None
            for s in sources:
                if s.name == request.source_name:
                    source = s
                    break

            if not source:
                source = self._knowledge_service.create_source(
                    base_id=request.base_id,
                    name=request.source_name,
                )

            # Add knowledge
            item = self._knowledge_service.add_knowledge(
                base_id=request.base_id,
                source_id=source.source_id,
                content=request.content,
                title=request.title,
                metadata=request.content_metadata,
                generate_embedding=request.generate_embedding,
            )

            response = AddKnowledgeResponse(
                request_id=request.request_id,
                status=RequestStatus.COMPLETED,
                item_id=item.item_id,
                source_id=source.source_id,
                has_embedding=item.has_embedding,
            )

        except Exception as e:
            logger.error(f"Add knowledge failed: {e}")
            response = AddKnowledgeResponse(
                request_id=request.request_id,
                status=RequestStatus.FAILED,
                error_message=str(e),
                error_code="ADD_KNOWLEDGE_ERROR",
            )

        return self._record_and_respond(request, response, start_time)

    def search_knowledge(self, request: KnowledgeSearchRequest) -> KnowledgeSearchResponse:
        """
        Search a knowledge base.

        Args:
            request: Knowledge search request

        Returns:
            KnowledgeSearchResponse with results or error
        """
        start_time = time.time()

        # Check access
        error = self._check_access(request)
        if error:
            return KnowledgeSearchResponse(
                request_id=request.request_id,
                status=error.status,
                error_message=error.error_message,
                error_code=error.error_code,
            )

        try:
            self._ensure_initialized()
            results = self._knowledge_service.search(
                base_id=request.base_id,
                query=request.query,
                limit=request.limit,
                source_ids=request.source_ids,
                filters=request.filters,
                min_score=request.min_score,
                search_type=request.search_type,
            )

            # Convert to interface model
            result_items = []
            for r in results.results:
                result_items.append(SearchResultItem(
                    item_id=r.item.item_id,
                    source_id=r.item.source_id,
                    content=r.item.content,
                    title=r.item.title,
                    score=r.score,
                    rank=r.rank,
                    highlights=r.highlights,
                    item_metadata=r.item.metadata,
                ))

            response = KnowledgeSearchResponse(
                request_id=request.request_id,
                status=RequestStatus.COMPLETED,
                results=result_items,
                total_count=results.total_count,
                query_time_ms=results.query_time_ms,
            )

        except Exception as e:
            logger.error(f"Knowledge search failed: {e}")
            response = KnowledgeSearchResponse(
                request_id=request.request_id,
                status=RequestStatus.FAILED,
                error_message=str(e),
                error_code="SEARCH_ERROR",
            )

        return self._record_and_respond(request, response, start_time)

    def get_knowledge_answer(self, request: KnowledgeAnswerRequest) -> KnowledgeAnswerResponse:
        """
        Get a grounded answer from a knowledge base.

        Args:
            request: Knowledge answer request

        Returns:
            KnowledgeAnswerResponse with answer and citations or error
        """
        start_time = time.time()

        # Check access
        error = self._check_access(request)
        if error:
            return KnowledgeAnswerResponse(
                request_id=request.request_id,
                status=error.status,
                error_message=error.error_message,
                error_code=error.error_code,
            )

        try:
            self._ensure_initialized()
            answer = self._knowledge_service.get_answer(
                base_id=request.base_id,
                query=request.question,
                limit=request.limit,
                source_ids=request.source_ids,
            )

            # Convert citations
            citations = []
            for c in answer.citations:
                citations.append(CitationItem(
                    item_id=c.item_id,
                    source_id=c.source_id,
                    source_name=c.source_name,
                    excerpt=c.content_excerpt,
                    relevance_score=c.relevance_score,
                ))

            response = KnowledgeAnswerResponse(
                request_id=request.request_id,
                status=RequestStatus.COMPLETED,
                answer=answer.answer_text,
                citations=citations,
                confidence_score=answer.confidence_score,
                is_grounded=answer.is_grounded,
            )

        except Exception as e:
            logger.error(f"Knowledge answer failed: {e}")
            response = KnowledgeAnswerResponse(
                request_id=request.request_id,
                status=RequestStatus.FAILED,
                error_message=str(e),
                error_code="ANSWER_ERROR",
            )

        return self._record_and_respond(request, response, start_time)

    # =========================================================================
    # DOCUMENT PROCESSING
    # =========================================================================

    def process_document(self, request: ProcessDocumentRequest) -> ProcessDocumentResponse:
        """
        Process a document with chunking and embedding.

        Args:
            request: Document processing request

        Returns:
            ProcessDocumentResponse with chunks or error
        """
        start_time = time.time()

        # Check access
        error = self._check_access(request)
        if error:
            return ProcessDocumentResponse(
                request_id=request.request_id,
                status=error.status,
                error_message=error.error_message,
                error_code=error.error_code,
            )

        try:
            self._ensure_initialized()

            # Create document
            if request.document_type == "markdown":
                doc = Document.from_markdown(request.content, title=request.title)
            else:
                doc = Document.from_text(request.content, title=request.title)

            # Configure processor
            config = ProcessorConfig(
                chunking_strategy=ChunkingStrategy(request.chunking_strategy),
                chunk_size=request.chunk_size,
                generate_embeddings=request.generate_embeddings,
            )
            processor = DocumentProcessor(config)
            # Note: processor.initialize() would be async, but we're using the shared one
            # For this request, we'll use the instance config

            # Process document
            processed = self._document_processor.process_document(doc)

            # Convert chunks
            chunks = []
            for c in processed.chunks:
                chunks.append(ChunkInfo(
                    chunk_id=c.chunk_id,
                    index=c.chunk_index,
                    content=c.content,
                    char_count=c.character_count,
                    word_count=c.word_count,
                    has_embedding=c.has_embedding,
                ))

            response = ProcessDocumentResponse(
                request_id=request.request_id,
                status=RequestStatus.COMPLETED,
                document_id=processed.document_id,
                chunk_count=processed.chunk_count,
                embedding_count=processed.embedding_count,
                chunks=chunks,
                document_word_count=doc.word_count,
                document_char_count=doc.character_count,
            )

        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            response = ProcessDocumentResponse(
                request_id=request.request_id,
                status=RequestStatus.FAILED,
                error_message=str(e),
                error_code="DOCUMENT_ERROR",
            )

        return self._record_and_respond(request, response, start_time)

    # =========================================================================
    # GOVERNANCE
    # =========================================================================

    def get_governance_stats(self, request: GovernanceStatsRequest) -> GovernanceStatsResponse:
        """
        Get governance statistics.

        Args:
            request: Governance stats request

        Returns:
            GovernanceStatsResponse with statistics or error
        """
        start_time = time.time()

        # Check access
        error = self._check_access(request)
        if error:
            return GovernanceStatsResponse(
                request_id=request.request_id,
                status=error.status,
                error_message=error.error_message,
                error_code=error.error_code,
            )

        try:
            tracker = get_governance_tracker()
            stats = tracker.get_stats()

            response = GovernanceStatsResponse(
                request_id=request.request_id,
                status=RequestStatus.COMPLETED,
                total_operations=stats.total_operations,
                successful_operations=stats.successful_operations,
                failed_operations=stats.failed_operations,
                success_rate=stats.success_rate,
                total_tokens=stats.total_tokens,
                avg_duration_ms=stats.avg_duration_ms,
                operations_by_type=stats.operations_by_type if request.include_by_type else {},
                operations_by_provider=stats.operations_by_provider if request.include_by_provider else {},
            )

        except Exception as e:
            logger.error(f"Governance stats failed: {e}")
            response = GovernanceStatsResponse(
                request_id=request.request_id,
                status=RequestStatus.FAILED,
                error_message=str(e),
                error_code="GOVERNANCE_ERROR",
            )

        return self._record_and_respond(request, response, start_time)

    # =========================================================================
    # SYSTEM
    # =========================================================================

    def health_check(self, request: HealthCheckRequest) -> HealthCheckResponse:
        """
        Check system health.

        Args:
            request: Health check request

        Returns:
            HealthCheckResponse with health status
        """
        start_time = time.time()

        try:
            components = []

            if request.include_components:
                # Check embedding provider
                try:
                    provider = get_embedding_provider()
                    components.append(ComponentHealth(
                        name="embedding_provider",
                        status="healthy",
                        details={"provider": provider.name},
                    ))
                except Exception as e:
                    components.append(ComponentHealth(
                        name="embedding_provider",
                        status="unhealthy",
                        details={"error": str(e)},
                    ))

                # Check knowledge service
                if self._knowledge_service:
                    components.append(ComponentHealth(
                        name="knowledge_service",
                        status="healthy",
                        details={"initialized": self._knowledge_service.is_initialized},
                    ))
                else:
                    components.append(ComponentHealth(
                        name="knowledge_service",
                        status="not_initialized",
                        details={},
                    ))

                # Check document processor
                if self._document_processor:
                    components.append(ComponentHealth(
                        name="document_processor",
                        status="healthy",
                        details={},
                    ))
                else:
                    components.append(ComponentHealth(
                        name="document_processor",
                        status="not_initialized",
                        details={},
                    ))

            # Determine overall status
            overall = "healthy"
            for c in components:
                if c.status == "unhealthy":
                    overall = "unhealthy"
                    break
                elif c.status == "not_initialized":
                    overall = "degraded"

            response = HealthCheckResponse(
                request_id=request.request_id,
                status=RequestStatus.COMPLETED,
                overall_status=overall,
                version=grounded_version,
                components=components,
            )

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            response = HealthCheckResponse(
                request_id=request.request_id,
                status=RequestStatus.FAILED,
                overall_status="error",
                error_message=str(e),
            )

        response.processing_time_ms = (time.time() - start_time) * 1000
        return response

    def list_capabilities(self, request: CapabilityListRequest) -> CapabilityListResponse:
        """
        List available capabilities.

        Args:
            request: Capability list request

        Returns:
            CapabilityListResponse with available capabilities
        """
        start_time = time.time()

        try:
            # Get client's access level
            access_level = self._registry.get_client_access_level(request.client_id)

            # List capabilities at or below client's level
            capabilities = self._registry.list_capabilities(enabled_only=True)
            capability_infos = [c.to_capability_info() for c in capabilities]

            response = CapabilityListResponse(
                request_id=request.request_id,
                status=RequestStatus.COMPLETED,
                capabilities=capability_infos,
                api_version="v1",
            )

        except Exception as e:
            logger.error(f"Capability list failed: {e}")
            response = CapabilityListResponse(
                request_id=request.request_id,
                status=RequestStatus.FAILED,
                error_message=str(e),
            )

        response.processing_time_ms = (time.time() - start_time) * 1000
        return response

    def get_stats(self) -> Dict[str, Any]:
        """Get interface statistics."""
        return {
            "initialized": self._initialized,
            "version": grounded_version,
            "knowledge_service": self._knowledge_service.is_initialized if self._knowledge_service else False,
        }


# Global interface instance
_interface: Optional[GroundedInterface] = None


def get_interface() -> GroundedInterface:
    """Get the global interface instance."""
    global _interface
    if _interface is None:
        _interface = GroundedInterface()
    return _interface
