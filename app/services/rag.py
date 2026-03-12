"""RAG retrieval and answer generation service."""
import logging
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, UUID

from app.models.toolkit import ToolkitChunk, ToolkitDocument, ChatLog
from app.services.embeddings import get_embedding_provider
from app.services.completion import get_completion_client
from app.settings import settings

logger = logging.getLogger(__name__)


class SearchResult:
    """Search result with chunk and metadata."""

    def __init__(
        self,
        chunk_id: str,
        chunk_text: str,
        similarity_score: float,
        heading: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        document_version: Optional[str] = None
    ):
        self.chunk_id = chunk_id
        self.chunk_text = chunk_text
        self.similarity_score = similarity_score
        self.heading = heading
        self.metadata = metadata or {}
        self.document_version = document_version

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "chunk_id": self.chunk_id,
            "chunk_text": self.chunk_text,
            "similarity_score": self.similarity_score,
            "heading": self.heading,
            "metadata": self.metadata,
            "document_version": self.document_version
        }


def search_similar_chunks(
    db: Session,
    query: str,
    top_k: int = 5,
    similarity_threshold: float = 0.0,
    filters: Optional[Dict[str, Any]] = None
) -> List[SearchResult]:
    """
    Search for similar chunks using vector similarity.

    Args:
        db: Database session
        query: Search query text
        top_k: Number of results to return
        similarity_threshold: Minimum similarity score (0-1)
        filters: Optional filters (cluster, tool_name, tags, etc.)

    Returns:
        List of SearchResult objects ordered by similarity
    """
    # Get embedding provider
    provider = get_embedding_provider()
    if provider is None:
        raise ValueError("No embedding provider configured")

    # Create query embedding
    query_embedding = provider.create_embedding(query)

    # Build base query with vector similarity
    # pgvector uses <=> operator for cosine distance
    # Cosine similarity = 1 - cosine distance
    query_obj = (
        db.query(
            ToolkitChunk,
            ToolkitDocument.version_tag,
            (1 - ToolkitChunk.embedding.cosine_distance(query_embedding)).label('similarity')
        )
        .join(ToolkitDocument, ToolkitChunk.document_id == ToolkitDocument.id)
        .filter(ToolkitChunk.embedding.isnot(None))
        .filter(ToolkitDocument.is_active == True)
    )

    # Apply filters if provided
    if filters:
        # Filter by metadata fields if present
        if "cluster" in filters:
            query_obj = query_obj.filter(
                ToolkitChunk.chunk_metadata['cluster'].astext == filters['cluster']
            )
        if "tool_name" in filters:
            query_obj = query_obj.filter(
                ToolkitChunk.chunk_metadata['tool_name'].astext == filters['tool_name']
            )
        if "tags" in filters and isinstance(filters['tags'], list):
            # Filter chunks that have any of the specified tags
            for tag in filters['tags']:
                query_obj = query_obj.filter(
                    ToolkitChunk.chunk_metadata['tags'].contains([tag])
                )

    # Order by similarity and limit
    from sqlalchemy import desc
    results = (
        query_obj
        .order_by(desc('similarity'))
        .limit(top_k)
        .all()
    )

    # Convert to SearchResult objects and filter by threshold
    search_results = []
    for chunk, version_tag, similarity in results:
        if similarity >= similarity_threshold:
            search_results.append(
                SearchResult(
                    chunk_id=str(chunk.id),
                    chunk_text=chunk.chunk_text,
                    similarity_score=float(similarity),
                    heading=chunk.heading,
                    metadata=chunk.chunk_metadata,
                    document_version=version_tag
                )
            )

    return search_results


