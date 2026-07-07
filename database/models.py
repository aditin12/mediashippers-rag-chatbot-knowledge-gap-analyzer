from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"
    id            = Column(Integer, primary_key=True, index=True)
    document_name = Column(String, nullable=False)
    source_file   = Column(String, nullable=False)
    s3_uri        = Column(String, nullable=True, default="")
    content       = Column(Text, nullable=True)
    uploaded_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class QueryLog(Base):
    """
    Logs EVERY incoming chat question (relevant + irrelevant, answered +
    unanswered) for the Knowledge Gap Analytics dashboard.

    category:
      - "answered_relevant"  -> score >= 0.45 AND Gemini gave a confident answer
      - "knowledge_gap"      -> score >= 0.45 BUT Gemini could not answer confidently
      - "irrelevant"         -> score <  0.45 (or off-topic / no retrieval hits at all)
    """
    __tablename__ = "query_logs"
    id          = Column(Integer, primary_key=True, index=True)
    question    = Column(Text, nullable=False)
    answer      = Column(Text, nullable=True)
    score       = Column(Float, nullable=True)
    category    = Column(String, nullable=False)   # answered_relevant | knowledge_gap | irrelevant
    frequency   = Column(Integer, default=1)
    first_seen  = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen   = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class UnansweredQuery(Base):
    __tablename__ = "unanswered_queries"
    id            = Column(Integer, primary_key=True, index=True)
    question      = Column(Text, nullable=False)
    response      = Column(Text, nullable=True)
    confidence    = Column(String, nullable=False)
    reason        = Column(String, nullable=True)
    frequency     = Column(Integer, default=1)
    first_seen    = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen     = Column(DateTime, default=lambda: datetime.now(timezone.utc))
