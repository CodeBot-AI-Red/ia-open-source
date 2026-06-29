# api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from api.core.config import settings
from api.routes.health import router as health_router
# Os demais routers serão ativados conforme os módulos forem criados:
# from api.routes.text_analysis import router as text_analysis_router
# from api.routes.text_generation import router as text_generation_router
# from api.routes.image_analysis import router as image_analysis_router
# from api.routes.speech_to_text import router as speech_to_text_router

from api.middleware.logging import LoggingMiddleware
# Middleware de rate limit pode ser adicionado posteriormente

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia ciclo de vida da aplicação: inicializa recursos na subida
    e libera na descida.
    """
    logger.info("Inicializando serviços...")
    # Aqui podem ser carregados modelos, conexões com banco, etc.
    yield
    logger.info("Encerrando aplicação e liberando recursos...")

# Instanciação do app com configurações do arquivo core/config.py
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="API central do IA Open Source - NLP, LLM, Visão e Voz",
    lifespan=lifespan,
)

# Configuração de CORS (origens permitidas definidas em settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware customizado de logging (registra tempo de resposta, etc.)
app.add_middleware(LoggingMiddleware)

# Registro das rotas de saúde (sempre ativa)
app.include_router(health_router, tags=["Health"])

# As demais rotas serão registradas aqui quando os módulos existirem
# app.include_router(text_analysis_router, prefix="/analysis", tags=["Text Analysis"])
# app.include_router(text_generation_router, prefix="/generation", tags=["Text Generation"])
# app.include_router(image_analysis_router, prefix="/vision", tags=["Image Analysis"])
# app.include_router(speech_to_text_router, prefix="/speech", tags=["Speech to Text"])

# Rota raiz opcional para verificação rápida
@app.get("/")
async def root():
    return {"message": f"Bem-vindo à {settings.PROJECT_NAME}", "version": settings.PROJECT_VERSION}
