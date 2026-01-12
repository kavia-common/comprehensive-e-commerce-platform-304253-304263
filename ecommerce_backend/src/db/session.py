"""
Database engine/session management for the FastAPI backend.

Connection string resolution order:
1) If the database container's db_connection.txt exists (monorepo path), parse it and use it.
   The file typically contains: `psql postgresql://user:pass@host:port/dbname`
2) Otherwise use DATABASE_URL env var if set.
3) Otherwise fallback to a safe local default (matches the provided database startup.sh).

We intentionally do NOT create tables from ORM models in this service because the DB
container owns schema creation and seeding.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def _parse_db_connection_txt(raw: str) -> Optional[str]:
    """Parse db_connection.txt contents and return a SQLAlchemy URL if possible."""
    raw = raw.strip()
    if not raw:
        return None

    # Common format: "psql postgresql://...."
    if raw.startswith("psql "):
        raw = raw[len("psql ") :].strip()

    # Accept both "postgresql://" and "postgres://"
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://") :]

    if raw.startswith("postgresql://"):
        return raw

    return None


def _find_db_connection_file() -> Optional[Path]:
    """
    Attempt to locate ecommerce_database/db_connection.txt within the monorepo.

    We keep this logic resilient to path differences by walking up from this file's
    location and looking for the known relative path within container workspaces.
    """
    this_file = Path(__file__).resolve()

    # Typical workspace layout:
    # .../comprehensive-e-commerce-platform-.../ecommerce_backend/src/db/session.py
    # .../comprehensive-e-commerce-platform-.../../comprehensive-e-commerce-platform-.../ecommerce_database/db_connection.txt
    for parent in [this_file] + list(this_file.parents):
        candidate = (
            parent
            / ".."
            / ".."
            / ".."
            / ".."
            / ".."
            / "comprehensive-e-commerce-platform-304253-304262"
            / "ecommerce_database"
            / "db_connection.txt"
        ).resolve()
        if candidate.exists():
            return candidate

        # More generic search: look for a sibling workspace with ecommerce_database/
        candidate2 = parent / "ecommerce_database" / "db_connection.txt"
        if candidate2.exists():
            return candidate2

    return None


def _resolve_database_url() -> str:
    """Resolve the database URL using db_connection.txt, env var, or fallback."""
    conn_file = _find_db_connection_file()
    if conn_file and conn_file.exists():
        raw = conn_file.read_text(encoding="utf-8")
        parsed = _parse_db_connection_txt(raw)
        if parsed:
            return parsed

    # ENV fallback (request from user/orchestrator if not present in .env)
    # The orchestrator should set DATABASE_URL in ecommerce_backend/.env when deploying.
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return _parse_db_connection_txt(env_url) or env_url

    # Local dev fallback matching ecommerce_database/startup.sh defaults.
    return "postgresql://appuser:dbuser123@localhost:5000/myapp"


# Create global engine/sessionmaker for dependency injection.
DATABASE_URL = _resolve_database_url()

_engine: Engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)


# PUBLIC_INTERFACE
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a SQLAlchemy session and ensures it's closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# PUBLIC_INTERFACE
def db_healthcheck() -> bool:
    """
    Perform a simple DB liveness check.

    Returns:
        bool: True if DB is reachable and responds to `SELECT 1`, else False.
    """
    try:
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
