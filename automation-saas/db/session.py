"""
Database session factory.

Provides:
  - engine:      SQLAlchemy engine bound to DATABASE_URL
  - SessionLocal: scoped session factory
  - get_db():    FastAPI dependency that yields a session
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from utils.config import settings

# Ensure the connection string uses the psycopg (v3) driver.
# If the user has "postgresql://" in .env, replace with "postgresql+psycopg://".
_db_url = settings.DATABASE_URL
if _db_url.startswith("postgresql://"):
    _db_url = _db_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine_kwargs = {"pool_pre_ping": True}
if _db_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_size"] = 20
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["pool_recycle"] = 1800 # Prevent stale connections

engine = create_engine(
    _db_url,
    **engine_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a DB session and closes on teardown."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
