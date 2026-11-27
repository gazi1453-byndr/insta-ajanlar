"""ÜRETİM HATTI (ajanları sırayla çalıştıran koordinatör)

Fikir Ajanı → Veri Araştırmacısı → Hook Yazarı → İçerik Üretici → Tasarımcı/Video → Müdür
                                                       ↑__________ REVİZYON __________|

ONAY alan içerik bir paylaşım saatiyle data/queue/ klasörüne girer.
"""
from __future__ import annotations

import shutil
from datetime import datetime, timedelta

from . import creator, data_researcher, designer, hook_writer, manager, strategist, video
from .common import (PUBLISHED, QUEUE, REJECTED, ROOT, TR, config, log, now, read_json, write_json, DATA)

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


def _series_no() -> int:
    return len(list(PUBLISHED.glob("*.json"))) + len(list(QUEUE.glob("*.json"))) + 1


def _rel(p) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def produce_one(idea: strategist.Idea, idx: int) -> dict:
    post_id = f"{now():%Y%m%d-%H%M}-{idx}"
    log(AGENT, f"Fikir: {idea.konu} ({idea.format})")

    sheet = data_researcher.run(idea)
    if sheet.guven == "dusuk":
        log(AGENT, "Veri güveni düşük, içerik üretilmedi")
        post = {"id": post_id, "durum": "reddedildi", "fikir": idea.model_dump(),
                "veri": sheet.model_dump(), "mudur": {"toplam": 0, "tutar_mi": "Veri güveni düşük"}}
        write_json(REJECTED / f"{post_id}.json", post)
        return post

    hooks = hook_writer.run(idea, sheet)
    best = hooks.hooklar[min(max(hooks.secilen_index, 0), len(hooks.hooklar) - 1)]
    log(AGENT, f"Hook: {best.metin} ({best.puan})")

    series = _series_no()
    draft, verdict, images, history = None, None, [], []
    for attempt in range(1, 2 + config()["uretim"]["revizyon_hakki"]):
        draft = creator.run(idea, best.metin, sheet, series, previous=draft,
                            feedback=verdict.geri_bildirim if verdict else None)
        images = (designer.stills_vertical(draft, sheet, post_id) if idea.format == "reel"
                  else designer.carousel(draft, sheet, post_id))
        verdict = manager.run(idea, draft, sheet, images, attempt)
        history.append({"deneme": attempt, "toplam": verdict.toplam, "karar": verdict.karar,
                        "rakam_hatalari": verdict.rakam_hatalari, "geri_bildirim": verdict.geri_bildirim})
        log(AGENT, f"Müdür kararı (deneme {attempt}): {verdict.karar} - {verdict.toplam}/100")
        if verdict.karar != "REVIZYON":
            break

    post = {
        "id": post_id, "olusturma": now().isoformat(), "seri_no": series,
        "fikir": idea.model_dump(), "veri": sheet.model_dump(),
        "hook_secenekleri": hooks.model_dump(), "taslak": draft.model_dump(),
        "mudur": verdict.model_dump(), "mudur_gecmisi": history,
    }
    if verdict.karar != "ONAY":
        post["durum"] = "reddedildi"
        write_json(REJECTED / f"{post_id}.json", post)
        shutil.rmtree(images[0].parent, ignore_errors=True)
        return post

    if idea.format == "reel":
        post["video"] = _rel(video.render(draft, sheet, post_id))
        post["gorseller"] = [_rel(images[0])]          # kapak
        for p in images[1:]:
            p.unlink(missing_ok=True)
    else:
        post["gorseller"] = [_rel(p) for p in images]
    post["durum"] = "kuyrukta"
    post["planlanan_zaman"] = next_slot()
    write_json(QUEUE / f"{post_id}.json", post)
    log(AGENT, f"Kuyruğa eklendi → {post['planlanan_zaman']}")
    return post


def run() -> list[dict]:
    ideas = strategist.run(config()["uretim"]["gunluk_gonderi"])
    results = []
    for i, idea in enumerate(ideas):
        try:
            results.append(produce_one(idea, i))
        except Exception as e:  # bir içerik bozulursa diğerleri devam etsin
            log(AGENT, f"HATA ({idea.konu}): {e}")
    write_json(DATA / "last_production.json", [
        {"id": r["id"], "konu": r["fikir"]["konu"], "format": r["fikir"]["format"], "durum": r["durum"],
         "puan": r["mudur"]["toplam"], "zaman": r.get("planlanan_zaman")} for r in results])
    return results
