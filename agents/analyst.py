"""9) ANALİST AJAN
Yayınlanan gönderilerin metriklerini toplar, haftalık rapor yazar ve
"neyin işe yaradığı" notlarını (data/learnings.md) günceller. Diğer tüm
ajanlar bu notları okuyarak zamanla daha iyi içerik üretir.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from pydantic import BaseModel, Field

from . import instagram as ig
from .common import DATA, PUBLISHED, REJECTED, REPORTS, brand_brief, learnings, log, now, read_json, write_json
from .llm import ask

AGENT = "Analist"


class Analysis(BaseModel):
    rapor_markdown: str = Field(description="Kullanıcıya gidecek haftalık rapor, Türkçe, başlıklı ve tablolu Markdown")
    ogrenilenler: list[str] = Field(description="Diğer ajanların uygulayacağı en fazla 12 kısa, net kural")
    en_iyi_saatler: list[str] = Field(description="Veri yeterliyse önerilen paylaşım saatleri (SS:DD), yoksa boş")
    mudur_kalibrasyonu: str = Field(description="Müdürün puanları gerçek performansla uyumlu mu? Kısa değerlendirme")


def run() -> Analysis:
    cutoff = now() - timedelta(days=30)
    posts = []
    for f in sorted(PUBLISHED.glob("*.json")):
        p = read_json(f)
        if datetime.fromisoformat(p["yayin_zamani"]) < cutoff:
            continue
        p["metrikler"] = ig.media_insights(p["ig_media_id"])
        write_json(f, p)
        posts.append({
            "konu": p["fikir"]["konu"], "format": p["fikir"]["format"], "hook": p["taslak"]["hook"],
            "yayin": p["yayin_zamani"], "mudur_puani": p["mudur"]["toplam"], "metrikler": p["metrikler"],
        })

    account = ig.account_info()
    hist = read_json(DATA / "account_history.json", [])
    hist.append({"tarih": now().isoformat(), **account})
    write_json(DATA / "account_history.json", hist[-120:])

    rejected = [{"konu": read_json(f)["fikir"]["konu"], "neden": read_json(f)["mudur"]["tutar_mi"]}
                for f in sorted(REJECTED.glob("*.json"))[-15:]]

    a = ask(
        AGENT,
        system=("Sen veri odaklı bir Instagram büyüme analistisin. Az veriyle kesin konuşmazsın; "
                "örneklem küçükse bunu söylersin.\n\n" + brand_brief()),
        content=(
            f"## Hesap geçmişi\n{json.dumps(hist[-12:], ensure_ascii=False)}\n\n"
            f"## Son 30 günün gönderileri\n{json.dumps(posts, ensure_ascii=False)}\n\n"
            f"## Müdürün reddettikleri\n{json.dumps(rejected, ensure_ascii=False)}\n\n"
            f"## Mevcut öğrenilenler\n{learnings()}\n\n"
            "Haftalık raporu yaz: takipçi değişimi, en iyi ve en kötü 3 gönderi ve nedenleri, "
            "format karşılaştırması, saat analizi, gelecek hafta için 3 somut öneri. "
            "Öğrenilenler listesini yeni verilere göre güncelle (eski kuralları gerekirse sil)."
        ),
        schema=Analysis,
    )
    stamp = f"{now():%Y-%m-%d}"
    (REPORTS / f"{stamp}.md").write_text(a.rapor_markdown, encoding="utf-8")
    (DATA / "learnings.md").write_text(
        f"# Öğrenilenler (güncelleme: {stamp})\n\n" + "\n".join(f"- {x}" for x in a.ogrenilenler)
        + (f"\n\nÖnerilen saatler: {', '.join(a.en_iyi_saatler)}" if a.en_iyi_saatler else ""),
        encoding="utf-8")
    log(AGENT, f"Rapor yazıldı: data/reports/{stamp}.md")
    return a
