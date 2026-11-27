"""2) FİKİR / STRATEJİ AJANI
Araştırma raporunu, analistin öğrendiklerini ve geçmiş gönderileri kullanarak
günün içerik fikirlerini çıkarır ve önceliklendirir.
"""
from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from .common import DATA, PUBLISHED, QUEUE, brand_brief, config, learnings, read_json
from .llm import ask

AGENT = "Fikir Ajanı"


class Idea(BaseModel):
    konu: str
    aci: str = Field(description="Konuyu farklı kılan bakış açısı")
    format: Literal["carousel", "tek_gorsel", "reel_senaryosu"]
    hedef_duygu: str = Field(description="Okuyucuda uyandırılacak duygu: merak, şaşkınlık, rahatlama vb.")
    neden_simdi: str
    beklenen_etki: Literal["kaydetme", "paylaşma", "yorum", "takip"]
    puan: int = Field(description="1-100 arası tutma potansiyeli tahmini")


class IdeaList(BaseModel):
    fikirler: list[Idea]


def _recent_topics(limit: int = 30) -> list[str]:
    topics = []
    for folder in (PUBLISHED, QUEUE):
        for f in sorted(folder.glob("*.json"))[-limit:]:
            post = read_json(f, {})
            topics.append(post.get("fikir", {}).get("konu", ""))
    return [t for t in topics if t]


def run(count: int) -> list[Idea]:
    research = read_json(DATA / "research" / "latest.json", {}).get("rapor", {})
    has_inbox = any(p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
                    for p in (DATA.parent / "media" / "inbox").iterdir())
    result = ask(
        AGENT,
        system=(
            "Sen bir Instagram içerik stratejistisin. Kaydedilen ve paylaşılan içerik fikirleri "
            "bulursun. Yeni bir hesabın büyümesi için değerli, net ve tek fikirli içerikleri seçersin.\n\n"
            + brand_brief()
        ),
        content=(
            f"## Araştırma raporu\n{json.dumps(research, ensure_ascii=False)}\n\n"
            f"## Geçmiş verilerden öğrenilenler\n{learnings()}\n\n"
            f"## Son paylaşılan/planlanan konular (TEKRARLAMA)\n{json.dumps(_recent_topics(), ensure_ascii=False)}\n\n"
            f"Klasörde kullanıcının hazırladığı görsel {'VAR (en az bir fikir tek_gorsel olsun)' if has_inbox else 'yok'}.\n\n"
            f"{count * 3} farklı içerik fikri üret, puana göre büyükten küçüğe sırala. "
            f"Çoğunlukla carousel öner (yeni hesaplarda kaydetme ve erişim için en güçlü format)."
        ),
        schema=IdeaList,
    )
    ideas = sorted(result.fikirler, key=lambda i: i.puan, reverse=True)
    return ideas[:count]
