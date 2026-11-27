"""HOOK YAZARI AJAN
Bir fikir ve onun maliyet tablosu için farklı tekniklerle "ilk 3 saniye"
kancaları yazar, puanlar ve en güçlüsünü seçer. Kanca tablodaki en şaşırtıcı
rakama dayanmalı ve vaadi içerikte mutlaka karşılanmalı.
"""
from __future__ import annotations

import json

from pydantic import BaseModel, Field

from .common import DATA, brand_brief, learnings, read_json
from .data_researcher import DataSheet, as_text
from .llm import ask
from .strategist import Idea

AGENT = "Hook Yazarı"

TECHNIQUES = [
    "şaşırtıcı toplam rakam ('Bu araba yılda cebinden 187.000 TL alıyor')",
    "gizli maliyet ('Kimsenin hesaba katmadığı kalem…')",
    "A mı B mi ikilemi ('Clio mu Egea mı? Fark 1 yılda …')",
    "yaygın inanışa karşı çıkmak",
    "doğrudan soru ('100.000 TL ile İstanbul'da ne iş kurulur?')",
    "kişisel hesap ('Maaşımla bunu alsam kaç ay çalışmam gerekir')",
    "liste vaadi (X kalem, Y gizli masraf)",
    "zaman baskısı / zam gündemi",
]


class Hook(BaseModel):
    metin: str = Field(description="En fazla 12 kelime; ilk 3 saniyede okunur/söylenir")
    teknik: str
    puan: int = Field(description="1-100: kaydırmayı durdurma gücü")
    gerekce: str


class HookSet(BaseModel):
    hooklar: list[Hook]
    secilen_index: int = Field(description="En iyi hook'un indeksi (0'dan başlar)")


def run(idea: Idea, sheet: DataSheet) -> HookSet:
    research = read_json(DATA / "research" / "latest.json", {}).get("rapor", {})
    return ask(
        AGENT,
        system=(
            "Sen kısa video ve Instagram için hook yazmada uzman bir metin yazarısın. Kanca tablodaki "
            "GERÇEK bir rakama dayanır; tabloda olmayan rakam kullanmazsın, abartmazsın.\n\n" + brand_brief()
        ),
        content=(
            f"## Fikir\n{idea.model_dump_json()}\n\n## Maliyet tablosu\n{as_text(sheet)}\n\n"
            f"## Büyük sayfalardan gözlenen hook yapıları\n"
            f"{json.dumps(research.get('hook_ornekleri', []), ensure_ascii=False)}\n\n"
            f"## Öğrenilenler\n{learnings()}\n\n"
            f"Şu tekniklerin her biriyle bir hook yaz: {'; '.join(TECHNIQUES)}. "
            "Sonra dürüstçe puanla ve en güçlüsünü seç."
        ),
        schema=HookSet,
    )
