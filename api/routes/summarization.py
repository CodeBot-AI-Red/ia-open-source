"""Summarization API proxy."""
from __future__ import annotations

import re

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.core.config import settings
from api.core.dependencies import get_current_user, get_http_client

router = APIRouter()


class SummarizationRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000)
    max_sentences: int = Field(5, ge=1, le=20)


class SummarizationResponse(BaseModel):
    summary: str
    sentences: list[str]
    model: str = "local-extractive-v1"


def extractive_summary(text: str, max_sentences: int = 5) -> SummarizationResponse:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if not sentences:
        sentences = [text.strip()]
    selected = sentences[:max_sentences]
    return SummarizationResponse(summary=" ".join(selected), sentences=selected)


@router.post("/summarize", response_model=SummarizationResponse, summary="Sumariza texto")
async def summarize(
    body: SummarizationRequest,
    user=Depends(get_current_user),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    try:
        async with client:
            response = await client.post(f"{settings.SUMMARIZER_SERVICE_URL}/summarize", json=body.model_dump())
        if response.status_code == 404:
            return extractive_summary(body.text, body.max_sentences)
        response.raise_for_status()
        return response.json()
    except httpx.ConnectError:
        return extractive_summary(body.text, body.max_sentences)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erro ao sumarizar texto: {exc}") from exc
