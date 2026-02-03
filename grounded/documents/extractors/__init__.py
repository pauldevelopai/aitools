"""
GROUNDED Document Extractors - Text extraction from various formats.

Provides a protocol-based framework for extracting text from different
document formats (text, markdown, HTML, PDF, etc.).
"""

from grounded.documents.extractors.base import (
    BaseExtractor,
    ExtractorProtocol,
    ExtractionResult,
)
from grounded.documents.extractors.text import PlainTextExtractor
from grounded.documents.extractors.markdown import MarkdownExtractor
from grounded.core.base import Registry

# Global extractor registry
extractor_registry: Registry[BaseExtractor] = Registry(name="document_extractors")


def register_default_extractors() -> None:
    """Register the default set of extractors."""
    extractor_registry.register("text", PlainTextExtractor(), set_as_default=True)
    extractor_registry.register("markdown", MarkdownExtractor())


def get_extractor(document_type: str) -> BaseExtractor:
    """
    Get an extractor for the given document type.

    Args:
        document_type: The document type (text, markdown, etc.)

    Returns:
        Appropriate extractor instance

    Raises:
        KeyError: If no extractor for the document type
    """
    # Map document types to extractor keys
    type_mapping = {
        "text": "text",
        "markdown": "markdown",
        "md": "markdown",
        "html": "text",  # Fallback to text for now
        "unknown": "text",
    }
    extractor_key = type_mapping.get(document_type, "text")
    return extractor_registry.get_or_raise(extractor_key)


__all__ = [
    "BaseExtractor",
    "ExtractorProtocol",
    "ExtractionResult",
    "PlainTextExtractor",
    "MarkdownExtractor",
    "extractor_registry",
    "register_default_extractors",
    "get_extractor",
]
