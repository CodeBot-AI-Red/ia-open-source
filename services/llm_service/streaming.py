"""Streaming helpers for LLM responses."""
from __future__ import annotations

from collections.abc import Iterable


def token_stream(text: str) -> Iterable[str]:
    for token in text.split():
        yield token + " "
