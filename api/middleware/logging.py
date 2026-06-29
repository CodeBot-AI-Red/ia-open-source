# api/middleware/logging.py
import logging
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("api.middleware.logging")

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware que registra método, caminho, status code e tempo de resposta
    de cada requisição.
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000  # ms
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code} - {process_time:.2f}ms"
        )
        return response
