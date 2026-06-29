# api/routes/health.py
from fastapi import APIRouter, Depends
from datetime import datetime
import platform

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Endpoint de monitoramento: retorna status da API, timestamp e versão.
    Útil para Kubernetes liveness/readiness probes.
    """
    return {
        "status": "ok",
        "service": "IA Open Source API",
        "timestamp": datetime.utcnow().isoformat(),
        "python_version": platform.python_version(),
    }

@router.get("/ready")
async def readiness_check():
    """
    Endpoint adicional para readiness probe (pode incluir verificações de dependências).
    Por enquanto retorna o mesmo status, depois evoluiremos.
    """
    return {"status": "ready"}
