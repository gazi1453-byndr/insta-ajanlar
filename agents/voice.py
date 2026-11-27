"""SESLENDİRME (isteğe bağlı)
ELEVENLABS_API_KEY ve ELEVENLABS_VOICE_ID tanımlıysa her sahnenin seslendirme
metnini ElevenLabs ile (tercihen kendi sesinin klonuyla) sese çevirir.
Tanımlı değilse None döner; video sessiz, ekranda yazıyla üretilir.
"""
from __future__ import annotations

import os
from pathlib import Path

import requests

from .common import log

AGENT = "Seslendirme"


def enabled() -> bool:
    return bool(os.environ.get("ELEVENLABS_API_KEY") and os.environ.get("ELEVENLABS_VOICE_ID"))


def synthesize(text: str, out: Path) -> Path | None:
    if not enabled() or not text.strip():
        return None
    voice = os.environ["ELEVENLABS_VOICE_ID"]
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "Content-Type": "application/json"},
        json={
            "text": text,
            "model_id": os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.25},
        },
        timeout=120,
    )
    if r.status_code != 200:
        log(AGENT, f"Ses üretilemedi ({r.status_code}): {r.text[:200]} — sahne sessiz kalacak")
        return None
    out.write_bytes(r.content)
    return out
