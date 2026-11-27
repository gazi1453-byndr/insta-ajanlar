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
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
