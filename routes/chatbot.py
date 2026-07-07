import re
from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel
from services.retrieval_service import retrieve_documents, top_score
from services.gemini_service import generate_answer
from services.query_logger import (
    log_query, print_report, get_all_unanswered,
    export_to_excel, log_analytics, get_analytics_summary, get_activity_data,
)

router = APIRouter()

OFF_TOPIC = re.compile(
    r"\b(weather|recipe|cook|food|sport|cricket|football|netflix|hotstar|"
    r"instagram|facebook|twitter|whatsapp|joke|jokes|poem|story|essay|"
    r"javascript|java|sql|hospital|doctor|medicine|health|"
    r"news|politics|election|stock|crypto|bitcoin|bank|loan|tax|"
    r"exam|college|university|school|game|music|song|celebrity|"
    r"actress|actor|bollywood|hollywood)\b",
    re.IGNORECASE
)

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []

@router.post("/chat")
def chat(request: ChatRequest):
    try:
        message = request.message.strip()
        if not message:
            return {"answer": "Please type a question.", "sources": []}

        # Off-topic check
        if OFF_TOPIC.search(message):
            ans = ("I can only help with MediaShippers-related questions — "
                   "deals, rights, payments, content submissions, and buyer/seller rules.")
            log_query(message, ans, 0, out_of_scope=True)
            log_analytics(message, ans, score=0.0, retrieved_count=0, out_of_scope=True)
            return {"answer": ans, "sources": []}

        # Retrieve documents from OpenSearch (or Postgres fallback)
        documents = retrieve_documents(message)
        score = top_score(documents)

        # No documents found at all
        if not documents:
            ans = "I could not find this information in the MediaShippers documentation."
            log_query(message, ans, 0)
            log_analytics(message, ans, score=0.0, retrieved_count=0)
            return {"answer": ans, "sources": []}

        # Documents found — always answer. Score only used for analytics.
        context = "\n\n".join(doc.content or "" for doc in documents)
        answer = generate_answer(message, context)
        sources = list(dict.fromkeys(doc.source_file for doc in documents))

        log_query(message, answer, len(documents))
        log_analytics(message, answer, score=score, retrieved_count=len(documents))
        return {"answer": answer, "sources": sources}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"answer": f"Server error: {str(e)}", "sources": []}

@router.get("/unanswered")
def unanswered():
    print_report()
    rows = get_all_unanswered()
    return {
        "total": len(rows),
        "queries": [
            {"question": r.question, "confidence": r.confidence,
             "reason": r.reason, "frequency": r.frequency,
             "first_seen": str(r.first_seen), "last_seen": str(r.last_seen)}
            for r in rows
        ]
    }

@router.get("/analytics")
def analytics():
    return get_analytics_summary()

@router.get("/analytics/activity")
def activity(from_date: str = None, to_date: str = None):
    return get_activity_data(from_date=from_date, to_date=to_date)

@router.get("/export-excel")
def export_excel():
    path = export_to_excel()
    if path:
        return FileResponse(
            path, filename="unanswered_queries.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    return {"error": "Export failed. Check terminal for details."}
