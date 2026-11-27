"""SANAT YÖNETMENİ AJAN
BİTMİŞ videodan çıkarılan sahne karelerini (animasyon bitmiş hali) görerek kontrol eder:
okunurluk, yazım/Türkçe hataları, renk ve seri şablonu tutarlılığı, rakamların ekranda
doğru ve tam görünmesi, telefonda Reels arayüzüyle çakışma. "Mükemmel değilse geçmez."
"""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from .common import brand_brief, config
from .creator import Draft
from .data_researcher import DataSheet, as_text
from .llm import ask

AGENT = "Sanat Yönetmeni"


class ArtReview(BaseModel):
    puan: int = Field(description="0-100 görsel kalite puanı")
    gecti: bool = Field(description="Sadece hiçbir sorun yoksa true")
    sorunlar: list[str] = Field(description="Sahne numarasıyla somut sorunlar; yoksa boş liste")
    yazim_hatalari: list[str] = Field(description="Ekrandaki Türkçe yazım/noktalama hataları; yoksa boş")


def run(draft: Draft, sheet: DataSheet, frames: list[Path]) -> ArtReview:
    scenes = "\n".join(f"Sahne {i}: [{s.tur}] {s.baslik} | {s.metin}" for i, s in enumerate(draft.slaytlar, 1))
    content = [{"type": "image_path", "path": str(p)} for p in frames] + [{"type": "text", "text": (
        f"Ekteki görseller videonun sırasıyla sahne 1..{len(frames)} son kareleri.\n\n"
        f"## Sahne metinleri\n{scenes}\n\n## Maliyet tablosu\n{as_text(sheet)}\n\n"
        "Kontrol et: (1) her yazı telefonda kolay okunuyor mu, (2) kesik/taşan/üst üste binen yazı var mı, "
        "(3) Türkçe yazım ve noktalama hatası var mı, (4) ekrandaki rakamlar tabloyla aynı mı, "
        "(5) her sahnede seri rozeti ve aynı renk düzeni var mı, (6) grafik anlaşılır mı. "
        f"Seri adı: {config().get('seri', {}).get('ad', 'GERÇEK MALİYET')}. "
        "Sadece kusursuzsa gecti=true ver.")}]
    v = ask(AGENT,
            system=("Sen kısa video ve infografik konusunda deneyimli bir sanat yönetmenisin. Telefonda izlenen "
                    "videolarda okunurluk ve tutarlılık konusunda acımasızsın.\n\n" + brand_brief()),
            content=content, schema=ArtReview)
    if v.sorunlar or v.yazim_hatalari or v.puan < 85:
        v.gecti = False
    return v
