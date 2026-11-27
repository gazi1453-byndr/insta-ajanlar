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

import sys

from agents.common import DATA, PUBLISHED, QUEUE, REJECTED, read_json


def durum() -> None:
    q = sorted(QUEUE.glob("*.json"))
    print(f"Kuyrukta: {len(q)} | Yayınlanan: {len(list(PUBLISHED.glob('*.json')))} | "
          f"Reddedilen: {len(list(REJECTED.glob('*.json')))}")
    for f in q:
        p = read_json(f)
        print(f"  {p['planlanan_zaman'][:16]}  {p['mudur']['toplam']:>3}/100  {p['fikir']['konu']}")
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
            stills = designer.stills_vertical(draft, sheet, p["id"])
            p["video"] = rel(video.render(draft, sheet, p["id"]))
            p["gorseller"] = [rel(stills[0])]
            for s in stills[1:]:
                s.unlink(missing_ok=True)
        else:
            p["gorseller"] = [rel(x) for x in designer.carousel(draft, sheet, p["id"])]
        write_json(f, p)
        print("Yeniden çizildi:", p["fikir"]["konu"])


def kontrol() -> None:
    """Claude kullanmadan bağlantıları ve izinleri test eder."""
    import os
    from agents import instagram as ig
    ok = True
    from agents import llm
    from pydantic import BaseModel

    class Ping(BaseModel):
        cevap: str

    print("Claude bağlantı şekli:", llm.backend())
    try:
        r = llm.ask("kontrol", "Kısa yanıt ver.", "Sadece 'hazır' kelimesini döndür.", Ping, role="topluluk")
        print(f"✓ Claude yanıt verdi: {r.cevap}")
        notes = llm.research("kontrol", "Kısa yanıt ver.", "Bugün Türkiye'de 1 litre benzinin fiyatı kaç TL? Kaynağıyla tek cümle.", 1)
        print(f"✓ Web araması çalışıyor: {notes[:160]}")
    except Exception as e:
        ok = False
        print("✗ Claude:", e)
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
        from agents import researcher
        researcher.run()
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
    elif cmd == "yeniden_ciz":
        yeniden_ciz()
    elif cmd == "kontrol":
        kontrol()
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
