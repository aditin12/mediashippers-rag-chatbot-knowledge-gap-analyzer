"""
diagnose_analytics.py
Run this to find out exactly why /analytics is returning "undefined" values.
Usage:  python diagnose_analytics.py
"""
import sys
import traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("STEP 1 — Can we import the settings / .env?")
print("=" * 70)
try:
    from config.settings import settings
    print("✅  .env loaded OK")
    print(f"    DB_HOST   = {settings.DB_HOST}")
    print(f"    DB_NAME   = {settings.DB_NAME}")
    print(f"    DB_USER   = {settings.DB_USER}")
except Exception:
    print("❌  FAILED loading config/settings.py")
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 70)
print("STEP 2 — Can we connect to PostgreSQL?")
print("=" * 70)
try:
    from database.postgres import engine, SessionLocal
    conn = engine.connect()
    print("✅  Postgres connection OK")
    conn.close()
except Exception:
    print("❌  FAILED connecting to PostgreSQL")
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 70)
print("STEP 3 — Does the query_logs table exist with the right columns?")
print("=" * 70)
try:
    from sqlalchemy import inspect
    insp = inspect(engine)
    tables = insp.get_table_names()
    print(f"    Tables found: {tables}")
    if "query_logs" not in tables:
        print("❌  query_logs table does NOT exist. Run reset step (see below).")
    else:
        cols = [c["name"] for c in insp.get_columns("query_logs")]
        print(f"    query_logs columns: {cols}")
        expected = {"id", "question", "answer", "score", "category",
                    "frequency", "first_seen", "last_seen"}
        missing = expected - set(cols)
        if missing:
            print(f"❌  query_logs is MISSING columns: {missing}")
            print("    -> Your table has a stale/old schema. Run the reset command below.")
        else:
            print("✅  query_logs schema looks correct")
except Exception:
    print("❌  FAILED inspecting query_logs table")
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 70)
print("STEP 4 — Can we actually run get_analytics_summary()?")
print("=" * 70)
try:
    from services.query_logger import get_analytics_summary
    result = get_analytics_summary()
    print("✅  get_analytics_summary() ran successfully!")
    print(f"    Result: {result}")
except Exception:
    print("❌  get_analytics_summary() THREW AN EXCEPTION — this is the real bug:")
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 70)
print("STEP 5 — How many rows are actually in query_logs right now?")
print("=" * 70)
try:
    from database.models import QueryLog
    db = SessionLocal()
    count = db.query(QueryLog).count()
    db.close()
    print(f"    {count} row(s) currently logged.")
    if count == 0:
        print("    ⚠️  No questions logged yet — ask the chatbot a few questions first,")
        print("       THEN check the Analytics tab. Zero rows still means real 0s, not 'undefined'.")
except Exception:
    print("❌  FAILED counting rows")
    traceback.print_exc()

print()
print("=" * 70)
print("DONE. If everything above shows ✅, the backend is fine and the issue")
print("is the browser hitting an OLD server process. Stop uvicorn completely")
print("(Ctrl+C) and restart it fresh, then hard-refresh the browser (Ctrl+Shift+R).")
print("=" * 70)
