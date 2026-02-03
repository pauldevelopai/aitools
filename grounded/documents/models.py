"""
GROUNDED Document Intelligence - Data Models.

Defines the core data structures for document processing including
Document, DocumentChunk, DocumentCollection, and ProcessingResult.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import hashlib
import uuid


class DocumentType(Enum):
    """Supported document types."""

    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    UNKNOWN = "unknown"


class ProcessingStatus(Enum):
    """Status of document processing."""

    PENDING = "pending"
    EXTRACTING = "extracting"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DocumentMetadata:
    """Metadata associated with a document."""

    title: Optional[str] = None
    author: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    language: str = "en"
    tags: List[str] = field(default_factory=list)
    custom: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "author": self.author,
            "source": self.source,
            "source_url": self.source_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "language": self.language,
            "tags": self.tags,
            "custom": self.custom,
        }


@dataclass
class Document:
    """
    A document to be processed by the Document Intelligence service.

    Documents are the input to the processing pipeline. They contain
    raw content that will be extracted, chunked, and embedded.
    """

    content: str
    document_type: DocumentType = DocumentType.TEXT
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    document_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Generate content hash after initialization."""
        self._content_hash = hashlib.sha256(self.content.encode("utf-8")).hexdigest()

    @property
    def content_hash(self) -> str:
        """SHA-256 hash of document content for deduplication."""
        return self._content_hash

    @property
    def character_count(self) -> int:
        """Number of characters in the document."""
        return len(self.content)

    @property
    def word_count(self) -> int:
        """Approximate word count."""
        return len(self.content.split())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "document_id": self.document_id,
            "document_type": self.document_type.value,
            "content_hash": self.content_hash,
            "character_count": self.character_count,
            "word_count": self.word_count,
            "metadata": self.metadata.to_dict(),
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_text(
        cls,
        text: str,
        title: Optional[str] = None,
        source: Optional[str] = None,
        **metadata_kwargs: Any,
    ) -> "Document":
        """
        Create a Document from plain text.

        Args:
            text: The document text content
            title: Optional document title
            source: Optional source identifier
            **metadata_kwargs: Additional metadata fields

        Returns:
            Document instance
        """
        metadata = DocumentMetadata(title=title, source=source, **metadata_kwargs)
        return cls(content=text, document_type=DocumentType.TEXT, metadata=metadata)

    @classmethod
    def from_markdown(
        cls,
        markdown: str,
        title: Optional[str] = None,
        source: Optional[str] = None,
        **metadata_kwargs: Any,
    ) -> "Document":
        """
        Create a Document from markdown content.

        Args:
            markdown: The markdown content
            title: Optional document title
            source: Optional source identifier
            **metadata_kwargs: Additional metadata fields

        Returns:
            Document instance
        """
        metadata = DocumentMetadata(title=title, source=source, **metadata_kwargs)
        return cls(content=markdown, document_type=DocumentType.MARKDOWN, metadata=metadata)


@dataclass
class DocumentChunk:
    """
    A chunk of a processed document.

    Chunks are the unit of storage and retrieval. Each chunk contains
    a portion of the original document text along with its embedding
    and positional information.
    """

    chunk_id: str
    document_id: str
    content: str
    chunk_index: int
    start_char: int
    end_char: int
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def has_embedding(self) -> bool:
        """Check if this chunk has an embedding."""
        return self.embedding is not None and len(self.embedding) > 0

    @property
    def character_count(self) -> int:
        """Number of characters in this chunk."""
        return len(self.content)

    @property
    def word_count(self) -> int:
        """Approximate word count in this chunk."""
        return len(self.content.split())

    def to_dict(self, include_embedding: bool = False) -> Dict[str, Any]:
        """
        Convert to dictionary representation.

        Args:
            include_embedding: Whether to include the embedding vector

        Returns:
            Dictionary representation
        """
        result = {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "content": self.content,
            "chunk_index": self.chunk_index,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "has_embedding": self.has_embedding,
            "character_count": self.character_count,
            "word_count": self.word_count,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }
        if include_embedding and self.embedding:
            result["embedding"] = self.embedding
        return result


