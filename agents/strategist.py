"""FİKİR / STRATEJİ AJANI
Haftalık hook bankasını (gerçek arama ilgisi), araştırma raporunu, analistin
öğrendiklerini ve geçmiş gönderileri kullanarak günün içerik fikirlerini seçer.
"""
from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from .common import DATA, PUBLISHED, QUEUE, brand_brief, config, gunun_serisi, learnings, read_json, write_json
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
    alt_seri: str = Field(default="", description="Günün alt serisine aitse onun adı (ör. 'ZAM TAKİBİ'), değilse boş")
    izleyici: str = Field(default="", description="Bir takipçinin yorumdaki isteğinden geldiyse kullanıcı adı (@ olmadan), değilse boş")
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
    tema = gunun_serisi()
    istekler = [r for r in read_json(DATA / "izleyici_istekleri.json", {"istekler": []})["istekler"]
                if not r.get("kullanildi")]
    istekler = sorted(istekler, key=lambda r: -r.get("sayi", 1))[:10]
    result = ask(
        AGENT,
        system=(
            "Sen bir 'gerçek maliyet' içerik kanalının içerik stratejistisin. İzleyiciye para kazandıran, "
            "para tasarruf ettiren ya da merakını gideren, somut rakamla anlatılabilen konular seçersin. "
            "Konu rakamla doğrulanamıyorsa seçmezsin.\n\n" + brand_brief()
        ),
        content=(
            f"## Güncel fikir bankası (kaynak='gundem' olanlar BUGÜN taranan internet ve sosyal medya "
            f"gündeminden; 'guncellik' puanı yüksek olanlar ÖNCELİKLİ. Fikirlerin en az 2/3'ü bugünün "
            f"gündeminden gelsin: güncellik izlenmeyi katlar)\n"
            f"{json.dumps([{'index': i, **h} for i, h in unused], ensure_ascii=False)}\n\n"
            f"## BUGÜNÜN ALT SERİSİ: {tema or 'yok'}\nİlk fikir MUTLAKA bu alt seriye uysun ve alt_seri alanına "
            f"'{tema}' yaz (haftalık sabit gün: izleyici bu günü bekler). Diğer fikirlerde alt_seri boş kalsın.\n\n"
            f"## Takipçi istekleri (yorumlardan; 'sayi' = kaç kişi istedi)\n{json.dumps(istekler, ensure_ascii=False)}\n"
            "Uygun bir istek varsa en az 1 fikri ondan üret ve izleyici alanına isteyen kullanıcının adını yaz "
            "(İZLEYİCİ SORUSU gününde ilk fikir mutlaka bir takipçi isteği olsun).\n\n"
            f"## Araştırma raporu\n{json.dumps(research, ensure_ascii=False)[:9000]}\n\n"
            f"## Geçmiş verilerden öğrenilenler\n{learnings()}\n\n"
            f"## Son paylaşılan/planlanan konular (TEKRARLAMA)\n{json.dumps(_recent_topics(), ensure_ascii=False)}\n\n"
            f"{count * 3} farklı fikir üret ve puana göre sırala. Format dağılımı yaklaşık: "
            f"%{int(cfg['format_orani']['reel'] * 100)} reel ({cfg.get('video_suresi_sn', 60)} sn video), "
            f"%{int(cfg['format_orani']['carousel'] * 100)} carousel (maliyet tablosu)."
        ),
        schema=IdeaList,
    )
    ranked = sorted(result.fikirler, key=lambda i: i.puan, reverse=True)
    themed = [i for i in ranked if tema and i.alt_seri.strip().upper() == tema.upper()]
    if themed:  # günün alt serisi her zaman ilk sırada (izleyici o günü bekler)
        ranked = [themed[0]] + [i for i in ranked if i is not themed[0]]
    for i in ranked[1:]:
        if i.alt_seri and i.alt_seri.strip().upper() == tema.upper() and i is not ranked[0]:
            i.alt_seri = ""  # günde tek tema videosu
    ideas = ranked[:count]
    for idea in ideas:  # kullanılan hook'ları işaretle
        if 0 <= idea.hook_bankasi_index < len(bank.get("hooklar", [])):
            bank["hooklar"][idea.hook_bankasi_index]["kullanildi"] = True
    if bank.get("hooklar"):
        write_json(bank_file, bank)
    used_users = {i.izleyici.lstrip("@").lower() for i in ideas if i.izleyici}
    if used_users:  # kullanılan takipçi isteklerini işaretle
        reqs = read_json(DATA / "izleyici_istekleri.json", {"istekler": []})
        for r in reqs["istekler"]:
            if r.get("kullanici", "").lower() in used_users:
                r["kullanildi"] = True
        write_json(DATA / "izleyici_istekleri.json", reqs)
    return ideas
