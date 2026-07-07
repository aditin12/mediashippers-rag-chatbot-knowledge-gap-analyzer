"""
opensearch_service.py
----------------------
k-NN vector retrieval against AWS OpenSearch Serverless.
Returns [] (not an exception) whenever OpenSearch isn't reachable,
so the rest of the app can fall back to PostgreSQL keyword search.
"""

from config.settings import settings
from services.embedding_service import embed_text

INDEX_NAME = "mediashippers-docs"

_client = None

def get_client():
    global _client
    if _client is not None:
        return _client
    try:
        if not settings.OPENSEARCH_HOST or "your-" in settings.OPENSEARCH_HOST:
            return None

        import boto3
        from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

        credentials = boto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        ).get_credentials()

        auth = AWSV4SignerAuth(credentials, settings.AWS_REGION, "aoss")

        _client = OpenSearch(
            hosts=[{"host": settings.OPENSEARCH_HOST, "port": 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=15,
        )
        return _client
    except Exception as e:
        print(f"⚠️  OpenSearch client init failed: {e}")
        return None


def index_chunk(chunk_id: str, text: str, source_file: str, document_name: str) -> bool:
    """Embed a chunk and index it into OpenSearch. Returns True on success."""
    client = get_client()
    if not client:
        return False
    try:
        vector = embed_text(text)
        # AWS OpenSearch Serverless does not support explicit document IDs
        # so we omit the id parameter entirely
        client.index(
            index=INDEX_NAME,
            body={
                "text": text,
                "source_file": source_file,
                "document_name": document_name,
                "embedding": vector,
            },
        )
        return True
    except Exception as e:
        print(f"    ⚠️  OpenSearch index failed for chunk: {e}")
        return False


def search(query: str, top_k: int = 5) -> list[dict]:
    """
    k-NN semantic search. Returns list of {text, source_file, document_name, score}.
    Returns [] if OpenSearch is unreachable — caller should fall back.
    """
    client = get_client()
    if not client:
        return []
    try:
        vector = embed_text(query)
        body = {
            "size": top_k,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": vector,
                        "k": top_k,
                    }
                }
            },
            "_source": ["text", "source_file", "document_name"],
        }
        res  = client.search(index=INDEX_NAME, body=body)
        hits = res["hits"]["hits"]
        return [
            {
                "text":          h["_source"]["text"],
                "source_file":   h["_source"]["source_file"],
                "document_name": h["_source"]["document_name"],
                "score":         h["_score"],
            }
            for h in hits
        ]
    except Exception as e:
        print(f"⚠️  OpenSearch search failed: {e}")
        return []
