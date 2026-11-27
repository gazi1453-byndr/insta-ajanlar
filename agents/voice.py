"""SESLENDİRME
Sağlayıcı sırası:
  1) ElevenLabs (ELEVENLABS_API_KEY + ELEVENLABS_VOICE_ID tanımlıysa; ücretli)
  2) Microsoft Edge nöral Türkçe ses (ÜCRETSİZ, anahtar gerekmez; varsayılan: tr-TR-AhmetNeural)
Rakamlar seslendirmeden ÖNCE Türkçe yazıya çevrilir ("29.923,30 TL" → "yirmi dokuz bin dokuz yüz
yirmi üç lira otuz kuruş") ki ses motoru yanlış okumasın. Ses Denetçisi (qa.voice_check) sesi
yazıya döküp bu metinle karşılaştırır.
"""
from __future__ import annotations

import asyncio
import os
import re
import time
from pathlib import Path

import requests

from .common import config, log

AGENT = "Seslendirme"

_ONES = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
_TENS = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]


def _three(n: int) -> list[str]:
    out = []
    h, r = divmod(n, 100)
    if h:
        out += (["yüz"] if h == 1 else [_ONES[h], "yüz"])
    t, o = divmod(r, 10)
    if t:
        out.append(_TENS[t])
    if o:
        out.append(_ONES[o])
    return out


def sayi(n: int) -> str:
    """Tam sayıyı Türkçe yazıya çevirir: 29923 → 'yirmi dokuz bin dokuz yüz yirmi üç'."""
    if n == 0:
        return "sıfır"
    if n < 0:
        return "eksi " + sayi(-n)
    words = []
    for value, name in ((10 ** 9, "milyar"), (10 ** 6, "milyon"), (1000, "bin")):
        q, n = divmod(n, value)
        if q:
            words += (["bin"] if (q == 1 and name == "bin") else _three(q) + [name]) if q < 1000 else sayi(q).split() + [name]
    words += _three(n)
    return " ".join(words)


def _num(s: str) -> int:
    return int(s.replace(".", ""))


def speakable(text: str) -> str:
    """Metni ses motorunun hatasız okuyacağı biçime çevirir."""
    t = text.replace("~", " yaklaşık ").replace("₺", " TL")
    t = re.sub(r"%\s?(\d+)(?:,(\d+))?", lambda m: "yüzde " + sayi(int(m[1])) + (f" virgül {sayi(int(m[2]))}" if m[2] else ""), t)

    def money(m):
        lira = sayi(_num(m[1])) + " lira"
        kurus = int((m[2] or "0").ljust(2, "0"))
        return lira + (f" {sayi(kurus)} kuruş" if kurus else "")
    t = re.sub(r"(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?\s*(?:TL|lira)\b", money, t)
    t = re.sub(r"\b(\d+)\s*kuruş", lambda m: sayi(int(m[1])) + " kuruş", t)
    t = re.sub(r"(\d{1,3}(?:\.\d{3})+|\d+),(\d+)", lambda m: f"{sayi(_num(m[1]))} virgül {sayi(int(m[2]))}", t)
    t = re.sub(r"\d{1,3}(?:\.\d{3})+|\d+", lambda m: sayi(_num(m[0])), t)
    t = re.sub(r"\bkm\b", "kilometre", t)
    t = re.sub(r"\bm²|\bm2\b", "metrekare", t)
    t = re.sub(r"\bTL\b", "lira", t)
    return re.sub(r"\s{2,}", " ", t).strip()


def _cfg() -> dict:
    return config().get("ses", {}) or {}


def enabled() -> bool:
    return _cfg().get("saglayici", "edge") != "yok"


def _elevenlabs(text: str, out: Path) -> Path | None:
    voice = os.environ["ELEVENLABS_VOICE_ID"]
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "Content-Type": "application/json"},
        json={"text": text, "model_id": os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
              "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.25}},
        timeout=120)
    if r.status_code != 200:
        log(AGENT, f"ElevenLabs hata ({r.status_code}) → ücretsiz sese geçiliyor")
        return None
    out.write_bytes(r.content)
    return out


def _edge(text: str, out: Path) -> Path | None:
    import edge_tts
    cfg = _cfg()
    voice, rate = cfg.get("edge_ses", "tr-TR-AhmetNeural"), cfg.get("hiz", "+8%")
    for attempt in range(4):
        try:
            asyncio.run(edge_tts.Communicate(text, voice, rate=rate).save(str(out)))
            if out.exists() and out.stat().st_size > 1000:
                return out
        except Exception as e:  # ağ hatası: bekle, tekrar dene
            log(AGENT, f"Edge ses hatası (deneme {attempt + 1}): {str(e)[:120]}")
        time.sleep(3 * (attempt + 1))
    return None


def synthesize(text: str, out: Path) -> Path | None:
    if not enabled() or not text.strip():
        return None
    spoken = speakable(text)
    if os.environ.get("ELEVENLABS_API_KEY") and os.environ.get("ELEVENLABS_VOICE_ID"):
        r = _elevenlabs(spoken, out)
        if r:
            return r
    r = _edge(spoken, out)
    if r is None:
        raise RuntimeError("Seslendirme üretilemedi (Edge TTS 4 denemede yanıt vermedi)")
    return r
