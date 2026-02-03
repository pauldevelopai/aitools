"""
GROUNDED Knowledge Answerer - Grounded answer generation.

Provides answer generation based on retrieved knowledge with source citations.
This is a stub implementation that will be expanded with LLM integration.
"""

import time
from typing import Any, Dict, List, Optional

from grounded.knowledge.exceptions import (
    AnswerGenerationError,
    RetrievalError,
)
from grounded.knowledge.models import (
    Citation,
    GroundedAnswer,
    KnowledgeItem,
    RetrievalResult,
    RetrievalResults,
)
from grounded.knowledge.repository import KnowledgeRepository
from grounded.knowledge.retriever import KnowledgeRetriever


class KnowledgeAnswerer:
    """
    Grounded answer generation based on retrieved knowledge.

    Generates answers that are grounded in retrieved knowledge sources,
    including citations for transparency and verification.

    This is currently a stub implementation that returns the top
    retrieval results as the answer. Future versions will integrate
    with LLM providers for proper answer generation.

    Example:
        answerer = KnowledgeAnswerer(repository, retriever)

        answer = answerer.get_answer(
            base_id="kb-123",
            query="How many vacation days do employees get?",
        )

        print(answer.answer_text)
        for citation in answer.citations:
            print(f"  - {citation.source_name}: {citation.content_excerpt}")
    """

    def __init__(
        self,
        repository: KnowledgeRepository,
        retriever: KnowledgeRetriever,
    ):
        """
        Initialize the answerer.

        Args:
            repository: Knowledge repository for data access
            retriever: Knowledge retriever for search operations
        """
        self._repository = repository
        self._retriever = retriever
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if the answerer is initialized."""
        return self._initialized

    async def initialize(self) -> None:
        """
        Initialize the answerer.

        Ensures the retriever is initialized.
        """
        if not self._retriever.is_initialized:
            await self._retriever.initialize()

        self._initialized = True

    def _ensure_initialized(self) -> None:
        """Ensure the answerer is initialized."""
        if not self._initialized:
            import asyncio
            asyncio.get_event_loop().run_until_complete(self.initialize())

    def _create_citation(
        self,
        result: RetrievalResult,
        source_name: str,
    ) -> Citation:
        """
        Create a citation from a retrieval result.

        Args:
            result: The retrieval result
            source_name: Name of the source

        Returns:
            Citation object
        """
        # Create excerpt (first 200 chars or highlight)
        if result.highlights:
            excerpt = result.highlights[0]
        else:
            excerpt = result.item.content[:200]
            if len(result.item.content) > 200:
                excerpt += "..."

        return Citation(
            item_id=result.item.item_id,
            source_id=result.item.source_id,
            source_name=source_name,
            content_excerpt=excerpt,
            relevance_score=result.score,
            start_char=result.item.start_char,
            end_char=result.item.end_char,
        )

    def _generate_simple_answer(
        self,
        query: str,
        results: RetrievalResults,
    ) -> str:
        """
        Generate a simple answer from retrieval results.

        This is a stub implementation that concatenates the top results.
        Future versions will use an LLM for proper answer generation.

        Args:
            query: The original query
            results: Retrieval results

        Returns:
            Generated answer text
        """
        if not results.results:
            return "I couldn't find any relevant information to answer your question."

        # For now, just return the content of the top result
        top_result = results.results[0]

        if top_result.highlights:
            # Use highlights if available
            answer = " ".join(top_result.highlights)
        else:
            # Otherwise use the full content (truncated)
            answer = top_result.item.content
            if len(answer) > 500:
                # Find a sentence boundary
                end_pos = answer.rfind('.', 0, 500)
                if end_pos > 200:
                    answer = answer[:end_pos + 1]
                else:
                    answer = answer[:500] + "..."

        return answer

    def get_answer(
        self,
        base_id: str,
        query: str,
        limit: int = 5,
        source_ids: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
    ) -> GroundedAnswer:
        """
        Get a grounded answer for a query.

        Retrieves relevant knowledge and generates an answer with citations.

        Args:
            base_id: Knowledge base to search
            query: The question to answer
            limit: Maximum number of sources to use
            source_ids: Optional source filter
            filters: Optional metadata filters
            min_score: Minimum relevance score for sources

        Returns:
            GroundedAnswer with answer text and citations

        Raises:
            AnswerGenerationError: If answer generation fails
        """
        self._ensure_initialized()

        start_time = time.time()

        try:
            # Retrieve relevant knowledge
            results = self._retriever.hybrid_search(
                base_id=base_id,
                query_text=query,
                limit=limit,
                source_ids=source_ids,
                filters=filters,
                min_score=min_score,
            )

            # Generate answer
            answer_text = self._generate_simple_answer(query, results)

            # Create citations
            citations = []
            for result in results.results:
                # Get source name
                source = self._repository.get_source_or_none(
                    result.item.source_id,
                    base_id,
                )
                source_name = source.name if source else "Unknown Source"

                citation = self._create_citation(result, source_name)
                citations.append(citation)

            # Calculate confidence based on top score
            confidence = 0.0
            if results.results:
                confidence = min(results.results[0].score, 1.0)

            generation_time_ms = (time.time() - start_time) * 1000

            return GroundedAnswer(
                answer_text=answer_text,
                query=query,
                base_id=base_id,
                citations=citations,
                confidence_score=confidence,
                retrieval_results=results,
                generation_time_ms=generation_time_ms,
                model_name="stub",  # Will be updated when LLM is integrated
                metadata={
                    "retrieval_count": len(results.results),
                    "total_matches": results.total_count,
                },
            )

        except RetrievalError:
            raise
        except Exception as e:
            raise AnswerGenerationError(
                message=f"Failed to generate answer: {str(e)}",
                query=query,
                original_error=e,
            )

    def get_answer_with_context(
        self,
        base_id: str,
        query: str,
        context: str,
        limit: int = 5,
        source_ids: Optional[List[str]] = None,
    ) -> GroundedAnswer:
        """
        Get a grounded answer with additional context.

        Useful for conversational contexts where previous messages
        provide additional context for the query.

        Args:
            base_id: Knowledge base to search
            query: The question to answer
            context: Additional context (e.g., conversation history)
            limit: Maximum number of sources to use
            source_ids: Optional source filter

        Returns:
            GroundedAnswer with answer text and citations

        Raises:
            AnswerGenerationError: If answer generation fails
        """
        # For now, combine context and query for search
        # Future: use context more intelligently in answer generation
        combined_query = f"{context}\n\n{query}" if context else query

        return self.get_answer(
            base_id=base_id,
            query=combined_query,
            limit=limit,
            source_ids=source_ids,
        )

    def verify_answer(
        self,
        answer: GroundedAnswer,
    ) -> Dict[str, Any]:
        """
        Verify an answer's grounding in sources.

        Stub for future implementation of answer verification
        using NLI or other verification methods.

        Args:
            answer: The answer to verify

        Returns:
            Verification results
        """
        # Stub implementation
        return {
            "verified": answer.is_grounded,
            "citation_count": answer.citation_count,
            "average_citation_score": (
                sum(c.relevance_score for c in answer.citations) / len(answer.citations)
                if answer.citations else 0.0
            ),
            "method": "stub",
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get answerer statistics."""
        return {
            "initialized": self._initialized,
            "retriever_stats": self._retriever.get_stats(),
        }
