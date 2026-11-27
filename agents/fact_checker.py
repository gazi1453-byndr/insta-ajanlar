"""KAYNAK DOĞRULAYICI AJAN
Maliyet tablosundaki HER kalemi, araştırmada bulunan kaynak sayfaların metniyle tek tek
karşılaştırır: rakam kaynakta birebir geçiyor mu, tablodaki diğer kalemlerden mi hesaplanmış,
yoksa desteksiz mi? Desteksiz ve 'tahmini' işaretlenmemiş kalem varsa tablo geçemez.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .data_researcher import DataSheet, as_text
from .llm import ask

AGENT = "Kaynak Doğrulayıcı"


class ItemCheck(BaseModel):
    secenek: str
    kalem: str
    durum: Literal["kaynakta_var", "hesaplanan", "tahmini_isaretli", "desteksiz"]
    alinti: str = Field(description="Rakamı destekleyen kaynak cümlesi (birebir) ya da hesap formülü; yoksa boş")
    aciklama: str


class FactCheck(BaseModel):
    kalemler: list[ItemCheck]
    tarih_guncel_mi: bool = Field(description="Kaynakların tarihi tablodaki fiyat tarihiyle uyumlu mu?")
    ozet: str


def run(sheet: DataSheet, pages: list[dict]) -> FactCheck:
    if pages:
        src = "\n\n".join(f"[{i + 1}] {p['title']} — {p['url']}\n{p['content'][:2000]}" for i, p in enumerate(pages[:14]))
    else:
        src = "(Ham sayfa metni yok; sadece tablodaki kaynak listesine ve açıklamalara bakabilirsin.)"
    return ask(
        AGENT,
        system=("Sen titiz bir finans editörü ve doğrulayıcısın (fact-checker). Hiçbir rakamı varsayımla "
                "geçirmezsin. Bir rakam ancak kaynak metinde birebir geçiyorsa ya da tablodaki başka kalemlerden "
                "açık bir formülle hesaplanıyorsa desteklidir."),
        content=(f"## Maliyet tablosu\n{as_text(sheet)}\nVarsayımlar: {sheet.varsayimlar}\n\n"
                 f"## Kaynak sayfalar\n{src}\n\n"
                 "Tablodaki her seçeneğin her kalemini kontrol et. Kalem 'tahmini' işaretliyse ve varsayımı "
                 "makulse 'tahmini_isaretli' de. Kalemin 'hesap' açıklamasındaki formül, kaynak metinde geçen bir "
                 "fiyat/oranla (ör. '4.500.000 × %21,1', kaynakta %21,1 var) ya da tablodaki/varsayımlardaki değerlerle "
                 "kuruluyorsa formülü kendin hesapla: sonuç tutarla 1 TL içinde uyuşuyorsa 'hesaplanan' de ve "
                 "alıntıya formülü + kaynaktaki oranın geçtiği cümleyi yaz. Rakam kaynakta yoksa ve hesaplanamıyorsa "
                 "'desteksiz' de."),
        schema=FactCheck,
    )


def unsupported(report) -> list[str]:
    """Desteksiz (kaynakta olmayan, hesaplanamayan, 'tahmini' işaretlenmemiş) kalemler.
    FactCheck nesnesini ya da raporun sözlük hâlini kabul eder:
    {"kaynak_dogrulama": {...}} (üretim hattı), {"rapor": {...}} (senaryo denetimi) ya da doğrudan {"kalemler": [...]}."""
    if report is None:
        return []
    if isinstance(report, FactCheck):
        items = [c.model_dump() for c in report.kalemler]
    else:
        d = report
        while isinstance(d, dict) and "kalemler" not in d:
            d = d.get("kaynak_dogrulama") or d.get("rapor")
        items = (d or {}).get("kalemler", []) if isinstance(d, dict) else []
    return [f"{c.get('secenek', '')} / {c.get('kalem', '')}" for c in items if c.get("durum") == "desteksiz"]


def problems(fc: FactCheck) -> list[str]:
    out = [f"{c.secenek} / {c.kalem}: kaynakta yok ({c.aciklama})" for c in fc.kalemler if c.durum == "desteksiz"]
    if not fc.tarih_guncel_mi:
        out.append("Kaynakların tarihi güncel değil: " + fc.ozet)
    return out
