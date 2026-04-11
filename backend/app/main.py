from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from app.whisper_service import transcribe_audio
from app.gpt_service import generate_soap_note

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    transcript = await transcribe_audio(audio)
    return {"transcript": transcript}

@app.post("/generate-note")
async def generate_note(data: dict):
    soap_note = await generate_soap_note(data["transcript"])
    return soap_note

@app.post("/process-audio")
async def process_audio(audio: UploadFile = File(...)):
    transcript = await transcribe_audio(audio)
    soap_note = await generate_soap_note(transcript)
    return soap_note