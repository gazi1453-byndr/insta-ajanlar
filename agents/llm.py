"""Yapay zeka bağlantısı. Tüm ajanlar modellere buradan ulaşır.

KURAL: Sağlayıcılar config.yaml'daki `yapay_zeka.sira` listesindeki sırayla denenir.
Varsayılan sıra: önce Google Gemini (ücretsiz), Gemini'nin günlük limiti dolarsa ya da
hata verirse sistem DURMAZ, otomatik olarak Groq'a (ücretsiz) geçip devam eder.
Günlük limiti dolan sağlayıcı o çalışma boyunca bir daha denenmez (boşa istek atılmaz).

Gerekli ortam değişkenleri (GitHub Secrets):
  GEMINI_API_KEY   → https://aistudio.google.com/apikey
  GROQ_API_KEY     → https://console.groq.com/keys
İsteğe bağlı sağlayıcılar: "claude_abonelik" (CLAUDE_CODE_OAUTH_TOKEN), "claude_api" (ANTHROPIC_API_KEY)

- ask():       Pydantic şemasına uyan yapılandırılmış (JSON) yanıt döndürür.
- research():  Web'de arama yaparak kaynaklı serbest metin araştırma notu döndürür.
İçerikte görsel göndermek için {"type": "image_path", "path": "..."} blokları kullanılır.
"""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, TypeVar

import requests
from pydantic import BaseModel, ValidationError

from .common import ROOT, config, log

T = TypeVar("T", bound=BaseModel)

DEFAULTS = {
    "sira": ["gemini", "groq"],
    "gemini_model": ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.5-flash-lite", "gemini-flash-lite-latest"],
    "groq_model": ["openai/gpt-oss-120b", "llama-3.3-70b-versatile"],
    "groq_gorsel_model": ["meta-llama/llama-4-scout-17b-16e-instruct"],
    "groq_arastirma_model": ["groq/compound", "groq/compound-mini"],
}


class LLMError(RuntimeError):
    pass


class QuotaExhausted(LLMError):
    """Sağlayıcının günlük/aylık limiti doldu: bu çalışmada bir daha denenmez."""


_down: set[str] = set()          # limiti dolan sağlayıcılar
_down_models: set[str] = set()   # limiti dolan tek tek modeller (limitler model başına)
_last_call: dict[str, float] = {}


def _cfg(key: str):
    v = (config().get("yapay_zeka") or {}).get(key, DEFAULTS.get(key))
    return v if isinstance(v, list) else [v]


def providers() -> list[str]:
    forced = os.environ.get("LLM_SIRA")
    order = forced.split(",") if forced else _cfg("sira")
    env = {"gemini": "GEMINI_API_KEY", "groq": "GROQ_API_KEY",
           "claude_abonelik": "CLAUDE_CODE_OAUTH_TOKEN", "claude_api": "ANTHROPIC_API_KEY"}
    return [p.strip() for p in order if os.environ.get(env.get(p.strip(), "_"))]


def backend() -> str:
    """Kullanılabilir sağlayıcı zinciri (ör. 'gemini → groq')."""
    return " → ".join(providers()) or "YOK (GEMINI_API_KEY / GROQ_API_KEY tanımlı değil)"


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


def _b64(p: Path) -> str:
    return base64.standard_b64encode(p.read_bytes()).decode()


def _throttle(name: str, gap: float) -> None:
    """Ücretsiz katmanların dakika başı sınırına takılmamak için istekler arası bekleme."""
    wait = gap - (time.time() - _last_call.get(name, 0))
    if wait > 0:
        time.sleep(wait)
    _last_call[name] = time.time()


def _schema_prompt(schema: type[BaseModel]) -> str:
    return ("\n\n---\nYANIT BİÇİMİ: Yanıtını SADECE aşağıdaki JSON Şemasına birebir uyan tek bir JSON "
            "nesnesi olarak ver. Açıklama, markdown ya da kod bloğu ekleme. Zorunlu alanların hepsini doldur.\n"
            + json.dumps(schema.model_json_schema(), ensure_ascii=False))


def _parse_json(text: str) -> Any:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        a, b = text.find("{"), text.rfind("}")
        if a >= 0 and b > a:
            return json.loads(text[a:b + 1])
        raise


# ================================================================== GEMINI

