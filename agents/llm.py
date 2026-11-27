"""Claude API yardımcıları. Tüm ajanlar Claude'a buradan ulaşır.

- ask():       Pydantic şemasına uyan yapılandırılmış yanıt döndürür.
- research():  Web araması yaparak serbest metin araştırma notu döndürür.

Güvenlik sınıflandırıcısı bir isteği reddederse, sunucu tarafı yedek model
(fallbacks="default") isteği otomatik olarak başka bir modelde yeniden çalıştırır.
"""
from __future__ import annotations

from typing import Any, TypeVar

import anthropic
from pydantic import BaseModel

from .common import config, log

T = TypeVar("T", bound=BaseModel)

_FALLBACK = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
_client: anthropic.Anthropic | None = None


class LLMError(RuntimeError):
    pass


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(max_retries=4)  # ANTHROPIC_API_KEY ortam değişkeninden okunur
    return _client


def model(role: str = "varsayilan") -> str:
    m = config().get("modeller", {})
    return m.get(role) or m.get("varsayilan") or "claude-opus-5-5"


def _check(resp: Any, agent: str) -> None:
    if resp.stop_reason == "refusal":
        cat = getattr(resp.stop_details, "category", None) if resp.stop_details else None
        raise LLMError(f"{agent}: model isteği reddetti (kategori: {cat})")
    if resp.stop_reason == "max_tokens":
        raise LLMError(f"{agent}: yanıt token sınırına takıldı")


def ask(
    agent: str,
    system: str,
    content: str | list[dict],
    schema: type[T],
    effort: str = "high",
    role: str = "varsayilan",
    max_tokens: int = 16000,
) -> T:
    """Claude'a sorar ve `schema` tipinde doğrulanmış nesne döndürür."""
    resp = client().beta.messages.parse(
        model=model(role),
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": content}],
        output_format=schema,
        output_config={"effort": effort},
        **_FALLBACK,
    )
    _check(resp, agent)
    if resp.parsed_output is None:
        raise LLMError(f"{agent}: yapılandırılmış yanıt alınamadı")
    log(agent, f"Claude yanıtı alındı ({resp.usage.input_tokens} girdi / {resp.usage.output_tokens} çıktı token)")
    return resp.parsed_output


def research(agent: str, system: str, prompt: str, max_searches: int = 8) -> str:
    """Web aramasıyla araştırma yapar, bulguları metin olarak döndürür."""
    messages: list[dict] = [{"role": "user", "content": prompt}]
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": max_searches}]
    for _ in range(5):  # pause_turn olursa devam ettir
        resp = client().beta.messages.create(
            model=model(),
            max_tokens=16000,
            system=system,
            messages=messages,
            tools=tools,
            output_config={"effort": "medium"},
            **_FALLBACK,
        )
        if resp.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": resp.content})
            continue
        _check(resp, agent)
        text = "\n".join(b.text for b in resp.content if b.type == "text").strip()
        log(agent, "Web araştırması tamamlandı")
        return text
    raise LLMError(f"{agent}: araştırma bitmedi")
