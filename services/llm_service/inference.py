"""FastAPI entrypoint for the local LLM service."""
from __future__ import annotations

import json
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from services.llm_service.chat_handler import GenerationConfig, PromptSafetyError, chat, trim_to_token_budget


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    messages: list[Message] = Field(..., min_length=1)
    max_tokens: int = Field(512, ge=1, le=4096)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    stream: bool = False


class CompletionRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8000)
    max_tokens: int = Field(256, ge=1, le=4096)
    temperature: float = Field(0.7, ge=0.0, le=2.0)


app = FastAPI(title="Open Source AI LLM Service", version="2.0.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "model": "open-source-ai-local-fallback-v2"}


@app.post("/chat")
async def chat_endpoint(body: ChatRequest):
    try:
        result = chat([m.model_dump() for m in body.messages], GenerationConfig(body.max_tokens, body.temperature))
    except PromptSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result.__dict__


@app.post("/complete")
async def complete_endpoint(body: CompletionRequest):
    result = chat([{"role": "user", "content": body.prompt}], GenerationConfig(body.max_tokens, body.temperature))
    text, reason = trim_to_token_budget(result.message, body.max_tokens)
    return {"id": result.id.replace("chatcmpl", "cmpl"), "text": text, "finish_reason": reason, "usage": result.usage}


@app.post("/chat/stream")
async def stream_chat_endpoint(body: ChatRequest):
    async def events():
        result = chat([m.model_dump() for m in body.messages], GenerationConfig(body.max_tokens, body.temperature))
        for token in result.message.split():
            yield json.dumps({"token": token + " "}, ensure_ascii=False) + "\n"
        yield json.dumps({"finish_reason": result.finish_reason, "usage": result.usage}, ensure_ascii=False) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson")
