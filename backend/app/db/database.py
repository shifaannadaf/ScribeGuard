"""SQLAlchemy engine, session factory, and declarative Base."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings


# Pool sizing is only meaningful for client/server databases. SQLite (used
# in some test setups) uses SingletonThreadPool which doesn't accept those
# kwargs, so we only set them when the URL clearly points at a real DB.
_engine_kwargs: dict = {"pool_pre_ping": True, "future": True}
if not settings.DATABASE_URL.startswith("sqlite"):
    _engine_kwargs.update({"pool_size": 10, "max_overflow": 20})
engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Single declarative base shared by every model."""
    pass


def get_db():
    """FastAPI dependency that yields a SQLAlchemy session and closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
