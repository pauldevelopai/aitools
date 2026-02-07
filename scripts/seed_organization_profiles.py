#!/usr/bin/env python3
"""Seed organization profiles and link users for validation.

Usage:
    python scripts/seed_organization_profiles.py

Creates:
    - 2 organization profiles (Reuters, BBC World Service)
    - Validates create, edit, user linkage
    - Idempotent (skips if data already exists)
"""
import sys
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db import SessionLocal
from app.models.organization_profile import OrganizationProfile
from app.models.auth import User


def seed():
    db = SessionLocal()
    try:
        # Guard: skip if data already exists
        existing = db.query(OrganizationProfile).filter(
            OrganizationProfile.slug == "reuters"
        ).first()
        if existing:
            print("Seed data already exists — skipping.")
            return

        # =====================================================================
        # 1. Create organization profiles
        # =====================================================================
        print("Creating organization profiles...")

        reuters = OrganizationProfile(
            name="Reuters",
            slug=OrganizationProfile.generate_slug("Reuters"),
            country="United Kingdom",
            jurisdiction="Global",
            sector="newsroom",
            size="enterprise",
            risk_tolerance="low",
            description="Global news agency providing trusted journalism worldwide.",
        )
        db.add(reuters)

        bbc = OrganizationProfile(
            name="BBC World Service",
            slug=OrganizationProfile.generate_slug("BBC World Service"),
            country="United Kingdom",
            jurisdiction="EU",
            sector="newsroom",
            size="large",
            risk_tolerance="medium",
            description="International broadcaster delivering news and analysis.",
        )
        db.add(bbc)
        db.flush()

        print(f"  Created: {reuters.slug} (sector={reuters.sector}, size={reuters.size})")
        print(f"  Created: {bbc.slug} (sector={bbc.sector}, size={bbc.size})")

        # =====================================================================
        # 2. Validate model constraints
        # =====================================================================
        print("\nValidating constraints...")

        assert reuters.sector == "newsroom"
        assert bbc.risk_tolerance == "medium"
        assert reuters.slug != bbc.slug
        print("  CHECK constraints valid")

        # Verify slug generation
        slug = OrganizationProfile.generate_slug("Test Org With Special Ch@rs!")
        assert slug == "test-org-with-special-chrs"
        print(f"  Slug generation: '{slug}'")

        # =====================================================================
        # 3. Test user linkage (if users exist)
        # =====================================================================
        print("\nChecking user linkage...")
        first_user = db.query(User).first()
        if first_user:
            original_org = first_user.organization_profile_id
            first_user.organization_profile_id = reuters.id
            db.flush()
            assert first_user.organization_profile_id == reuters.id
            print(f"  Linked user '{first_user.username}' to {reuters.name}")

            # Restore original
            first_user.organization_profile_id = original_org
            db.flush()
            print(f"  Restored user's original org assignment")
        else:
            print("  No users found — skipping linkage test")

        # Commit everything
        db.commit()
        print("\nSeed data committed successfully.")

        # Summary
        print("\n--- Seed Summary ---")
        print(f"  OrganizationProfiles: 2")
        print(f"    - {reuters.slug} ({reuters.sector}, {reuters.size})")
        print(f"    - {bbc.slug} ({bbc.sector}, {bbc.size})")
        print(f"  All constraints validated.")

    except Exception as e:
        db.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
