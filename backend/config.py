from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # LiveKit
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""

    # Groq — LLM (LLaMA 3.1 70B Versatile)
    groq_api_key: str = ""
    llm_model: str = "llama-3.1-70b-versatile"

    # STT — Deepgram
    deepgram_api_key: str = ""

    # TTS
    tts_provider: str = "elevenlabs"
    elevenlabs_api_key: str = ""
    cartesia_api_key: str = ""

    # Database
    # Dev default: SQLite (zero setup). Prod: switch to postgresql+asyncpg://...
    database_url: str = "sqlite+aiosqlite:///./audit.db"

    # Redis — session store (TTL-keyed by session UUID, never by PHI)
    redis_url: str = "redis://localhost:6379"
    redis_session_ttl_seconds: int = 1800

    # Mock flags — set to false to call real external backends
    use_mock_fhir: bool = True
    use_mock_talkehr: bool = True
    use_mock_insurance: bool = True

    # External APIs (only active when corresponding USE_MOCK_* = false)
    fhir_base_url: str = ""
    fhir_api_key: str = ""
    talkehr_base_url: str = ""
    talkehr_api_key: str = ""
    insurance_base_url: str = ""
    insurance_api_key: str = ""

    # Application
    environment: str = "development"
    log_level: str = "INFO"

    # Human fallback
    human_fallback_number: str = ""


settings = Settings()
