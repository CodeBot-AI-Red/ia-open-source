# api/middleware/rate_limit.py
"""
Rate limiter baseado em sliding window (janela deslizante) em memória.

Para ambientes com múltiplos workers ou pods Kubernetes, substitua
`_store` por um backend Redis (ex: via `redis.asyncio`).
"""
import time
from collections import defaultdict, deque
from typing import Deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from api.core.config import settings

# Rotas isentas de rate limiting
_EXEMPT_PATHS = {"/health", "/ready", "/"}

# Store em memória: { client_key: deque([timestamp, ...]) }
_store: dict[str, Deque[float]] = defaultdict(deque)


def _client_key(request: Request) -> str:
    """Identifica o cliente por IP (usa X-Forwarded-For se disponível)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter.

    Configuração (via .env ou Settings):
        RATE_LIMIT_ENABLED        = True
        RATE_LIMIT_REQUESTS       = 60    (máximo por janela)
        RATE_LIMIT_WINDOW_SECONDS = 60    (tamanho da janela em segundos)
    """

    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED or request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        key = _client_key(request)
        now = time.time()
        window = settings.RATE_LIMIT_WINDOW_SECONDS
        limit = settings.RATE_LIMIT_REQUESTS

        timestamps = _store[key]

        # Remove timestamps fora da janela deslizante
        while timestamps and timestamps[0] < now - window:
            timestamps.popleft()

        remaining = max(0, limit - len(timestamps))
        reset_at = int(timestamps[0] + window) if timestamps else int(now + window)

        if len(timestamps) >= limit:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "detail": f"Limite de {limit} requisições por {window}s atingido.",
                    "retry_after": reset_at - int(now),
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_at),
                    "Retry-After": str(reset_at - int(now)),
                },
            )

        timestamps.append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining - 1)
        response.headers["X-RateLimit-Reset"] = str(reset_at)
        return response
