"""İÇERİK ÜRETİCİ AJAN
Fikir, hook ve maliyet tablosundan videonun tamamını SABİT SERİ FORMATINDA yazar
(her video aynı iskelet → izleyicinin aklında kalır):

  1  metin   HOOK: ilk 3 saniye, tablodaki en şaşırtıcı rakam
  2  metin   Herkesin bildiği fiyat ("Etikette yazan…")
  3-6 metin  Gizli kalemler (her sahne tek kalem)
  7  grafik  Kalem kalem animasyonlu grafik (tablodan otomatik çizilir)
  8  reveal  "GERÇEK MALİYET" imza sahnesi: tek büyük rakam (tablodan otomatik)
  9  metin   Çıkarım / ipucu (izleyiciye ne kazandırır)
  10 sonuc   Tartışma sorusu + seri imzası

Platforma özel metinler: Instagram Reels, TikTok, YouTube Shorts.
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
    tur: Literal["metin", "grafik", "reveal", "sonuc"] = Field(
        description="metin: başlık+kısa yazı; grafik: maliyet tablosunu çizer; "
                    "reveal: GERÇEK MALİYET büyük rakam sahnesi; sonuc: kapanış sorusu")
    baslik: str = Field(description="Ekrandaki büyük yazı, en fazla 8 kelime")
    metin: str = Field(description="Ekrandaki küçük yazı, en fazla 22 kelime; boş olabilir")
    seslendirme: str = Field(description="Bu sahnede söylenecek doğal konuşma metni, 8-30 kelime")


class Draft(BaseModel):
    hook: str
    slaytlar: list[Slide] = Field(description="Seri formatındaki 8-10 sahne")
    caption: str = Field(description="Instagram açıklaması: ilk satır merak, kısa paragraflar, sonda tartışma "
                                     "sorusu, en altta 'Kaynaklar:' ve fiyat tarihi")
    hashtagler: list[str] = Field(description="Instagram için 3-5 hashtag, # işaretsiz")
    tiktok_aciklama: str = Field(description="TikTok: kısa, merak uyandıran, yorumda tartışma başlatacak soru")
    tiktok_hashtagler: list[str] = Field(description="TikTok için 3-5 hashtag")
    youtube_baslik: str = Field(description="YouTube Shorts: arama odaklı başlık + seri numarası, ör. "
                                            "'Clio mu Egea mı? 1 Yıllık Gerçek Maliyet #3'")
    youtube_aciklama: str = Field(description="Arama anahtar kelimeleri içeren 2-4 cümle + seri numarası + kaynaklar")
    youtube_etiketler: list[str] = Field(description="5-10 arama anahtar kelimesi")
    yorum_sorusu: str = Field(description="Sabitlenecek ilk yorum: tartışma başlatan soru")
    alt_text: str


FORMAT = """SERİ FORMATI (her videoda AYNI, sırayı bozma):
1. [metin] HOOK — ilk 3 saniye. Tablodaki en şaşırtıcı rakama dayan. Seslendirme seri açılışıyla başlasın: "{acilis}"
2. [metin] Herkesin bildiği fiyat (etiket fiyatı / ilk bakışta görülen)
3-6. [metin] Gizli kalemler: her sahnede TEK kalem, tutarıyla (2-4 sahne)
7. [grafik] Kalem kalem grafik. Başlığı tablonun içeriğini anlatsın (grafik tablodan otomatik çizilir)
8. [reveal] Başlık 'GERÇEK MALİYET'. Büyük rakam tablodan otomatik konur, sen yazma. metin alanına tek cümle bağlam yaz
9. [metin] Çıkarım: izleyici bu bilgiyle ne yapmalı / nasıl tasarruf eder (tarafsız, tavsiye değil ipucu)
10. [sonuc] Tartışma sorusu. Seslendirme seri kapanışıyla bitsin: "{kapanis}"
Toplam 8-10 sahne, toplam seslendirme ~{kelime} kelime (~{sure} saniye)."""


def run(idea: Idea, hook: str, sheet: DataSheet, series_no: int,
        previous: Draft | None = None, feedback: str | None = None) -> Draft:
    cfg = config()
    sure = cfg["uretim"]["video_suresi_sn"]
    seri = cfg.get("seri", {})
    fmt = FORMAT.format(acilis=seri.get("acilis", "Bunun gerçek maliyetini hesapladık."),
                        kapanis=seri.get("kapanis_ses", "Gerçek rakamlar için takipte kal."),
                        kelime=int(sure * 2.35), sure=sure)
    task = (
        f"## Fikir\n{idea.model_dump_json()}\n\n## Seçilen hook\n{hook}\n\n"
        f"## Maliyet tablosu (TEK RAKAM KAYNAĞIN BU)\n{as_text(sheet)}\n\n"
        f"## Kaynaklar\n" + "\n".join(sheet.kaynaklar) + "\n\n"
        f"## Öğrenilenler\n{learnings()}\n\n{fmt}\n\n"
        f"Bu video serinin #{series_no}. bölümü; YouTube başlığı ve açıklamasında seri numarasını kullan.\n"
        "Ekrandaki ve seslendirmedeki her rakam tablodakiyle birebir aynı olmalı; kuruşlu rakamları kuruşuyla "
        "yaz (ör. 421.132,50 TL), yuvarlayacaksan '~' kullan. Tabloda olmayan rakam ASLA kullanma. "
        "Seslendirmede rakamları doğal oku (ör. 'yüz on dokuz lira doksan dokuz kuruş' değil '119 lira 99 kuruş'). "
        "Ekrandaki yazılarda (baslik/metin) EMOJİ kullanma; emojiyi sadece açıklamalarda kullan. "
        "Rakamla yazdığın her TL tutarı otomatik olarak tabloyla karşılaştırılır; eşleşmeyen video yayınlanmaz."
    )
    if previous and feedback:
        task += (f"\n\n## Önceki taslak\n{previous.model_dump_json()}\n\n"
                 f"## Düzeltilmesi gerekenler (HEPSİNİ düzelt)\n{feedback}")
    return ask(
        AGENT,
        system=(
            "Sen 'Gerçek Maliyet' serisi için 1 dakikalık dikey videolar yazan bir senaristsin. Format her "
            "bölümde aynıdır; bu, serinin akılda kalmasını sağlar. İzleyiciyi ilk 3 saniyede yakalar, rakamlarla "
            "akıcı bir hikaye anlatır, sonunda yorum yazdıracak bir soru sorarsın. Seslendirme doğal, konuşma "
            "dilinde ve robotik olmayan cümlelerle yazılır.\n\n" + brand_brief()
        ),
        content=task,
        schema=Draft,
    )
