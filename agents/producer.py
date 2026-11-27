"""ÜRETİM HATTI — çok katlı kalite kontrol

Fikir Ajanı
  → Veri Araştırmacısı → Kaynak Doğrulayıcı (her kalem kaynakla karşılaştırılır)
  → Hook Yazarı
  → [döngü, en fazla 1 + revizyon_hakki tur]
      İçerik Üretici (seri formatı)
      → Format Denetçisi + Grafik Denetçisi (ölçüm: taşma, üst üste binme, rakam)   ✗ → geri
      → Müdür (içerik, rakam doğruluğu)                                             ✗ → geri
      → Video Kurgucu → Senkron Kontrolcüsü (bitmiş videoyu ölçer; ses kayması 0)   ✗ → yeniden kurgu
      → Sanat Yönetmeni (bitmiş videonun karelerini görür)                         ✗ → geri
      → Baş Müdür (tüm raporlar, daha yüksek eşik, veto)                            ✗ → geri / RED
  → kuyruk (paylaşım saati)
"""
from __future__ import annotations

import shutil
from datetime import datetime, timedelta

from . import (art_director, chief, creator, data_researcher, designer, hook_writer, manager, qa,
               strategist, video)
from .common import DATA, PUBLISHED, QUEUE, REJECTED, ROOT, TR, config, log, now, read_json, write_json

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
    start = now() + timedelta(minutes=45)
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


def _reject(post: dict, reason: str, folder=None) -> dict:
    post.update(durum="reddedildi", red_nedeni=reason)
    write_json(REJECTED / f"{post['id']}.json", post)
    if folder:
        shutil.rmtree(folder, ignore_errors=True)
    log(AGENT, f"✗ Reddedildi: {reason}")
    return post


