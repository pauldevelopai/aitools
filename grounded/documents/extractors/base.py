"""
GROUNDED Document Extractor Base - Protocol and base class for extractors.

Defines the interface for document text extraction, enabling pluggable
extractors for different document formats.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from grounded.core.base import GroundedComponent
from grounded.documents.models import Document, DocumentType


@dataclass
class ExtractionResult:
    """Result of text extraction from a document."""

    extracted_text: str
    success: bool = True
    error_message: Optional[str] = None
    metadata_updates: Dict[str, Any] = field(default_factory=dict)
    sections: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def character_count(self) -> int:
        """Number of characters in extracted text."""
        return len(self.extracted_text)

    @property
    def word_count(self) -> int:
        """Approximate word count in extracted text."""
        return len(self.extracted_text.split())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "success": self.success,
            "character_count": self.character_count,
            "word_count": self.word_count,
            "error_message": self.error_message,
            "metadata_updates": self.metadata_updates,
            "section_count": len(self.sections),
            "warnings": self.warnings,
        }


@runtime_checkable
class ExtractorProtocol(Protocol):
    """
    Protocol for document extractors.

    Any class implementing this protocol can extract text from documents.
    """

    @property
    def name(self) -> str:
        """Extractor name identifier."""
        ...

    @property
    def supported_types(self) -> List[DocumentType]:
        """List of document types this extractor supports."""
        ...

    def supports(self, document_type: DocumentType) -> bool:
        """Check if this extractor supports the given document type."""
        ...

    def extract(self, document: Document) -> ExtractionResult:
        """
        Extract text from a document.

        Args:
            document: The document to extract text from

        Returns:
            ExtractionResult with extracted text
        """
        ...


class BaseExtractor(GroundedComponent, ABC):
    """
    Base class for document extractors.

    Extends GroundedComponent to add extraction-specific utilities.
    Concrete extractors should inherit from this class.

    Example:
        class PDFExtractor(BaseExtractor):
            @property
            def name(self) -> str:
                return "pdf_extractor"

            @property
            def supported_types(self) -> List[DocumentType]:
                return [DocumentType.PDF]

            def extract(self, document: Document) -> ExtractionResult:
                # PDF extraction logic
                text = extract_pdf_text(document.content)
                return ExtractionResult(extracted_text=text)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Extractor name identifier."""
        ...

    @property
    @abstractmethod
    def supported_types(self) -> List[DocumentType]:
        """List of document types this extractor supports."""
        ...

    def supports(self, document_type: DocumentType) -> bool:
        """
        Check if this extractor supports the given document type.

        Args:
            document_type: The document type to check

        Returns:
            True if this extractor can handle the document type
        """
        return document_type in self.supported_types

    @abstractmethod
    def extract(self, document: Document) -> ExtractionResult:
        """
        Extract text from a document.

        Args:
            document: The document to extract text from

        Returns:
            ExtractionResult with extracted text
        """
        ...

    def preprocess(self, content: str) -> str:
        """
        Preprocess content before extraction.

        Override to add custom preprocessing logic.

        Args:
            content: Raw document content

        Returns:
            Preprocessed content
        """
        return content

    def postprocess(self, text: str) -> str:
        """
        Postprocess extracted text.

        Override to add custom postprocessing logic.

        Args:
            text: Extracted text

        Returns:
            Postprocessed text
        """
        # Default: normalize whitespace
        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            # Collapse multiple spaces
            cleaned = " ".join(line.split())
            cleaned_lines.append(cleaned)

        # Collapse multiple blank lines
        result_lines = []
        prev_blank = False
        for line in cleaned_lines:
            is_blank = len(line.strip()) == 0
            if is_blank and prev_blank:
                continue
            result_lines.append(line)
            prev_blank = is_blank

        return "\n".join(result_lines).strip()
