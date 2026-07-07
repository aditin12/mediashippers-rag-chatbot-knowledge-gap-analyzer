import google.generativeai as genai
from config.settings import settings

genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

def generate_answer(question: str, context: str) -> str:
    prompt = f"""You are a MediaShippers Help Assistant.

STRICT RULES:
- Answer ONLY using the documentation provided below.
- Never use external knowledge or guess.
- Answer ONLY questions about the MediaShippers platform — deals, rights, payments, content submissions, buyer/seller rules.
- If the answer is not in the documentation, respond exactly: "I could not find this information in the MediaShippers documentation."
- Keep answers concise and factual. Use bullet points for lists.

DOCUMENTATION:
{context}

QUESTION:
{question}"""

    response = model.generate_content(prompt)
    return response.text
