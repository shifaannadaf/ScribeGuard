import openai
import os
from dotenv import load_dotenv

load_dotenv()

client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
You are a medical scribe. Given a raw conversation transcript between a doctor and patient, 
generate a structured SOAP note in JSON format with exactly these fields:
{
    "subjective": "...",
    "objective": "...",
    "assessment": "...",
    "plan": "...",
    "medications": ["med1", "med2"]
}
- Subjective: what the patient reports (symptoms, complaints)
- Objective: measurable findings (vitals, observations)
- Assessment: diagnosis or clinical impression
- Plan: treatment plan
- Medications: list of any medications mentioned in the plan
Only return the JSON, nothing else.
"""

async def generate_soap_note(transcript: str):
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Transcript:\n{transcript}"}
        ]
    )
    
    import json
    content = response.choices[0].message.content
    soap_note = json.loads(content)
    return soap_note