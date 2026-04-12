from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Load database URL from environment variable
# Format: postgresql://username:password@host:port/database_name
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/soap_notes_db"
)

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Each request gets its own session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all ORM models
Base = declarative_base()


def get_db():
    """
    Dependency for FastAPI routes.
    Usage in a route:
        from database.database import get_db
        from sqlalchemy.orm import Session
        from fastapi import Depends

        @app.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Creates all tables in the database.
    Call this once on app startup.
    """
    from database.models import Transcript, GeneratedNote, PhysicianEdit, AuditLog  # noqa: F401
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    print("Creating tables...")
    create_tables()
    print("✅ All tables created successfully.")
