"""
GROUNDED Integration - Partner and external integration framework.

Provides infrastructure for partner integrations, API adapters,
and external service connections.

Usage:
    from grounded.integration import BasePartnerIntegration, PartnerInfo
    from grounded.integration.adapters.fastapi import audit_endpoint
"""

from grounded.integration.partners.base import (
    BasePartnerIntegration,
    PartnerInfo,
    PartnerCapability,
    PartnerStatus,
)

__all__ = [
    "BasePartnerIntegration",
    "PartnerInfo",
    "PartnerCapability",
    "PartnerStatus",
]
