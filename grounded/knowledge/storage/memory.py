"""
GROUNDED Knowledge Storage - In-Memory Backend.

Provides an in-memory storage implementation for development and testing.
Supports full-text search and vector similarity search with tenant isolation.
"""

import math
import re
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from grounded.core.base import ComponentStatus, HealthCheckResult
from grounded.knowledge.models import (
    KnowledgeBase,
    KnowledgeSource,
    KnowledgeItem,
    KnowledgeQuery,
    KnowledgeItemStatus,
    RetrievalResult,
    RetrievalResults,
)
from grounded.knowledge.storage.base import BaseKnowledgeStorage


class InMemoryKnowledgeStorage(BaseKnowledgeStorage):
    """
    In-memory storage backend for knowledge management.

    Suitable for development, testing, and small-scale deployments.
    Data is not persisted across restarts.

    Features:
    - Full tenant isolation via base_id
    - Full-text search with basic ranking
    - Vector similarity search (cosine similarity)
    - Thread-safe operations (basic)
    """

    def __init__(self):
        """Initialize the in-memory storage."""
        # Knowledge bases indexed by base_id
        self._knowledge_bases: Dict[str, KnowledgeBase] = {}

        # Sources indexed by source_id, scoped by base_id
        self._sources: Dict[str, Dict[str, KnowledgeSource]] = defaultdict(dict)

        # Items indexed by item_id, scoped by base_id
        self._items: Dict[str, Dict[str, KnowledgeItem]] = defaultdict(dict)

        # Index: source_id -> list of item_ids
        self._source_items: Dict[str, List[str]] = defaultdict(list)

        # Inverted text index: token -> set of (base_id, item_id) tuples
        self._text_index: Dict[str, Set[tuple]] = defaultdict(set)

    @property
    def name(self) -> str:
        return "in_memory"

    async def health_check(self) -> HealthCheckResult:
        """Check storage health."""
        return HealthCheckResult(
            status=ComponentStatus.HEALTHY,
            component_name=self.name,
            message="In-memory knowledge storage operational",
            details={
                "knowledge_base_count": len(self._knowledge_bases),
                "total_items": sum(len(items) for items in self._items.values()),
            },
        )

    # Knowledge Base operations

    def store_knowledge_base(self, base: KnowledgeBase) -> bool:
        """Store a knowledge base."""
        try:
            base.updated_at = datetime.utcnow()
            self._knowledge_bases[base.base_id] = base
            return True
        except Exception:
            return False

    def get_knowledge_base(self, base_id: str) -> Optional[KnowledgeBase]:
        """Retrieve a knowledge base by ID."""
        return self._knowledge_bases.get(base_id)

    def delete_knowledge_base(self, base_id: str) -> bool:
        """Delete a knowledge base and all its contents."""
        if base_id not in self._knowledge_bases:
            return False

        # Delete all items in this base
        if base_id in self._items:
            for item_id, item in list(self._items[base_id].items()):
                self._remove_item_from_index(item)
            del self._items[base_id]

        # Delete all sources in this base
        if base_id in self._sources:
            for source_id in list(self._sources[base_id].keys()):
                if source_id in self._source_items:
                    del self._source_items[source_id]
            del self._sources[base_id]

        # Delete the knowledge base
        del self._knowledge_bases[base_id]
        return True

    def list_knowledge_bases(
        self,
        owner_type: Optional[str] = None,
        owner_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[KnowledgeBase]:
        """List knowledge bases with optional filtering."""
        bases = list(self._knowledge_bases.values())

        # Apply filters
        if owner_type:
            bases = [b for b in bases if b.owner_type == owner_type]
        if owner_id:
            bases = [b for b in bases if b.owner_id == owner_id]

        # Sort by created_at descending
        bases.sort(key=lambda b: b.created_at, reverse=True)

        # Apply pagination
        return bases[offset : offset + limit]

    # Knowledge Source operations

    def store_source(self, source: KnowledgeSource) -> bool:
        """Store a knowledge source."""
        try:
            source.updated_at = datetime.utcnow()
            self._sources[source.base_id][source.source_id] = source
            return True
        except Exception:
            return False

    def get_source(self, source_id: str, base_id: str) -> Optional[KnowledgeSource]:
        """Retrieve a source by ID within a base."""
        return self._sources.get(base_id, {}).get(source_id)

    def delete_source(self, source_id: str, base_id: str) -> bool:
        """Delete a source and all its items."""
        if base_id not in self._sources or source_id not in self._sources[base_id]:
            return False

        # Delete all items in this source
        item_ids = self._source_items.get(source_id, [])
        for item_id in item_ids:
            if item_id in self._items.get(base_id, {}):
                item = self._items[base_id][item_id]
                self._remove_item_from_index(item)
                del self._items[base_id][item_id]

        # Remove source item tracking
        if source_id in self._source_items:
            del self._source_items[source_id]

        # Delete the source
        del self._sources[base_id][source_id]
        return True

    def list_sources(
        self,
        base_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[KnowledgeSource]:
        """List sources within a knowledge base."""
        sources = list(self._sources.get(base_id, {}).values())

        # Sort by created_at descending
        sources.sort(key=lambda s: s.created_at, reverse=True)

        # Apply pagination
        return sources[offset : offset + limit]

    # Knowledge Item operations

    def store_item(self, item: KnowledgeItem) -> bool:
        """Store a knowledge item."""
        try:
            item.updated_at = datetime.utcnow()

            # Remove old index entries if updating
            old_item = self._items.get(item.base_id, {}).get(item.item_id)
            if old_item:
                self._remove_item_from_index(old_item)

            # Store item
            self._items[item.base_id][item.item_id] = item

            # Track item in source
            if item.item_id not in self._source_items[item.source_id]:
                self._source_items[item.source_id].append(item.item_id)

            # Index item for search
            self._index_item(item)

            return True
        except Exception:
            return False

    def get_item(self, item_id: str, base_id: str) -> Optional[KnowledgeItem]:
        """Retrieve an item by ID within a base."""
        return self._items.get(base_id, {}).get(item_id)

    def delete_item(self, item_id: str, base_id: str) -> bool:
        """Delete an item."""
        if base_id not in self._items or item_id not in self._items[base_id]:
            return False

        item = self._items[base_id][item_id]

        # Remove from source tracking
        if item.source_id in self._source_items:
            if item_id in self._source_items[item.source_id]:
                self._source_items[item.source_id].remove(item_id)

        # Remove from index
        self._remove_item_from_index(item)

        # Delete item
        del self._items[base_id][item_id]
        return True

    def list_items(
        self,
        base_id: str,
        source_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[KnowledgeItem]:
        """List items within a base, optionally filtered by source."""
        if source_id:
            # Get items for specific source
            item_ids = self._source_items.get(source_id, [])
            items = [
                self._items.get(base_id, {}).get(item_id)
                for item_id in item_ids
                if item_id in self._items.get(base_id, {})
            ]
            items = [i for i in items if i is not None]
        else:
            items = list(self._items.get(base_id, {}).values())

        # Sort by created_at descending
        items.sort(key=lambda i: i.created_at, reverse=True)

        # Apply pagination
        return items[offset : offset + limit]

    # Indexing helpers

    def _index_item(self, item: KnowledgeItem) -> None:
        """Build text index for an item."""
        tokens = self._tokenize(item.content)
        if item.title:
            tokens.update(self._tokenize(item.title))

        for token in tokens:
            self._text_index[token].add((item.base_id, item.item_id))

    def _remove_item_from_index(self, item: KnowledgeItem) -> None:
        """Remove item from text index."""
        tokens = self._tokenize(item.content)
        if item.title:
            tokens.update(self._tokenize(item.title))

        for token in tokens:
            self._text_index[token].discard((item.base_id, item.item_id))

    def _tokenize(self, text: str) -> Set[str]:
        """Simple tokenization for text indexing."""
        words = re.findall(r'\b\w+\b', text.lower())
        return set(words)

    # Search operations

    def search(self, query: KnowledgeQuery) -> RetrievalResults:
        """Search for items matching the query within a knowledge base."""
        start_time = time.time()

        # Get candidate item IDs (always scoped to base_id)
        candidate_ids = self._get_candidates(query)

        # Score and rank candidates
        scored_results = []
        for item_id in candidate_ids:
            item = self._items.get(query.base_id, {}).get(item_id)
            if not item:
                continue

            # Apply source filter
            if query.source_ids and item.source_id not in query.source_ids:
                continue

            # Apply metadata filters
            if not self._matches_filters(item, query):
                continue

            # Calculate score
            score = self._calculate_score(item, query)
            if score >= query.min_score:
                scored_results.append((item, score))

        # Sort by score descending
        scored_results.sort(key=lambda x: x[1], reverse=True)

        # Apply pagination
        total_count = len(scored_results)
        paginated = scored_results[query.offset : query.offset + query.limit]

        # Build results
        results = []
        for rank, (item, score) in enumerate(paginated, start=query.offset + 1):
            highlights = []
            if query.query_text and query.include_content:
                highlights = self._generate_highlights(item.content, query.query_text)

            results.append(
                RetrievalResult(
                    item=item,
                    score=score,
                    highlights=highlights,
                    rank=rank,
                )
            )

        query_time_ms = (time.time() - start_time) * 1000

        return RetrievalResults(
            results=results,
            total_count=total_count,
            query_time_ms=query_time_ms,
            query=query,
        )

    def _get_candidates(self, query: KnowledgeQuery) -> Set[str]:
        """Get candidate item IDs based on query."""
        base_id = query.base_id

        # Start with all items in the base
        all_items_in_base = set(self._items.get(base_id, {}).keys())

        # If text query, use inverted index
        if query.query_text:
            tokens = self._tokenize(query.query_text)
            text_candidates: Optional[Set[str]] = None

            for token in tokens:
                # Get items that have this token AND are in the correct base
                token_items = {
                    item_id
                    for (b_id, item_id) in self._text_index.get(token, set())
                    if b_id == base_id
                }
                if text_candidates is None:
                    text_candidates = token_items
                else:
                    # Union for OR-style matching (find any matching token)
                    text_candidates |= token_items

            if text_candidates is not None:
                return text_candidates & all_items_in_base

        # For pure embedding search or no query, return all items in base
        return all_items_in_base

    def _matches_filters(self, item: KnowledgeItem, query: KnowledgeQuery) -> bool:
        """Check if item matches query filters."""
        for key, value in query.filters.items():
            item_value = item.metadata.get(key)
            if item_value != value:
                return False
        return True

    def _calculate_score(self, item: KnowledgeItem, query: KnowledgeQuery) -> float:
        """Calculate relevance score for an item."""
        score = 0.0

        # Text relevance score
        if query.query_text:
            text_score = self._text_similarity(item.content, query.query_text)
            if item.title:
                title_score = self._text_similarity(item.title, query.query_text)
                text_score = max(text_score, title_score * 1.2)  # Boost title matches
            score += text_score * 0.5

        # Vector similarity score
        if query.query_embedding and item.embedding:
            vector_score = self._cosine_similarity(item.embedding, query.query_embedding)
            score += vector_score * 0.5

        # Normalize if only one type of search
        if query.query_text and not query.query_embedding:
            score *= 2
        elif query.query_embedding and not query.query_text:
            score *= 2

        return score

    def _text_similarity(self, content: str, query: str) -> float:
        """Calculate text similarity score."""
        content_tokens = self._tokenize(content)
        query_tokens = self._tokenize(query)

        if not query_tokens:
            return 0.0

        # Count matching tokens
        matches = len(content_tokens & query_tokens)

        # Normalize by query length
        return matches / len(query_tokens)

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _generate_highlights(self, content: str, query: str) -> List[str]:
        """Generate text highlights for search results."""
        highlights = []
        query_tokens = self._tokenize(query)

        # Find sentences containing query terms
        sentences = re.split(r'[.!?]+', content)
        for sentence in sentences:
            sentence_tokens = self._tokenize(sentence)
            if sentence_tokens & query_tokens:
                highlight = sentence.strip()
                if len(highlight) > 200:
                    highlight = highlight[:200] + "..."
                highlights.append(highlight)
                if len(highlights) >= 3:
                    break

        return highlights

    # Statistics

    def count_knowledge_bases(
        self,
        owner_type: Optional[str] = None,
        owner_id: Optional[str] = None,
    ) -> int:
        """Count knowledge bases."""
        if not owner_type and not owner_id:
            return len(self._knowledge_bases)

        count = 0
        for base in self._knowledge_bases.values():
            if owner_type and base.owner_type != owner_type:
                continue
            if owner_id and base.owner_id != owner_id:
                continue
            count += 1
        return count

    def count_sources(self, base_id: str) -> int:
        """Count sources in a knowledge base."""
        return len(self._sources.get(base_id, {}))

    def count_items(
        self,
        base_id: str,
        source_id: Optional[str] = None,
    ) -> int:
        """Count items in a knowledge base."""
        if source_id:
            return len(self._source_items.get(source_id, []))
        return len(self._items.get(base_id, {}))

    def clear(self) -> None:
        """Clear all stored data."""
        self._knowledge_bases.clear()
        self._sources.clear()
        self._items.clear()
        self._source_items.clear()
        self._text_index.clear()
