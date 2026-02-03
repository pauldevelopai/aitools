"""
GROUNDED Document Chunking - Text chunking strategies.

Provides multiple strategies for splitting documents into chunks
suitable for embedding and retrieval.
"""

import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Protocol, runtime_checkable

from grounded.documents.models import DocumentChunk


class ChunkingStrategy(Enum):
    """Available chunking strategies."""

    FIXED_SIZE = "fixed_size"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    SEMANTIC = "semantic"


@dataclass
class ChunkingConfig:
    """Configuration for chunking behavior."""

    strategy: ChunkingStrategy = ChunkingStrategy.FIXED_SIZE
    chunk_size: int = 512  # Target chunk size in characters
    chunk_overlap: int = 50  # Overlap between chunks
    min_chunk_size: int = 100  # Minimum chunk size
    max_chunk_size: int = 1000  # Maximum chunk size
    preserve_sentences: bool = True  # Try not to break mid-sentence
    preserve_paragraphs: bool = False  # Try not to break mid-paragraph

    def __post_init__(self):
        """Validate configuration."""
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        if self.min_chunk_size > self.chunk_size:
            raise ValueError("min_chunk_size must not exceed chunk_size")


@runtime_checkable
class ChunkerProtocol(Protocol):
    """Protocol for text chunkers."""

    def chunk(
        self,
        text: str,
        document_id: str,
        config: Optional[ChunkingConfig] = None,
    ) -> List[DocumentChunk]:
        """Split text into chunks."""
        ...


class BaseChunker(ABC):
    """
    Base class for text chunkers.

    Provides common functionality for splitting text into chunks.
    """

    def __init__(self, config: Optional[ChunkingConfig] = None):
        """
        Initialize the chunker.

        Args:
            config: Chunking configuration (uses defaults if not provided)
        """
        self.config = config or ChunkingConfig()

    @abstractmethod
    def chunk(
        self,
        text: str,
        document_id: str,
        config: Optional[ChunkingConfig] = None,
    ) -> List[DocumentChunk]:
        """
        Split text into chunks.

        Args:
            text: The text to chunk
            document_id: ID of the source document
            config: Optional override configuration

        Returns:
            List of DocumentChunk instances
        """
        ...

    def _create_chunk(
        self,
        content: str,
        document_id: str,
        chunk_index: int,
        start_char: int,
        end_char: int,
    ) -> DocumentChunk:
        """
        Create a DocumentChunk instance.

        Args:
            content: Chunk text content
            document_id: Source document ID
            chunk_index: Index of this chunk
            start_char: Start character position in original text
            end_char: End character position in original text

        Returns:
            DocumentChunk instance
        """
        return DocumentChunk(
            chunk_id=str(uuid.uuid4()),
            document_id=document_id,
            content=content,
            chunk_index=chunk_index,
            start_char=start_char,
            end_char=end_char,
        )


class FixedSizeChunker(BaseChunker):
    """
    Chunks text into fixed-size segments with optional overlap.

    The most basic chunking strategy, suitable when document structure
    is not important or unknown.
    """

    def chunk(
        self,
        text: str,
        document_id: str,
        config: Optional[ChunkingConfig] = None,
    ) -> List[DocumentChunk]:
        """Split text into fixed-size chunks with overlap."""
        cfg = config or self.config
        chunks: List[DocumentChunk] = []

        if not text.strip():
            return chunks

        text_length = len(text)
        start = 0
        chunk_index = 0

        while start < text_length:
            # Calculate end position
            end = min(start + cfg.chunk_size, text_length)

            # If preserving sentences, try to end at sentence boundary
            if cfg.preserve_sentences and end < text_length:
                end = self._find_sentence_boundary(text, start, end, cfg)

            # Extract chunk content
            content = text[start:end].strip()

            # Only create chunk if it meets minimum size (except for last chunk)
            if len(content) >= cfg.min_chunk_size or start + cfg.chunk_size >= text_length:
                if content:  # Don't create empty chunks
                    chunks.append(
                        self._create_chunk(content, document_id, chunk_index, start, end)
                    )
                    chunk_index += 1

            # Move to next position with overlap
            start = end - cfg.chunk_overlap
            if start <= chunks[-1].start_char if chunks else 0:
                # Prevent infinite loop
                start = end

        return chunks

    def _find_sentence_boundary(
        self,
        text: str,
        start: int,
        end: int,
        config: ChunkingConfig,
    ) -> int:
        """
        Find a sentence boundary near the end position.

        Args:
            text: Full text
            start: Chunk start position
            end: Target end position
            config: Chunking configuration

        Returns:
            Adjusted end position at sentence boundary
        """
        # Look for sentence endings within a window
        window_start = max(start + config.min_chunk_size, end - 100)
        window = text[window_start:end]

        # Find last sentence boundary in window
        sentence_ends = []
        for match in re.finditer(r'[.!?]+\s+', window):
            sentence_ends.append(window_start + match.end())

        if sentence_ends:
            return sentence_ends[-1]

        return end


