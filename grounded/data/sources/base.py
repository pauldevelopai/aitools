"""
GROUNDED Data Source Base - Protocol definitions for data sources.

Defines the interfaces (protocols) that data sources must implement,
enabling pluggable data ingestion throughout the GROUNDED infrastructure.

This module is a stub for future implementation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Protocol, runtime_checkable

from grounded.core.base import GroundedComponent, HealthCheckResult


class DataSourceType(Enum):
    """Types of data sources supported by GROUNDED."""

    FILE = "file"
    DATABASE = "database"
    API = "api"
    STREAM = "stream"
    WEBHOOK = "webhook"


@dataclass
class DataSourceInfo:
    """Information about a data source."""

    name: str
    source_type: DataSourceType
    description: str = ""
    schema_version: str = "1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_sync: Optional[datetime] = None


@dataclass
class DataRecord:
    """A single record from a data source."""

    id: str
    source: str
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@runtime_checkable
class DataSourceProtocol(Protocol):
    """
    Protocol for data sources.

    Any class implementing this protocol can be used as a data source
    in the GROUNDED infrastructure.
    """

    @property
    def info(self) -> DataSourceInfo:
        """Get data source information."""
        ...

    def fetch(self, limit: Optional[int] = None) -> List[DataRecord]:
        """
        Fetch records from the data source.

        Args:
            limit: Maximum number of records to fetch

        Returns:
            List of data records
        """
        ...

    def fetch_iter(self, batch_size: int = 100) -> Iterator[DataRecord]:
        """
        Iterate over records from the data source.

        Args:
            batch_size: Number of records per batch

        Yields:
            Individual data records
        """
        ...


class BaseDataSource(GroundedComponent, ABC):
    """
    Base class for data sources.

    Extends GroundedComponent to add data source-specific utilities.
    Concrete data sources should inherit from this class.

    This is a stub class for future implementation.

    Example:
        class MyDataSource(BaseDataSource):
            @property
            def name(self) -> str:
                return "my_source"

            @property
            def info(self) -> DataSourceInfo:
                return DataSourceInfo(
                    name=self.name,
                    source_type=DataSourceType.API,
                    description="My custom data source"
                )

            def fetch(self, limit=None) -> List[DataRecord]:
                # Fetch implementation
                return []
    """

    def __init__(self, source_type: DataSourceType, description: str = ""):
        """
        Initialize the data source.

        Args:
            source_type: The type of data source
            description: Human-readable description
        """
        self._source_type = source_type
        self._description = description
        self._last_sync: Optional[datetime] = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Data source name identifier."""
        ...

    @property
    def info(self) -> DataSourceInfo:
        """Get data source information."""
        return DataSourceInfo(
            name=self.name,
            source_type=self._source_type,
            description=self._description,
            last_sync=self._last_sync,
        )

    @abstractmethod
    def fetch(self, limit: Optional[int] = None) -> List[DataRecord]:
        """
        Fetch records from the data source.

        Args:
            limit: Maximum number of records to fetch

        Returns:
            List of data records
        """
        ...

    def fetch_iter(self, batch_size: int = 100) -> Iterator[DataRecord]:
        """
        Iterate over records from the data source.

        Default implementation fetches all and iterates.
        Override for more efficient streaming implementations.

        Args:
            batch_size: Number of records per batch

        Yields:
            Individual data records
        """
        records = self.fetch()
        yield from records

    async def fetch_async(self, limit: Optional[int] = None) -> List[DataRecord]:
        """
        Async version of fetch.

        Default implementation calls sync version.
        Override for true async implementations.

        Args:
            limit: Maximum number of records to fetch

        Returns:
            List of data records
        """
        return self.fetch(limit=limit)

    async def fetch_iter_async(self, batch_size: int = 100) -> AsyncIterator[DataRecord]:
        """
        Async iterator over records from the data source.

        Args:
            batch_size: Number of records per batch

        Yields:
            Individual data records
        """
        records = await self.fetch_async()
        for record in records:
            yield record

    def mark_synced(self) -> None:
        """Mark the data source as synced."""
        self._last_sync = datetime.utcnow()
