"""1) ARAŞTIRMACI AJAN
Nişteki büyük sayfaların en iyi performans gösteren gönderilerini, popüler
hashtag içeriklerini ve web'deki güncel trendleri inceler; "ne tutuyor ve
neden tutuyor" raporu çıkarır.
"""
from __future__ import annotations

import json
from datetime import datetime

from pydantic import BaseModel, Field

from . import instagram as ig
from .common import DATA, brand_brief, config, log, now, read_json, write_json
from .llm import ask, research

AGENT = "Araştırmacı"


class Pattern(BaseModel):
    kalip: str = Field(description="Tekrar eden başarılı içerik kalıbı")
    neden_tutuyor: str
    ornek_link: str = Field(description="Örnek gönderi linki, yoksa boş")


class ResearchReport(BaseModel):
    ozet: str
    viral_kaliplar: list[Pattern]
    hook_ornekleri: list[str] = Field(description="Büyük sayfalardan gözlenen etkili açılış cümlesi yapıları")
    konu_firsatlari: list[str] = Field(description="Kitlenin ilgilendiği ama az işlenmiş konular")
    guncel_trendler: list[str]
    format_onerileri: list[str] = Field(description="Carousel / tek görsel / reel için format gözlemleri")
    kacinilacaklar: list[str]


def _top_posts(posts: list[dict], followers: int, n: int = 6) -> list[dict]:
    for p in posts:
        eng = (p.get("like_count") or 0) + 3 * (p.get("comments_count") or 0)
        p["etkilesim_orani"] = round(eng / max(followers, 1) * 100, 3)
    return sorted(posts, key=lambda p: p["etkilesim_orani"], reverse=True)[:n]


class PageCandidates(BaseModel):
    kullanici_adlari: list[str] = Field(description="Instagram kullanıcı adları, @ ve link olmadan")


def _clean(u: str) -> str:
    u = u.strip().lstrip("@").rstrip("/")
    return u.split("instagram.com/")[-1].split("?")[0].strip("/").lower()


def discover_pages(max_pages: int = 10) -> list[str]:
    """Nişteki büyük sayfaları web'de bulur ve Instagram API ile doğrular. Haftada bir yenilenir."""
    cache_file = DATA / "pages.json"
    cache = read_json(cache_file, {})
    if cache.get("sayfalar") and (now() - datetime.fromisoformat(cache["tarih"])).days < 7:
        return cache["sayfalar"]

    cfg = config()["hesap"]
    notes = research(
        AGENT,
        system="Instagram hesaplarını araştıran bir asistansın. Sadece gerçekten var olduğundan emin olduğun hesapları yaz.",
        prompt=(f"Niş: {cfg['nis']}. Bu nişte Instagram'da en çok takipçili ve en çok etkileşim alan "
                "hesapları bul: önce Türkçe içerik üretenler, sonra dünyadaki en büyükler. "
                "Her biri için tam kullanıcı adını (instagram.com/... linkindeki haliyle) ve yaklaşık takipçi sayısını yaz. "
                "25 hesap listele."),
        max_searches=10,
    )
    cands = ask(AGENT, system="Metinden Instagram kullanıcı adlarını çıkar.", content=notes,
                schema=PageCandidates, effort="low").kullanici_adlari
    cands = list(dict.fromkeys(_clean(c) for c in cands if c.strip()))

    valid = []
    for u in cands:
        try:
            bd = ig.business_discovery(u, media_limit=1)
            valid.append((u, bd.get("followers_count") or 0))
        except ig.InstagramError:
            log(AGENT, f"@{u} doğrulanamadı (yok ya da kişisel hesap), atlandı")
    pages = [u for u, _ in sorted(valid, key=lambda x: x[1], reverse=True)[:max_pages]]
    write_json(cache_file, {"tarih": now().isoformat(), "sayfalar": pages,
                            "takipciler": dict(valid)})
    log(AGENT, f"Otomatik bulunan büyük sayfalar: {', '.join('@' + p for p in pages) or 'yok'}")
    return pages


def collect_instagram() -> dict:
    cfg = config()
    out: dict = {"sayfalar": [], "hashtagler": []}
    if not ig.configured():
        log(AGENT, "Instagram bağlı değil, sadece web araştırması yapılacak")
        return out
    pages = list(cfg.get("buyuk_sayfalar") or [])
    if cfg.get("otomatik_sayfa_bulma", True):
        pages += [p for p in discover_pages() if p not in pages]
    for user in pages:
        try:
            bd = ig.business_discovery(user)
            posts = bd.get("media", {}).get("data", [])
            out["sayfalar"].append({
                "kullanici": user,
                "takipci": bd.get("followers_count"),
                "en_iyi_gonderiler": [
                    {k: p.get(k) for k in ("caption", "like_count", "comments_count", "media_type",
                                           "media_product_type", "permalink", "etkilesim_orani")}
                    for p in _top_posts(posts, bd.get("followers_count") or 1)
                ],
            })
            log(AGENT, f"@{user} incelendi ({len(posts)} gönderi)")
        except ig.InstagramError as e:
            log(AGENT, f"@{user} incelenemedi: {e}")
    for tag in cfg.get("hashtagler", []):
        try:
            media = ig.hashtag_top_media(tag)[:8]
            out["hashtagler"].append({"hashtag": tag, "populer": [
                {k: m.get(k) for k in ("caption", "like_count", "comments_count", "media_type", "permalink")}
                for m in media
            ]})
        except ig.InstagramError as e:
            log(AGENT, f"#{tag} incelenemedi: {e}")
    return out


