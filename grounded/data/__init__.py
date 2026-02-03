"""
GROUNDED Data - Data pipeline abstractions.

Provides protocol-based interfaces for data sources and pipelines,
enabling pluggable data ingestion and processing.

This module is currently a stub for future implementation.
"""

from grounded.data.sources.base import BaseDataSource, DataSourceInfo

__all__ = [
    "BaseDataSource",
    "DataSourceInfo",
]
