# api/main.py
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.core.config import settings
from starlette.middleware.cors import CORSMiddleware

from api.middleware.cors import cors_kwargs
from api.middleware.logging import LoggingMiddleware
from api.middleware.rate_limit import RateLimitMiddleware
from api.middleware.request_id import RequestIDMiddleware  # novo
from api.routes import (
    health,
    image_analysis,
    speech_to_text,
    text_analysis,
    text_generation,
    summarization,  # novo
)
from api.auth.jwt_handler import decode_access_token
from api.auth.api_key_manager import verify_api_key_hash

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: startup / shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Iniciando IA Open Source API v%s", settings.PROJECT_VERSION)

    # Verifica conectividade com os serviços internos
    services = {
        "nlp": settings.NLP_SERVICE_URL,
        "llm": settings.LLM_SERVICE_URL,
        "vision": settings.VISION_SERVICE_URL,
        "speech": settings.SPEECH_SERVICE_URL,
        "summarizer": settings.SUMMARIZER_SERVICE_URL,
    }

    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in services.items():
            try:
                r = await client.get(f"{url}/health")
                if r.status_code == 200:
                    logger.info("  ✅ Serviço '%s' acessível em %s", name, url)
                else:
                    logger.warning(
                        "  ⚠️  Serviço '%s' retornou status %s", name, r.status_code
                    )
            except Exception as e:
                logger.warning(
                    "  ⚠️  Serviço '%s' não está acessível em %s: %s", name, url, str(e)
                )

    logger.info("📦 Aplicação pronta para receber requisições.")
    yield

    logger.info("🛑 Encerrando IA Open Source API — recursos liberados.")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=(
        "API central do IA Open Source. Oferece endpoints unificados para "
        "análise de texto, geração de texto (LLM), visão computacional, "
        "transcrição de áudio e sumarização, com autenticação JWT/API-Key "
        "e rate limiting."
    ),
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middlewares (ordem importa: último adicionado = primeiro executado)
# ---------------------------------------------------------------------------
app.add_middleware(RequestIDMiddleware)  # adiciona request_id
app.add_middleware(CORSMiddleware, **cors_kwargs())
app.add_middleware(RateLimitMiddleware)
app.add_middleware(LoggingMiddleware)


# ---------------------------------------------------------------------------
# Dependência de autenticação global (opcional, pode ser aplicada por rota)
# ---------------------------------------------------------------------------
async def auth_dependency(request: Request):
    """
    Verifica se a requisição possui um token JWT válido ou uma API Key válida.
    Se a autenticação estiver desabilitada (settings.ENABLE_AUTH=False), passa sem verificação.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cabeçalho Authorization ausente",
        )

    # Tenta JWT
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer ") :]
        decode_access_token(token)
        return True

    # Tenta API Key (formato: "ApiKey <key>")
    if auth_header.startswith("ApiKey "):
        api_key = auth_header[len("ApiKey ") :]
        if await verify_api_key_hash(api_key):
            return True
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API Key inválida",
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Formato de autenticação não suportado",
    )


# ---------------------------------------------------------------------------
# Exception handlers globais
# ---------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "detail": exc.errors(),
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Erro não tratado na rota %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "detail": "Ocorreu um erro interno. Tente novamente mais tarde.",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
v1 = settings.API_V1_STR

# Rotas públicas (sem autenticação)
app.include_router(health.router, prefix=v1, tags=["Health"])

# Rotas protegidas (com autenticação via dependência)
protected_routers = [
    (text_analysis.router, f"{v1}/analysis", "Text Analysis"),
    (text_generation.router, f"{v1}/generation", "Text Generation"),
    (image_analysis.router, f"{v1}/vision", "Image Analysis"),
    (speech_to_text.router, f"{v1}/speech", "Speech to Text"),
    (summarization.router, f"{v1}/summarization", "Summarization"),  # nova rota
]

for router, prefix, tag in protected_routers:
    app.include_router(
        router,
        prefix=prefix,
        tags=[tag],
        dependencies=[Depends(auth_dependency)],  # aplica autenticação
    )


# ---------------------------------------------------------------------------
# Rota raiz
# ---------------------------------------------------------------------------
@app.get("/", tags=["Root"])
async def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "docs": f"{settings.API_V1_STR}/docs",
    }
