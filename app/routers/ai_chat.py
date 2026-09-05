"""Admin AI assistant — a Groq-powered helper for the Thibitisha dashboard.

Lets a shift admin chat with the same Groq model used for equipment questions.
The assistant receives a live snapshot of the facility so its answers are
grounded in the current incident and equipment state.
"""

import logging
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.database import SessionLocal
from app.models import Equipment, Incident
from app.services.ai import _client

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str
    model: str


def _plant_context() -> str:
    """Compact snapshot of the facility used to ground assistant answers."""
    db = SessionLocal()
    try:
        equipment_count = db.query(Equipment).count()
        open_incidents = (
            db.query(Incident)
            .filter(Incident.status.in_(["NEW", "ACKNOWLEDGED", "UNDER_REPAIR"]))
            .order_by(Incident.reported_at.desc())
            .limit(8)
            .all()
        )
        lines = [f"Equipment registered: {equipment_count}"]
        lines.append("Most recent open incidents (id, equipment, status, category, message, channel):")
        if not open_incidents:
            lines.append("- (none open right now)")
        for inc in open_incidents:
            code = inc.equipment.code if inc.equipment else "Unassigned"
            lines.append(
                f"- #{inc.id} {code} [{inc.status}] ({inc.category or 'uncategorised'}): "
                f"{inc.original_message[:80]} via {inc.channel}"
            )
        return "\n".join(lines)
    finally:
        db.close()


def _clean_reply(text: str) -> str:
    """Strip leftover Markdown so replies are pure plain text.

    Removes bold/italic asterisks, heading hashes, and leading bullet markers.
    """
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-•·]\s+", "", text, flags=re.MULTILINE)
    return text.strip()


@router.post("/api/ai/chat", response_model=ChatResponse)
def ai_chat(req: ChatRequest):
    settings = get_settings()
    client = _client()
    if client is None:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY is not configured on the server.")

    system = (
        "You are Thibitisha, a concise plant maintenance assistant for a manufacturing facility. "
        "You help shift admins understand equipment faults, prioritise incidents, suggest likely root "
        "causes and next repair steps, and explain the SMS/USSD incident reporting flow. "
        "Answer in plain text only: no Markdown, no asterisks (*), no bold or bullet markers. "
        "Use short labelled lines, numbered plain steps, and blank lines between sections. "
        "Keep answers short and practical.\n\n"
        "Live snapshot of the facility:\n"
        f"{_plant_context()}"
    )

    messages = [{"role": "system", "content": system}]
    for msg in req.history[-12:]:
        if msg.role in ("user", "assistant") and msg.content.strip():
            messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": req.message})

    try:
        completion = client.chat.completions.create(
            model=settings.groq_model,
            messages=messages,
            temperature=0.4,
            max_tokens=1024,
        )
        reply = _clean_reply(completion.choices[0].message.content or "")
    except Exception as exc:
        logger.error("Groq admin chat failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"AI request failed: {exc}")

    if not reply:
        raise HTTPException(status_code=502, detail="AI returned an empty response.")

    return ChatResponse(reply=reply, model=settings.groq_model)