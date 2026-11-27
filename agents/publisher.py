"""7) YAYINCI AJAN
Kuyruktaki, paylaşım saati gelmiş gönderileri Instagram'a yükler.
Instagram görselleri herkese açık bir URL'den çeker; varsayılan olarak
GitHub reposundaki dosyanın raw adresi kullanılır (repo public olmalı) ya da
MEDIA_BASE_URL ile başka bir adres verilebilir.
"""
from __future__ import annotations

import os
from datetime import datetime

from . import instagram as ig
from .common import PUBLISHED, QUEUE, REJECTED, dry_run, log, now, read_json, write_json

AGENT = "Yayıncı"


def media_url(rel_path: str) -> str:
    base = os.environ.get("MEDIA_BASE_URL")
    if not base:
        repo = os.environ.get("GITHUB_REPOSITORY")
        branch = os.environ.get("GITHUB_REF_NAME", "main")
        if not repo:
            raise RuntimeError("MEDIA_BASE_URL ya da GITHUB_REPOSITORY tanımlı olmalı")
        base = f"https://raw.githubusercontent.com/{repo}/{branch}"
    return f"{base.rstrip('/')}/{rel_path}"


def caption_of(post: dict) -> str:
    t = post["taslak"]
    tags = " ".join("#" + h.lstrip("#").replace(" ", "") for h in t.get("hashtagler", []))
    return f"{t['caption'].strip()}\n\n{tags}".strip()[:2200]


def run() -> int:
    due = []
    for f in sorted(QUEUE.glob("*.json")):
        post = read_json(f)
        if datetime.fromisoformat(post["planlanan_zaman"]) <= now():
            due.append((f, post))
    if not due:
        log(AGENT, "Saati gelmiş gönderi yok")
        return 0

    if not ig.configured() and not dry_run():
        raise RuntimeError("Instagram bilgileri (IG_USER_ID / IG_ACCESS_TOKEN) eksik")

    done = 0
    for f, post in due[:2]:  # bir çalışmada en fazla 2 gönderi (spam görünmesin)
        try:
            urls = [media_url(p) for p in post["gorseller"]]
            media_id = ig.publish(urls, caption_of(post))
            post.update(durum="yayinlandi", ig_media_id=media_id, yayin_zamani=now().isoformat())
            if dry_run():
                log(AGENT, f"[DRY_RUN] {post['id']} yayınlanmış sayıldı (dosya kuyrukta bırakıldı)")
                log(AGENT, f"Görsel URL'leri: {urls}")
                log(AGENT, f"Açıklama:\n{caption_of(post)}")
                continue
            write_json(PUBLISHED / f.name, post)
            f.unlink()
            done += 1
            log(AGENT, f"Yayınlandı: {post['fikir']['konu']} (medya {media_id})")
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
