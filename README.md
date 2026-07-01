# IA Open Source

Uma plataforma modular de IA open source com API FastAPI e serviços separados para NLP, LLM, visão computacional, fala e sumarização.

## Melhorias desta versão

- **Serviço LLM funcional offline**: o serviço `services/llm_service` agora possui um backend local determinístico para chat, completions e streaming, útil para desenvolvimento sem baixar modelos pesados.
- **Segurança de prompt**: detecção básica de prompt injection bloqueia pedidos para revelar instruções internas, tokens ou segredos.
- **Contabilidade de tokens**: respostas de chat incluem `prompt_tokens`, `completion_tokens` e `total_tokens`.
- **Streaming**: `/chat/stream` emite chunks NDJSON para integração incremental.
- **Sumarização resiliente**: a API ganhou rota de sumarização com fallback extrativo local quando o serviço dedicado não está disponível.
- **Observabilidade**: middleware de `X-Request-ID` correlaciona requisições e respostas.
- **Base pronta para produção**: `requirements.txt` declara as dependências mínimas para API, testes e execução com Uvicorn.

## Endpoints principais

- `GET /api/v1/health` — liveness da API.
- `GET /api/v1/ready` — readiness com checagem dos serviços internos.
- `POST /api/v1/generation/chat` — chat com o LLM.
- `POST /api/v1/generation/chat/stream` — chat com streaming SSE via API gateway.
- `POST /api/v1/generation/complete` — completa um prompt.
- `POST /api/v1/summarization/summarize` — sumariza texto.

## Executando localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload
```

Para executar apenas o serviço LLM:

```bash
uvicorn services.llm_service.inference:app --host 0.0.0.0 --port 8002 --reload
```

## Testes

```bash
pytest
python -m py_compile api/main.py api/routes/summarization.py api/middleware/request_id.py services/llm_service/*.py tests/unit/test_llm.py
```

## Próximos passos recomendados

1. Conectar o seam `generate_with_backend` a um modelo real via Transformers, llama.cpp ou vLLM.
2. Persistir API keys e rate limiting em Redis/PostgreSQL para múltiplos workers.
3. Adicionar avaliação automática de qualidade e segurança para prompts adversariais.
4. Publicar imagens Docker para cada serviço e ativar CI completo.
