"""
Convenience bootstrap that creates the database schema in one shot.

Production deployments should prefer Alembic:

    alembic upgrade head

This script remains for quick local setup / first-time bring-up where the
developer wants `python create_tables.py` to "just work".
"""
from __future__ import annotations

from app.db.database import Base, engine
import app.models  # noqa: F401  -- registers every model


def main() -> None:
    print("Creating ScribeGuard agentic schema...")
    Base.metadata.create_all(bind=engine)
    print("Done. Tables:")
    for t in Base.metadata.sorted_tables:
        print(f"  ✓ {t.name}")


if __name__ == "__main__":
    main()
