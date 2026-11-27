"""ÜRETİM HATTI (ajanları sırayla çalıştıran koordinatör)

Fikir Ajanı → Hook Yazarı → İçerik Üretici → Tasarımcı → Müdür
                                   ↑______ REVİZYON _______|

ONAY alan içerik, bir paylaşım saatiyle data/queue/ klasörüne girer.
Reel senaryoları data/reels/ klasörüne yazılır (videoyu sen çekersin).
"""
from __future__ import annotations

import shutil
from datetime import datetime, timedelta
from pathlib import Path

from . import creator, designer, hook_writer, manager, strategist
from .common import (DATA, MEDIA_INBOX, MEDIA_USED, PUBLISHED, QUEUE, REJECTED, ROOT, TR,
                     config, log, now, read_json, write_json)

AGENT = "Üretim Hattı"


def _taken_slots() -> set[str]:
    taken = set()
    for folder in (QUEUE, PUBLISHED):
        for f in folder.glob("*.json"):
            t = read_json(f, {}).get("planlanan_zaman")
            if t:
                taken.add(t[:16])
    return taken


def next_slot() -> str:
    """Kuyrukta boş olan bir sonraki paylaşım saatini bulur."""
    hours = config()["uretim"]["paylasim_saatleri"]
    taken = _taken_slots()
    start = now() + timedelta(minutes=30)
    for day in range(0, 60):
        d = (start + timedelta(days=day)).date()
        for h in sorted(hours):
            hh, mm = map(int, h.split(":"))
            slot = datetime(d.year, d.month, d.day, hh, mm, tzinfo=TR)
            if slot > start and slot.isoformat()[:16] not in taken:
                return slot.isoformat()
    raise RuntimeError("60 gün içinde boş paylaşım saati yok")


def _inbox_image() -> Path | None:
    imgs = sorted(p for p in MEDIA_INBOX.iterdir()
                  if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
    return imgs[0] if imgs else None


def produce_one(idea: strategist.Idea, idx: int) -> dict:
    post_id = f"{now():%Y%m%d-%H%M}-{idx}"
    log(AGENT, f"Fikir: {idea.konu} ({idea.format})")

    hooks = hook_writer.run(idea)
    best = hooks.hooklar[min(max(hooks.secilen_index, 0), len(hooks.hooklar) - 1)]
    log(AGENT, f"Hook: {best.metin} ({best.puan})")

    user_img = _inbox_image() if idea.format == "tek_gorsel" else None
    draft, verdict, images = None, None, []
    history = []
    max_attempts = 1 + config()["uretim"]["revizyon_hakki"]

    for attempt in range(1, max_attempts + 1):
        draft = creator.run(idea, best.metin, user_img, previous=draft,
                            feedback=verdict.geri_bildirim if verdict else None)
        images = [designer.from_user_image(user_img, post_id)] if user_img else designer.run(draft, post_id)
        verdict = manager.run(idea, draft, images, attempt)
        history.append({"deneme": attempt, "toplam": verdict.toplam, "karar": verdict.karar,
                        "geri_bildirim": verdict.geri_bildirim})
        log(AGENT, f"Müdür kararı (deneme {attempt}): {verdict.karar} - {verdict.toplam}/100")
        if verdict.karar != "REVIZYON":
            break

    post = {
        "id": post_id,
        "olusturma": now().isoformat(),
        "fikir": idea.model_dump(),
        "hook_secenekleri": hooks.model_dump(),
        "taslak": draft.model_dump(),
        "gorseller": [str(p.relative_to(ROOT)).replace("\\", "/") for p in images],
        "mudur": verdict.model_dump(),
        "mudur_gecmisi": history,
    }

    if verdict.karar != "ONAY":
        post["durum"] = "reddedildi"
        write_json(REJECTED / f"{post_id}.json", post)
        shutil.rmtree(images[0].parent, ignore_errors=True)
        return post

    if idea.format == "reel_senaryosu":
        post["durum"] = "cekim_bekliyor"
        write_json(DATA / "reels" / f"{post_id}.json", post)
        (DATA / "reels" / f"{post_id}.md").write_text(
            f"# Reel: {draft.hook}\n\n## Senaryo\n{draft.reel_senaryosu}\n\n"
            f"## Açıklama\n{draft.caption}\n\n" + " ".join("#" + h for h in draft.hashtagler) + "\n",
            encoding="utf-8")
        return post

    post["durum"] = "kuyrukta"
    post["planlanan_zaman"] = next_slot()
    write_json(QUEUE / f"{post_id}.json", post)
    if user_img:
        shutil.move(str(user_img), MEDIA_USED / user_img.name)
    log(AGENT, f"Kuyruğa eklendi → {post['planlanan_zaman']}")
    return post


def run() -> list[dict]:
    count = config()["uretim"]["gunluk_gonderi"]
    ideas = strategist.run(count)
    results = []
    for i, idea in enumerate(ideas):
        try:
            results.append(produce_one(idea, i))
        except Exception as e:  # bir içerik bozulursa diğerleri devam etsin
            log(AGENT, f"HATA ({idea.konu}): {e}")
    write_json(DATA / "last_production.json", [
        {"id": r["id"], "konu": r["fikir"]["konu"], "durum": r["durum"],
         "puan": r["mudur"]["toplam"], "zaman": r.get("planlanan_zaman")} for r in results])
    return results
