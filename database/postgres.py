from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import settings

DATABASE_URL = (
    f"postgresql://{settings.DB_USER}:"
    f"{settings.DB_PASSWORD}@"
    f"{settings.DB_HOST}:"
    f"{settings.DB_PORT}/"
    f"{settings.DB_NAME}"
)

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from database.models import Base, QueryLog
Base.metadata.create_all(bind=engine)

# ── Self-heal query_logs schema ─────────────────────────────────────────────
# create_all() only creates tables that don't exist yet — it never alters an
# existing table. If query_logs was created earlier with a different/partial
# schema (e.g. during development), every read/write against it would keep
# silently failing forever. Detect that here and auto-fix it once at startup.
try:
    from sqlalchemy import inspect as _inspect
    _insp = _inspect(engine)
    if "query_logs" in _insp.get_table_names():
        _existing_cols = {c["name"] for c in _insp.get_columns("query_logs")}
        _expected_cols = {c.name for c in QueryLog.__table__.columns}
        if not _expected_cols.issubset(_existing_cols):
            print(f"⚠️  query_logs schema is stale (missing {_expected_cols - _existing_cols}). "
                  f"Recreating table automatically...")
            QueryLog.__table__.drop(bind=engine, checkfirst=True)
            QueryLog.__table__.create(bind=engine, checkfirst=True)
            print("✅  query_logs table rebuilt with correct schema.")
except Exception as _e:
    print(f"⚠️  query_logs self-heal check failed (non-fatal): {_e}")
