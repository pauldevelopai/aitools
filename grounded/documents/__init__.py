"""
GROUNDED Document Intelligence - Reusable document processing service.

A shared AI capability for document processing, providing:
- Text extraction from multiple formats
- Semantic chunking for optimal retrieval
- Embedding generation for vector search
- Storage and search infrastructure

This module is designed to be used by any application or partner
without being tied to any specific workflow or UI.

Quick Start:
    from grounded.documents import DocumentProcessor, Document

    # Initialize processor
    processor = DocumentProcessor()
    await processor.initialize()

    # Process a document
    doc = Document.from_text("Your document text...", title="My Document")
    processed = processor.process_document(doc)

    # Search processed documents
    results = processor.search("relevant query")

    # Access results
    for result in results.results:
        print(f"Score: {result.score}, Content: {result.chunk.content}")

Working with Collections:
    from grounded.documents import DocumentCollection

    collection = DocumentCollection(name="Research Papers")
    collection.add_document(doc1)
    collection.add_document(doc2)

    result = processor.process_collection(collection)
    print(f"Processed {result.successful_count} documents")

Custom Configuration:
    from grounded.documents import ProcessorConfig, ChunkingStrategy

    config = ProcessorConfig(
        chunking_strategy=ChunkingStrategy.SEMANTIC,
        chunk_size=1000,
        generate_embeddings=True,
    )
    processor = DocumentProcessor(config)
"""

# Models
from grounded.documents.models import (
    Document,
    DocumentChunk,
    DocumentCollection,
    DocumentMetadata,
    DocumentType,
    ProcessedDocument,
    ProcessingResult,
    ProcessingStatus,
)

# Processor
from grounded.documents.processor import (
    DocumentProcessor,
    ProcessorConfig,
    process_documents,
)

# Chunking
from grounded.documents.chunking import (
    ChunkingConfig,
    ChunkingStrategy,
    BaseChunker,
    FixedSizeChunker,
    SentenceChunker,
    ParagraphChunker,
    SemanticChunker,
    get_chunker,
)

# Extractors
from grounded.documents.extractors import (
    BaseExtractor,
    ExtractionResult,
    PlainTextExtractor,
    MarkdownExtractor,
    extractor_registry,
    register_default_extractors,
    get_extractor,
)

# Storage
from grounded.documents.storage import (
    BaseDocumentStorage,
    SearchQuery,
    SearchResult,
    SearchResults,
    InMemoryDocumentStorage,
    storage_registry,
    register_default_storage,
    get_storage,
)

__all__ = [
    # Models
    "Document",
    "DocumentChunk",
    "DocumentCollection",
    "DocumentMetadata",
    "DocumentType",
    "ProcessedDocument",
    "ProcessingResult",
    "ProcessingStatus",
    # Processor
    "DocumentProcessor",
    "ProcessorConfig",
    "process_documents",
    # Chunking
    "ChunkingConfig",
    "ChunkingStrategy",
    "BaseChunker",
    "FixedSizeChunker",
    "SentenceChunker",
    "ParagraphChunker",
    "SemanticChunker",
    "get_chunker",
    # Extractors
    "BaseExtractor",
    "ExtractionResult",
    "PlainTextExtractor",
    "MarkdownExtractor",
    "extractor_registry",
    "register_default_extractors",
    "get_extractor",
    # Storage
    "BaseDocumentStorage",
    "SearchQuery",
    "SearchResult",
    "SearchResults",
    "InMemoryDocumentStorage",
    "storage_registry",
    "register_default_storage",
    "get_storage",
]
