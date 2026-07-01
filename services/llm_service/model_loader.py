"""Model loading seam for future transformer/llama.cpp backends."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelInfo:
    name: str = "open-source-ai-local-fallback-v2"
    loaded: bool = True
    backend: str = "deterministic-local"


def get_model_info() -> ModelInfo:
    return ModelInfo()
