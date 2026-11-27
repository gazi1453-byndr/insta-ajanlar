"""BAŞ MÜDÜR AJAN (Genel Yayın Yönetmeni) — son kapı
Müdürün onayladığı, kontrollerden geçen ve videosu çekilmiş içeriği en son o görür.
Tüm raporları (kaynak doğrulama, grafik/senkron ölçümleri, sanat yönetmeni, müdür) okur;
müdürden daha yüksek eşikle karar verir ve VETO yetkisi vardır.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from .common import brand_brief, config, learnings
from .creator import Draft
from .data_researcher import DataSheet, as_text
from .llm import ask
from .strategist import Idea

AGENT = "Baş Müdür"


class ChiefVerdict(BaseModel):
    puan: int = Field(description="0-100")
    karar: Literal["YAYINLA", "REVIZYON", "RED"]
    gerekce: str = Field(description="2-4 cümle")
    duzeltmeler: list[str] = Field(description="REVIZYON ise somut düzeltmeler; değilse boş")
    seri_uyumu: bool = Field(description="Video serinin sabit formatına ve kimliğine uyuyor mu?")


def run(idea: Idea, draft: Draft, sheet: DataSheet, reports: dict, frames: list[Path]) -> ChiefVerdict:
    esik = config()["uretim"].get("bas_mudur_esigi", 85)
    content = [{"type": "image_path", "path": str(p)} for p in frames[:6]] + [{"type": "text", "text": (
        f"## Fikir\n{idea.model_dump_json()}\n\n## Maliyet tablosu\n{as_text(sheet)}\n\n"
        f"## Senaryo\n{draft.model_dump_json()}\n\n"
        f"## Kontrol raporları\n{json.dumps(reports, ensure_ascii=False)[:9000]}\n\n"
        f"## Öğrenilenler\n{learnings()}\n\n"
        f"Yayın eşiğin {esik}/100. Hesap günde 3 video yayınlıyor: vasat bir video bile serinin güvenini "
        "zedeler. Rakam şüphesi, okunurluk sorunu, sıkıcı açılış ya da format dışı akış varsa YAYINLAMA. "
        "Düzeltilebilirse REVIZYON, fikir zayıfsa RED. BAŞLIĞIN/HOOK'UN VERDİĞİ SÖZ: Başlık ya da hook bir soru soruyor ya da bir hesap vaat ediyorsa (ör. 'aylık depo maliyeti ne?'), video bunu RAKAMLA cevaplamıyorsa en fazla 55 puan ver. Tablo tek bir etiket fiyatından ibaretse 'gerçek maliyet' değildir: en fazla 50 puan. ")}]
    v = ask(AGENT,
            system=("Sen bir finans/medya kuruluşunun genel yayın yönetmenisin; müdürlerin onayını da denetlersin. "
                    "Senden geçen her video markanın imzasını taşır.\n\n" + brand_brief()),
            content=content, role="denetci", schema=ChiefVerdict)
    if v.karar == "YAYINLA" and (v.puan < esik or not v.seri_uyumu):
        v.karar = "REVIZYON"
    return v
