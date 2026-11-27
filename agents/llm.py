"""Claude bağlantısı. Tüm ajanlar Claude'a buradan ulaşır.

İki çalışma şekli var (otomatik seçilir):
1) ABONELİK (varsayılan): Claude Code komut satırı + CLAUDE_CODE_OAUTH_TOKEN.
   Claude Pro/Max aboneliğinle çalışır, ayrıca API faturası çıkmaz.
   Token: bilgisayarda `claude setup-token` komutuyla alınır.
2) API: ANTHROPIC_API_KEY tanımlıysa Claude API kullanılır (kullandıkça ödenir).

- ask():       Pydantic şemasına uyan yapılandırılmış yanıt döndürür.
- research():  Web araması yaparak serbest metin araştırma notu döndürür.
İçerikte görsel göndermek için {"type": "image_path", "path": "..."} blokları kullanılır.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from .common import ROOT, config, log

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


def backend() -> str:
    forced = os.environ.get("LLM_BACKEND")
    if forced:
        return forced
    return "api" if os.environ.get("ANTHROPIC_API_KEY") else "abonelik"


def model(role: str = "varsayilan") -> str:
    m = config().get("modeller", {})
    return m.get(role) or m.get("varsayilan") or "claude-opus-5-5"


def _split(content: str | list[dict]) -> tuple[str, list[Path]]:
    if isinstance(content, str):
        return content, []
    texts, images = [], []
    for b in content:
        if b.get("type") == "text":
            texts.append(b["text"])
        elif b.get("type") == "image_path":
            images.append(Path(b["path"]))
    return "\n\n".join(texts), images


# ------------------------------------------------------------------ ABONELİK (Claude Code)

def _claude_bin() -> str:
    exe = os.environ.get("CLAUDE_BIN") or shutil.which("claude")
    if not exe:
        raise LLMError("Claude Code bulunamadı (GitHub'da 'npm i -g @anthropic-ai/claude-code' ile kurulur)")
    return exe


def _cli(agent: str, system: str, prompt: str, *, role: str, tools: str = "",
         schema: dict | None = None, timeout: int = 1500) -> dict:
    cmd = [_claude_bin(), "-p", "--output-format", "json", "--no-session-persistence",
           "--model", model(role), "--system-prompt", system, "--tools", tools]
    if tools:
        cmd += ["--allowedTools", tools]
    if schema:
        cmd += ["--json-schema", json.dumps(schema, ensure_ascii=False)]
    for attempt in range(3):
        try:
            p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                               cwd=str(ROOT), timeout=timeout)
        except subprocess.TimeoutExpired:
            log(agent, "Claude Code zaman aşımı, tekrar deneniyor")
            continue
        try:
            data = json.loads(p.stdout)
        except json.JSONDecodeError:
            raise LLMError(f"{agent}: Claude Code çıktısı okunamadı: {(p.stdout or p.stderr)[-500:]}")
        if data.get("is_error"):
            msg = str(data.get("result", ""))
            mi = cmd.index("--model") + 1
            if "model" in msg.lower() and "sonnet" not in cmd[mi] and attempt < 2:
                log(agent, f"{cmd[mi]} kullanılamadı ({msg[:100]}), Sonnet ile deneniyor")
                cmd[mi] = "claude-sonnet-5-5"
                continue
            if any(k in msg.lower() for k in ("overloaded", "rate", "529", "timeout")) and attempt < 2:
                log(agent, f"Geçici hata, tekrar deneniyor: {msg[:120]}")
                continue
            raise LLMError(f"{agent}: {msg[:400]}")
        return data
    raise LLMError(f"{agent}: Claude Code 3 denemede yanıt vermedi")


def _ask_cli(agent: str, system: str, content, schema: type[T], role: str) -> T:
    text, images = _split(content)
    tools = ""
    if images:
        tools = "Read"
        text = ("Önce şu görselleri Read aracıyla aç ve incele:\n"
                + "\n".join(str(p.resolve()) for p in images) + "\n\n" + text)
    data = _cli(agent, system, text, role=role, tools=tools, schema=schema.model_json_schema())
    raw: Any = data.get("structured_output")
    if raw is None:
        res = data.get("result", "")
        try:
            raw = json.loads(res[res.find("{"): res.rfind("}") + 1]) if isinstance(res, str) else res
        except json.JSONDecodeError:
            raise LLMError(f"{agent}: yapılandırılmış yanıt alınamadı")
    try:
        out = schema.model_validate(raw)
    except ValidationError as e:
        raise LLMError(f"{agent}: yanıt şemaya uymadı: {e}")
    log(agent, f"Claude yanıtı alındı (abonelik, {data.get('num_turns', 1)} adım)")
    return out


# ------------------------------------------------------------------ API

_FALLBACK = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
_client = None


def _api():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(max_retries=4)
    return _client


def _check(resp: Any, agent: str) -> None:
    if resp.stop_reason == "refusal":
        cat = getattr(resp.stop_details, "category", None) if resp.stop_details else None
        raise LLMError(f"{agent}: model isteği reddetti (kategori: {cat})")
    if resp.stop_reason == "max_tokens":
        raise LLMError(f"{agent}: yanıt token sınırına takıldı")


def _api_content(content) -> str | list[dict]:
    if isinstance(content, str):
        return content
    out = []
    for b in content:
        if b.get("type") == "image_path":
            out.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                        "data": base64.standard_b64encode(Path(b["path"]).read_bytes()).decode()}})
        else:
            out.append(b)
    return out


def _ask_api(agent, system, content, schema: type[T], effort, role, max_tokens) -> T:
    resp = _api().beta.messages.parse(
        model=model(role), max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": _api_content(content)}],
        output_format=schema, output_config={"effort": effort}, **_FALLBACK,
    )
    _check(resp, agent)
    if resp.parsed_output is None:
        raise LLMError(f"{agent}: yapılandırılmış yanıt alınamadı")
    log(agent, f"Claude yanıtı alındı (API, {resp.usage.input_tokens} girdi / {resp.usage.output_tokens} çıktı token)")
    return resp.parsed_output


def _research_api(agent, system, prompt, max_searches) -> str:
    messages: list[dict] = [{"role": "user", "content": prompt}]
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": max_searches}]
    for _ in range(5):
        resp = _api().beta.messages.create(
            model=model(), max_tokens=16000, system=system, messages=messages, tools=tools,
            output_config={"effort": "medium"}, **_FALLBACK,
        )
        if resp.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": resp.content})
            continue
        _check(resp, agent)
        return "\n".join(b.text for b in resp.content if b.type == "text").strip()
    raise LLMError(f"{agent}: araştırma bitmedi")


# ------------------------------------------------------------------ Ortak arayüz

def ask(agent: str, system: str, content: str | list[dict], schema: type[T], effort: str = "high",
        role: str = "varsayilan", max_tokens: int = 16000) -> T:
    if backend() == "api":
        return _ask_api(agent, system, content, schema, effort, role, max_tokens)
    return _ask_cli(agent, system, content, schema, role)


def research(agent: str, system: str, prompt: str, max_searches: int = 8) -> str:
    if backend() == "api":
        text = _research_api(agent, system, prompt, max_searches)
    else:
        prompt += (f"\n\nWebSearch aracıyla en fazla {max_searches} arama yap, gerekirse WebFetch ile "
                   "sayfaları aç. Sonunda bulgularını kaynak linkleriyle birlikte düz metin olarak yaz.")
        text = str(_cli(agent, system, prompt, role="varsayilan", tools="WebSearch,WebFetch").get("result", ""))
    log(agent, "Web araştırması tamamlandı")
    return text