class SentenceChunker(BaseChunker):
    """
    Chunks text by sentences, grouping sentences to meet size targets.

    Preserves sentence integrity while creating appropriately sized chunks.
    """

    def chunk(
        self,
        text: str,
        document_id: str,
        config: Optional[ChunkingConfig] = None,
    ) -> List[DocumentChunk]:
        """Split text into sentence-based chunks."""
        cfg = config or self.config
        chunks: List[DocumentChunk] = []

        if not text.strip():
            return chunks

        # Split into sentences
        sentences = self._split_sentences(text)

        current_chunk_sentences: List[str] = []
        current_start = 0
        current_length = 0
        chunk_index = 0

        for sentence, sent_start, sent_end in sentences:
            sentence_length = len(sentence)

            # Check if adding this sentence would exceed max size
            would_exceed = current_length + sentence_length > cfg.max_chunk_size

            # If current chunk is big enough and adding would exceed, finalize it
            if current_chunk_sentences and would_exceed and current_length >= cfg.min_chunk_size:
                content = " ".join(current_chunk_sentences)
                chunks.append(
                    self._create_chunk(
                        content, document_id, chunk_index, current_start, sent_start
                    )
                )
                chunk_index += 1

                # Start new chunk (with overlap from previous sentences)
                overlap_sentences = self._get_overlap_sentences(
                    current_chunk_sentences, cfg.chunk_overlap
                )
                current_chunk_sentences = overlap_sentences
                current_start = sent_start - sum(len(s) + 1 for s in overlap_sentences)
                current_length = sum(len(s) + 1 for s in overlap_sentences)

            current_chunk_sentences.append(sentence)
            current_length += sentence_length + 1  # +1 for space

        # Don't forget the last chunk
        if current_chunk_sentences:
            content = " ".join(current_chunk_sentences)
            chunks.append(
                self._create_chunk(
                    content, document_id, chunk_index, current_start, len(text)
                )
            )

        return chunks

    def _split_sentences(self, text: str) -> List[tuple]:
        """
        Split text into sentences with positions.

        Returns:
            List of (sentence, start_pos, end_pos) tuples
        """
        sentences = []
        # Pattern for sentence boundaries
        pattern = r'(?<=[.!?])\s+'

        last_end = 0
        for match in re.finditer(pattern, text):
            sentence = text[last_end:match.start() + 1].strip()
            if sentence:
                sentences.append((sentence, last_end, match.end()))
            last_end = match.end()

        # Add final sentence
        final = text[last_end:].strip()
        if final:
            sentences.append((final, last_end, len(text)))

        return sentences

    def _get_overlap_sentences(
        self,
        sentences: List[str],
        overlap_chars: int,
    ) -> List[str]:
        """Get sentences for overlap from the end of current chunk."""
        if not sentences or overlap_chars <= 0:
            return []

        overlap_sentences = []
        char_count = 0

        for sentence in reversed(sentences):
            if char_count >= overlap_chars:
                break
            overlap_sentences.insert(0, sentence)
            char_count += len(sentence) + 1

        return overlap_sentences


class ParagraphChunker(BaseChunker):
    """
    Chunks text by paragraphs, grouping paragraphs to meet size targets.

    Best for documents with clear paragraph structure.
    """

    def chunk(
        self,
        text: str,
        document_id: str,
        config: Optional[ChunkingConfig] = None,
    ) -> List[DocumentChunk]:
        """Split text into paragraph-based chunks."""
        cfg = config or self.config
        chunks: List[DocumentChunk] = []

        if not text.strip():
            return chunks

        # Split into paragraphs (double newline)
        paragraphs = self._split_paragraphs(text)

        current_paragraphs: List[str] = []
        current_start = 0
        current_length = 0
        chunk_index = 0

        for para, para_start, para_end in paragraphs:
            para_length = len(para)

            # Check if adding this paragraph would exceed max size
            would_exceed = current_length + para_length > cfg.max_chunk_size

            # If current chunk is big enough and adding would exceed, finalize it
            if current_paragraphs and would_exceed and current_length >= cfg.min_chunk_size:
                content = "\n\n".join(current_paragraphs)
                chunks.append(
                    self._create_chunk(
                        content, document_id, chunk_index, current_start, para_start
                    )
                )
                chunk_index += 1

                # Start new chunk
                current_paragraphs = []
                current_start = para_start
                current_length = 0

            current_paragraphs.append(para)
            current_length += para_length + 2  # +2 for \n\n

        # Don't forget the last chunk
        if current_paragraphs:
            content = "\n\n".join(current_paragraphs)
            chunks.append(
                self._create_chunk(
                    content, document_id, chunk_index, current_start, len(text)
                )
            )

        return chunks

    def _split_paragraphs(self, text: str) -> List[tuple]:
        """
        Split text into paragraphs with positions.

        Returns:
            List of (paragraph, start_pos, end_pos) tuples
        """
        paragraphs = []
        pattern = r'\n\n+'

        last_end = 0
        for match in re.finditer(pattern, text):
            para = text[last_end:match.start()].strip()
            if para:
                paragraphs.append((para, last_end, match.start()))
            last_end = match.end()

        # Add final paragraph
        final = text[last_end:].strip()
        if final:
            paragraphs.append((final, last_end, len(text)))

        return paragraphs


