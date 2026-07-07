"""
embedding_service.py
Generates 384-dim embeddings using sentence-transformers (all-MiniLM-L6-v2).
Loaded once and reused — model download happens automatically on first run (~90MB).
"""

_model = None

def get_model():
    global _model
    if _model is None:
        print("📦  Loading embedding model (all-MiniLM-L6-v2)...", end="  ", flush=True)
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        print("✅")
    return _model

def embed_text(text: str) -> list[float]:
    model = get_model()
    return model.encode(text, normalize_embeddings=True).tolist()

def embed_batch(texts: list[str]) -> list[list[float]]:
    model = get_model()
    return model.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False).tolist()
