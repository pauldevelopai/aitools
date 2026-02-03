"""
GROUNDED Document Processor - Main document intelligence service.

The DocumentProcessor is the primary entry point for document intelligence
capabilities. It orchestrates extraction, chunking, embedding, and storage
to provide a complete document processing pipeline.

Usage:
    from grounded.documents import DocumentProcessor, Document

    processor = DocumentProcessor()
    await processor.initialize()

    doc = Document.from_text("Your document content here...", title="My Doc")
    result = processor.process_document(doc)

    # Search processed documents
    results = processor.search("search query")
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from grounded.core.base import ComponentStatus, GroundedComponent, HealthCheckResult
from grounded.core.config import get_settings
from grounded.ai import EmbeddingProvider, get_embedding_provider, register_default_providers, embedding_registry
from grounded.governance.ai import (
    AIOperationType,
    AIDataType,
    get_governance_tracker,
    GovernedEmbeddingProvider,
)
from grounded.documents.models import (
    Document,
    DocumentChunk,
    DocumentCollection,
    DocumentType,
    ProcessedDocument,
    ProcessingResult,
    ProcessingStatus,
)
from grounded.documents.extractors import (
    BaseExtractor,
    get_extractor,
    register_default_extractors,
    extractor_registry,
)
from grounded.documents.chunking import (
    BaseChunker,
    ChunkingConfig,
    ChunkingStrategy,
    get_chunker,
)
from grounded.documents.storage import (
    BaseDocumentStorage,
    SearchQuery,
    SearchResults,
    register_default_storage,
    get_storage,
)

logger = logging.getLogger(__name__)


@dataclass
class ProcessorConfig:
    """Configuration for the DocumentProcessor."""

    # Chunking settings
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.SENTENCE
    chunk_size: int = 512
    chunk_overlap: int = 50
    min_chunk_size: int = 100
    max_chunk_size: int = 1000

    # Embedding settings
    embedding_provider: Optional[str] = None  # Use default if None
    generate_embeddings: bool = True
    embedding_batch_size: int = 10

    # Storage settings
    storage_backend: str = "memory"
    auto_store: bool = True  # Automatically store processed documents

    # Processing settings
    extract_metadata: bool = True
    on_progress: Optional[Callable[[str, float], None]] = None

    # Governance settings
    enable_governance: bool = True  # Track operations in AI governance
    governance_actor_type: str = "system"
    governance_actor_id: Optional[str] = None

    def to_chunking_config(self) -> ChunkingConfig:
        """Convert to ChunkingConfig."""
        return ChunkingConfig(
            strategy=self.chunking_strategy,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            min_chunk_size=self.min_chunk_size,
            max_chunk_size=self.max_chunk_size,
        )


class DocumentProcessor(GroundedComponent):
    """
    Main document intelligence service.

    Provides a complete pipeline for processing documents:
    1. Extract text from various formats
    2. Split into semantic chunks
    3. Generate embeddings for each chunk
    4. Store for retrieval and search

    This service is designed to be:
    - Reusable across multiple applications
    - Configurable for different use cases
    - Extensible with custom extractors and storage backends

    Example:
        processor = DocumentProcessor()
        await processor.initialize()

        # Process a single document
        doc = Document.from_text("Your content...", title="Title")
        processed = processor.process_document(doc)

        # Process a collection
        collection = DocumentCollection(name="My Docs")
        collection.add_documents([doc1, doc2, doc3])
        result = processor.process_collection(collection)

        # Search processed documents
        results = processor.search("query text")
    """

    def __init__(self, config: Optional[ProcessorConfig] = None):
        """
        Initialize the DocumentProcessor.

        Args:
            config: Processor configuration (uses defaults if not provided)
        """
        self._config = config or ProcessorConfig()
        self._embedding_provider: Optional[EmbeddingProvider] = None
        self._storage: Optional[BaseDocumentStorage] = None
        self._chunker: Optional[BaseChunker] = None
        self._initialized = False

    @property
    def name(self) -> str:
        return "document_processor"

    @property
    def config(self) -> ProcessorConfig:
        """Get current configuration."""
        return self._config

    async def initialize(self) -> None:
        """
        Initialize the processor and its dependencies.

        Sets up extractors, storage, and embedding providers.
        """
        if self._initialized:
            return

        logger.info("Initializing DocumentProcessor")

        # Register default extractors
        if len(extractor_registry) == 0:
            register_default_extractors()

        # Register default storage
        register_default_storage()

        # Register default AI providers
        if len(embedding_registry) == 0:
            register_default_providers()

        # Get storage backend
        self._storage = get_storage(self._config.storage_backend)

        # Get embedding provider if enabled
        if self._config.generate_embeddings:
            try:
                base_provider = get_embedding_provider(
                    self._config.embedding_provider
                )
                # Wrap with governance tracking if enabled
                if self._config.enable_governance:
                    self._embedding_provider = GovernedEmbeddingProvider(
                        provider=base_provider,
                        source_component="DocumentProcessor",
                        actor_type=self._config.governance_actor_type,
                        actor_id=self._config.governance_actor_id,
                    )
                    logger.info(f"Using governed embedding provider: {base_provider.name}")
                else:
                    self._embedding_provider = base_provider
                    logger.info(f"Using embedding provider: {base_provider.name}")
            except Exception as e:
                logger.warning(f"Could not initialize embedding provider: {e}")
                self._embedding_provider = None

        # Initialize chunker
        self._chunker = get_chunker(
            self._config.chunking_strategy,
            self._config.to_chunking_config(),
        )

        self._initialized = True
        logger.info("DocumentProcessor initialized")

    async def shutdown(self) -> None:
        """Shutdown the processor."""
        self._initialized = False
        logger.info("DocumentProcessor shutdown")

    async def health_check(self) -> HealthCheckResult:
        """Check processor health."""
        if not self._initialized:
            return HealthCheckResult(
                status=ComponentStatus.UNKNOWN,
                component_name=self.name,
                message="Processor not initialized",
            )

        details = {
            "storage_backend": self._storage.name if self._storage else None,
            "embedding_provider": self._embedding_provider.name if self._embedding_provider else None,
            "chunking_strategy": self._config.chunking_strategy.value,
        }

        return HealthCheckResult(
            status=ComponentStatus.HEALTHY,
            component_name=self.name,
            message="DocumentProcessor operational",
            details=details,
        )

    def process_document(
        self,
        document: Document,
        config: Optional[ProcessorConfig] = None,
    ) -> ProcessedDocument:
        """
        Process a single document through the full pipeline.

        Args:
            document: The document to process
            config: Optional configuration override

        Returns:
            ProcessedDocument with extracted text and chunks
        """
        cfg = config or self._config
        start_time = time.time()
        tracker = get_governance_tracker() if cfg.enable_governance else None
        gov_record = None

        # Start governance tracking for document processing
        if tracker:
            gov_record = tracker.start_operation(
                operation_type=AIOperationType.DOCUMENT_PROCESSING,
                source_component="DocumentProcessor",
                source_module="grounded.documents.processor",
                source_function="process_document",
                provider_name=self._embedding_provider.name if self._embedding_provider else "",
                input_data_type=AIDataType.DOCUMENT,
                input_size=document.character_count,
                input_count=1,
                actor_type=cfg.governance_actor_type,
                actor_id=cfg.governance_actor_id,
                document_type=document.document_type.value,
                document_title=document.metadata.title or "",
            )

        try:
            # 1. Extract text
            self._report_progress(cfg, "extracting", 0.1)
            extractor = get_extractor(document.document_type.value)
            extraction_result = extractor.extract(document)

            if not extraction_result.success:
                return self._create_failed_result(
                    document,
                    f"Extraction failed: {extraction_result.error_message}",
                    start_time,
                )

            extracted_text = extraction_result.extracted_text

            # Update document metadata if extracted
            if cfg.extract_metadata and extraction_result.metadata_updates:
                for key, value in extraction_result.metadata_updates.items():
                    if value and not getattr(document.metadata, key, None):
                        setattr(document.metadata, key, value)

            # 2. Chunk text
            self._report_progress(cfg, "chunking", 0.3)
            chunks = self._chunker.chunk(
                extracted_text,
                document.document_id,
                cfg.to_chunking_config(),
            )

            # 3. Generate embeddings
            if cfg.generate_embeddings and self._embedding_provider:
                self._report_progress(cfg, "embedding", 0.5)
                chunks = self._generate_embeddings(chunks, cfg)

            self._report_progress(cfg, "finalizing", 0.9)

            # Create processed document
            processing_time = (time.time() - start_time) * 1000
            processed = ProcessedDocument(
                document_id=document.document_id,
                original_document=document,
                extracted_text=extracted_text,
                chunks=chunks,
                processing_status=ProcessingStatus.COMPLETED,
                processing_time_ms=processing_time,
            )

            # 4. Store if configured
            if cfg.auto_store and self._storage:
                self._storage.store_document(processed)

            # Complete governance tracking
            if tracker and gov_record:
                tracker.complete_operation(
                    gov_record.record_id,
                    output_size=len(extracted_text),
                    output_count=processed.chunk_count,
                    output_data_type=AIDataType.DOCUMENT,
                    chunks_created=processed.chunk_count,
                    embeddings_generated=processed.embedding_count,
                )

            self._report_progress(cfg, "completed", 1.0)
            return processed

        except Exception as e:
            # Fail governance tracking
            if tracker and gov_record:
                tracker.fail_operation(
                    gov_record.record_id,
                    error_message=str(e),
                    error_type=type(e).__name__,
                )
            logger.error(f"Error processing document {document.document_id}: {e}")
            return self._create_failed_result(document, str(e), start_time)

    def process_collection(
        self,
        collection: DocumentCollection,
        config: Optional[ProcessorConfig] = None,
    ) -> ProcessingResult:
        """
        Process all documents in a collection.

        Args:
            collection: The document collection to process
            config: Optional configuration override

        Returns:
            ProcessingResult with summary and all processed documents
        """
        cfg = config or self._config
        result = ProcessingResult()

        total_docs = collection.document_count
        for i, document in enumerate(collection.documents):
            # Update progress
            progress = (i / total_docs) if total_docs > 0 else 0
            self._report_progress(cfg, f"processing document {i + 1}/{total_docs}", progress)

            # Add collection reference to document metadata
            document.metadata.custom["collection_id"] = collection.collection_id

            # Process document
            processed = self.process_document(document, cfg)
            result.add_processed_document(processed)

        result.finalize()
        return result

    def process_texts(
        self,
        texts: List[str],
        titles: Optional[List[str]] = None,
        source: Optional[str] = None,
        config: Optional[ProcessorConfig] = None,
    ) -> ProcessingResult:
        """
        Convenience method to process a list of text strings.

        Args:
            texts: List of text contents to process
            titles: Optional list of titles (parallel to texts)
            source: Optional source identifier for all documents
            config: Optional configuration override

        Returns:
            ProcessingResult with all processed documents
        """
        documents = []
        for i, text in enumerate(texts):
            title = titles[i] if titles and i < len(titles) else None
            doc = Document.from_text(text, title=title, source=source)
            documents.append(doc)

        collection = DocumentCollection(
            name=source or "text_collection",
            documents=documents,
        )

        return self.process_collection(collection, config)

    def _generate_embeddings(
        self,
        chunks: List[DocumentChunk],
        config: ProcessorConfig,
    ) -> List[DocumentChunk]:
        """Generate embeddings for chunks in batches."""
        if not self._embedding_provider:
            return chunks

        batch_size = config.embedding_batch_size
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            texts = [chunk.content for chunk in batch]

            try:
                embeddings = self._embedding_provider.create_embeddings(texts)
                for chunk, embedding in zip(batch, embeddings):
                    chunk.embedding = embedding
            except Exception as e:
                logger.warning(f"Failed to generate embeddings for batch: {e}")

        return chunks

    def _create_failed_result(
        self,
        document: Document,
        error_message: str,
        start_time: float,
    ) -> ProcessedDocument:
        """Create a failed processing result."""
        return ProcessedDocument(
            document_id=document.document_id,
            original_document=document,
            extracted_text="",
            chunks=[],
            processing_status=ProcessingStatus.FAILED,
            processing_time_ms=(time.time() - start_time) * 1000,
            error_message=error_message,
        )

    def _report_progress(
        self,
        config: ProcessorConfig,
        stage: str,
        progress: float,
    ) -> None:
        """Report processing progress if callback configured."""
        if config.on_progress:
            try:
                config.on_progress(stage, progress)
            except Exception:
                pass  # Don't let progress reporting break processing

    # Search and retrieval methods

    def search(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.0,
        collection_id: Optional[str] = None,
        use_embeddings: bool = True,
    ) -> SearchResults:
        """
        Search for relevant chunks across processed documents.

        Args:
            query: Search query text
            limit: Maximum number of results
            min_score: Minimum relevance score (0-1)
            collection_id: Optional collection filter
            use_embeddings: Whether to use semantic search

        Returns:
            SearchResults with matching chunks
        """
        if not self._storage:
            return SearchResults()

        search_query = SearchQuery(
            query_text=query,
            limit=limit,
            min_score=min_score,
            collection_id=collection_id,
        )

        # Add embedding if semantic search enabled
        if use_embeddings and self._embedding_provider:
            try:
                search_query.query_embedding = self._embedding_provider.create_embedding(query)
            except Exception as e:
                logger.warning(f"Could not generate query embedding: {e}")

        return self._storage.search(search_query)

    def search_similar(
        self,
        text: str,
        limit: int = 10,
        min_score: float = 0.5,
        exclude_self: bool = True,
    ) -> SearchResults:
        """
        Find chunks similar to the given text.

        Args:
            text: Text to find similar chunks for
            limit: Maximum number of results
            min_score: Minimum similarity score
            exclude_self: Exclude exact matches

        Returns:
            SearchResults with similar chunks
        """
        if not self._storage or not self._embedding_provider:
            return SearchResults()

        try:
            embedding = self._embedding_provider.create_embedding(text)
            return self._storage.search_by_embedding(
                embedding=embedding,
                limit=limit + (1 if exclude_self else 0),
                min_score=min_score,
            )
        except Exception as e:
            logger.warning(f"Similarity search failed: {e}")
            return SearchResults()

    def get_document(self, document_id: str) -> Optional[ProcessedDocument]:
        """
        Retrieve a processed document by ID.

        Args:
            document_id: The document ID

        Returns:
            ProcessedDocument or None if not found
        """
        if not self._storage:
            return None
        return self._storage.get_document(document_id)

    def get_chunk(self, chunk_id: str) -> Optional[DocumentChunk]:
        """
        Retrieve a specific chunk by ID.

        Args:
            chunk_id: The chunk ID

        Returns:
            DocumentChunk or None if not found
        """
        if not self._storage:
            return None
        return self._storage.get_chunk(chunk_id)

    def delete_document(self, document_id: str) -> bool:
        """
        Delete a processed document and its chunks.

        Args:
            document_id: The document ID to delete

        Returns:
            True if deletion successful
        """
        if not self._storage:
            return False
        return self._storage.delete_document(document_id)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get processor and storage statistics.

        Returns:
            Dictionary of statistics
        """
        stats = {
            "processor": {
                "name": self.name,
                "initialized": self._initialized,
                "chunking_strategy": self._config.chunking_strategy.value,
                "embeddings_enabled": self._config.generate_embeddings,
            }
        }

        if self._storage:
            stats["storage"] = self._storage.get_stats()

        if self._embedding_provider:
            stats["embedding_provider"] = self._embedding_provider.name

        return stats


# Convenience function for quick processing
async def process_documents(
    texts: List[str],
    titles: Optional[List[str]] = None,
    **config_kwargs: Any,
) -> ProcessingResult:
    """
    Convenience function to quickly process a list of texts.

    Args:
        texts: List of text contents
        titles: Optional list of titles
        **config_kwargs: Configuration options

    Returns:
        ProcessingResult
    """
    config = ProcessorConfig(**config_kwargs)
    processor = DocumentProcessor(config)
    await processor.initialize()

    return processor.process_texts(texts, titles)
