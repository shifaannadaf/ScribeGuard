from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from app.db.database import get_db
from app.models.models import Encounter, ChatMessage
from app.schemas.misc import ChatRequest, ChatResponse
from app.gpt_service import chat_with_transcript
from app.openmrs.history import get_patient_history, format_history_for_prompt

router = APIRouter(prefix="/encounters", tags=["AI Chat"])
logger = logging.getLogger(__name__)


@router.post("/{encounter_id}/chat", response_model=ChatResponse)
async def chat(encounter_id: str, body: ChatRequest, db: Session = Depends(get_db)):
    enc = db.get(Encounter, encounter_id)
    if not enc:
        raise HTTPException(status_code=404, detail="Encounter not found")

    # Save user message
    db.add(ChatMessage(encounter_id=encounter_id, role="user", content=body.message))

    # Fetch patient history from OpenMRS if patient has been pushed
    patient_history_text = "No patient history available."
    if enc.openmrs_patient_uuid:
        try:
            logger.info(f"Fetching patient history for {enc.openmrs_patient_uuid}")
            patient_history = get_patient_history(enc.openmrs_patient_uuid)
            patient_history_text = format_history_for_prompt(patient_history)
            logger.info(f"Retrieved patient history: {len(patient_history_text)} chars")
        except Exception as e:
            logger.warning(f"Failed to fetch patient history: {e}")
            patient_history_text = "Patient history could not be retrieved from OpenMRS."

    # Build chat history
    history = [{"role": m.role, "content": m.content} for m in body.history]
    
    # Get AI response with patient history context
    reply = await chat_with_transcript(
        transcript=enc.transcript or "(No transcript available)",
        message=body.message,
        history=history,
        patient_history=patient_history_text,
    )

    # Save assistant message
    msg = ChatMessage(encounter_id=encounter_id, role="assistant", content=reply)
    db.add(msg)
    db.commit()
    db.refresh(msg)

    return ChatResponse(reply=reply, message_id=msg.id)
