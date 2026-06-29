# api/middleware/cors.py
"""
Configurações de CORS centralizadas.

O middleware em si é registrado no main.py via CORSMiddleware do Starlette.
Este módulo expõe `cors_kwargs()` para manter a configuração em um só lugar
e facilitar testes ou ajustes por ambiente.
"""
from api.core.config import settings


def cors_kwargs() -> dict:
    """
    Retorna os kwargs prontos para passar ao CORSMiddleware.

    Uso:
        app.add_middleware(CORSMiddleware, **cors_kwargs())
    """
    return {
        "allow_origins": settings.ALLOWED_ORIGINS,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": [
            "Authorization",
            "Content-Type",
            settings.API_KEY_HEADER,
            "X-Request-ID",
        ],
        "expose_headers": [
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ],
        "max_age": 600,  # segundos que o preflight pode ser cacheado pelo browser
    }
