"""
retrieval_service.py
---------------------
retrieve_documents() is the single retrieval entry point used by routes/chatbot.py.

Order of attempts:
  1. AWS OpenSearch Serverless — semantic k-NN vector search (best quality)
  2. PostgreSQL keyword search — fallback if OpenSearch unavailable/unconfigured

Both paths return a list of lightweight objects with .content, .source_file,
.document_name attributes so the caller code never needs to know which
backend actually served the result.
"""

import re
from database.postgres import SessionLocal
from database.models import Document
from services.opensearch_service import search as opensearch_search

STOP_WORDS = {
    "how", "do", "i", "the", "is", "are", "a", "an", "to",
    "of", "for", "in", "on", "and", "what", "where", "when",
    "can", "will", "does", "my", "me", "you", "it", "this", "that"
}


class RetrievedChunk:
    """Lightweight stand-in so OpenSearch results look like Document rows."""
    def __init__(self, content, source_file, document_name, score=None):
        self.content       = content
        self.source_file   = source_file
        self.document_name = document_name
        self.score         = score


def _retrieve_from_opensearch(query: str, top_k: int):
    hits = opensearch_search(query, top_k)
    if not hits:
        return []
    return [
        RetrievedChunk(h["text"], h["source_file"], h["document_name"], h.get("score"))
        for h in hits
    ]


def _retrieve_from_postgres(query: str, top_k: int):
    db = SessionLocal()
    try:
        documents = db.query(Document).all()
        keywords  = [
            w for w in re.findall(r"\w+", query.lower())
            if w not in STOP_WORDS
        ]
        matches = []
        for doc in documents:
            score   = 0
            content = (doc.content or "").lower()
            for word in keywords:
                if word in doc.document_name.lower(): score += 10
                if word in doc.source_file.lower():   score += 5
                score += content.count(word)
            if score > 0:
                matches.append((score, doc))
        matches.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in matches[:top_k]]
    finally:
        db.close()


def top_score(documents) -> float:
    """
    Best relevance score among retrieved documents, used for the 0.45
    knowledge-gap / irrelevant-question threshold.

    OpenSearch hits carry a real k-NN similarity score (0-1 range).
    PostgreSQL keyword-fallback hits don't have a comparable score, so any
    match found there is treated as relevant (1.0) — the keyword match
    itself is the relevance signal in that path.
    """
    if not documents:
        return 0.0
    scores = []
    for doc in documents:
        s = getattr(doc, "score", None)
        scores.append(s if s is not None else 1.0)
    return max(scores)


def retrieve_documents(query: str, top_k: int = 5):
    """
    Primary retrieval function. Tries OpenSearch first (semantic search),
    falls back to PostgreSQL keyword search if OpenSearch returns nothing
    (e.g. not configured yet, or this query has zero embedding matches).
    """
    results = _retrieve_from_opensearch(query, top_k)
    if results:
        return results
    return _retrieve_from_postgres(query, top_k)
