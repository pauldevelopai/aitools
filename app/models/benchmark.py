"""Benchmarking models for anonymous peer comparison."""
import uuid
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db import Base


class OrgBenchmark(Base):
    """Individual organisation's benchmark snapshot."""

    __tablename__ = "org_benchmarks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    adoption_stage = Column(Float, nullable=False)  # 1.0 - 5.0
    dimension_scores = Column(JSONB, nullable=False)  # same 5 dims as readiness
    sector = Column(String, nullable=True)
    country = Column(String, nullable=True)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SectorBenchmarkAggregate(Base):
    """Aggregated benchmark stats per sector/country.

    Recalculated periodically. Requires minimum sample_count
    for anonymity.
    """

    __tablename__ = "sector_benchmark_aggregates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sector = Column(String, nullable=False, index=True)
    country = Column(String, nullable=True)  # null = global
    avg_stage = Column(Float, nullable=False)
    median_stage = Column(Float, nullable=False)
    sample_count = Column(Integer, nullable=False)
    dimension_averages = Column(JSONB, nullable=False)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