def _gemini_call(prompt: str, system: str, images: list[Path], *, json_mode: bool, search: bool) -> str:
    key = os.environ["GEMINI_API_KEY"]
    parts: list[dict] = [{"inline_data": {"mime_type": "image/jpeg", "data": _b64(p)}} for p in images]
    parts.append({"text": prompt})
    body: dict[str, Any] = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 16384},
    }
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"
    if search:
        body["tools"] = [{"google_search": {}}]
    last_err = None
    models = _cfg("gemini_model")
    for model in models:
        mkey = f"gemini:{model}:{'arama' if search else 'normal'}"
        if mkey in _down_models:  # bu modelin limiti bu çalışmada dolmuştu
            continue
        for attempt in range(3):
            _throttle("gemini", 6.5)
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                json=body, timeout=300)
            if r.status_code == 200:
                data = r.json()
                cands = data.get("candidates") or []
                if not cands:
                    raise LLMError(f"Gemini yanıt vermedi: {str(data.get('promptFeedback', data))[:300]}")
                text = "".join(p.get("text", "") for p in cands[0].get("content", {}).get("parts", []))
                if search:  # kaynak linklerini metne ekle
                    chunks = cands[0].get("groundingMetadata", {}).get("groundingChunks", [])
                    links = [f"- {c['web'].get('title', '')}: {c['web'].get('uri', '')}" for c in chunks if c.get("web")]
                    if links:
                        text += "\n\nKaynaklar (Google arama):\n" + "\n".join(links)
                if not text.strip():
                    raise LLMError(f"Gemini boş yanıt döndü (finishReason: {cands[0].get('finishReason')})")
                return text
            msg = r.text[:600]
            if r.status_code == 429:
                low = msg.lower()
                daily = "perday" in low or "per day" in low or ("quota" in low and "minute" not in low)
                if not daily and attempt == 0:
                    log("gemini", "Dakika başı sınır, 30 sn bekleniyor")
                    time.sleep(30)
                    continue
                # Limitler MODEL BAŞINA: bu modeli kapat, sıradaki Gemini modelini dene
                _down_models.add(mkey)
                last_err = f"{model} limiti doldu"
                log("gemini", f"{model} limiti doldu → sıradaki Gemini modeli")
                break
            if r.status_code == 404 or "not found" in msg.lower():
                last_err = f"{model} bulunamadı"
                break  # sıradaki modeli dene
            if r.status_code >= 500 or "high demand" in msg.lower() or "overloaded" in msg.lower():
                # Geçici yoğunluk: artan aralıklarla bekle, olmazsa sıradaki Gemini modeline geç
                if attempt < 2:
                    wait = 8 * (attempt + 1)
                    log("gemini", f"{model} yoğun ({r.status_code}), {wait} sn sonra tekrar")
                    time.sleep(wait)
                    continue
                last_err = f"{model} yoğun ({r.status_code})"
                log("gemini", f"{model} yanıt vermiyor → sıradaki Gemini modeli")
                break
            raise LLMError(f"Gemini hata {r.status_code}: {msg[:300]}")
    if all(f"gemini:{m}:{'arama' if search else 'normal'}" in _down_models for m in models):
        raise QuotaExhausted(f"Gemini: bütün modellerin limiti doldu (son: {last_err})")
    raise LLMError(f"Gemini: hiçbir model yanıt vermedi (son: {last_err})")


# ================================================================== GROQ

def _groq_call(prompt: str, system: str, images: list[Path], *, json_mode: bool, search: bool) -> str:
    key = os.environ["GROQ_API_KEY"]
    if search:
        models = _cfg("groq_arastirma_model")
    elif images:
        models = _cfg("groq_gorsel_model")
    else:
        models = _cfg("groq_model")
    if images:
        user: Any = [{"type": "text", "text": prompt}] + [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_b64(p)}"}} for p in images[:5]]
    else:
        user = prompt
    last_err = None
    for model in models:
        mkey = f"groq:{model}"
        if mkey in _down_models:
            continue
        body: dict[str, Any] = {"model": model, "temperature": 0.6, "max_completion_tokens": 8192,
                                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        for attempt in range(2):
            _throttle("groq", 2.5)
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                              headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                              json=body, timeout=300)
            if r.status_code == 200:
                text = r.json()["choices"][0]["message"].get("content") or ""
                if not text.strip():
                    raise LLMError("Groq boş yanıt döndü")
                return text
            msg = r.text[:600]
            if r.status_code == 429:
                daily = "per day" in msg.lower() or "TPD" in msg or "RPD" in msg
                wait = min(float(r.headers.get("retry-after", 20) or 20), 60)
                if not daily and attempt == 0:
                    log("groq", f"Dakika başı sınır, {wait:.0f} sn bekleniyor")
                    time.sleep(wait)
                    continue
                _down_models.add(mkey)  # Groq'ta da limitler model başına
                last_err = f"{model} limiti doldu"
                log("groq", f"{model} limiti doldu → sıradaki Groq modeli")
                break
            if r.status_code == 413 or "too large" in msg.lower():
                if isinstance(user, str) and len(user) > 12000:  # istemi kısaltıp tekrar dene
                    user = user[:9000] + "\n…(kısaltıldı)…\n" + user[-3000:]
                    body["messages"][1]["content"] = user
                    continue
            if r.status_code in (400, 404) and ("model" in msg.lower() or "decommission" in msg.lower()):
                last_err = f"{model}: {msg[:120]}"
                break
            if r.status_code >= 500 and attempt == 0:
                time.sleep(10)
                continue
            raise LLMError(f"Groq hata {r.status_code}: {msg[:300]}")
    if all(f"groq:{m}" in _down_models for m in models):
        raise QuotaExhausted(f"Groq: bütün modellerin limiti doldu (son: {last_err})")
    raise LLMError(f"Groq: kullanılabilir model yok ({last_err})")


