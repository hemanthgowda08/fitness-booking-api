
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fitness.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 15})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for the application's SQLAlchemy models."""


def get_db():
    """Provide one database session per request."""
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
