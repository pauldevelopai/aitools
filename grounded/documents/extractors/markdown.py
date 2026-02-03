"""
GROUNDED Document Extractor - Markdown.

Extracts text from markdown documents, preserving structure information
and handling common markdown elements.
"""

import re
from typing import Any, Dict, List

from grounded.documents.extractors.base import BaseExtractor, ExtractionResult
from grounded.documents.models import Document, DocumentType


class MarkdownExtractor(BaseExtractor):
    """
    Extractor for Markdown documents.

    Handles markdown-specific elements:
    - Headers (extracts title from first H1)
    - Code blocks (preserves or removes based on config)
    - Links (extracts text, optionally preserves URLs)
    - Lists (normalizes formatting)
    - Emphasis (removes markdown syntax)
    """

    def __init__(
        self,
        preserve_code_blocks: bool = True,
        preserve_links: bool = False,
        extract_title_from_h1: bool = True,
    ):
        """
        Initialize the markdown extractor.

        Args:
            preserve_code_blocks: Keep code block content in output
            preserve_links: Keep URL references in output
            extract_title_from_h1: Extract first H1 as document title
        """
        self._preserve_code_blocks = preserve_code_blocks
        self._preserve_links = preserve_links
        self._extract_title = extract_title_from_h1

    @property
    def name(self) -> str:
        return "markdown_extractor"

    @property
    def supported_types(self) -> List[DocumentType]:
        return [DocumentType.MARKDOWN]

    def extract(self, document: Document) -> ExtractionResult:
        """
        Extract text from a markdown document.

        Args:
            document: The document to extract from

        Returns:
            ExtractionResult with extracted text and structure
        """
        try:
            content = self.preprocess(document.content)

            # Extract structure
            sections = self._extract_sections(content)

            # Extract metadata updates
            metadata_updates: Dict[str, Any] = {}
            if self._extract_title:
                title = self._extract_title_from_content(content)
                if title:
                    metadata_updates["title"] = title

            # Convert to plain text
            extracted_text = self._markdown_to_text(content)

            # Postprocess
            extracted_text = self.postprocess(extracted_text)

            return ExtractionResult(
                extracted_text=extracted_text,
                success=True,
                sections=sections,
                metadata_updates=metadata_updates,
            )

        except Exception as e:
            return ExtractionResult(
                extracted_text="",
                success=False,
                error_message=str(e),
            )

    def _extract_title_from_content(self, content: str) -> str | None:
        """Extract title from first H1 heading."""
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_sections(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract document sections based on headers.

        Args:
            content: Markdown content

        Returns:
            List of section dictionaries
        """
        sections = []
        header_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

        for match in header_pattern.finditer(content):
            level = len(match.group(1))
            title = match.group(2).strip()
            sections.append({
                "type": "header",
                "level": level,
                "title": title,
                "start_char": match.start(),
                "end_char": match.end(),
            })

        return sections

    def _markdown_to_text(self, content: str) -> str:
        """
        Convert markdown to plain text.

        Args:
            content: Markdown content

        Returns:
            Plain text content
        """
        text = content

        # Handle code blocks
        if self._preserve_code_blocks:
            # Keep code content but remove fence markers
            text = re.sub(r"```[\w]*\n", "\n", text)
            text = re.sub(r"```", "", text)
        else:
            # Remove code blocks entirely
            text = re.sub(r"```[\w]*\n.*?```", "", text, flags=re.DOTALL)

        # Remove inline code backticks but keep content
        text = re.sub(r"`([^`]+)`", r"\1", text)

        # Handle links
        if self._preserve_links:
            # Convert [text](url) to "text (url)"
            text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
        else:
            # Keep just the link text
            text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

        # Handle images - remove or keep alt text
        text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)

        # Remove emphasis markers but keep text
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)  # Bold
        text = re.sub(r"\*([^*]+)\*", r"\1", text)  # Italic
        text = re.sub(r"__([^_]+)__", r"\1", text)  # Bold
        text = re.sub(r"_([^_]+)_", r"\1", text)  # Italic
        text = re.sub(r"~~([^~]+)~~", r"\1", text)  # Strikethrough

        # Convert headers to plain text (keep the text)
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

        # Convert horizontal rules to blank lines
        text = re.sub(r"^[-*_]{3,}\s*$", "\n", text, flags=re.MULTILINE)

        # Normalize list markers
        text = re.sub(r"^\s*[-*+]\s+", "• ", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)

        # Remove blockquote markers
        text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)

        # Clean up HTML comments
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

        # Clean up HTML tags (basic)
        text = re.sub(r"<[^>]+>", "", text)

        return text
