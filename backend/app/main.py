from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import encounters, pipeline, openmrs, chat, export
from app.openmrs.router import router as fhir_router

app = FastAPI(
    title="ScribeGuard API",
    description="AI-powered clinical documentation backend",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(encounters.router)
app.include_router(pipeline.router)
app.include_router(openmrs.router)
app.include_router(chat.router)
app.include_router(export.router)
app.include_router(fhir_router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
