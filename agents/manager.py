"""MÜDÜR AJAN (Yayın Yönetmeni)
Her içeriği yayına çıkmadan önce inceler ve "bu içerik tutar mı?" sorusuna
puanlı karar verir: ONAY, REVİZYON (geri bildirimle üreticiye geri gönder)
ya da RED. Görselleri görür; ekrandaki her rakamı maliyet tablosuyla
karşılaştırır. Kaynaksız ya da tabloyla uyuşmayan rakam = onay yok.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from .common import brand_brief, config, learnings
from .creator import Draft
from .data_researcher import DataSheet, as_text
from .llm import ask
from .strategist import Idea

AGENT = "Müdür"


class Scores(BaseModel):
    hook_gucu: int = Field(description="0-25: ilk 3 saniyede kaydırmayı durdurur mu?")
    deger: int = Field(description="0-20: izleyiciye para kazandırır/tasarruf ettirir/merakını giderir mi?")
    rakam_dogrulugu: int = Field(description="0-20: ekrandaki ve seslendirmedeki her rakam tabloyla birebir mi, kaynak ve tarih var mı?")
    akis_ve_tutma: int = Field(description="0-10: sahneler sonuna kadar izletir mi, kurgu hızlı mı?")
    ozgunluk: int = Field(description="0-10: farklı bir açı ya da gizli maliyet var mı?")
    platform_metinleri: int = Field(description="0-5: Reels/TikTok/YouTube metinleri platforma uygun mu?")
    gorsel_okunurluk: int = Field(description="0-10: telefonda kolay okunuyor mu?")


class Verdict(BaseModel):
    puanlar: Scores
    toplam: int = Field(description="Puanların toplamı, 0-100")
    karar: Literal["ONAY", "REVIZYON", "RED"]
    tutar_mi: str = Field(description="Bu içerik neden tutar ya da tutmaz, 2-3 cümle")
    rakam_hatalari: list[str] = Field(description="Tabloyla uyuşmayan ya da kaynaksız her rakam; yoksa boş")
    geri_bildirim: str = Field(description="REVİZYON ise somut, maddeli düzeltme talimatları")


def _img(path: Path) -> dict:
    return {"type": "image_path", "path": str(path)}


def run(idea: Idea, draft: Draft, sheet: DataSheet, images: list[Path], attempt: int) -> Verdict:
    cfg = config()["uretim"]
    text = (
        f"## Fikir\n{idea.model_dump_json()}\n\n## Maliyet tablosu\n{as_text(sheet)}\n"
        f"Veri güveni: {sheet.guven}. Kaynaklar: {'; '.join(sheet.kaynaklar)}\n\n"
        f"## Taslak\n{draft.model_dump_json()}\n\n"
        f"## Geçmiş verilerden öğrenilenler\n{learnings()}\n\n"
        f"Bu {attempt}. deneme. Onay eşiği {cfg['onay_esigi']}/100. Eşik altındaysa ve düzeltilebilirse "
        "REVIZYON, fikir temelden zayıfsa ya da veri güveni düşükse RED ver. BAŞLIĞIN/HOOK'UN VERDİĞİ SÖZ: Başlık ya da hook bir soru soruyor ya da bir hesap vaat ediyorsa (ör. 'aylık depo maliyeti ne?'), video bunu RAKAMLA cevaplamıyorsa en fazla 55 puan ver. Tablo tek bir etiket fiyatından ibaretse 'gerçek maliyet' değildir: en fazla 50 puan. İlk sahnelerin görselleri ektedir."
    )
    content = [*[_img(p) for p in images[:4]], {"type": "text", "text": text}]
    v = ask(
        AGENT,
        system=(
            "Sen büyük bir finans/medya yayınının yayın yönetmenisin. Yüzlerce viral kısa video yönettin. "
            "Sert ama adilsin: vasat içeriği onaylamazsın, yanlış rakamı ASLA geçirmezsin; çünkü sponsorlar "
            "ve izleyici güveni doğruluğa bağlı.\n\n" + brand_brief()
        ),
        content=content,
        role="denetci", schema=Verdict,
    )
    v.toplam = sum(v.puanlar.model_dump().values())
    if v.karar == "ONAY" and (v.toplam < cfg["onay_esigi"] or v.rakam_hatalari):
        v.karar = "REVIZYON"
        if v.rakam_hatalari:
            v.geri_bildirim = "Rakam hataları: " + "; ".join(v.rakam_hatalari) + "\n" + v.geri_bildirim
    return v
