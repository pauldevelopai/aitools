"""Database configuration - re-exports from app.db for backwards compatibility.

DEPRECATED: Import directly from app.db instead.
"""
from app.db import Base, get_db

# Re-export for backwards compatibility
__all__ = ['Base', 'get_db']
