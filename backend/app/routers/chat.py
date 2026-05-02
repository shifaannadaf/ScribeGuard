"""
AI chat endpoint — kept for backward compatibility with the existing UI.

In the new agentic architecture this is *not* a first-class agent (it has
no clinical-workflow side-effects). It's a thin wrapper around the OpenAI
chat completion that the dashboard can use to query a transcript.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from app.clients.openai_client import openai_client
from app.config import settings
from app.db.database import get_db
from app.repositories import EncounterRepository, SoapRepository, TranscriptRepository


router = APIRouter(prefix="/encounters", tags=["AI Chat"])
logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str


CHAT_SYSTEM = """You are ScribeGuard, an AI clinical documentation assistant.
You have access to a doctor-patient encounter transcript and (optionally) the
generated SOAP note. Answer questions concisely and accurately, citing the
section name when relevant. If something is not in the transcript or note,
say so clearly."""


@router.post("/{encounter_id}/chat", response_model=ChatResponse)
async def chat(encounter_id: str, body: ChatRequest, db: Session = Depends(get_db)):
    EncounterRepository(db).get_or_404(encounter_id)
    transcript = TranscriptRepository(db).latest_for(encounter_id)
    note = SoapRepository(db).current_for(encounter_id)

    if not transcript and not note:
        raise HTTPException(status_code=400, detail="No transcript or SOAP note for this encounter yet.")

    context_parts: list[str] = []
    if transcript:
        context_parts.append(
            "TRANSCRIPT:\n" + (transcript.formatted_text or transcript.raw_text or "")
        )
    if note:
        context_parts.append(
            "SOAP NOTE:\n"
            f"Subjective: {note.subjective}\n"
            f"Objective: {note.objective}\n"
            f"Assessment: {note.assessment}\n"
            f"Plan: {note.plan}"
        )

    system = CHAT_SYSTEM + "\n\n" + "\n\n".join(context_parts)
    history_text = "\n".join(f"{m.role}: {m.content}" for m in body.history)
    user = f"{history_text}\n\nuser: {body.message}".strip() if history_text else body.message

    completion = await openai_client.chat_text(
        system=system,
        user=user,
        model=settings.SOAP_MODEL,
        temperature=0.3,
    )
    return ChatResponse(reply=completion.content)
