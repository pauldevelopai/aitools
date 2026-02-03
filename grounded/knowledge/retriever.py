"""
GROUNDED Knowledge Retriever - Semantic and hybrid search implementation.

Provides AI-powered retrieval using embeddings and hybrid search strategies
to find relevant knowledge items.
"""

import time
from typing import Any, Dict, List, Optional

from grounded.ai import get_embedding_provider, EmbeddingProvider
from grounded.knowledge.exceptions import (
    EmbeddingError,
    RetrievalError,
    KnowledgeBaseNotFoundError,
)
from grounded.knowledge.models import (
    KnowledgeQuery,
    KnowledgeItem,
    RetrievalResult,
    RetrievalResults,
)
from grounded.knowledge.repository import KnowledgeRepository


class KnowledgeRetriever:
    """
    Semantic and hybrid search implementation for knowledge retrieval.

    Supports multiple search strategies:
    - Text search: Keyword-based matching
    - Semantic search: Embedding similarity
    - Hybrid search: Combination of text and semantic

    Example:
        retriever = KnowledgeRetriever(repository)
        await retriever.initialize()

        # Simple text search
        results = retriever.search(base_id, "vacation policy")

        # Semantic search
        results = retriever.semantic_search(base_id, "time off from work")

        # Hybrid search (recommended)
        results = retriever.hybrid_search(base_id, "how much vacation do I get")
    """

    def __init__(
        self,
        repository: KnowledgeRepository,
        embedding_provider: Optional[EmbeddingProvider] = None,
    ):
        """
        Initialize the retriever.

        Args:
            repository: Knowledge repository for data access
            embedding_provider: Optional embedding provider (uses default if not provided)
        """
        self._repository = repository
        self._embedding_provider = embedding_provider
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if the retriever is initialized."""
        return self._initialized

    async def initialize(self) -> None:
        """
        Initialize the retriever.

        Sets up the embedding provider if not already configured.
        """
        if self._embedding_provider is None:
            try:
                self._embedding_provider = get_embedding_provider()
            except Exception as e:
                # Fall back to stub provider or continue without embeddings
                from grounded.ai.providers.embedding import LocalStubEmbeddingProvider
                self._embedding_provider = LocalStubEmbeddingProvider()

        self._initialized = True

    def _ensure_initialized(self) -> None:
        """Ensure the retriever is initialized."""
        if not self._initialized:
            import asyncio
            asyncio.get_event_loop().run_until_complete(self.initialize())

    def _get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector

        Raises:
            EmbeddingError: If embedding generation fails
        """
        self._ensure_initialized()

        try:
            return self._embedding_provider.create_embedding(text)
        except Exception as e:
            raise EmbeddingError(
                message=f"Failed to generate embedding: {str(e)}",
                provider=self._embedding_provider.name if self._embedding_provider else "unknown",
                original_error=e,
            )

    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for multiple texts.

        Args:
            texts: Texts to embed

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingError: If embedding generation fails
        """
        self._ensure_initialized()

        try:
            return self._embedding_provider.create_embeddings(texts)
        except Exception as e:
            raise EmbeddingError(
                message=f"Failed to generate embeddings: {str(e)}",
                provider=self._embedding_provider.name if self._embedding_provider else "unknown",
                original_error=e,
            )

    def search(
        self,
        base_id: str,
        query_text: str,
        limit: int = 10,
        source_ids: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
    ) -> RetrievalResults:
        """
        Perform text-based search.

        Args:
            base_id: Knowledge base to search
            query_text: Search query
            limit: Maximum results
            source_ids: Optional source filter
            filters: Optional metadata filters
            min_score: Minimum relevance score

        Returns:
            RetrievalResults

        Raises:
            KnowledgeBaseNotFoundError: If base not found
            RetrievalError: If search fails
        """
        try:
            query = KnowledgeQuery(
                base_id=base_id,
                query_text=query_text,
                source_ids=source_ids,
                filters=filters or {},
                limit=limit,
                min_score=min_score,
            )

            return self._repository.search(query)

        except KnowledgeBaseNotFoundError:
            raise
        except Exception as e:
            raise RetrievalError(
                message=f"Text search failed: {str(e)}",
                query=query_text,
                original_error=e,
            )

    def semantic_search(
        self,
        base_id: str,
        query_text: str,
        limit: int = 10,
        source_ids: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
    ) -> RetrievalResults:
        """
        Perform semantic search using embeddings.

        Args:
            base_id: Knowledge base to search
            query_text: Search query (will be embedded)
            limit: Maximum results
            source_ids: Optional source filter
            filters: Optional metadata filters
            min_score: Minimum similarity score

        Returns:
            RetrievalResults

        Raises:
            KnowledgeBaseNotFoundError: If base not found
            EmbeddingError: If embedding generation fails
            RetrievalError: If search fails
        """
        try:
            # Generate query embedding
            query_embedding = self._get_embedding(query_text)

            query = KnowledgeQuery(
                base_id=base_id,
                query_embedding=query_embedding,
                source_ids=source_ids,
                filters=filters or {},
                limit=limit,
                min_score=min_score,
            )

            return self._repository.search(query)

        except (KnowledgeBaseNotFoundError, EmbeddingError):
            raise
        except Exception as e:
            raise RetrievalError(
                message=f"Semantic search failed: {str(e)}",
                query=query_text,
                original_error=e,
            )

    def hybrid_search(
        self,
        base_id: str,
        query_text: str,
        limit: int = 10,
        source_ids: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
        text_weight: float = 0.3,
        semantic_weight: float = 0.7,
    ) -> RetrievalResults:
        """
        Perform hybrid search combining text and semantic search.

        Args:
            base_id: Knowledge base to search
            query_text: Search query
            limit: Maximum results
            source_ids: Optional source filter
            filters: Optional metadata filters
            min_score: Minimum combined score
            text_weight: Weight for text search score (default 0.3)
            semantic_weight: Weight for semantic score (default 0.7)

        Returns:
            RetrievalResults

        Raises:
            KnowledgeBaseNotFoundError: If base not found
            EmbeddingError: If embedding generation fails
            RetrievalError: If search fails
        """
        try:
            start_time = time.time()

            # Generate query embedding
            query_embedding = self._get_embedding(query_text)

            # Use combined query with both text and embedding
            query = KnowledgeQuery(
                base_id=base_id,
                query_text=query_text,
                query_embedding=query_embedding,
                source_ids=source_ids,
                filters=filters or {},
                limit=limit,
                min_score=min_score,
            )

            results = self._repository.search(query)

            # Adjust query time to include embedding generation
            total_time_ms = (time.time() - start_time) * 1000
            results.query_time_ms = total_time_ms

            return results

        except (KnowledgeBaseNotFoundError, EmbeddingError):
            raise
        except Exception as e:
            raise RetrievalError(
                message=f"Hybrid search failed: {str(e)}",
                query=query_text,
                original_error=e,
            )

    def embed_item(self, item: KnowledgeItem) -> KnowledgeItem:
        """
        Generate embedding for a knowledge item.

        Args:
            item: Item to embed

        Returns:
            Item with embedding

        Raises:
            EmbeddingError: If embedding generation fails
        """
        text = item.content
        if item.title:
            text = f"{item.title}\n\n{text}"

        embedding = self._get_embedding(text)
        item.embedding = embedding

        return item

    def embed_items(self, items: List[KnowledgeItem]) -> List[KnowledgeItem]:
        """
        Generate embeddings for multiple knowledge items.

        Args:
            items: Items to embed

        Returns:
            Items with embeddings

        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not items:
            return items

        # Prepare texts for batch embedding
        texts = []
        for item in items:
            text = item.content
            if item.title:
                text = f"{item.title}\n\n{text}"
            texts.append(text)

        # Generate embeddings
        embeddings = self._get_embeddings(texts)

        # Assign embeddings to items
        for item, embedding in zip(items, embeddings):
            item.embedding = embedding

        return items

    def rerank_results(
        self,
        results: RetrievalResults,
        query_text: str,
        top_k: Optional[int] = None,
    ) -> RetrievalResults:
        """
        Rerank results using a more sophisticated scoring method.

        This is a stub for future implementation of cross-encoder reranking
        or other advanced reranking strategies.

        Args:
            results: Initial retrieval results
            query_text: Original query for reranking
            top_k: Number of results to keep after reranking

        Returns:
            Reranked results
        """
        # For now, just return original results
        # Future: implement cross-encoder reranking
        if top_k and top_k < len(results.results):
            results.results = results.results[:top_k]

        return results

    def get_similar_items(
        self,
        base_id: str,
        item_id: str,
        limit: int = 5,
        exclude_same_source: bool = False,
    ) -> RetrievalResults:
        """
        Find items similar to a given item.

        Args:
            base_id: Knowledge base ID
            item_id: ID of the item to find similar items for
            limit: Maximum results
            exclude_same_source: Whether to exclude items from the same source

        Returns:
            RetrievalResults with similar items

        Raises:
            KnowledgeItemNotFoundError: If item not found
            RetrievalError: If search fails
        """
        try:
            # Get the source item
            item = self._repository.get_item(item_id, base_id)

            # Get or generate embedding
            if not item.embedding:
                item = self.embed_item(item)

            # Search using item's embedding
            query = KnowledgeQuery(
                base_id=base_id,
                query_embedding=item.embedding,
                limit=limit + 1,  # Add 1 to account for self-match
            )

            results = self._repository.search(query)

            # Filter out the source item and optionally items from same source
            filtered_results = []
            for result in results.results:
                if result.item.item_id == item_id:
                    continue
                if exclude_same_source and result.item.source_id == item.source_id:
                    continue
                filtered_results.append(result)
                if len(filtered_results) >= limit:
                    break

            # Update ranks
            for rank, result in enumerate(filtered_results, start=1):
                result.rank = rank

            results.results = filtered_results
            results.total_count = len(filtered_results)

            return results

        except Exception as e:
            raise RetrievalError(
                message=f"Similar items search failed: {str(e)}",
                original_error=e,
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get retriever statistics."""
        return {
            "initialized": self._initialized,
            "embedding_provider": self._embedding_provider.name if self._embedding_provider else None,
        }
