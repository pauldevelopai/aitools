#!/usr/bin/env python3
"""Seed minimal structural records for PolicyDocument schema validation.

Usage:
    python scripts/seed_policy_documents.py

Creates:
    - 1 internal ethics_policy document (no org, public visibility) with 2 versions
    - 1 internal legal_framework document (no org, public visibility) with 1 version
    - Validates create_draft, new_draft, publish, list_versions, revert_to_version

This is NOT dummy lorem-ipsum content. The records contain real structural
metadata that validates constraints, relationships, and business methods.
"""
import sys
import os
from pathlib import Path
from datetime import date

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db import SessionLocal
from app.models.policy_document import PolicyDocument, PolicyDocumentVersion


def seed():
    db = SessionLocal()
    try:
        # Guard: skip if data already exists
        existing = db.query(PolicyDocument).filter(
            PolicyDocument.slug == "internal-ai-ethics-principles"
        ).first()
        if existing:
            print("Seed data already exists — skipping.")
            return

        # =====================================================================
        # 1. Ethics Policy document — exercises create_draft + new_draft + publish
        # =====================================================================
        print("Creating ethics policy document...")
        ethics_doc = PolicyDocument.create_draft(
            db,
            title="Internal AI Ethics Principles",
            doc_type="ethics_policy",
            content_markdown=(
                "## Purpose\n\n"
                "This document establishes core ethical principles for AI tool "
                "evaluation and deployment within journalism workflows.\n\n"
                "## Principles\n\n"
                "1. **Editorial sovereignty** — AI assists, never replaces, editorial judgement.\n"
                "2. **Transparency** — Disclose AI involvement in published work.\n"
                "3. **Data minimisation** — Only process data necessary for the task.\n"
                "4. **Accountability** — A named human is responsible for every AI-assisted output.\n"
            ),
            visibility="public",
            summary="Core ethical principles for responsible AI use in journalism.",
            source="Grounded Platform",
            publisher="Grounded Admin",
            publication_date=date(2026, 2, 7),
            jurisdiction="Global",
        )
        db.flush()
        print(f"  Created document: {ethics_doc.slug} (v1 draft)")

        # Publish v1
        v1 = ethics_doc.versions[0] if ethics_doc.versions else (
            db.query(PolicyDocumentVersion)
            .filter(PolicyDocumentVersion.document_id == ethics_doc.id)
            .first()
        )
        v1.publish(db)
        db.flush()
        print(f"  Published v1")

        # Create v2 draft with updated content
        v2 = ethics_doc.new_draft(
            db,
            content_markdown=(
                "## Purpose\n\n"
                "This document establishes core ethical principles for AI tool "
                "evaluation and deployment within journalism workflows.\n\n"
                "## Principles\n\n"
                "1. **Editorial sovereignty** — AI assists, never replaces, editorial judgement.\n"
                "2. **Transparency** — Disclose AI involvement in published work.\n"
                "3. **Data minimisation** — Only process data necessary for the task.\n"
                "4. **Accountability** — A named human is responsible for every AI-assisted output.\n"
                "5. **Bias awareness** — Actively test for and mitigate algorithmic bias.\n"
            ),
            change_notes="Added bias awareness principle (principle 5).",
            summary="Core ethical principles for responsible AI use in journalism.",
        )
        db.flush()
        print(f"  Created v2 draft (change: added principle 5)")

        # =====================================================================
        # 2. Legal Framework document — exercises create_draft with attribution
        # =====================================================================
        print("Creating legal framework document...")
        legal_doc = PolicyDocument.create_draft(
            db,
            title="EU AI Act Compliance Summary",
            doc_type="legal_framework",
            content_markdown=(
                "## Overview\n\n"
                "The EU AI Act (Regulation 2024/1689) establishes a risk-based "
                "regulatory framework for artificial intelligence systems.\n\n"
                "## Relevance to Journalism\n\n"
                "AI systems used in media content creation may be classified as "
                "limited-risk, requiring transparency obligations under Article 50.\n"
            ),
            visibility="public",
            summary="Summary of EU AI Act obligations relevant to journalism AI tools.",
            source="Official Journal of the European Union",
            publisher="European Parliament and Council",
            publication_date=date(2024, 7, 12),
            jurisdiction="EU",
            source_url="https://eur-lex.europa.eu/eli/reg/2024/1689/oj",
            license_notes="Public regulatory text; no copyright restrictions on factual summaries.",
        )
        db.flush()
        print(f"  Created document: {legal_doc.slug} (v1 draft)")

        # =====================================================================
        # 3. Validate business methods
        # =====================================================================
        print("\nValidating business methods...")

        # list_versions
        ethics_versions = ethics_doc.list_versions(db)
        assert len(ethics_versions) == 2, f"Expected 2 versions, got {len(ethics_versions)}"
        print(f"  list_versions: {len(ethics_versions)} versions ✓")

        # Version numbers
        assert ethics_versions[0].version_number == 2
        assert ethics_versions[1].version_number == 1
        print(f"  Version ordering (desc): v{ethics_versions[0].version_number}, v{ethics_versions[1].version_number} ✓")

        # Status checks
        assert ethics_versions[0].status == "draft"
        assert ethics_versions[1].status == "published"
        print(f"  Status: v2=draft, v1=published ✓")

        # current_version_id pointer
        assert ethics_doc.current_version_id == ethics_versions[1].id
        print(f"  current_version_id points to published v1 ✓")

        # revert_to_version
        v3 = ethics_doc.revert_to_version(db, version_number=1)
        db.flush()
        assert v3.version_number == 3
        assert v3.change_notes == "Reverted to version 1"
        assert v3.status == "draft"
        print(f"  revert_to_version(1) → v3 draft ✓")

        # Verify revert didn't delete anything
        all_versions = ethics_doc.list_versions(db)
        assert len(all_versions) == 3
        print(f"  Revert preserved all versions ({len(all_versions)} total) ✓")

        # Legal doc checks
        legal_versions = legal_doc.list_versions(db)
        assert len(legal_versions) == 1
        assert legal_versions[0].jurisdiction == "EU"
        assert legal_versions[0].source_url == "https://eur-lex.europa.eu/eli/reg/2024/1689/oj"
        print(f"  Legal doc attribution metadata intact ✓")

        # CHECK constraints
        assert ethics_doc.doc_type == "ethics_policy"
        assert legal_doc.doc_type == "legal_framework"
        assert ethics_doc.visibility == "public"
        print(f"  CHECK constraints valid ✓")

        # Commit everything
        db.commit()
        print("\nSeed data committed successfully.")

        # Summary
        print("\n--- Seed Summary ---")
        print(f"  PolicyDocuments: 2")
        print(f"    - {ethics_doc.slug} (ethics_policy, 3 versions)")
        print(f"    - {legal_doc.slug} (legal_framework, 1 version)")
        print(f"  PolicyDocumentVersions: 4 total")
        print(f"  All business methods validated.")

    except Exception as e:
        db.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
