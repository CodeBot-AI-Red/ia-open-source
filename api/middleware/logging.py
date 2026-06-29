# api/middleware/logging.py
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("api.access")

# Rotas excluídas do log (reduz ruído de health checks)
_SKIP_PATHS = {"/health", "/ready", "/"}


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware de acesso estruturado.

    Registra por requisição:
      - request_id  → UUID único para rastreamento (também enviado no header de resposta)
      - method / path / status_code
      - process_time_ms
      - client_ip
      - user_agent
      - content_length da resposta
    """

    async def dispatch(self, request: Request, call_next):
        # Gera e armazena o request_id no estado da requisição
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
        user_agent = request.headers.get("User-Agent", "-")

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Injeta o request_id na resposta para facilitar debugging no cliente
        response.headers["X-Request-ID"] = request_id

        logger.info(
            '%(method)s %(path)s %(status)s %(elapsed).1fms ip=%(ip)s rid=%(rid)s ua="%(ua)s"',
            {
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "elapsed": elapsed_ms,
                "ip": client_ip,
                "rid": request_id,
                "ua": user_agent,
            },
        )
        return response
