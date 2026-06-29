# api/core/config.py
from typing import List, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # ------------------------------------------------------------------
    # Projeto
    # ------------------------------------------------------------------
    PROJECT_NAME: str = "IA Open Source API"
    PROJECT_VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------
    API_V1_STR: str = "/api/v1"
    API_KEY_HEADER: str = "X-API-Key"

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    # ------------------------------------------------------------------
    # Segurança / JWT
    # ------------------------------------------------------------------
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_USE_OPENSSL_RAND_HEX_32"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60          # 1 hora
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7             # 7 dias

    # ------------------------------------------------------------------
    # Rate Limiting
    # ------------------------------------------------------------------
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 60        # requisições por janela
    RATE_LIMIT_WINDOW_SECONDS: int = 60  # tamanho da janela (segundos)

    # ------------------------------------------------------------------
    # URLs dos serviços internos
    # ------------------------------------------------------------------
    NLP_SERVICE_URL: str = "http://nlp_service:8001"
    LLM_SERVICE_URL: str = "http://llm_service:8002"
    VISION_SERVICE_URL: str = "http://vision_service:8003"
    SPEECH_SERVICE_URL: str = "http://speech_service:8004"
    SUMMARIZER_SERVICE_URL: str = "http://summarizer_service:8005"

    # ------------------------------------------------------------------
    # Timeouts HTTP (segundos)
    # ------------------------------------------------------------------
    SERVICE_CONNECT_TIMEOUT: float = 5.0
    SERVICE_READ_TIMEOUT: float = 60.0   # LLM pode demorar mais

    # ------------------------------------------------------------------
    # Upload de arquivos
    # ------------------------------------------------------------------
    MAX_UPLOAD_SIZE_MB: int = 25

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def http_timeout(self) -> dict:
        return {
            "connect": self.SERVICE_CONNECT_TIMEOUT,
            "read": self.SERVICE_READ_TIMEOUT,
        }


settings = Settings()