# ================================================================== CLAUDE (isteğe bağlı)

def _claude_cli_call(prompt: str, system: str, images: list[Path], *, json_mode: bool, search: bool) -> str:
    exe = os.environ.get("CLAUDE_BIN") or shutil.which("claude")
    if not exe:
        raise LLMError("Claude Code kurulu değil")
    tools = "WebSearch,WebFetch" if search else ("Read" if images else "")
    if images:
        prompt = "Önce şu görselleri Read aracıyla aç:\n" + "\n".join(str(p.resolve()) for p in images) + "\n\n" + prompt
    cmd = [exe, "-p", "--output-format", "json", "--no-session-persistence",
           "--system-prompt", system, "--tools", tools] + (["--allowedTools", tools] if tools else [])
    p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT), timeout=1500)
    data = json.loads(p.stdout or "{}")
    if data.get("is_error"):
        msg = str(data.get("result", ""))
        raise (QuotaExhausted if "limit" in msg.lower() else LLMError)(f"Claude: {msg[:300]}")
    return str(data.get("result", ""))


def _claude_api_call(prompt: str, system: str, images: list[Path], *, json_mode: bool, search: bool) -> str:
    import anthropic
    content: Any = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": _b64(p)}}
                    for p in images] + [{"type": "text", "text": prompt}]
    kw: dict[str, Any] = {}
    if search:
        kw["tools"] = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 8}]
    resp = anthropic.Anthropic(max_retries=3).messages.create(
        model="claude-opus-5-5", max_tokens=16000, system=system,
        messages=[{"role": "user", "content": content}], **kw)
    return "\n".join(b.text for b in resp.content if b.type == "text")


_CALLS = {"gemini": _gemini_call, "groq": _groq_call,
          "claude_abonelik": _claude_cli_call, "claude_api": _claude_api_call}


# ================================================================== ORTAK ARAYÜZ

def _run_chain(agent: str, fn_name: str, attempt_fn) -> Any:
    chain = providers()
    if not chain:
        raise LLMError(f"{agent}: hiçbir yapay zeka anahtarı tanımlı değil (GEMINI_API_KEY / GROQ_API_KEY)")
    errors = []
    for prov in chain:
        if prov in _down:
            continue
        try:
            out = attempt_fn(prov)
            log(agent, f"{fn_name} yanıtı alındı ({prov})")
            return out
        except QuotaExhausted as e:
            _down.add(prov)
            errors.append(f"{prov}: {e}")
            log(agent, f"⚠ {prov} limiti doldu → sıradaki sağlayıcıya geçiliyor")
        except (LLMError, requests.RequestException, ValueError, KeyError) as e:
            errors.append(f"{prov}: {e}")
            log(agent, f"⚠ {prov} hata verdi ({str(e)[:120]}) → sıradaki sağlayıcıya geçiliyor")
    raise LLMError(f"{agent}: tüm sağlayıcılar başarısız → " + " | ".join(errors))


def ask(agent: str, system: str, content: str | list[dict], schema: type[T], effort: str = "high",
        role: str = "varsayilan", max_tokens: int = 16000) -> T:
    """Yapılandırılmış yanıt. Şemaya uymayan yanıtı bir kez hatayla birlikte geri gönderip düzelttirir."""
    text, images = _split(content)
    prompt = text + _schema_prompt(schema)

    def attempt(prov: str) -> T:
        call = _CALLS[prov]
        p = prompt
        for i in range(2):
            raw = call(p, system, images, json_mode=True, search=False)
            try:
                return schema.model_validate(_parse_json(raw))
            except (ValidationError, json.JSONDecodeError) as e:
                if i == 1:
                    raise LLMError(f"yanıt şemaya uymadı: {str(e)[:200]}")
                p = prompt + f"\n\nÖNCEKİ YANITIN ŞEMAYA UYMADI, düzelt:\n{str(e)[:1500]}"
        raise LLMError("ulaşılamaz")

    return _run_chain(agent, "Yapay zeka", attempt)


def research(agent: str, system: str, prompt: str, max_searches: int = 8) -> str:
    prompt = (prompt + f"\n\nGüncel bilgi için web'de ara (en fazla {max_searches} arama). Her bulgunun yanına "
              "kaynak site adını ve linkini yaz. Bulamadığın bilgiyi uydurma.")

    def attempt(prov: str) -> str:
        out = _CALLS[prov](prompt, system, [], json_mode=False, search=True)
        if len(out.strip()) < 40:
            raise LLMError("araştırma sonucu boş")
        return out

    return _run_chain(agent, "Web araştırması", attempt)
