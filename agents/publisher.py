"""YAYINCI AJAN
Kuyruktaki, paylaşım saati gelmiş içerikleri Instagram'a yükler (Reels ya da
carousel), ilk yorumu (tartışma sorusu) yazar ve TikTok / YouTube Shorts için
platforma özel metinleri içeren bir "çapraz yayın paketi" hazırlar.
Instagram medyayı herkese açık bir URL'den çeker; varsayılan olarak GitHub
reposundaki dosyanın raw adresi kullanılır (repo public olmalı).
"""
from __future__ import annotations

import os
from datetime import datetime

from . import instagram as ig
from .common import DATA, PUBLISHED, QUEUE, REJECTED, ROOT, dry_run, log, now, read_json, write_json

AGENT = "Yayıncı"
CROSSPOST = DATA / "crosspost" / "pending"


def media_url(rel_path: str) -> str:
    base = os.environ.get("MEDIA_BASE_URL")
    if not base:
        repo = os.environ.get("GITHUB_REPOSITORY")
        branch = os.environ.get("GITHUB_REF_NAME", "main")
        if not repo:
            raise RuntimeError("MEDIA_BASE_URL ya da GITHUB_REPOSITORY tanımlı olmalı")
        base = f"https://raw.githubusercontent.com/{repo}/{branch}"
    return f"{base.rstrip('/')}/{rel_path}"


def _tags(tags: list[str]) -> str:
    return " ".join("#" + t.lstrip("#").replace(" ", "") for t in tags)


def caption_of(post: dict) -> str:
    t = post["taslak"]
    return f"{t['caption'].strip()}\n\n{_tags(t.get('hashtagler', []))}".strip()[:2200]


def crosspost_bundle(post: dict, video_link: str, ig_link: str) -> str:
    t = post["taslak"]
    return (
        f"Instagram'da yayınlandı: {ig_link or '(link alınamadı)'}\n\n"
        f"**Videoyu indir:** {video_link}\n\n"
        "---\n## 🎵 TikTok\n"
        f"```\n{t['tiktok_aciklama']}\n\n{_tags(t['tiktok_hashtagler'])}\n```\n"
        f"Sabitlenecek ilk yorum: **{t['yorum_sorusu']}**\n\n"
        "---\n## ▶️ YouTube Shorts\n"
        f"**Başlık:**\n```\n{t['youtube_baslik']}\n```\n"
        f"**Açıklama:**\n```\n{t['youtube_aciklama']}\n```\n"
        f"**Etiketler:** `{', '.join(t['youtube_etiketler'])}`\n\n"
        "---\nPaylaştıktan sonra bu issue'yu kapat."
    )


def run() -> int:
    due = []
    for f in sorted(QUEUE.glob("*.json")):
        post = read_json(f)
        if datetime.fromisoformat(post["planlanan_zaman"]) <= now():
            due.append((f, post))
    if not due:
        log(AGENT, "Saati gelmiş içerik yok")
        return 0
    if not ig.configured() and not dry_run():
        raise RuntimeError("IG_ACCESS_TOKEN eksik")

    done = 0
    for f, post in due[:2]:  # bir çalışmada en fazla 2 (spam görünmesin)
        try:
            cap = caption_of(post)
            if post.get("video"):
                video_link = media_url(post["video"])
                cover = media_url(post["gorseller"][0]) if post.get("gorseller") else None
                media_id = ig.publish_reel(video_link, cap, cover)
            else:
                video_link = ""
                media_id = ig.publish([media_url(p) for p in post["gorseller"]], cap)
            post.update(durum="yayinlandi", ig_media_id=media_id, yayin_zamani=now().isoformat())
            if dry_run():
                log(AGENT, f"[DRY_RUN] {post['id']} yayınlanmış sayıldı (kuyrukta bırakıldı)\n{cap}")
                continue
            ig.pin_comment(media_id, post["taslak"]["yorum_sorusu"])
            link = ig.permalink(media_id)
            post["permalink"] = link
            if post.get("video"):
                CROSSPOST.mkdir(parents=True, exist_ok=True)
                (CROSSPOST / f"{post['id']}.md").write_text(
                    f"# {post['taslak']['youtube_baslik']}\n\n" + crosspost_bundle(post, video_link, link),
                    encoding="utf-8")
            write_json(PUBLISHED / f.name, post)
            f.unlink()
            done += 1
            log(AGENT, f"Yayınlandı: {post['fikir']['konu']} ({link or media_id})")
        except Exception as e:
            post["hata_sayisi"] = post.get("hata_sayisi", 0) + 1
            post["son_hata"] = str(e)
            log(AGENT, f"Yayın hatası ({post['id']}): {e}")
            if post["hata_sayisi"] >= 3:
                post["durum"] = "yayin_hatasi"
                write_json(REJECTED / f.name, post)
                f.unlink()
            else:
                write_json(f, post)
    return done


def cleanup_old_media(days: int = 21) -> None:
    """Repo şişmesin: 3 haftadan eski yayınlanmış videoları sil (kapak görseli kalır)."""
    for f in PUBLISHED.glob("*.json"):
        p = read_json(f)
        v = p.get("video")
        if v and (now() - datetime.fromisoformat(p["yayin_zamani"])).days > days:
            (ROOT / v).unlink(missing_ok=True)