def generate_answer(
    db: Session,
    query: str,
    search_results: List[SearchResult],
    user_id: Optional[str] = None,
    save_to_log: bool = True,
    user_profile: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate answer using retrieved chunks with strict grounding.

    Args:
        db: Database session
        query: User query
        search_results: Retrieved chunks from search
        user_id: User ID for saving to chat logs
        save_to_log: Whether to save Q&A to chat_logs

    Returns:
        Dictionary with answer, citations, and metadata
    """
    # Build sector-specific context for system prompt
    org_type = (user_profile or {}).get("organisation_type", "")
    sector_context = _get_sector_context(org_type)

    # Check if we have any results above threshold
    if not search_results:
        # No matching toolkit content — use LLM with general knowledge
        try:
            fallback_system = f"""You are Grounded AI, a knowledgeable assistant for the Grounded platform — helping organisations implement AI ethically and effectively.

No directly relevant content was found in the Grounded knowledge base for this query. Use your general knowledge to help the user.
{sector_context}
RULES:
1. If the user is greeting you or making small talk, respond warmly and mention you can help with questions about AI tools, strategies, ethics policies, and best practices.
2. If the user asked a substantive question, answer it using your general knowledge. Be helpful and informative.
3. If your answer relates to topics covered in Grounded (AI tools, ethics, verification, data analysis, security, legal frameworks), suggest they explore specific Grounded features:
   - The **AI Toolkit** for discovering and comparing AI tools
   - The **Ethics Policy Builder** for creating an organisational AI ethics policy
   - The **Legal Framework Builder** for understanding regulatory requirements
   - The **Strategy Planner** for developing an AI implementation roadmap
4. Be concise but thorough."""

            client = get_completion_client()
            fallback_answer = client.complete(
                prompt=query,
                max_tokens=1024,
                temperature=0.7,
                system=fallback_system,
            )
        except Exception as e:
            logger.warning(f"Fallback completion failed: {e}")
            fallback_answer = "I couldn't find anything related to that in Grounded. Try asking about a specific AI tool or strategy."

        response = {
            "answer": fallback_answer,
            "citations": [],
            "similarity_scores": [],
            "refusal": True
        }

        if save_to_log and user_id:
            _save_chat_log(db, query, response, user_id)

        return response

    # Build context from search results
    context_parts = []
    for i, result in enumerate(search_results):
        context_parts.append(
            f"[{i+1}] {result.heading or 'Section'}\n{result.chunk_text}"
        )

    context = "\n\n".join(context_parts)

    # Truncate context if too long
    if len(context) > settings.RAG_MAX_CONTEXT_LENGTH:
        context = context[:settings.RAG_MAX_CONTEXT_LENGTH] + "..."

    # Build prompt with augmented grounding instructions
    system_prompt = f"""You are Grounded AI, a knowledgeable assistant for the Grounded platform — helping organisations implement AI ethically and effectively.
You have deep expertise in AI tools, ethics, governance, and technology. You are augmented with specific Grounded knowledge base content provided below.
{sector_context}
IMPORTANT RULES:
1. If the user is greeting you or making small talk, respond warmly. Mention you can help with questions about AI tools, ethics policies, legal frameworks, and implementation strategies.
2. PRIORITISE the provided Grounded context when answering. When you use Grounded content, cite which section ([1], [2], etc.) you're referencing.
3. You MAY supplement with your general knowledge to give fuller, more useful answers — but clearly distinguish between what comes from Grounded (cited) and your own knowledge.
4. When citing CDI scores or other specific data from Grounded, state the numbers exactly as given.
5. If the question is outside Grounded's scope, answer using your general knowledge and note that this isn't from the knowledge base.
6. Be helpful, concise, and accurate. Give practical advice where appropriate.
7. If you're unsure, say so rather than guessing.
8. When relevant, suggest Grounded features the user might find useful (Ethics Policy Builder, Legal Framework Builder, Strategy Planner, AI Toolkit)."""

    # Append user profile context if available
    if user_profile:
        profile_parts = []
        if user_profile.get("role"):
            profile_parts.append(f"Role: {user_profile['role']}")
        if user_profile.get("organisation_type"):
            profile_parts.append(f"Organisation type: {user_profile['organisation_type']}")
        if user_profile.get("country"):
            profile_parts.append(f"Country: {user_profile['country']}")
        if user_profile.get("interests"):
            profile_parts.append(f"Interests: {user_profile['interests']}")
        if user_profile.get("ai_experience_level"):
            profile_parts.append(f"AI experience: {user_profile['ai_experience_level']}")
        if profile_parts:
            system_prompt += f"""

USER CONTEXT (tailor your answer's complexity and focus accordingly):
{chr(10).join(profile_parts)}"""

    user_prompt = f"""Context from Grounded knowledge base:

{context}

Question: {query}

Answer the question using ONLY the context above. Cite your sources using [1], [2], etc."""

    # Call Claude API
    client = get_completion_client()

    try:
        answer_text = client.complete(
            prompt=user_prompt,
            max_tokens=2048,
            temperature=settings.OPENAI_CHAT_TEMPERATURE,
            system=system_prompt,
        )

    except Exception as e:
        raise ValueError(f"Error generating answer: {e}")

    # Build citations from search results
    citations = []
    for result in search_results:
        citations.append({
            "chunk_id": result.chunk_id,
            "heading": result.heading,
            "snippet": result.chunk_text[:200] + "..." if len(result.chunk_text) > 200 else result.chunk_text,
            "similarity_score": result.similarity_score,
            "document_version": result.document_version,
            "metadata": result.metadata
        })

    response = {
        "answer": answer_text,
        "citations": citations,
        "similarity_scores": [r.similarity_score for r in search_results],
        "refusal": False
    }

    if save_to_log and user_id:
        _save_chat_log(db, query, response, user_id)

    return response


def _get_sector_context(org_type: str) -> str:
    """Build sector-specific context for the system prompt."""
    sector_map = {
        "newsroom": (
            "\nYou are speaking with someone from a newsroom/media organisation. "
            "Tailor your advice to journalism workflows: editorial processes, "
            "fact-checking, content verification, audience analytics, and media ethics. "
            "Reference journalism-specific AI tools, standards (SPJ, EBU, AP), and "
            "case studies from news organisations when relevant."
        ),
        "ngo": (
            "\nYou are speaking with someone from an NGO/non-profit. "
            "Tailor your advice to social impact workflows: donor reporting, "
            "programme evaluation, data collection ethics, beneficiary privacy, "
            "and resource-constrained environments. Emphasise free/open-source tools "
            "and frameworks relevant to the development sector."
        ),
        "law_firm": (
            "\nYou are speaking with someone from a law firm/legal practice. "
            "Tailor your advice to legal workflows: legal research, contract review, "
            "e-discovery, compliance monitoring, and client confidentiality. "
            "Emphasise data protection, privilege concerns, and regulatory compliance. "
            "Reference legal-specific AI standards and bar association guidelines."
        ),
        "business": (
            "\nYou are speaking with someone from a business/corporate organisation. "
            "Tailor your advice to business workflows: operations, HR, customer service, "
            "supply chain, and competitive intelligence. Focus on ROI, scalability, "
            "enterprise security, and compliance with industry regulations."
        ),
    }
    return sector_map.get(org_type, "")


def _save_chat_log(db: Session, query: str, response: Dict[str, Any], user_id: str) -> None:
    """Save Q&A to chat_logs table."""
    chat_log = ChatLog(
        user_id=user_id,
        query=query,
        answer=response['answer'],
        citations=response['citations'],
        similarity_score=response.get('similarity_scores'),
        filters_applied=None  # Can be added later
    )
    db.add(chat_log)
    db.commit()


def rag_answer(
    db: Session,
    query: str,
    user_id: Optional[str] = None,
    top_k: Optional[int] = None,
    similarity_threshold: Optional[float] = None,
    filters: Optional[Dict[str, Any]] = None,
    user_profile: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Complete RAG pipeline: search + generate answer.

    Args:
        db: Database session
        query: User query
        user_id: User ID for saving to chat logs (optional for API, required for UI)
        top_k: Number of chunks to retrieve (default from settings)
        similarity_threshold: Minimum similarity (default from settings)
        filters: Optional filters for search
        user_profile: Optional user profile dict for personalizing answers

    Returns:
        Dictionary with answer and citations
    """
    # Use defaults from settings if not provided
    top_k = top_k or settings.RAG_TOP_K
    similarity_threshold = similarity_threshold or settings.RAG_SIMILARITY_THRESHOLD

    # Search for similar chunks
    search_results = search_similar_chunks(
        db=db,
        query=query,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
        filters=filters
    )

    # Track knowledge gaps for the Brain's self-improvement loop
    try:
        from app.brain.gap_detector import KnowledgeGapDetector
        gap_detector = KnowledgeGapDetector(db)
        sector = user_profile.get("organisation_type") if user_profile else None

        if not search_results:
            gap_detector.detect_fallback_response(query, sector=sector)
        elif search_results:
            best_similarity = max(r.similarity_score for r in search_results)
            gap_detector.detect_low_similarity(query, best_similarity, sector=sector)
    except Exception as e:
        logger.debug(f"Gap detection skipped: {e}")

    # Generate answer with citations
    return generate_answer(db, query, search_results, user_id=user_id, save_to_log=True, user_profile=user_profile)
