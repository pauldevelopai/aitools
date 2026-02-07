#!/usr/bin/env python3
"""Ingest curated AI policy documents into the Public Library.

Creates LibraryItem records (browsable on /library) and ToolkitChunk records
(searchable via RAG).

Usage:
    python scripts/ingest_library.py                # normal run (skip unchanged)
    python scripts/ingest_library.py --force        # re-ingest everything
    python scripts/ingest_library.py --no-embeddings  # skip embedding creation
    python scripts/ingest_library.py --status       # show current ingestion status
"""
import argparse
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import SessionLocal
from app.services.library_ingest import ingest_library, get_ingest_status


def main():
    parser = argparse.ArgumentParser(description="Ingest library sources")
    parser.add_argument("--force", action="store_true", help="Re-ingest all sources even if unchanged")
    parser.add_argument("--no-embeddings", action="store_true", help="Skip embedding creation")
    parser.add_argument("--status", action="store_true", help="Show current ingestion status and exit")
    args = parser.parse_args()

    db = SessionLocal()

    try:
        if args.status:
            status = get_ingest_status(db)
            print(f"\nLibrary Ingestion Status")
            print(f"========================")
            print(f"Catalog sources:   {status['total_sources']}")
            print(f"Ingested items:    {status['ingested_items']}")
            print(f"Published items:   {status['published_items']}")
            print(f"Total chunks:      {status['total_chunks']}")
            print(f"Embedded chunks:   {status['embedded_chunks']}")
            return

        print(f"\nIngesting library sources...")
        print(f"  Force: {args.force}")
        print(f"  Embeddings: {not args.no_embeddings}")
        print()

        result = ingest_library(
            db,
            create_embeddings=not args.no_embeddings,
            force=args.force,
        )

        print(f"\nResults")
        print(f"=======")
        print(f"Total sources:  {result['total_sources']}")
        print(f"Created:        {result['created']}")
        print(f"Updated:        {result['updated']}")
        print(f"Skipped:        {result['skipped']}")
        print(f"Errors:         {result['errors']}")
        print(f"Total chunks:   {result['total_chunks']}")

        print(f"\nPer-source details:")
        for r in result["results"]:
            status = r["action"].upper()
            chunks = r.get("chunks", "-")
            error = r.get("error", "")
            line = f"  [{status:8s}] {r['source_id']}"
            if chunks != "-":
                line += f" ({chunks} chunks)"
            if error:
                line += f" ERROR: {error}"
            print(line)

        # Show final status
        print()
        status = get_ingest_status(db)
        print(f"Final status: {status['ingested_items']}/{status['total_sources']} items, "
              f"{status['total_chunks']} chunks, {status['embedded_chunks']} with embeddings")

    finally:
        db.close()


if __name__ == "__main__":
    main()
