"""
Drop-and-recreate the ScribeGuard database schema.

The agentic refactor introduced a new schema that the original baseline
database cannot be reconciled with by ALTER alone (new enum values,
several new tables, renamed columns). Use this script ONLY in
development to rebuild the schema from scratch:

    python reset_db.py

It deletes the public schema in the configured database and recreates
every table cleanly. There is intentionally no skip-prompt: this is
destructive.
"""
from __future__ import annotations

from sqlalchemy import text

from app.config import settings
from app.db.database import Base, engine
import app.models  # noqa: F401  -- registers every model on Base.metadata


def main() -> None:
    print(f"Resetting schema on {settings.DATABASE_URL!r}...")
    confirm = input("This DROPs the entire 'public' schema. Type 'RESET' to proceed: ").strip()
    if confirm != "RESET":
        print("Aborted.")
        return

    with engine.begin() as conn:
        # Postgres-specific: nuke every table + every custom enum cleanly.
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))

    Base.metadata.create_all(bind=engine)
    print("Done. Schema recreated. Tables:")
    for t in Base.metadata.sorted_tables:
        print(f"  ✓ {t.name}")


if __name__ == "__main__":
    main()
