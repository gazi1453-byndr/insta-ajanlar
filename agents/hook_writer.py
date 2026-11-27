"""3) HOOK YAZARI AJAN
Bir fikir için farklı tekniklerle çok sayıda açılış cümlesi (hook) yazar,
her birini kendi puanlar ve en güçlüsünü seçer. Hook; kaydırmayı durduran
ilk cümle / ilk slayttır.
"""
from __future__ import annotations

import json

from pydantic import BaseModel, Field

from .common import DATA, brand_brief, learnings, read_json
from .llm import ask
from .strategist import Idea

AGENT = "Hook Yazarı"

TECHNIQUES = [
    "merak boşluğu (cevabı hemen vermeden soru açmak)",
    "yaygın inanışa karşı çıkmak",
    "somut rakam / sonuç",
    "kitlenin yaptığı hatayı söylemek",
    "kişisel itiraf / hikaye başlangıcı",
    "liste vaadi (X şey, Y adım)",
    "önce / sonra karşılaştırması",
    "doğrudan hedef kitleye seslenme",
]


class Hook(BaseModel):
    metin: str = Field(description="En fazla 12 kelime")
    teknik: str
    puan: int = Field(description="1-100: kaydırmayı durdurma gücü")
    gerekce: str


class HookSet(BaseModel):
    hooklar: list[Hook]
    secilen_index: int = Field(description="hooklar listesinde en iyi hook'un indeksi (0'dan başlar)")


def run(idea: Idea) -> HookSet:
    research = read_json(DATA / "research" / "latest.json", {}).get("rapor", {})
    return ask(
        AGENT,
        system=(
            "Sen Instagram için hook (açılış cümlesi) yazmada uzman bir metin yazarısın. "
            "İnsanların kaydırmayı bırakıp okumaya başlamasını sağlarsın; ama asla yalan "
            "ya da tık tuzağı vaat vermezsin. Hook'un vaadi içerikte mutlaka karşılanmalı.\n\n"
            + brand_brief()
        ),
        content=(
            f"## Fikir\n{idea.model_dump_json()}\n\n"
            f"## Büyük sayfalardan gözlenen hook yapıları\n"
            f"{json.dumps(research.get('hook_ornekleri', []), ensure_ascii=False)}\n\n"
            f"## Öğrenilenler\n{learnings()}\n\n"
            f"Şu tekniklerin her biriyle bir hook yaz: {'; '.join(TECHNIQUES)}. "
            "Sonra hepsini dürüstçe puanla ve en güçlüsünü seç."
        ),
        schema=HookSet,
    )
