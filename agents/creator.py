"""İÇERİK ÜRETİCİ AJAN
Fikir, hook ve maliyet tablosundan içeriğin tamamını yazar:
- Sahneler/slaytlar (metin, tablo/grafik, sonuç) ve her sahnenin seslendirme metni
- Platforma özel metinler: Instagram Reels, TikTok, YouTube Shorts
Müdür geri bildirim verirse taslağı revize eder.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .common import brand_brief, config, learnings
from .data_researcher import DataSheet, as_text
from .llm import ask
from .strategist import Idea

AGENT = "İçerik Üretici"


class Slide(BaseModel):
    tur: Literal["metin", "grafik", "sonuc"] = Field(
        description="metin: başlık+kısa yazı; grafik: maliyet tablosunu animasyonlu çubuk grafikle gösterir; sonuc: kapanış + soru")
    baslik: str = Field(description="Ekrandaki büyük yazı, en fazla 8 kelime")
    metin: str = Field(description="Ekrandaki küçük yazı, en fazla 25 kelime; boş olabilir")
    seslendirme: str = Field(description="Bu sahnede söylenecek doğal konuşma metni, 1-2 kısa cümle")


class Draft(BaseModel):
    hook: str
    slaytlar: list[Slide] = Field(description="İlk sahne hook; TAM OLARAK BİR 'grafik' sahnesi (maliyet tablosunu çizer); son sahne 'sonuc'")
    caption: str = Field(description="Instagram Reels/gönderi açıklaması: ilk satır merak, kısa paragraflar, "
                                     "sonda tartışma başlatan soru, en altta 'Kaynaklar:' ve fiyat tarihi")
    hashtagler: list[str] = Field(description="Instagram için 3-5 hashtag, # işaretsiz")
    tiktok_aciklama: str = Field(description="TikTok: kısa, merak uyandıran, yorumda tartışma başlatacak soru")
    tiktok_hashtagler: list[str] = Field(description="TikTok için 3-5 hashtag")
    youtube_baslik: str = Field(description="YouTube Shorts: arama odaklı başlık, ör. 'Clio mu Egea mı? 1 Yıllık Gerçek Maliyet #3'")
    youtube_aciklama: str = Field(description="Arama anahtar kelimeleri içeren 2-4 cümle + seri numarası + kaynaklar")
    youtube_etiketler: list[str] = Field(description="5-10 arama anahtar kelimesi")
    yorum_sorusu: str = Field(description="Sabitlenecek ilk yorum: tartışma başlatan soru")
    alt_text: str


def run(idea: Idea, hook: str, sheet: DataSheet, series_no: int,
        previous: Draft | None = None, feedback: str | None = None) -> Draft:
    cfg = config()["uretim"]
    if idea.format == "reel":
        shape = (f"{cfg['video_suresi_sn']} saniyelik dikey video için 6-8 sahne yaz. Seslendirme toplamı "
                 f"yaklaşık {int(cfg['video_suresi_sn'] * 2.4)} kelime olsun. Hızlı kurgu: her sahne tek fikir.")
    else:
        shape = f"{cfg['carousel_slayt_sayisi']} slaytlık carousel yaz (seslendirme alanını kısa özet olarak doldur)."
    task = (
        f"## Fikir\n{idea.model_dump_json()}\n\n## Seçilen hook\n{hook}\n\n"
        f"## Maliyet tablosu (TEK RAKAM KAYNAĞIN BU)\n{as_text(sheet)}\n\n"
        f"## Kaynaklar\n" + "\n".join(sheet.kaynaklar) + "\n\n"
        f"## Öğrenilenler\n{learnings()}\n\n"
        f"{shape}\nBu içerik serinin #{series_no}. bölümü; YouTube başlığı ve açıklamasında seri numarasını kullan.\n"
        "Ekrandaki ve seslendirmedeki her rakam tablodakiyle birebir aynı olmalı; kuruşlu rakamları kuruşuyla "
        "yaz (ör. 421.132,50 TL), yuvarlayacaksan '~' kullan. Sadece BİR 'grafik' sahnesi kullan: o sahne "
        "tablodaki seçenekleri ve kalemleri otomatik çizer; başlığını buna göre yaz. Tabloda olmayan bir "
        "karşılaştırmayı grafik olarak vaat etme, metin sahnesinde kaynağıyla ver."
    )
    if previous and feedback:
        task += (f"\n\n## Önceki taslak\n{previous.model_dump_json()}\n\n"
                 f"## Müdürün geri bildirimi (bunları mutlaka düzelt)\n{feedback}")
    return ask(
        AGENT,
        system=(
            "Sen 'gerçek maliyet' kanalı için kısa video ve carousel yazan bir içerik üreticisisin. "
            "İzleyiciyi ilk 3 saniyede yakalar, rakamlarla akıcı bir hikaye anlatır, sonunda yorum "
            "yazdıracak bir soru sorarsın. Seslendirme doğal, konuşma dilinde ve robotik olmayan "
            "cümlelerle yazılır.\n\n" + brand_brief()
        ),
        content=task,
        schema=Draft,
    )
