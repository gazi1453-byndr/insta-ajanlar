"""Ajanları çalıştıran komut satırı.

Kullanım:
  python pipeline.py arastir     # Araştırmacı: büyük sayfalar + hashtag + web trendleri
  python pipeline.py uret        # Fikir → Hook → Üretici → Tasarımcı → Müdür → kuyruk
  python pipeline.py yayinla     # Yayıncı: saati gelen gönderileri paylaşır
  python pipeline.py topluluk    # Topluluk yöneticisi: yorum / DM yanıtları
  python pipeline.py analiz      # Analist: haftalık rapor + öğrenilenler
  python pipeline.py durum       # Kuyruğun ve son üretimin özeti

DRY_RUN=1 ortam değişkeniyle Instagram'a hiçbir şey gönderilmez.
"""
from __future__ import annotations

import re
import sys

from agents.common import DATA, PUBLISHED, QUEUE, REJECTED, read_json


def durum() -> None:
    q = sorted(QUEUE.glob("*.json"))
    print(f"Kuyrukta: {len(q)} | Yayınlanan: {len(list(PUBLISHED.glob('*.json')))} | "
          f"Reddedilen: {len(list(REJECTED.glob('*.json')))}")
    for f in q:
        p = read_json(f)
        puan = (p.get("mudur") or {}).get("toplam", "—")  # senaryo gönderilerinde müdür/fikir olmayabilir
        konu = (p.get("fikir") or {}).get("konu") or p.get("konu") or f.stem
        print(f"  {p.get('planlanan_zaman', '')[:16]}  {puan:>3}/100  {konu}")
    last = read_json(DATA / "last_production.json", [])
    if last:
        print("Son üretim:")
        for r in last:
            print(f"  [{r['durum']}] {r['puan']}/100  {r['konu']}")


def yeniden_ciz() -> None:
    """Kuyruktaki içeriklerin görsel/videolarını Claude'u çağırmadan yeniden çizer
    (ör. kullanıcı adı, renk ya da tasarım değiştiğinde)."""
    from agents import designer, video
    from agents.common import ROOT, write_json
    from agents.creator import Draft
    from agents.data_researcher import DataSheet
    for f in sorted(QUEUE.glob("*.json")):
        p = read_json(f)
        draft, sheet = Draft(**p["taslak"]), DataSheet(**p["veri"])
        rel = lambda x: str(x.relative_to(ROOT)).replace("\\", "/")
        if p.get("video"):
            stills = designer.stills_vertical(draft, sheet, p["id"], p.get("seri_no", 0))
            p["video"] = rel(video.render(draft, sheet, p["id"], p.get("seri_no", 0)))
            p["gorseller"] = [rel(stills[0])]
            for s in stills[1:]:
                s.unlink(missing_ok=True)
        else:
            p["gorseller"] = [rel(x) for x in designer.carousel(draft, sheet, p["id"], p.get("seri_no", 0))]
        write_json(f, p)
        print("Yeniden çizildi:", p["fikir"]["konu"])


def kontrol() -> None:
    """Yapay zeka sağlayıcılarını, web aramasını ve Instagram bağlantısını test eder."""
    import os
    from agents import instagram as ig
    ok = True
    from agents import llm
    from pydantic import BaseModel

    class Ping(BaseModel):
        cevap: str

    print("Yapay zeka sırası:", llm.backend())
    from agents import search as _web
    print("Web arama:", "Tavily" if _web.enabled() else "YOK (TAVILY_API_KEY) → modelin kendi araması denenecek")
    import os as _os
    for prov in llm.providers():  # her sağlayıcıyı tek tek dene
        _os.environ["LLM_SIRA"] = prov
        try:
            r1 = llm.ask("kontrol", "Kısa yanıt ver.", "cevap alanına sadece 'hazır' yaz.", Ping)
            print(f"✓ {prov} çalışıyor: {r1.cevap}")
        except Exception as e:
            print(f"✗ {prov}: {str(e)[:200]}")
    _os.environ.pop("LLM_SIRA", None)
    try:
        r = llm.ask("kontrol", "Kısa yanıt ver.", "cevap alanına sadece 'hazır' yaz.", Ping)
        print(f"✓ Zincir yanıt verdi: {r.cevap}")
        notes = llm.research("kontrol", "Kısa yanıt ver.", "Bugün Türkiye'de 1 litre benzinin fiyatı kaç TL? Kaynağıyla tek cümle.", 1)
        print(f"✓ Web araması çalışıyor: {notes[:160]}")
    except Exception as e:
        ok = False
        print("✗ Yapay zeka:", e)
    try:
        ids = ig._discover()
        print(f"✓ Instagram hesabı: @{ids['username']} (IG {ids['ig']}, sayfa {ids['page']})")
        info = ig.account_info()
        print(f"✓ Hesap bilgisi: {info.get('followers_count')} takipçi, {info.get('media_count')} gönderi")
        print(f"✓ Son medya okunabiliyor: {len(ig.recent_media(3))} adet")
    except Exception as e:
        ok = False
        print("✗ Instagram:", e)
    for label, fn in [("Büyük sayfa inceleme (business_discovery)", lambda: ig.business_discovery("instagram", 1)),
                      ("Hashtag araması", lambda: ig.hashtag_top_media("ekonomi"))]:
        try:
            fn()
            print(f"✓ {label}")
        except Exception as e:
            print(f"✗ {label}: {e}")
    if not ok:
        raise SystemExit(1)


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "durum"
    if cmd == "arastir":
        from agents import producer, researcher
        researcher.run()
        producer.check_alarm()
    elif cmd == "uret":
        from agents import producer
        producer.run()
        durum()
    elif cmd == "yayinla":
        from agents import publisher
        publisher.run()
        publisher.cleanup_old_media()
    elif cmd == "topluluk":
        from agents import community
        community.run()
    elif cmd == "analiz":
        from agents import analyst
        analyst.run()
    elif cmd == "durum":
        durum()
    elif cmd == "denetle":  # python pipeline.py denetle data/senaryolar/<dosya>.json (yalnız rapor)
        from agents import producer
        producer.review_script(sys.argv[2])
    elif cmd == "senaryo":  # python pipeline.py senaryo data/senaryolar/<dosya>.json
        from agents import producer
        producer.produce_script(sys.argv[2])
    elif cmd == "onizleme":
        from agents import producer, researcher
        from agents.common import DATA as _D, now as _now
        if not (_D / "trends" / f"{_now():%Y-%m-%d}.json").exists():
            researcher.run()                 # önce günün gündemini tara (güncel fikir için)
        producer.run(preview=True)
    elif cmd in ("site", "plan"):
        from agents import plan, site
        site.build()
        plan.build()
    elif cmd == "gundem":
        from agents import producer, trend_scanner
        trend_scanner.run(light=True)            # gün içi hızlı tarama
        producer.check_alarm()                   # büyük zam haberi varsa acil video
    elif cmd == "onayla":
        from agents import producer
        only = sys.argv[2] if len(sys.argv) > 2 else ""
        if only and not re.fullmatch(r"[\w,-]+", only):
            raise SystemExit(f"Geçersiz kimlik: {only}")
        for line in producer.approve_previews(only) or ["Önizlemede onay bekleyen video yok"]:
            print("Onaylandı:", line)
    elif cmd == "yeniden_ciz":
        yeniden_ciz()
    elif cmd == "kontrol":
        kontrol()
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
