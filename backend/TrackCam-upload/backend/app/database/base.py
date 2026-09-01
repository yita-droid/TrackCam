"""
Declarative base for all SQLAlchemy ORM models.

Every model in app/models/*.py must import `Base` from here and inherit
from it, so that Alembic autogeneration (env.py) and `Base.metadata.create_all`
can discover every table from a single source of truth.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base class for all ORM models."""
    pass
