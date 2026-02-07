"""Library ingestion service — ingest curated sources into the Public Library.

Creates LibraryItem records (the public-facing document) and ToolkitChunk records
(for RAG search), with dedup via source_id + content_hash and re-ingest logic.

Usage:
    from app.services.library_ingest import ingest_library, get_ingest_status
    result = ingest_library(db, create_embeddings=True)
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.library_item import LibraryItem
from app.models.toolkit import ToolkitDocument, ToolkitChunk
from app.services.ingestion import chunk_content

logger = logging.getLogger(__name__)

# Version tag prefix for library documents in ToolkitDocument
LIBRARY_VERSION_PREFIX = "library"


def _build_content_blocks(source: dict) -> list[dict]:
    """Convert a library source into content blocks suitable for chunking.

    Produces blocks from the content_markdown and sections, with headings
    for context-aware overlapping chunks.
    """
    blocks = []
    title = source["title"]

    # Title block
    blocks.append({
        "type": "heading",
        "text": title,
        "heading": title,
    })

    # Summary block
    if source.get("summary"):
        blocks.append({
            "type": "paragraph",
            "text": source["summary"],
            "heading": title,
        })

    # Main content — split by markdown headings and paragraphs
    content = source.get("content_markdown", "")
    current_heading = title
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("##"):
            # Extract heading text (remove markdown #s)
            heading_text = stripped.lstrip("#").strip()
            current_heading = heading_text
            blocks.append({
                "type": "heading",
                "text": heading_text,
                "heading": current_heading,
            })
        else:
            blocks.append({
                "type": "paragraph",
                "text": stripped,
                "heading": current_heading,
            })

    # Sections (structured data)
    for section in source.get("sections") or []:
        heading = section.get("heading", "")
        content_text = section.get("content", "")
        if heading:
            blocks.append({
                "type": "heading",
                "text": heading,
                "heading": heading,
            })
        if content_text:
            blocks.append({
                "type": "paragraph",
                "text": content_text,
                "heading": heading or title,
            })

    return blocks


def _build_chunk_metadata(source: dict) -> dict:
    """Build the JSONB metadata for each chunk of a library source."""
    meta = {
        "type": "library",
        "document_type": source["document_type"],
        "source_id": source["source_id"],
        "title": source["title"],
    }
    if source.get("jurisdiction"):
        meta["jurisdiction"] = source["jurisdiction"]
    if source.get("publisher"):
        meta["publisher"] = source["publisher"]
    if source.get("tags"):
        meta["tags"] = source["tags"]
    if source.get("source_url"):
        meta["source_url"] = source["source_url"]
    return meta


def _get_or_create_toolkit_doc(
    db: Session,
    source_id: str,
) -> ToolkitDocument:
    """Get or create the ToolkitDocument that holds chunks for a library source.

    Each library source gets one ToolkitDocument (keyed by version_tag).
    On re-ingest, old chunks are deleted and the document is reused.
    """
    version_tag = f"{LIBRARY_VERSION_PREFIX}:{source_id}"

    doc = db.query(ToolkitDocument).filter(
        ToolkitDocument.version_tag == version_tag
    ).first()

    if doc:
        # Delete old chunks for re-ingest
        db.query(ToolkitChunk).filter(
            ToolkitChunk.document_id == doc.id
        ).delete()
        doc.chunk_count = 0
        doc.is_ingested = False
        db.flush()
        return doc

    doc = ToolkitDocument(
        version_tag=version_tag,
        source_filename=f"library:{source_id}",
        file_path=f"library://{source_id}",
        chunk_count=0,
        is_active=True,
        is_ingested=False,
    )
    db.add(doc)
    db.flush()
    return doc


def ingest_single_source(
    db: Session,
    source: dict,
    *,
    create_embeddings: bool = True,
    force: bool = False,
) -> dict:
    """Ingest a single library source. Returns a status dict.

    Dedup: if source_id already exists and content_hash hasn't changed, skip.
    Re-ingest: if content_hash changed or force=True, update the item and re-chunk.
    """
    source_id = source["source_id"]
    content = source.get("content_markdown", "")
    new_hash = LibraryItem.compute_hash(content)

    existing = db.query(LibraryItem).filter(
        LibraryItem.source_id == source_id
    ).first()

    if existing and not force:
        if existing.content_hash == new_hash:
            return {"source_id": source_id, "action": "skipped", "reason": "unchanged"}

    # --- Create or update LibraryItem ---
    if existing:
        item = existing
        item.title = source["title"]
        item.document_type = source["document_type"]
        item.jurisdiction = source.get("jurisdiction")
        item.publisher = source.get("publisher")
        item.publication_date = source.get("publication_date")
        item.source_url = source.get("source_url")
        item.summary = source.get("summary")
        item.content_markdown = content
        item.sections = source.get("sections")
        item.tags = source.get("tags")
        item.content_hash = new_hash
        action = "updated"
    else:
        slug = LibraryItem.generate_slug(source["title"])
        slug_exists = db.query(LibraryItem).filter(LibraryItem.slug == slug).first()
        if slug_exists:
            slug = f"{slug}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        item = LibraryItem(
            title=source["title"],
            slug=slug,
            document_type=source["document_type"],
            jurisdiction=source.get("jurisdiction"),
            publisher=source.get("publisher"),
            publication_date=source.get("publication_date"),
            source_url=source.get("source_url"),
            summary=source.get("summary"),
            content_markdown=content,
            sections=source.get("sections"),
            tags=source.get("tags"),
            is_published=True,  # Auto-publish curated content
            source_id=source_id,
            content_hash=new_hash,
        )
        db.add(item)
        action = "created"

    db.flush()

    # --- Create / refresh ToolkitDocument + chunks for RAG ---
    toolkit_doc = _get_or_create_toolkit_doc(db, source_id)

    content_blocks = _build_content_blocks(source)
    chunks = chunk_content(content_blocks, target_size=1000, overlap=150)

    base_metadata = _build_chunk_metadata(source)

    chunk_objects = []
    for chunk_data in chunks:
        meta = {**base_metadata, "char_count": len(chunk_data["chunk_text"])}
        chunk = ToolkitChunk(
            document_id=toolkit_doc.id,
            chunk_text=chunk_data["chunk_text"],
            chunk_index=chunk_data["chunk_index"],
            heading=chunk_data.get("heading"),
            chunk_metadata=meta,
            embedding=None,
        )
        chunk_objects.append(chunk)

    db.bulk_save_objects(chunk_objects)

    toolkit_doc.chunk_count = len(chunk_objects)
    toolkit_doc.is_ingested = True
    toolkit_doc.is_active = True

    db.commit()

    # Create embeddings
    if create_embeddings:
        try:
            from app.services.embeddings import create_embeddings_for_document
            embedded = create_embeddings_for_document(db, toolkit_doc.id)
            logger.info(f"  Created {embedded} embeddings for {source_id}")
        except Exception as e:
            logger.warning(f"  Embedding creation failed for {source_id}: {e}")

    return {
        "source_id": source_id,
        "action": action,
        "chunks": len(chunk_objects),
        "library_item_id": str(item.id),
    }


def ingest_library(
    db: Session,
    *,
    create_embeddings: bool = True,
    force: bool = False,
) -> dict:
    """Ingest all curated library sources.

    Args:
        db: Database session.
        create_embeddings: Whether to create vector embeddings for RAG search.
        force: If True, re-ingest even if content hasn't changed.

    Returns:
        Summary dict with counts and per-source results.
    """
    from app.services.library_sources import LIBRARY_SOURCES

    results = []
    created = 0
    updated = 0
    skipped = 0
    total_chunks = 0

    logger.info(f"Starting library ingestion: {len(LIBRARY_SOURCES)} sources, force={force}")

    for source in LIBRARY_SOURCES:
        try:
            result = ingest_single_source(
                db, source,
                create_embeddings=create_embeddings,
                force=force,
            )
            results.append(result)

            if result["action"] == "created":
                created += 1
                total_chunks += result.get("chunks", 0)
            elif result["action"] == "updated":
                updated += 1
                total_chunks += result.get("chunks", 0)
            else:
                skipped += 1

            logger.info(f"  [{result['action'].upper()}] {source['source_id']} ({result.get('chunks', 0)} chunks)")
        except Exception as e:
            logger.error(f"  [ERROR] {source['source_id']}: {e}")
            results.append({
                "source_id": source["source_id"],
                "action": "error",
                "error": str(e),
            })

    summary = {
        "total_sources": len(LIBRARY_SOURCES),
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors": len(results) - created - updated - skipped,
        "total_chunks": total_chunks,
        "results": results,
    }

    logger.info(
        f"Library ingestion complete: {created} created, {updated} updated, "
        f"{skipped} skipped, {summary['errors']} errors, {total_chunks} total chunks"
    )

    return summary


def get_ingest_status(db: Session) -> dict:
    """Get the current status of library ingestion."""
    from app.services.library_sources import LIBRARY_SOURCES

    source_ids = [s["source_id"] for s in LIBRARY_SOURCES]

    # Count library items
    item_count = db.query(LibraryItem).filter(
        LibraryItem.source_id.in_(source_ids)
    ).count()

    published_count = db.query(LibraryItem).filter(
        LibraryItem.source_id.in_(source_ids),
        LibraryItem.is_published == True,
    ).count()

    # Count chunks
    chunk_count = db.query(ToolkitChunk).join(
        ToolkitDocument
    ).filter(
        ToolkitDocument.version_tag.like(f"{LIBRARY_VERSION_PREFIX}:%"),
        ToolkitDocument.is_active == True,
    ).count()

    # Count embeddings
    embedding_count = db.query(ToolkitChunk).join(
        ToolkitDocument
    ).filter(
        ToolkitDocument.version_tag.like(f"{LIBRARY_VERSION_PREFIX}:%"),
        ToolkitDocument.is_active == True,
        ToolkitChunk.embedding.isnot(None),
    ).count()

    return {
        "total_sources": len(LIBRARY_SOURCES),
        "ingested_items": item_count,
        "published_items": published_count,
        "total_chunks": chunk_count,
        "embedded_chunks": embedding_count,
    }
