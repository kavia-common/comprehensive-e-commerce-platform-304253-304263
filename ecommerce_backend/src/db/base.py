"""
SQLAlchemy declarative base shared by all ORM models.

We only define mappings here; the database schema already exists and is created/seeded
by the `ecommerce_database` container. We do NOT run migrations from this service.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Naming conventions help Alembic/migrations; even though we don't generate migrations,
# they also make reflection/debugging more consistent across environments.
_NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base for ORM models."""

    metadata = MetaData(naming_convention=_NAMING_CONVENTION)
