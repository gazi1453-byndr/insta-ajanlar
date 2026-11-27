"""FİKİR / STRATEJİ AJANI
Haftalık hook bankasını (gerçek arama ilgisi), araştırma raporunu, analistin
öğrendiklerini ve geçmiş gönderileri kullanarak günün içerik fikirlerini seçer.
"""
from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from .common import DATA, PUBLISHED, QUEUE, brand_brief, config, learnings, read_json, write_json
from .llm import ask

AGENT = "Fikir Ajanı"


class Idea(BaseModel):
    konu: str = Field(description="Somut konu, ör. 'Clio vs Egea: 1 yılda cebinden çıkan gerçek para'")
    aci: str = Field(description="Konuyu farklı kılan bakış açısı / gizli maliyet vurgusu")
    format: Literal["reel", "carousel"]
    veri_ihtiyaci: str = Field(description="Araştırılması gereken fiyat ve rakamlar, maddeler halinde")
    hedef_duygu: str = Field(description="şaşkınlık, merak, rahatlama vb.")
    neden_simdi: str
    beklenen_etki: Literal["kaydetme", "paylaşma", "yorum", "takip"]
    hook_bankasi_index: int = Field(description="Kullanılan hook bankası maddesinin indeksi, yoksa -1")
    puan: int = Field(description="1-100 arası tutma potansiyeli tahmini")


class IdeaList(BaseModel):
    fikirler: list[Idea]


def _recent_topics(limit: int = 40) -> list[str]:
    topics = []
    for folder in (PUBLISHED, QUEUE):
        for f in sorted(folder.glob("*.json"))[-limit:]:
            topics.append(read_json(f, {}).get("fikir", {}).get("konu", ""))
    return [t for t in topics if t]


def run(count: int) -> list[Idea]:
    cfg = config()["uretim"]
    research = read_json(DATA / "research" / "latest.json", {}).get("rapor", {})
    bank_file = DATA / "hook_bank.json"
    bank = read_json(bank_file, {"hooklar": []})
    unused = [(i, h) for i, h in enumerate(bank.get("hooklar", [])) if not h.get("kullanildi")]
    result = ask(
        AGENT,
        system=(
            "Sen bir 'gerçek maliyet' içerik kanalının içerik stratejistisin. İzleyiciye para kazandıran, "
            "para tasarruf ettiren ya da merakını gideren, somut rakamla anlatılabilen konular seçersin. "
            "Konu rakamla doğrulanamıyorsa seçmezsin.\n\n" + brand_brief()
        ),
        content=(
            f"## Haftalık hook bankası (son 7 günün gerçek arama ilgisi; öncelik bunlarda)\n"
            f"{json.dumps([{'index': i, **h} for i, h in unused], ensure_ascii=False)}\n\n"
            f"## Araştırma raporu\n{json.dumps(research, ensure_ascii=False)[:30000]}\n\n"
            f"## Geçmiş verilerden öğrenilenler\n{learnings()}\n\n"
            f"## Son paylaşılan/planlanan konular (TEKRARLAMA)\n{json.dumps(_recent_topics(), ensure_ascii=False)}\n\n"
            f"{count * 3} farklı fikir üret ve puana göre sırala. Format dağılımı yaklaşık: "
            f"%{int(cfg['format_orani']['reel'] * 100)} reel (45 sn video), "
            f"%{int(cfg['format_orani']['carousel'] * 100)} carousel (maliyet tablosu)."
        ),
        schema=IdeaList,
    )
    ideas = sorted(result.fikirler, key=lambda i: i.puan, reverse=True)[:count]
    for idea in ideas:  # kullanılan hook'ları işaretle
        if 0 <= idea.hook_bankasi_index < len(bank.get("hooklar", [])):
            bank["hooklar"][idea.hook_bankasi_index]["kullanildi"] = True
    if bank.get("hooklar"):
        write_json(bank_file, bank)
    return ideas
