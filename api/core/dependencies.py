# api/core/dependencies.py
from typing import Annotated, Optional

import httpx
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from api.auth.api_key_manager import verify_api_key_hash
from api.auth.jwt_handler import decode_access_token
from api.auth.models import TokenData, UserRole
from api.core.config import settings

# ---------------------------------------------------------------------------
# Esquemas de segurança (declarados para o OpenAPI)
# ---------------------------------------------------------------------------
_api_key_scheme = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)
_bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Dependência: autenticação por API Key
# ---------------------------------------------------------------------------
async def get_api_key(api_key: Annotated[Optional[str], Security(_api_key_scheme)] = None) -> str:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key ausente. Inclua o header 'X-API-Key'.",
        )
    valid = await verify_api_key_hash(api_key)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key inválida ou revogada.",
        )
    return api_key


# ---------------------------------------------------------------------------
# Dependência: autenticação por JWT
# ---------------------------------------------------------------------------
async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Security(_bearer_scheme)] = None,
) -> TokenData:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Bearer ausente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    return payload


# ---------------------------------------------------------------------------
# Dependência: usuário atual (opcional — para rotas públicas com contexto)
# ---------------------------------------------------------------------------
async def get_optional_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Security(_bearer_scheme)] = None,
) -> Optional[TokenData]:
    if not credentials:
        return None
    try:
        return decode_access_token(credentials.credentials)
    except HTTPException:
        return None


# ---------------------------------------------------------------------------
# Guards de role
# ---------------------------------------------------------------------------
def require_role(*roles: UserRole):
    """
    Dependência de fábrica: valida que o usuário possui ao menos uma das roles exigidas.

    Uso:
        @router.post("/admin", dependencies=[Depends(require_role(UserRole.ADMIN))])
    """
    async def _guard(user: Annotated[TokenData, Depends(get_current_user)]) -> TokenData:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso negado. Roles necessárias: {[r.value for r in roles]}.",
            )
        return user

    return _guard


# ---------------------------------------------------------------------------
# Cliente HTTP reutilizável para comunicação com serviços internos
# ---------------------------------------------------------------------------
def get_http_client() -> httpx.AsyncClient:
    """
    Retorna um AsyncClient configurado com os timeouts globais.
    Deve ser usado como dependência em rotas que chamam serviços internos.
    """
    return httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=settings.SERVICE_CONNECT_TIMEOUT,
            read=settings.SERVICE_READ_TIMEOUT,
            write=10.0,
            pool=5.0,
        ),
        headers={"Content-Type": "application/json"},
    )
