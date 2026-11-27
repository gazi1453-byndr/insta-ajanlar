"""VERİ ARAŞTIRMACISI AJAN
Her içerik fikri için güncel Türkiye fiyatlarını web'de araştırır ve kalem kalem, kaynaklı
bir maliyet tablosu (DataSheet) çıkarır. Toplamları Python yeniden hesaplar.
Ardından KAYNAK DOĞRULAYICI her kalemi kaynak sayfa metniyle karşılaştırır; desteksiz rakam
varsa tablo bir kez düzeltilir, yine geçmezse güven 'düşük' olur ve içerik üretilmez.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .common import brand_brief, log, now
from .llm import ask, research
from .strategist import Idea

AGENT = "Veri Araştırmacısı"


class CostItem(BaseModel):
    kalem: str = Field(description="Kısa kalem adı, ör. 'Kasko', 'Yakıt (15.000 km)'")
    tutar_tl: float = Field(description="Hesap dönemi için TL tutarı (dönem: DataSheet.hesap_donemi)")
    aciklama: str = Field(description="Nasıl hesaplandı, kısa")
    kaynak: str = Field(description="Kaynak sitenin adı ya da URL'si")
    tahmini: bool = Field(description="Kaynakta doğrudan yoksa ve varsayımla hesaplandıysa true")


class Option(BaseModel):
    ad: str = Field(description="Seçeneğin KISA adı, en fazla 22 karakter, ör. 'Renault Clio', '%30 zam'")
    kalemler: list[CostItem]
    toplam_tl: float = Field(description="Kalemlerin toplamı (sistem yeniden hesaplar)")


class DataSheet(BaseModel):
    baslik: str
    fiyat_tarihi: str = Field(description="Fiyatların ait olduğu ay/yıl, ör. 'Kasım 2026'")
    hesap_donemi: str = Field(description="Tüm tutarların kapsadığı dönem, ör. '1 yıl', '1 ay'")
    secenekler: list[Option] = Field(description="Tek konu ise 1, karşılaştırma ise 2-3 seçenek")
    varsayimlar: list[str]
    kaynaklar: list[str] = Field(description="Kullanılan kaynakların listesi (site adı + URL)")
    sonuc: str = Field(description="Rakamlardan çıkan tek cümlelik tarafsız sonuç")
    guven: Literal["yuksek", "orta", "dusuk"] = Field(description="Verilerin güvenilirliği")


def _recompute(sheet: DataSheet) -> DataSheet:
    for opt in sheet.secenekler:
        real = round(sum(i.tutar_tl for i in opt.kalemler), 2)
        if abs(real - opt.toplam_tl) > 1:
            log(AGENT, f"Toplam düzeltildi ({opt.ad}): {opt.toplam_tl:,.0f} → {real:,.0f}")
        opt.toplam_tl = real
    return sheet


def _build(idea: Idea, notes: str, feedback: list[str] | None = None) -> DataSheet:
    extra = ""
    if feedback:
        extra = ("\n\n## KAYNAK DOĞRULAYICI BU SORUNLARI BULDU (düzelt: kaynakta olmayan rakamı çıkar ya da "
                 "açıkça tahmini işaretle ve varsayımını yaz)\n- " + "\n- ".join(feedback))
    sheet = ask(
        AGENT,
        system=("Araştırma notlarını tutarlı bir maliyet tablosuna dönüştürürsün. Tüm tutarlar aynı "
                "hesap dönemine çevrilmiş olmalı. Notlarda olmayan rakamı ekleme; varsayımla "
                "hesapladığın kalemi tahmini=true işaretle.\n\n" + brand_brief()),
        content=f"## Fikir\n{idea.model_dump_json()}\n\n## Araştırma notları\n{notes}{extra}",
        schema=DataSheet,
    )
    return _recompute(sheet)


def run(idea: Idea) -> tuple[DataSheet, dict]:
    from . import fact_checker, llm

    notes = research(
        AGENT,
        system=("Sen titiz bir fiyat ve maliyet araştırmacısısın. Türkiye'deki GÜNCEL fiyatları "
                "resmi siteler, bayi/fiyat listeleri, sigorta/vergi tabloları ve güvenilir haber "
                "kaynaklarından bulursun. Her rakamın yanına kaynağını ve tarihini yazarsın."),
        prompt=(
            f"Bugün {now():%d.%m.%Y}. Şu içerik için gereken bütün maliyet kalemlerini araştır:\n"
            f"Konu: {idea.konu}\nAçı: {idea.aci}\nGereken veriler: {idea.veri_ihtiyaci}\n\n"
            "Her kalem için: güncel TL tutarı, kaynağı (site + URL) ve hesap yöntemi. Gözden kaçan "
            "gizli maliyetleri de bul (vergi, sigorta, bakım, amortisman, komisyon vb.). "
            "Bulamadığın rakamları uydurma; 'bulunamadı' yaz."
        ),
        max_searches=10,
    )
    pages = list(getattr(llm, "last_pages", []) or [])
    sheet = _build(idea, notes)
    fc = fact_checker.run(sheet, pages)
    probs = fact_checker.problems(fc)
    if probs:
        log(AGENT, f"Kaynak doğrulayıcı {len(probs)} sorun buldu → tablo düzeltiliyor")
        sheet = _build(idea, notes, probs)
        fc = fact_checker.run(sheet, pages)
        probs = fact_checker.problems(fc)
    if probs:
        sheet.guven = "dusuk"
        log(AGENT, f"Tablo doğrulamadan geçemedi: {probs[:3]}")
    log(AGENT, f"Tablo hazır: {sheet.baslik} ({len(sheet.secenekler)} seçenek, güven: {sheet.guven})")
    return sheet, {"kaynak_dogrulama": fc.model_dump(), "sorunlar": probs}


def as_text(sheet: DataSheet) -> str:
    """Diğer ajanlara verilecek okunur tablo."""
    out = [f"# {sheet.baslik} ({sheet.hesap_donemi}, {sheet.fiyat_tarihi} fiyatları)"]
    for o in sheet.secenekler:
        out.append(f"\n## {o.ad} — TOPLAM {o.toplam_tl:,.2f} TL")
        for i in o.kalemler:
            out.append(f"- {i.kalem}: {i.tutar_tl:,.2f} TL{' (tahmini)' if i.tahmini else ''} — {i.kaynak}")
    out.append("\nVarsayımlar: " + "; ".join(sheet.varsayimlar))
    out.append("Sonuç: " + sheet.sonuc)
    return "\n".join(out)
