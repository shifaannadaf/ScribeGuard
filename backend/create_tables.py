"""
Run this script once to create all tables in the database.
Usage: python create_tables.py
"""
from app.db.database import engine, Base
import app.models.models  # noqa: F401 — registers all models with Base

if __name__ == "__main__":
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Done. Tables created:")
    for table in Base.metadata.sorted_tables:
        print(f"  ✓ {table.name}")
