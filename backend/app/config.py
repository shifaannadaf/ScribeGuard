"""
ScribeGuard configuration.

All runtime configuration is centralized here. The agent layer reads from
this single Settings instance so that test/CI/dev/prod can swap behavior
through environment variables alone.
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str

    # ── AI provider selection ─────────────────────────────────────────────
    # "openai" → Whisper + GPT (paid). "local" → faster-whisper + Ollama (free).
    SERVICE_PROVIDER: str = "openai"

    # ── OpenAI (Whisper + GPT-4) ──────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    WHISPER_MODEL: str = "whisper-1"
    SOAP_MODEL: str = "gpt-4o-mini"  # GPT-4 family; can be swapped
    MEDICATION_MODEL: str = "gpt-4o-mini"
    OPENAI_TIMEOUT_SECONDS: float = 60.0

    # ── Local provider (faster-whisper + Ollama) ──────────────────────────
    # faster-whisper model size: tiny | base | small | medium | large-v3
    # `base` is a good balance of speed and accuracy on CPU.
    LOCAL_WHISPER_MODEL: str = "base"
    LOCAL_WHISPER_DEVICE: str = "cpu"          # "cpu" | "cuda" | "auto"
    LOCAL_WHISPER_COMPUTE_TYPE: str = "int8"   # "int8" (cpu) | "float16" (gpu)

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_LLM_MODEL: str = "llama3.2"
    OLLAMA_TIMEOUT_SECONDS: float = 120.0

    # ── OpenMRS (FHIR R4) ─────────────────────────────────────────────────
    FHIR_SERVER: str = "http://localhost:8080/openmrs/ws/fhir2/R4"
    OPENMRS_USER: str = "Admin"
    OPENMRS_PASSWORD: str = "Admin123"
    OPENMRS_DEFAULT_PRACTITIONER_UUID: str = "f9badd80-ab76-11e2-9e96-0800200c9a66"
    OPENMRS_DEFAULT_LOCATION_UUID: str = "8d6c993e-c2cc-11de-8d13-0010c6dffd0f"

    # ScribeGuard is a production system — by default it talks to the real
    # OpenMRS FHIR R4 endpoint configured above. Set OPENMRS_SIMULATE=true
    # ONLY for ephemeral CI / unit tests where no sandbox is reachable.
    OPENMRS_SIMULATE: bool = False

    # ── Agent runtime ────────────────────────────────────────────────────
    AGENT_MAX_RETRIES: int = 2
    AGENT_RETRY_BASE_DELAY_SECONDS: float = 1.5
    AGENT_AUDIT_ENABLED: bool = True

    # ── Audio storage ────────────────────────────────────────────────────
    AUDIO_STORAGE_DIR: str = "./audio_store"

    # ── CORS ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