class SemanticChunker(BaseChunker):
    """
    Chunks text based on semantic boundaries.

    Uses heuristics to detect topic shifts and natural break points.
    This is a simplified version - a full implementation would use
    embeddings to detect semantic similarity.
    """

    def __init__(
        self,
        config: Optional[ChunkingConfig] = None,
        section_markers: Optional[List[str]] = None,
    ):
        """
        Initialize the semantic chunker.

        Args:
            config: Chunking configuration
            section_markers: Patterns that indicate section boundaries
        """
        super().__init__(config)
        self._section_markers = section_markers or [
            r'^#{1,6}\s+',  # Markdown headers
            r'^[A-Z][^.!?]*:$',  # Title-like lines ending with colon
            r'^\d+\.\s+[A-Z]',  # Numbered sections
            r'^[IVX]+\.\s+',  # Roman numeral sections
        ]

    def chunk(
        self,
        text: str,
        document_id: str,
        config: Optional[ChunkingConfig] = None,
    ) -> List[DocumentChunk]:
        """Split text at semantic boundaries."""
        cfg = config or self.config
        chunks: List[DocumentChunk] = []

        if not text.strip():
            return chunks

        # Find semantic boundaries
        boundaries = self._find_semantic_boundaries(text)

        # Create chunks between boundaries
        chunk_index = 0
        for i, (start, end) in enumerate(boundaries):
            content = text[start:end].strip()

            if not content:
                continue

            # If content is too large, use sentence chunking within it
            if len(content) > cfg.max_chunk_size:
                sentence_chunker = SentenceChunker(cfg)
                sub_chunks = sentence_chunker.chunk(content, document_id, cfg)

                # Adjust positions and indices
                for sub_chunk in sub_chunks:
                    sub_chunk.start_char += start
                    sub_chunk.end_char += start
                    sub_chunk.chunk_index = chunk_index
                    chunk_index += 1
                    chunks.append(sub_chunk)
            elif len(content) >= cfg.min_chunk_size:
                chunks.append(
                    self._create_chunk(content, document_id, chunk_index, start, end)
                )
                chunk_index += 1
            elif chunks:
                # Merge small chunk with previous
                prev_chunk = chunks[-1]
                merged_content = prev_chunk.content + "\n\n" + content
                prev_chunk.content = merged_content
                prev_chunk.end_char = end

        return chunks

    def _find_semantic_boundaries(self, text: str) -> List[tuple]:
        """
        Find semantic boundaries in text.

        Returns:
            List of (start, end) position tuples
        """
        boundaries = [(0, 0)]  # Will update first end

        # Find all section markers
        for pattern in self._section_markers:
            for match in re.finditer(pattern, text, re.MULTILINE):
                # Section starts at the beginning of the line containing the match
                line_start = text.rfind('\n', 0, match.start()) + 1
                boundaries.append((line_start, 0))

        # Also split on double newlines if they're followed by capital letters
        for match in re.finditer(r'\n\n+(?=[A-Z])', text):
            boundaries.append((match.end(), 0))

        # Sort and deduplicate boundaries
        boundary_starts = sorted(set(b[0] for b in boundaries))

        # Create proper (start, end) tuples
        result = []
        for i, start in enumerate(boundary_starts):
            if i + 1 < len(boundary_starts):
                end = boundary_starts[i + 1]
            else:
                end = len(text)
            result.append((start, end))

        return result


def get_chunker(strategy: ChunkingStrategy, config: Optional[ChunkingConfig] = None) -> BaseChunker:
    """
    Get a chunker for the specified strategy.

    Args:
        strategy: The chunking strategy to use
        config: Optional configuration

    Returns:
        Appropriate chunker instance
    """
    chunkers = {
        ChunkingStrategy.FIXED_SIZE: FixedSizeChunker,
        ChunkingStrategy.SENTENCE: SentenceChunker,
        ChunkingStrategy.PARAGRAPH: ParagraphChunker,
        ChunkingStrategy.SEMANTIC: SemanticChunker,
    }
    chunker_class = chunkers.get(strategy, FixedSizeChunker)
    return chunker_class(config)
