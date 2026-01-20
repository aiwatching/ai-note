"""Database connection and session management."""
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .config import get_settings

settings = get_settings()

# Ensure database directory exists
db_path = Path(settings.database_url.replace("sqlite:///", ""))
db_path.parent.mkdir(parents=True, exist_ok=True)

# Create engine with SQLite specific settings
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # Needed for SQLite
    echo=settings.debug,
)


# Enable foreign key constraints for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    # Import all models to ensure they are registered
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
