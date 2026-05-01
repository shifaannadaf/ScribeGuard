"""
Production schema bootstrap.

ScribeGuard is a production clinical system — it does NOT seed fake
patient encounters into the database. This script only ensures every
table exists (idempotent) so a fresh deployment can start serving
real intake calls immediately.

Use Alembic in production:

    alembic upgrade head

This script remains for first-time local bring-up:

    python seed.py
"""
from __future__ import annotations

from app.db.database import Base, engine
import app.models  # noqa: F401  -- registers every model on Base.metadata


def ensure_schema() -> None:
    print("Ensuring ScribeGuard schema is present (idempotent)...")
    Base.metadata.create_all(bind=engine)
    for t in Base.metadata.sorted_tables:
        print(f"  ✓ {t.name}")
    print("Schema ready. No demo data inserted (this is a production system).")


if __name__ == "__main__":
    ensure_schema()
