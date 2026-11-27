"""1) ARAŞTIRMACI AJAN
Nişteki büyük sayfaların en iyi performans gösteren gönderilerini, popüler
hashtag içeriklerini ve web'deki güncel trendleri inceler; "ne tutuyor ve
neden tutuyor" raporu çıkarır.
"""
from __future__ import annotations

import json

from pydantic import BaseModel, Field

from . import instagram as ig
from .common import DATA, brand_brief, config, log, now, write_json
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


def collect_instagram() -> dict:
    cfg = config()
    out: dict = {"sayfalar": [], "hashtagler": []}
    if not ig.configured():
        log(AGENT, "Instagram bağlı değil, sadece web araştırması yapılacak")
        return out
    for user in cfg.get("buyuk_sayfalar", []):
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


def run() -> ResearchReport:
    cfg = config()
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
