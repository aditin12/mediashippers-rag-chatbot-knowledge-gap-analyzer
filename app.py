from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from config.settings import settings

app = FastAPI(title="MediaShippers RAG Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routes MUST be included before any static mount ───────────────────────
try:
    from routes.chatbot import router
    app.include_router(router)
    print("✅  Routes loaded: /chat  /analytics  /unanswered  /export-excel")
except Exception as e:
    import traceback
    print(f"❌  FAILED to load routes: {e}")
    traceback.print_exc()

# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "storage": "PostgreSQL", "llm": "gemini-2.0-flash"}

# ── Frontend: serve index.html at root, then static files ────────────────────
FRONTEND = Path(__file__).parent / "frontend"

@app.get("/")
def serve_frontend():
    return FileResponse(str(FRONTEND / "index.html"))

# Static mount LAST — must come after all API routes
if FRONTEND.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")

# ── Startup banner ────────────────────────────────────────────────────────────
print("\n🚀  MediaShippers RAG Chatbot starting...")
if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your-gemini-api-key-here":
    print("⚠️   GEMINI_API_KEY not set")
else:
    print("✅  Gemini API key loaded")
if not settings.OPENSEARCH_HOST:
    print("⚠️   OPENSEARCH_HOST not set — using PostgreSQL fallback")
else:
    print(f"✅  OpenSearch host: {settings.OPENSEARCH_HOST}")
print(f"✅  PostgreSQL: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
print(f"🌐  Open http://localhost:8000 in your browser\n")

try:
    from services.query_logger import print_report
    print_report()
except Exception:
    pass