def produce_one(idea: strategist.Idea, idx: int, preview: bool = False) -> dict:
    post_id = f"{now():%Y%m%d-%H%M}-{idx}"
    folder = None
    log(AGENT, f"Fikir: {idea.konu}")
    post = {"id": post_id, "olusturma": now().isoformat(), "fikir": idea.model_dump(), "kontroller": []}

    sheet, fc_report = data_researcher.run(idea)
    post["veri"], post["kaynak_dogrulama"] = sheet.model_dump(), fc_report
    if sheet.guven == "dusuk":
        return _reject(post, "Veri güveni düşük / kaynak doğrulamadan geçmedi")

    hooks = hook_writer.run(idea, sheet)
    best = hooks.hooklar[min(max(hooks.secilen_index, 0), len(hooks.hooklar) - 1)]
    post["hook_secenekleri"] = hooks.model_dump()
    log(AGENT, f"Hook: {best.metin} ({best.puan})")

    series = _series_no()
    post["seri_no"] = series
    draft, feedback = None, None
    rounds = 1 + config()["uretim"]["revizyon_hakki"]
    for attempt in range(1, rounds + 1):
        step = {"deneme": attempt}
        post["kontroller"].append(step)
        draft = creator.run(idea, best.metin, sheet, series, previous=draft, feedback=feedback)

        # 1) Format + Grafik Denetçisi (ölçüm)
        issues = qa.structure_check(draft) + qa.money_check(draft, sheet) + qa.layout_audit(draft, sheet, series)
        step["format_grafik_denetimi"] = issues
        if issues:
            log(AGENT, f"Denetim (deneme {attempt}): {len(issues)} sorun → senaryo düzeltiliyor")
            feedback = "Format/Grafik Denetçisi ölçümleri:\n- " + "\n- ".join(issues)
            continue

        # 2) Müdür
        stills = designer.stills_vertical(draft, sheet, post_id, series)
        folder = stills[0].parent
        step["renk_dengesi"] = qa.color_balance(stills)          # 60-30-10 ölçümü (rapor)
        verdict = manager.run(idea, draft, sheet, stills, attempt)
        step["mudur"] = verdict.model_dump()
        log(AGENT, f"Müdür (deneme {attempt}): {verdict.karar} {verdict.toplam}/100")
        if verdict.karar == "RED":
            return _reject(post | {"taslak": draft.model_dump()}, "Müdür: " + verdict.tutar_mi, folder)
        if verdict.karar != "ONAY":
            feedback = "Müdür: " + verdict.geri_bildirim
            continue

        # 3) Video + Senkron Kontrolcüsü (gerekirse bir kez yeniden kurgu)
        vid = video.render(draft, sheet, post_id, series)
        sync = qa.av_sync(vid)
        if sync:
            log(AGENT, f"Senkron sorunu, yeniden kurgulanıyor: {sync}")
            vid = video.render(draft, sheet, post_id, series)
            sync = qa.av_sync(vid)
        step["senkron_kontrolu"] = sync
        if sync:
            short = any("hedef dışında" in x and video.media_duration(vid) < config()["uretim"]["video_suresi_sn"]
                        for x in sync)
            hint = ("Video kısa kaldı: seslendirmeyi uzat ya da bir gizli kalem sahnesi ekle." if short
                    else "Sığmayan sahnelerin seslendirmesini kısalt ya da sahneyi ikiye böl.")
            feedback = "Senkron Kontrolcüsü:\n- " + "\n- ".join(sync) + "\n" + hint
            continue

        # 3b) Ses Denetçisi (sesi yazıya döküp senaryoyla karşılaştırır, seviye/hız ölçer)
        vcheck = qa.voice_check(vid, draft)
        step["ses_denetimi"] = vcheck
        if vcheck:
            log(AGENT, f"Ses Denetçisi: {vcheck}")
            feedback = ("Ses Denetçisi:\n- " + "\n- ".join(vcheck) +
                        "\nSeslendirmeyi sade, kısa cümlelerle yaz; kısaltma ve özel sembol kullanma.")
            continue

        # 4) Sanat Yönetmeni (bitmiş videonun kareleri)
        frames = qa.keyframes(vid, folder / "kontrol")
        art = art_director.run(draft, sheet, frames)
        step["sanat_yonetmeni"] = art.model_dump()
        log(AGENT, f"Sanat Yönetmeni: {'GEÇTİ' if art.gecti else 'KALDI'} {art.puan}/100")
        if not art.gecti:
            feedback = "Sanat Yönetmeni:\n- " + "\n- ".join(art.sorunlar + art.yazim_hatalari)
            continue

        # 5) Baş Müdür (son kapı)
        reports = {"kaynak_dogrulama": fc_report, "mudur": verdict.model_dump(), "ses_denetimi": "sorunsuz",
                   "renk_dengesi_60_30_10": step["renk_dengesi"],
                   "senkron": "sorunsuz", "grafik_denetimi": "sorunsuz", "sanat_yonetmeni": art.model_dump()}
        top = chief.run(idea, draft, sheet, reports, frames)
        step["bas_mudur"] = top.model_dump()
        log(AGENT, f"Baş Müdür: {top.karar} {top.puan}/100")
        if top.karar == "RED":
            return _reject(post | {"taslak": draft.model_dump()}, "Baş Müdür: " + top.gerekce, folder)
        if top.karar != "YAYINLA":
            feedback = "Baş Müdür:\n- " + "\n- ".join(top.duzeltmeler or [top.gerekce])
            continue

        # Onaylandı
        shutil.rmtree(folder / "kontrol", ignore_errors=True)
        for p in stills[1:]:
            p.unlink(missing_ok=True)
        post.update(taslak=draft.model_dump(), mudur=verdict.model_dump(), bas_mudur=top.model_dump(),
                    video=_rel(vid), gorseller=[_rel(stills[0])])
        if preview:  # önizleme: yayın kuyruğuna GİRMEZ, kullanıcı onayını bekler
            post["durum"] = "onizleme"
            write_json(DATA / "onizleme" / f"{post_id}.json", post)
            log(AGENT, f"✓ Önizleme hazır (yayınlanmayacak): {post['video']}")
            return post
        post.update(durum="kuyrukta", planlanan_zaman=next_slot())
        write_json(QUEUE / f"{post_id}.json", post)
        log(AGENT, f"✓ Kuyruğa eklendi → {post['planlanan_zaman']}")
        return post

    return _reject(post | {"taslak": draft.model_dump() if draft else None},
                   f"{rounds} denemede tüm kontrollerden geçemedi", folder)


def approve_previews() -> list[str]:
    """Önizlemedeki videoları yayın kuyruğuna alır (kullanıcı izleyip onayladıktan sonra)."""
    done = []
    for f in sorted((DATA / "onizleme").glob("*.json")):
        post = read_json(f)
        post.update(durum="kuyrukta", planlanan_zaman=next_slot(), onaylayan="kullanici")
        write_json(QUEUE / f.name, post)
        f.unlink()
        done.append(f"{post['fikir']['konu']} → {post['planlanan_zaman']}")
    return done


def run(preview: bool = False) -> list[dict]:
    target = 1 if preview else config()["uretim"]["gunluk_gonderi"]
    ideas = strategist.run(target + 2)   # yedek fikirler: reddedilen olursa sıradaki denenir
    results, approved = [], 0
    for i, idea in enumerate(ideas):
        if approved >= target:
            break
        try:
            r = produce_one(idea, i, preview)
            results.append(r)
            approved += r["durum"] in ("kuyrukta", "onizleme")
        except Exception as e:  # bir içerik bozulursa diğerleri devam etsin
            log(AGENT, f"HATA ({idea.konu}): {e}")
    log(AGENT, f"Günün sonucu: {approved}/{target} video onaylandı")
    write_json(DATA / "last_production.json", [
        {"id": r["id"], "konu": r["fikir"]["konu"], "durum": r["durum"],
         "puan": (r.get("bas_mudur") or {}).get("puan", 0), "zaman": r.get("planlanan_zaman"),
         "neden": r.get("red_nedeni")} for r in results])
    return results
