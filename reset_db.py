"""
reset_db.py
Drops and recreates all tables in PostgreSQL.
Run this ONCE before running ingest for the first time,
or whenever you get database schema errors.

Usage: python reset_db.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from database.postgres import engine
from database.models import Base

print("\n⚠️  Dropping all tables...")
Base.metadata.drop_all(bind=engine)
print("✅  Tables dropped.")

print("🔧  Creating fresh tables...")
Base.metadata.create_all(bind=engine)
print("✅  Tables created successfully!")
print("\nNow run: python -m ingestion.index_document\n")
