"""
Document Intelligence Demo - Admin-only demo page for GROUNDED document processing.

Provides a UI to demonstrate the document intelligence capabilities:
- Process text/markdown documents
- View chunking results
- Test semantic search
- Explore embeddings
"""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_admin
from app.models.auth import User
from app.products.admin_context import get_admin_context_dict
from app.templates_engine import templates

from grounded.documents import (
    Document,
    DocumentCollection,
    DocumentProcessor,
    ProcessorConfig,
    ChunkingStrategy,
)
from grounded.governance.ai import (
    get_governance_tracker,
    AIOperationType,
    AIOperationStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/demo", tags=["admin", "demo"])

# Shared processor instance (initialized on first use)
_processor: Optional[DocumentProcessor] = None


async def get_processor() -> DocumentProcessor:
    """Get or create the shared DocumentProcessor instance."""
    global _processor
    if _processor is None:
        config = ProcessorConfig(
            chunking_strategy=ChunkingStrategy.SENTENCE,
            chunk_size=500,
            chunk_overlap=50,
            min_chunk_size=100,
            generate_embeddings=True,
            auto_store=True,
        )
        _processor = DocumentProcessor(config)
        await _processor.initialize()
        logger.info("Document Intelligence demo processor initialized")
    return _processor


@router.get("/documents", response_class=HTMLResponse)
async def demo_documents_page(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Document Intelligence demo page.

    Allows admins to:
    - Process sample or custom documents
    - View chunking and embedding results
    - Test semantic search
    """
    admin_context = get_admin_context_dict(request)
    processor = await get_processor()
    stats = processor.get_stats()

    return templates.TemplateResponse(
        "admin/demo_documents.html",
        {
            "request": request,
            "user": user,
            **admin_context,
            "active_admin_page": "agent",
            "stats": stats,
        }
    )


@router.post("/documents/process", response_class=JSONResponse)
async def process_document(
    request: Request,
    content: str = Form(...),
    title: str = Form(""),
    doc_type: str = Form("text"),
    chunking_strategy: str = Form("sentence"),
    chunk_size: int = Form(500),
    user: User = Depends(require_admin),
):
    """
    Process a document and return results.

    Returns chunking results, embeddings info, and processing stats.
    """
    try:
        # Create processor with specified config
        config = ProcessorConfig(
            chunking_strategy=ChunkingStrategy(chunking_strategy),
            chunk_size=chunk_size,
            chunk_overlap=50,
            min_chunk_size=50,
            generate_embeddings=True,
            auto_store=True,
        )
        processor = DocumentProcessor(config)
        await processor.initialize()

        # Create document based on type
        if doc_type == "markdown":
            doc = Document.from_markdown(content, title=title or "Untitled", source="demo")
        else:
            doc = Document.from_text(content, title=title or "Untitled", source="demo")

        # Process document
        processed = processor.process_document(doc)

        # Format chunks for response
        chunks_data = []
        for chunk in processed.chunks:
            chunks_data.append({
                "index": chunk.chunk_index,
                "content": chunk.content,
                "char_count": chunk.character_count,
                "word_count": chunk.word_count,
                "has_embedding": chunk.has_embedding,
                "embedding_preview": chunk.embedding[:5] if chunk.embedding else None,
            })

        return JSONResponse({
            "success": True,
            "document_id": processed.document_id,
            "status": processed.processing_status.value,
            "processing_time_ms": round(processed.processing_time_ms, 2),
            "extracted_text_length": len(processed.extracted_text),
            "chunk_count": processed.chunk_count,
            "has_embeddings": processed.has_embeddings,
            "chunks": chunks_data,
            "original": {
                "title": doc.metadata.title,
                "type": doc.document_type.value,
                "word_count": doc.word_count,
                "char_count": doc.character_count,
            },
        })

    except Exception as e:
        logger.error(f"Document processing error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
        }, status_code=400)


@router.post("/documents/search", response_class=JSONResponse)
async def search_documents(
    request: Request,
    query: str = Form(...),
    limit: int = Form(10),
    use_embeddings: bool = Form(True),
    user: User = Depends(require_admin),
):
    """
    Search processed documents.

    Performs text and/or semantic search across all processed documents.
    """
    try:
        processor = await get_processor()

        results = processor.search(
            query=query,
            limit=limit,
            use_embeddings=use_embeddings,
        )

        # Format results
        results_data = []
        for result in results.results:
            results_data.append({
                "score": round(result.score, 4),
                "document_id": result.document_id,
                "chunk_index": result.chunk.chunk_index,
                "content": result.chunk.content,
                "highlights": result.highlights,
                "word_count": result.chunk.word_count,
            })

        return JSONResponse({
            "success": True,
            "query": query,
            "total_results": results.total_count,
            "returned_results": results.count,
            "query_time_ms": round(results.query_time_ms, 2),
            "results": results_data,
        })

    except Exception as e:
        logger.error(f"Search error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
        }, status_code=400)


@router.get("/documents/stats", response_class=JSONResponse)
async def get_stats(
    request: Request,
    user: User = Depends(require_admin),
):
    """Get current processor and storage statistics."""
    try:
        processor = await get_processor()
        stats = processor.get_stats()

        return JSONResponse({
            "success": True,
            "stats": stats,
        })

    except Exception as e:
        logger.error(f"Stats error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
        }, status_code=400)


@router.post("/documents/clear", response_class=JSONResponse)
async def clear_storage(
    request: Request,
    user: User = Depends(require_admin),
):
    """Clear all processed documents from storage."""
    try:
        processor = await get_processor()

        # Get storage and clear it
        if processor._storage:
            processor._storage.clear()

        return JSONResponse({
            "success": True,
            "message": "Storage cleared",
        })

    except Exception as e:
        logger.error(f"Clear error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
        }, status_code=400)


@router.post("/documents/load-sample", response_class=JSONResponse)
async def load_sample_documents(
    request: Request,
    user: User = Depends(require_admin),
):
    """Load sample documents for demonstration."""
    try:
        processor = await get_processor()

        # Sample documents about AI topics
        samples = [
            {
                "title": "Introduction to Machine Learning",
                "content": """Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed. It focuses on developing computer programs that can access data and use it to learn for themselves.

The process begins with observations or data, such as examples, direct experience, or instruction, to look for patterns in data and make better decisions in the future. The primary aim is to allow computers to learn automatically without human intervention and adjust actions accordingly.

Machine learning algorithms are often categorized as supervised or unsupervised. Supervised learning algorithms apply what has been learned in the past to new data using labeled examples. Unsupervised learning algorithms draw inferences from datasets without labeled responses.""",
            },
            {
                "title": "Natural Language Processing Overview",
                "content": """Natural Language Processing (NLP) is a branch of artificial intelligence that helps computers understand, interpret, and manipulate human language. NLP draws from many disciplines, including computer science and computational linguistics, to fill the gap between human communication and computer understanding.

Key NLP tasks include text classification, sentiment analysis, named entity recognition, machine translation, question answering, and text summarization. Modern NLP systems often use deep learning techniques, particularly transformer-based models like BERT and GPT.

Applications of NLP are everywhere: virtual assistants, email filters, search engines, and translation services all rely on NLP technologies to function effectively.""",
            },
            {
                "title": "Computer Vision Fundamentals",
                "content": """Computer vision is a field of artificial intelligence that trains computers to interpret and understand the visual world. Using digital images from cameras and videos and deep learning models, machines can accurately identify and classify objects.

Core computer vision tasks include image classification, object detection, image segmentation, and facial recognition. These capabilities enable applications ranging from autonomous vehicles to medical image analysis.

Deep learning has revolutionized computer vision. Convolutional Neural Networks (CNNs) are particularly effective for image-related tasks, automatically learning hierarchical features from raw pixel data.""",
            },
        ]

        # Process each sample
        collection = DocumentCollection(name="AI Sample Documents")
        for sample in samples:
            doc = Document.from_text(
                sample["content"],
                title=sample["title"],
                source="sample",
            )
            collection.add_document(doc)

        result = processor.process_collection(collection)

        return JSONResponse({
            "success": True,
            "documents_loaded": result.successful_count,
            "total_chunks": result.total_chunks,
            "processing_time_ms": round(result.total_processing_time_ms, 2),
        })

    except Exception as e:
        logger.error(f"Load sample error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
        }, status_code=400)


# =============================================================================
# AI GOVERNANCE AUDIT TRAIL
# =============================================================================

@router.get("/governance", response_class=HTMLResponse)
async def governance_audit_page(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    AI Governance audit trail page.

    Shows all tracked AI operations with statistics and filtering.
    """
    admin_context = get_admin_context_dict(request)
    tracker = get_governance_tracker()
    stats = tracker.get_stats()
    recent_records = tracker.get_recent_records(limit=50)

    return templates.TemplateResponse(
        "admin/demo_governance.html",
        {
            "request": request,
            "user": user,
            **admin_context,
            "active_admin_page": "agent",
            "stats": stats,
            "recent_records": recent_records,
        }
    )


@router.get("/governance/records", response_class=JSONResponse)
async def get_governance_records(
    request: Request,
    operation_type: Optional[str] = Query(None),
    provider: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    user: User = Depends(require_admin),
):
    """Get filtered AI governance audit records."""
    try:
        tracker = get_governance_tracker()

        # Parse filters
        op_type = AIOperationType(operation_type) if operation_type else None
        op_status = AIOperationStatus(status) if status else None

        records = tracker.get_records(
            operation_type=op_type,
            provider_name=provider if provider else None,
            status=op_status,
            limit=limit,
            offset=offset,
        )

        return JSONResponse({
            "success": True,
            "records": [r.to_dict() for r in records],
            "count": len(records),
        })

    except Exception as e:
        logger.error(f"Get records error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
        }, status_code=400)


@router.get("/governance/stats", response_class=JSONResponse)
async def get_governance_stats(
    request: Request,
    user: User = Depends(require_admin),
):
    """Get AI governance statistics."""
    try:
        tracker = get_governance_tracker()
        stats = tracker.get_stats()
        hourly = tracker.get_stats_by_hour(hours=24)

        return JSONResponse({
            "success": True,
            "stats": stats.to_dict(),
            "hourly": hourly,
        })

    except Exception as e:
        logger.error(f"Get governance stats error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
        }, status_code=400)


@router.post("/governance/clear", response_class=JSONResponse)
async def clear_governance_records(
    request: Request,
    user: User = Depends(require_admin),
):
    """Clear all AI governance audit records."""
    try:
        tracker = get_governance_tracker()
        tracker.clear()

        return JSONResponse({
            "success": True,
            "message": "Governance audit records cleared",
        })

    except Exception as e:
        logger.error(f"Clear governance error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
        }, status_code=400)
