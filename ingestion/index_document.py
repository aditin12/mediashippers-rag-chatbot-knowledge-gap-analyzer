"""
index_document.py
Reads training_docs/ → stores chunks in PostgreSQL (always)
                      → also pushes to AWS OpenSearch Serverless if configured
                      → also uploads originals to S3 if configured

Run: python -m ingestion.index_document
"""
import sys, re, uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.postgres import SessionLocal
from database.models   import Document
from services.document_loader import extract_text
from services.s3_service import upload_file
from services.opensearch_service import index_chunk, get_client as get_opensearch_client

TRAINING_DIR = Path(__file__).parent.parent / "training_docs"
CHUNK_SIZE   = 800
OVERLAP      = 100
SUPPORTED    = {".pdf", ".docx", ".txt", ".json", ".yaml", ".html"}

def chunk_text(text: str) -> list[str]:
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    chunks, start = [], 0
    while start < len(text):
        s = text[start:start+CHUNK_SIZE].strip()
        if s: chunks.append(s)
        start += CHUNK_SIZE - OVERLAP
    return chunks

def ingest():
    if not TRAINING_DIR.exists():
        print(f"\n❌  training_docs/ not found\n"); sys.exit(1)

    files = sorted(TRAINING_DIR.iterdir())
    print(f"\n📂  Found {len(files)} files in training_docs/\n")

    opensearch_available = get_opensearch_client() is not None
    print(f"🔍  OpenSearch: {'connected — will index for semantic search' if opensearch_available else 'not configured — PostgreSQL keyword search only'}\n")

    db = SessionLocal()
    total_pg = 0
    total_os = 0

    try:
        for f in files:
            if f.suffix.lower() not in SUPPORTED:
                print(f"  SKIPPED : {f.name}")
                continue

            print(f"  Reading : {f.name} ...", end="  ", flush=True)
            try:
                text   = extract_text(str(f))
                chunks = chunk_text(text)

                if not chunks:
                    print("SKIPPED (empty)")
                    continue

                # Upload original file to S3 (optional — skipped if not configured)
                s3_uri = upload_file(f)

                # Delete old PostgreSQL chunks for this file, then re-insert
                db.query(Document).filter(Document.source_file == f.name).delete()
                db.commit()

                os_indexed = 0
                for i, chunk in enumerate(chunks):
                    doc_name = f"{f.stem} (chunk {i+1})"

                    db.add(Document(
                        document_name=doc_name,
                        source_file=f.name,
                        s3_uri=s3_uri,
                        content=chunk,
                    ))

                    if opensearch_available:
                        chunk_id = f"{f.stem}-{i+1}-{uuid.uuid4().hex[:8]}"
                        if index_chunk(chunk_id, chunk, f.name, doc_name):
                            os_indexed += 1

                db.commit()
                total_pg += len(chunks)
                total_os += os_indexed

                if opensearch_available:
                    print(f"{len(chunks)} chunks → PostgreSQL ✅  |  {os_indexed} → OpenSearch ✅")
                else:
                    print(f"{len(chunks)} chunks → PostgreSQL ✅")

            except Exception as e:
                print(f"ERROR: {e}")
                db.rollback()
    finally:
        db.close()

    print(f"\n✅  Done!")
    print(f"    PostgreSQL chunks : {total_pg}")
    if opensearch_available:
        print(f"    OpenSearch chunks : {total_os}")
    print()

if __name__ == "__main__":
    ingest()