@dataclass
class ProcessedDocument:
    """
    A fully processed document with extracted text and chunks.

    This is the output of the document processing pipeline, containing
    the original document reference, extracted text, and all chunks.
    """

    document_id: str
    original_document: Document
    extracted_text: str
    chunks: List[DocumentChunk] = field(default_factory=list)
    processing_status: ProcessingStatus = ProcessingStatus.COMPLETED
    processing_time_ms: float = 0.0
    error_message: Optional[str] = None
    processed_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def chunk_count(self) -> int:
        """Number of chunks in this document."""
        return len(self.chunks)

    @property
    def has_embeddings(self) -> bool:
        """Check if all chunks have embeddings."""
        return all(chunk.has_embedding for chunk in self.chunks)

    @property
    def embedding_count(self) -> int:
        """Number of chunks with embeddings."""
        return sum(1 for chunk in self.chunks if chunk.has_embedding)

    def get_chunk(self, chunk_index: int) -> Optional[DocumentChunk]:
        """Get a chunk by index."""
        for chunk in self.chunks:
            if chunk.chunk_index == chunk_index:
                return chunk
        return None

    def to_dict(self, include_chunks: bool = True, include_embeddings: bool = False) -> Dict[str, Any]:
        """
        Convert to dictionary representation.

        Args:
            include_chunks: Whether to include chunk details
            include_embeddings: Whether to include embedding vectors

        Returns:
            Dictionary representation
        """
        result = {
            "document_id": self.document_id,
            "original_document": self.original_document.to_dict(),
            "extracted_text_length": len(self.extracted_text),
            "chunk_count": self.chunk_count,
            "has_embeddings": self.has_embeddings,
            "embedding_count": self.embedding_count,
            "processing_status": self.processing_status.value,
            "processing_time_ms": self.processing_time_ms,
            "error_message": self.error_message,
            "processed_at": self.processed_at.isoformat(),
        }
        if include_chunks:
            result["chunks"] = [
                chunk.to_dict(include_embedding=include_embeddings) for chunk in self.chunks
            ]
        return result


@dataclass
class DocumentCollection:
    """
    A collection of documents for batch processing.

    Collections allow grouping related documents together for
    processing, storage, and retrieval.
    """

    collection_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    documents: List[Document] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def document_count(self) -> int:
        """Number of documents in this collection."""
        return len(self.documents)

    @property
    def total_characters(self) -> int:
        """Total characters across all documents."""
        return sum(doc.character_count for doc in self.documents)

    @property
    def total_words(self) -> int:
        """Total words across all documents."""
        return sum(doc.word_count for doc in self.documents)

    def add_document(self, document: Document) -> None:
        """Add a document to the collection."""
        self.documents.append(document)

    def add_documents(self, documents: List[Document]) -> None:
        """Add multiple documents to the collection."""
        self.documents.extend(documents)

    def get_document(self, document_id: str) -> Optional[Document]:
        """Get a document by ID."""
        for doc in self.documents:
            if doc.document_id == document_id:
                return doc
        return None

    def remove_document(self, document_id: str) -> bool:
        """Remove a document by ID. Returns True if found and removed."""
        for i, doc in enumerate(self.documents):
            if doc.document_id == document_id:
                self.documents.pop(i)
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "collection_id": self.collection_id,
            "name": self.name,
            "description": self.description,
            "document_count": self.document_count,
            "total_characters": self.total_characters,
            "total_words": self.total_words,
            "documents": [doc.to_dict() for doc in self.documents],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ProcessingResult:
    """
    Result of processing a document or collection.

    Contains summary statistics and references to processed documents.
    """

    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    processed_documents: List[ProcessedDocument] = field(default_factory=list)
    total_documents: int = 0
    successful_count: int = 0
    failed_count: int = 0
    total_chunks: int = 0
    total_embeddings: int = 0
    total_processing_time_ms: float = 0.0
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    errors: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_documents == 0:
            return 0.0
        return (self.successful_count / self.total_documents) * 100

    @property
    def is_complete(self) -> bool:
        """Check if processing is complete."""
        return self.completed_at is not None

    def add_processed_document(self, doc: ProcessedDocument) -> None:
        """Add a processed document to results."""
        self.processed_documents.append(doc)
        self.total_documents += 1
        self.total_processing_time_ms += doc.processing_time_ms

        if doc.processing_status == ProcessingStatus.COMPLETED:
            self.successful_count += 1
            self.total_chunks += doc.chunk_count
            self.total_embeddings += doc.embedding_count
        else:
            self.failed_count += 1
            if doc.error_message:
                self.errors.append({
                    "document_id": doc.document_id,
                    "error": doc.error_message,
                })

    def finalize(self) -> None:
        """Mark processing as complete."""
        self.completed_at = datetime.utcnow()

    def to_dict(self, include_documents: bool = False) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "result_id": self.result_id,
            "total_documents": self.total_documents,
            "successful_count": self.successful_count,
            "failed_count": self.failed_count,
            "success_rate": self.success_rate,
            "total_chunks": self.total_chunks,
            "total_embeddings": self.total_embeddings,
            "total_processing_time_ms": self.total_processing_time_ms,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "is_complete": self.is_complete,
            "errors": self.errors,
        }
        if include_documents:
            result["processed_documents"] = [
                doc.to_dict(include_chunks=True) for doc in self.processed_documents
            ]
        return result
