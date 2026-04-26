from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Encounter, ChatMessage
from app.schemas.misc import ChatRequest, ChatResponse
from app.gpt_service import chat_with_transcript

router = APIRouter(prefix="/encounters", tags=["AI Chat"])


@router.post("/{encounter_id}/chat", response_model=ChatResponse)
async def chat(encounter_id: str, body: ChatRequest, db: Session = Depends(get_db)):
    enc = db.get(Encounter, encounter_id)
    if not enc:
        raise HTTPException(status_code=404, detail="Encounter not found")

    db.add(ChatMessage(encounter_id=encounter_id, role="user", content=body.message))

    history = [{"role": m.role, "content": m.content} for m in body.history]
    reply = await chat_with_transcript(
        transcript=enc.transcript or "(No transcript available)",
        message=body.message,
        history=history,
    )

    msg = ChatMessage(encounter_id=encounter_id, role="assistant", content=reply)
    db.add(msg)
    db.commit()
    db.refresh(msg)

    return ChatResponse(reply=reply, message_id=msg.id)
