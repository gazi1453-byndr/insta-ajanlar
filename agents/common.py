"""Ortak yardımcılar: ayarlar, veri dosyaları, zaman, log."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

for _s in (sys.stdout, sys.stderr):  # Windows konsolunda Türkçe karakter / ok işareti hatası olmasın
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
QUEUE = DATA / "queue"            # Onaylanmış, yayın bekleyen gönderiler
PUBLISHED = DATA / "published"    # Yayınlanmış gönderiler
REJECTED = DATA / "rejected"      # Müdürün reddettikleri (öğrenmek için saklanır)
REPORTS = DATA / "reports"
MEDIA_INBOX = ROOT / "media" / "inbox"          # Senin koyduğun görseller
MEDIA_USED = ROOT / "media" / "used"
MEDIA_GENERATED = ROOT / "media" / "generated"  # Ajanın ürettiği görseller

TR = timezone(timedelta(hours=3))  # Türkiye saati (UTC+3, yaz saati yok)

for _d in (DATA, QUEUE, PUBLISHED, REJECTED, REPORTS, MEDIA_INBOX, MEDIA_USED, MEDIA_GENERATED):
    _d.mkdir(parents=True, exist_ok=True)


def config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def now() -> datetime:
    return datetime.now(TR)


def dry_run() -> bool:
    """DRY_RUN=1 iken Instagram'a hiçbir şey gönderilmez."""
    return os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def read_text(path: Path, default: str = "") -> str:
    return path.read_text(encoding="utf-8") if path.exists() else default


def log(agent: str, msg: str) -> None:
    print(f"[{now():%H:%M:%S}] [{agent}] {msg}", flush=True)


def brand_brief() -> str:
    """Her ajanın sistem talimatına eklenen hesap özeti."""
    h = config()["hesap"]
    rules = "\n".join(f"- {r}" for r in h.get("marka_kurallari", []))
    return (
        f"Hesap: @{h['kullanici_adi']}\n"
        f"Niş: {h['nis']}\n"
        f"Hedef kitle: {h['hedef_kitle']}\n"
        f"Dil: {h['dil']}\n"
        f"Ton: {h['ton']}\n"
        f"Marka kuralları:\n{rules}"
    )


def learnings() -> str:
    """Analistin yazdığı 'neyin işe yaradığı' notları."""
    return read_text(DATA / "learnings.md", "Henüz veri yok: hesap yeni, ilk haftalar deneme dönemi.")


GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


def gunun_serisi(when=None) -> str:
    """Haftalık programa göre günün alt serisi (ör. Pazartesi → 'ZAM TAKİBİ')."""
    prog = config().get("haftalik_program") or {}
    return prog.get(GUNLER[(when or now()).weekday()], "")


def maas_cevir(tutar: float) -> dict:
    """Bir tutarı asgari ücretle kaç gün/saat çalışmaya denk geldiğine çevirir.
    {'deger': 32, 'birim': 'gün', 'metin': 'Asgari ücretle ≈ 32 gün çalışma'}"""
    m = config().get("maas_cevirisi") or {}
    net = float(m.get("asgari_ucret_net") or 0)
    if net <= 0 or tutar <= 0:
        return {}
    gunluk = net / float(m.get("aylik_calisma_gunu", 30))
    saatlik = net / float(m.get("aylik_calisma_saati", 225))
    if tutar >= gunluk:
        deger, birim = round(tutar / gunluk), "gün"
    else:
        deger, birim = max(1, round(tutar / saatlik)), "saat"
    return {"deger": deger, "birim": birim, "metin": f"Asgari ücretle ≈ {deger} {birim} çalışma",
            "kaynak": m.get("kaynak", "")}
