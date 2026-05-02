from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    OPENAI_API_KEY: str = ""
    FHIR_SERVER: str = "http://host.docker.internal:8080/openmrs/ws/fhir2/R4"
    OPENMRS_USER: str = "admin"
    OPENMRS_PASSWORD: str = "Admin123"

    class Config:
        env_file = ".env"


settings = Settings()
