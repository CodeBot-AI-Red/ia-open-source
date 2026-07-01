"""Deterministic chat orchestration for the local open-source LLM service.

The project should be useful even before a heavy model is downloaded.  This
module provides a strong rule-based fallback with safety checks, prompt hygiene,
context summarisation and token accounting.  A model backend can be plugged in
later by replacing ``generate_with_backend`` while keeping the HTTP contract.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Iterable, Literal

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class ChatMessage:
    role: Role
    content: str


@dataclass(frozen=True)
class GenerationConfig:
    max_tokens: int = 512
    temperature: float = 0.7
    language: str = "pt-BR"


@dataclass(frozen=True)
class ChatResult:
    id: str
    model: str
    message: str
    finish_reason: Literal["stop", "length", "error"]
    usage: dict[str, int]


_WORD_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)
_DANGEROUS_PATTERNS = (
    re.compile(r"\b(ignore|ignorem|desconsidere)\b.*\b(instruções|instructions|sistema|system)\b", re.I),
    re.compile(r"\b(revele|vaze|mostre|print)\b.*\b(prompt|segredo|secret|token|chave|key)\b", re.I),
    re.compile(r"\b(system prompt|developer message|mensagem de sistema)\b", re.I),
)


class PromptSafetyError(ValueError):
    """Raised when user input appears to be a prompt-injection attempt."""


def count_tokens(text: str) -> int:
    """Small tokenizer approximation used for local accounting and truncation."""
    return len(_WORD_RE.findall(text or ""))


def normalize_messages(raw_messages: Iterable[dict | ChatMessage]) -> list[ChatMessage]:
    messages: list[ChatMessage] = []
    for item in raw_messages:
        if isinstance(item, ChatMessage):
            role, content = item.role, item.content
        else:
            role = item.get("role")
            content = item.get("content", "")
        if role not in {"system", "user", "assistant"}:
            raise ValueError(f"role inválido: {role}")
        cleaned = " ".join(str(content).split())
        if not cleaned:
            raise ValueError("mensagens não podem ser vazias")
        messages.append(ChatMessage(role=role, content=cleaned))
    if not messages:
        raise ValueError("envie ao menos uma mensagem")
    return messages


def detect_prompt_injection(messages: Iterable[ChatMessage]) -> list[str]:
    findings: list[str] = []
    for message in messages:
        if message.role == "user":
            for pattern in _DANGEROUS_PATTERNS:
                if pattern.search(message.content):
                    findings.append(pattern.pattern)
    return findings


def build_context(messages: list[ChatMessage], max_context_tokens: int = 1800) -> str:
    """Builds a compact conversation context, keeping recent turns first."""
    rendered: list[str] = []
    total = 0
    for message in reversed(messages):
        line = f"{message.role.upper()}: {message.content}"
        tokens = count_tokens(line)
        if rendered and total + tokens > max_context_tokens:
            break
        rendered.append(line)
        total += tokens
    return "\n".join(reversed(rendered))


def _extract_last_user(messages: list[ChatMessage]) -> str:
    for message in reversed(messages):
        if message.role == "user":
            return message.content
    return messages[-1].content


def _bulletize(text: str, max_items: int = 5) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|;\s+|\n+", text)
    return [p.strip(" -") for p in parts if p.strip()][:max_items]


def generate_with_backend(messages: list[ChatMessage], config: GenerationConfig) -> str:
    """High-quality local fallback generator.

    It is intentionally transparent: it does not pretend to be a huge model when
    no model is loaded.  The response is structured, actionable and Portuguese by
    default, which makes the API immediately useful for demos, tests and offline
    development.
    """
    question = _extract_last_user(messages)
    lower = question.lower()

    if any(word in lower for word in ("resuma", "sumarize", "summarize", "tl;dr")):
        bullets = _bulletize(question.replace("resuma", "", 1))
        core = "\n".join(f"- {item}" for item in bullets) or "- Não há conteúdo suficiente para resumir."
        return f"Resumo objetivo:\n{core}\n\nPróximo passo sugerido: valide os pontos principais com a fonte original."

    if any(word in lower for word in ("código", "codigo", "python", "javascript", "bug", "erro")):
        return (
            "Posso ajudar com isso. Uma abordagem segura é:\n"
            "1. Reproduzir o problema com um exemplo mínimo.\n"
            "2. Isolar entradas, saída esperada e saída real.\n"
            "3. Corrigir em pequenos passos com testes automatizados.\n"
            "4. Revisar logs e casos de borda.\n\n"
            f"Contexto entendido: {question[:500]}"
        )

    ideas = _bulletize(question, max_items=3)
    focus = "; ".join(ideas) if ideas else question
    return (
        "Entendi. Vou responder de forma direta, prática e verificável.\n\n"
        f"Resposta: {focus}\n\n"
        "Recomendação: transforme isso em uma tarefa pequena, defina critérios de sucesso "
        "e teste o resultado antes de evoluir para a próxima melhoria."
    )


def trim_to_token_budget(text: str, max_tokens: int) -> tuple[str, Literal["stop", "length"]]:
    tokens = _WORD_RE.findall(text)
    if len(tokens) <= max_tokens:
        return text, "stop"
    trimmed = " ".join(tokens[:max_tokens]).replace(" .", ".").replace(" ,", ",")
    return trimmed, "length"


def chat(raw_messages: Iterable[dict | ChatMessage], config: GenerationConfig | None = None) -> ChatResult:
    config = config or GenerationConfig()
    messages = normalize_messages(raw_messages)
    findings = detect_prompt_injection(messages)
    if findings:
        raise PromptSafetyError("Possível prompt injection detectado; reformule a solicitação sem pedir segredos ou instruções internas.")

    prompt_tokens = sum(count_tokens(m.content) for m in messages)
    _ = build_context(messages)  # preserved for backend implementations and observability hooks
    generated = generate_with_backend(messages, config)
    final_text, reason = trim_to_token_budget(generated, config.max_tokens)
    completion_tokens = count_tokens(final_text)
    return ChatResult(
        id=f"chatcmpl-{uuid.uuid4().hex[:16]}",
        model="open-source-ai-local-fallback-v2",
        message=final_text,
        finish_reason=reason,
        usage={
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    )
