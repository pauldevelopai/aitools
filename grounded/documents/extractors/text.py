"""
GROUNDED Document Extractor - Plain Text.

Extracts and normalizes text from plain text documents.
"""

from typing import List

from grounded.documents.extractors.base import BaseExtractor, ExtractionResult
from grounded.documents.models import Document, DocumentType


class PlainTextExtractor(BaseExtractor):
    """
    Extractor for plain text documents.

    Handles text normalization, whitespace cleanup, and basic
    structure detection (paragraphs).
    """

    @property
    def name(self) -> str:
        return "plain_text_extractor"

    @property
    def supported_types(self) -> List[DocumentType]:
        return [DocumentType.TEXT, DocumentType.UNKNOWN]

    def extract(self, document: Document) -> ExtractionResult:
        """
        Extract and normalize text from a plain text document.

        Args:
            document: The document to extract from

        Returns:
            ExtractionResult with cleaned text
        """
        try:
            # Preprocess
            content = self.preprocess(document.content)

            # Detect paragraphs as sections
            sections = self._detect_paragraphs(content)

            # Postprocess
            extracted_text = self.postprocess(content)

            return ExtractionResult(
                extracted_text=extracted_text,
                success=True,
                sections=sections,
            )

        except Exception as e:
            return ExtractionResult(
                extracted_text="",
                success=False,
                error_message=str(e),
            )

    def _detect_paragraphs(self, text: str) -> List[dict]:
        """
        Detect paragraphs in the text.

        Args:
            text: The text to analyze

        Returns:
            List of section dictionaries
        """
        sections = []
        paragraphs = text.split("\n\n")

        char_offset = 0
        for i, para in enumerate(paragraphs):
            para_stripped = para.strip()
            if para_stripped:
                sections.append({
                    "type": "paragraph",
                    "index": i,
                    "content": para_stripped,
                    "start_char": char_offset,
                    "end_char": char_offset + len(para),
                })
            char_offset += len(para) + 2  # +2 for \n\n

        return sections
