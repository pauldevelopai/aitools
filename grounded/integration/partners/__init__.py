"""
GROUNDED Integration Partners - Partner integration framework.

Contains protocol definitions and base classes for partner
integrations with the GROUNDED infrastructure.
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