class HookIdea(BaseModel):
    soru: str = Field(description="İnsanların gerçekten aradığı/sorduğu soru")
    hook: str = Field(description="İlk 3 saniyede söylenecek/yazılacak kanca, en fazla 12 kelime")
    platform_kaniti: str = Field(description="Bu ilginin görüldüğü yer: Google Trends, Reddit, YouTube, Ekşi Sözlük, haber vb.")
    veri_ihtiyaci: str = Field(description="Bu içerik için hangi fiyatlar/rakamlar araştırılmalı")
    format: str = Field(description="reel ya da carousel")


class HookBank(BaseModel):
    hooklar: list[HookIdea] = Field(description="15-20 adet")


def weekly_hook_bank() -> list[dict]:
    """TREND MADENCİSİ: Haftada bir son 7 günün en çok aranan sorularından 15-20 hook üretir."""
    bank_file = DATA / "hook_bank.json"
    bank = read_json(bank_file, {})
    if bank.get("tarih") and (now() - datetime.fromisoformat(bank["tarih"])).days < 7:
        return bank["hooklar"]
    cfg = config()["hesap"]
    notes = research(
        AGENT,
        system="Sen bir arama ve sosyal medya trend analistisin. Sadece gerçekten gözlemlediğin ilgiyi raporla.",
        prompt=(
            f"Bugün {now():%d.%m.%Y}. Niş: {cfg['nis']}. Kitle: {cfg['hedef_kitle']}.\n"
            "Son 7 günde Türkiye'de bu nişte insanların en çok aradığı ve sorduğu soruları bul: "
            "Google Trends (yükselen aramalar), Reddit (r/Turkey, r/TurkeyJerky, r/KGBTR vb. ve global finans "
            "subreddit'leri), YouTube (popüler yeni videolar ve yorumlardaki sorular), Ekşi Sözlük ve "
            "gündemdeki fiyat/zam haberleri. 'X kaça mal olur', 'A mı B mi', 'X ile ne yapılır' tipi "
            "soruları öne çıkar. Her soru için nerede gördüğünü yaz. 25 madde."
        ),
        max_searches=15,
    )
    hb = ask(
        AGENT,
        system=("Sen viral kısa video senaristisin. Gerçek arama ilgisinden ilk 3 saniyede izleyiciyi "
                "durduran, merak uyandıran ama yalan vaat etmeyen kancalar yazarsın.\n\n" + brand_brief()),
        content=f"Şu trend notlarından 15-20 içerik kancası üret:\n\n{notes}",
        schema=HookBank,
    )
    items = [{**h.model_dump(), "kullanildi": False} for h in hb.hooklar]
    write_json(bank_file, {"tarih": now().isoformat(), "hooklar": items})
    log(AGENT, f"Haftalık hook bankası yenilendi: {len(items)} kanca")
    return items


def run() -> ResearchReport:
    cfg = config()
    weekly_hook_bank()
    ig_data = collect_instagram()

    web = research(
        AGENT,
        system="Sen bir sosyal medya trend araştırmacısısın. Kısa, maddeli ve kaynaklı notlar çıkar.",
        prompt=(
            f"Niş: {cfg['hesap']['nis']}. Hedef kitle: {cfg['hesap']['hedef_kitle']}.\n"
            f"Bugün {now():%d %B %Y}. Bu niş için Türkiye'de ve dünyada şu an Instagram'da "
            "konuşulan güncel konuları, gündem olaylarını, yükselen içerik formatlarını ve "
            "kitlenin şu an en çok merak ettiği soruları araştır. En fazla 15 madde."
        ),
    )

    report = ask(
        AGENT,
        system=(
            "Sen kıdemli bir Instagram büyüme stratejistisin. Büyük sayfaların verisini analiz "
            "edip neyin neden tuttuğunu çıkarırsın. Kopyalamayı değil, kalıpları öğrenmeyi önerirsin.\n\n"
            + brand_brief()
        ),
        content=(
            "Aşağıdaki verileri analiz et ve araştırma raporu çıkar.\n\n"
            f"## Büyük sayfaların en iyi gönderileri ve hashtag verileri\n"
            f"{json.dumps(ig_data, ensure_ascii=False)[:60000]}\n\n"
            f"## Web trend notları\n{web}"
        ),
        schema=ResearchReport,
    )
    stamp = f"{now():%Y-%m-%d}"
    payload = {"tarih": stamp, "rapor": report.model_dump(), "ham_instagram": ig_data, "web_notlari": web}
    write_json(DATA / "research" / f"{stamp}.json", payload)
    write_json(DATA / "research" / "latest.json", payload)
    log(AGENT, f"Rapor kaydedildi: {len(report.viral_kaliplar)} kalıp, {len(report.konu_firsatlari)} fırsat")
    return report
