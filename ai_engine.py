
import requests
from typing import List
from config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL_NAME, LLM_TEMPERATURE
from database import search_chunks, get_chunk_by_id

SYSTEM_PROMPT_ANSWER_ENGINE = (
    "You are a senior pharmaceutical expert. Answer questions using ONLY the "
    "context provided from reference documents plus your core domain expertise. "
    "If you are not sure, clearly say you are not sure. Always be practical, regulatory-"
    "compliant and concise."
)

SYSTEM_PROMPT_SOP = (
    "You are a pharma documentation specialist. Draft detailed, step-wise SOPs "
    "in clean professional English suitable for regulated environments. Follow "
    "WHO / EU / USFDA / Schedule M expectations where applicable."
)

def _call_llm(messages: List[dict]) -> str:
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL_NAME,
        "messages": messages,
        "temperature": LLM_TEMPERATURE,
    }
    resp = requests.post(LLM_API_BASE, json=payload, headers=headers, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    # Adapt depending on provider format
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        return str(data)

def answer_with_context(question: str) -> str:
    rows = search_chunks(question, limit=5)
    context_parts = []
    for row in rows:
        chunk_id = row["rowid"]
        chunk = get_chunk_by_id(chunk_id)
        if chunk:
            context_parts.append(chunk["content"])

    context_text = "\n\n---\n\n".join(context_parts) if context_parts else "(No specific document context found.)"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_ANSWER_ENGINE},
        {
            "role": "user",
            "content": (
                "Question:\n" + question + "\n\n"
                "Context extracted from pharma reference PDFs:\n"
                + context_text
            ),
        },
    ]
    return _call_llm(messages)

def generate_sop(topic: str, extra_details: str = "") -> str:
    user_prompt = (
        f"Draft a detailed SOP for: {topic}.\n"
        f"Additional details: {extra_details}\n\n"
        "Structure with the following sections where applicable: "
        "1. Purpose 2. Scope 3. Responsibility 4. Definitions 5. Procedure "
        "6. Precautions / Safety 7. Records 8. References."
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_SOP},
        {"role": "user", "content": user_prompt},
    ]
    return _call_llm(messages)
