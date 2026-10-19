"""Database setup — SQLAlchemy engine, session, and base model."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, sessionmaker

from app.config import get_settings

settings = get_settings()


class Base(MappedAsDataclass, DeclarativeBase):
    """Base class for all ORM models."""


# Create engine
engine = create_engine(
    str(settings.database_url),
    echo=settings.db_echo,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db():
    """Yield a database session for dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Call on startup for development."""
    Base.metadata.create_all(bind=engine)
