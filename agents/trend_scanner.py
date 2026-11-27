"""GÜNDEM TARAYICI AJAN (her gün)
İnternet ve sosyal medyadaki GÜNCEL ilgiyi tarar, o günün en güncel içerik fikirlerini çıkarır:
  - Google Trends Türkiye: günün yükselen aramaları (ücretsiz RSS, anahtar gerekmez)
  - Haberler (son 48 saat): zamlar, yeni fiyat listeleri, vergi/maaş düzenlemeleri
  - Sosyal medya: Reddit, Ekşi Sözlük, YouTube (Tavily alan adı filtresiyle)
Sonuç: data/trends/YYYY-MM-DD.json + hook bankasına "gündem" etiketiyle eklenir (4 gün geçerli).
Fikir Ajanı güncel (bugünkü) maddelere öncelik verir.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime

import requests
from pydantic import BaseModel, Field

from . import search as web
from .common import DATA, brand_brief, config, log, now, read_json, write_json
from .llm import ask

AGENT = "Gündem Tarayıcı"

NEWS_QUERIES = ["zam geldi yeni fiyat", "yeni fiyat listesi açıklandı", "vergi maaş düzenlemesi yeni",
                "abonelik ücretlerine zam", "fiyatlar ne kadar oldu bugün"]
SOCIAL = [("reddit.com", "Türkiye fiyat zam maaş geçinmek"),
          ("eksisozluk.com", "zam fiyat pahalılık"),
          ("youtube.com", "fiyat karşılaştırma maliyet 2026")]


class AgendaItem(BaseModel):
    konu: str = Field(description="Güncel, rakamla anlatılabilecek somut konu")
    neden_simdi: str = Field(description="Bugün/bu hafta neden konuşuluyor (olay, zam, açıklama)")
    kanit: str = Field(description="Gündemde olduğunu gösteren kaynak (site + link)")
    hook: str = Field(description="İlk 3 saniye kancası, en fazla 12 kelime")
    veri_ihtiyaci: str = Field(description="Araştırılacak fiyatlar/rakamlar")
    guncellik: int = Field(description="1-10: ne kadar güncel/sıcak (10 = bugün herkes konuşuyor)")


class Agenda(BaseModel):
    maddeler: list[AgendaItem] = Field(description="8-12 madde, en güncelden aza")
    ozet: str = Field(description="Günün gündeminin 3-4 cümlelik özeti")


def google_trends_tr() -> list[dict]:
    try:
        r = requests.get("https://trends.google.com/trending/rss?geo=TR", timeout=30,
                         headers={"User-Agent": "Mozilla/5.0 (insta-ajanlar gundem tarayici)"})
        r.raise_for_status()
        root = ET.fromstring(r.content)
        ns = {"ht": "https://trends.google.com/trending/rss"}
        out = []
        for it in root.iter("item"):
            title = (it.findtext("title") or "").strip()
            traffic = it.findtext("ht:approx_traffic", default="", namespaces=ns)
            news = [n.findtext("ht:news_item_title", default="", namespaces=ns) for n in it.findall("ht:news_item", ns)]
            out.append({"arama": title, "hacim": traffic, "haberler": [x for x in news if x][:2]})
        log(AGENT, f"Google Trends TR: {len(out)} yükselen arama")
        return out[:25]
    except Exception as e:
        log(AGENT, f"Google Trends okunamadı: {str(e)[:120]}")
        return []


def _scan_web() -> list[dict]:
    items = []
    if not web.enabled():
        log(AGENT, "TAVILY_API_KEY yok: haber/sosyal medya taraması atlandı")
        return items
    for q in NEWS_QUERIES:
        try:
            for it in web.search(q, 4, days=2):
                items.append({"tur": "haber", "baslik": it["title"], "url": it["url"], "ozet": it["content"][:500]})
        except Exception as e:
            log(AGENT, f"Haber araması başarısız ({q}): {str(e)[:100]}")
    for domain, q in SOCIAL:
        try:
            for it in web.search(q, 4, days=None, domains=[domain]):
                items.append({"tur": domain, "baslik": it["title"], "url": it["url"], "ozet": it["content"][:500]})
        except Exception as e:
            log(AGENT, f"{domain} taraması başarısız: {str(e)[:100]}")
    log(AGENT, f"Haber + sosyal medya: {len(items)} sonuç")
    return items


def run() -> Agenda | None:
    stamp = f"{now():%Y-%m-%d}"
    out_file = DATA / "trends" / f"{stamp}.json"
    if out_file.exists():
        log(AGENT, "Bugünün gündemi zaten tarandı")
        return Agenda(**read_json(out_file)["gundem"])
    trends = google_trends_tr()
    found = _scan_web()
    if not trends and not found:
        return None
    cfg = config()["hesap"]
    agenda = ask(
        AGENT,
        system=("Sen bir gündem editörüsün. Türkiye'de BUGÜN konuşulan konular içinden, gerçek maliyet / fiyat "
                "karşılaştırmasıyla anlatılabilecek olanları seçersin. Sadece verilen kaynaklarda gerçekten "
                "görülen gündemi kullanırsın; uydurma olay yazmazsın.\n\n" + brand_brief()),
        content=(f"Bugün {now():%d.%m.%Y}. Niş: {cfg['nis']}\n\n"
                 f"## Google Trends Türkiye (bugün yükselen aramalar)\n{trends}\n\n"
                 f"## Son 48 saatin haberleri ve sosyal medya\n{found}\n\n"
                 "Bu nişe uyan, rakamla anlatılabilecek en güncel 8-12 içerik fikrini çıkar. Fiyat/zam/maliyetle "
                 "ilgisi olmayan gündemi (spor sonucu, magazin) ancak maliyet açısı kurulabiliyorsa al."),
        schema=Agenda,
    )
    write_json(out_file, {"tarih": now().isoformat(), "gundem": agenda.model_dump(),
                          "google_trends": trends, "kaynaklar": found})
    # hook bankasına ekle: gündem maddeleri 4 gün geçerli, en üstte
    bank = read_json(DATA / "hook_bank.json", {"hooklar": []})
    keep = []
    for h in bank.get("hooklar", []):
        if h.get("kaynak") == "gundem":
            try:
                if (now() - datetime.fromisoformat(h["tarih"])).days > 4:
                    continue
            except (KeyError, ValueError):
                continue
        keep.append(h)
    new = [{"soru": m.konu, "hook": m.hook, "platform_kaniti": m.kanit, "veri_ihtiyaci": m.veri_ihtiyaci,
            "format": "reel", "kullanildi": False, "kaynak": "gundem", "tarih": now().isoformat(),
            "guncellik": m.guncellik, "neden_simdi": m.neden_simdi} for m in agenda.maddeler]
    bank["hooklar"] = sorted(new, key=lambda x: -x["guncellik"]) + keep
    bank.setdefault("tarih", now().isoformat())
    write_json(DATA / "hook_bank.json", bank)
    log(AGENT, f"Günün gündemi: {len(agenda.maddeler)} güncel fikir → hook bankası")
    return agenda


def summary_text() -> str:
    f = DATA / "trends" / f"{now():%Y-%m-%d}.json"
    d = read_json(f, {})
    if not d:
        return "Bugünün gündem taraması yok."
    g = d["gundem"]
    lines = [g["ozet"]] + [f"- {m['konu']} ({m['neden_simdi']}) [{m['kanit']}]" for m in g["maddeler"]]
    return re.sub(r"\s+\n", "\n", "\n".join(lines))
