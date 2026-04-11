import openai
import os
from dotenv import load_dotenv

load_dotenv()

client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def transcribe_audio(audio):
    contents = await audio.read()
    
    transcript = await client.audio.transcriptions.create(
        model="whisper-1",
        file=(audio.filename, contents, audio.content_type)
    )
    
    return transcript.text