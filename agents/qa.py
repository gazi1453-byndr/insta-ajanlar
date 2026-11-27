"""KALİTE KONTROL AJANLARI (yapay zeka değil, ölçüm yapan kod: hata kaçırmaz, kota harcamaz)

1) FORMAT DENETÇİSİ    structure_check()  Seri şablonuna uyuyor mu? (sahne sırası, süre, seslendirme)
2) GRAFİK DENETÇİSİ    layout_audit()     Her sahnede yazı taşması / üst üste binme / güvenli alan
                                           + grafikte görünen HER rakam tabloyla birebir mi?
3) SENKRON KONTROLCÜSÜ av_sync()          Bitmiş videoyu ölçer: görüntü-ses süresi farkı, sahne sınırları,
                                           seslendirme kesiliyor mu, toplam süre
4) YAYIN ÖNCESİ KONTROL preflight()        Yüklemeden hemen önce dosya + senkron + medya adresi
Her fonksiyon sorun listesi döndürür; boş liste = geçti.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import requests

from . import designer
from .common import ROOT, config
from .creator import Draft
from .data_researcher import DataSheet

FRAME = 1 / 30


# ------------------------------------------------------------------ 1) FORMAT DENETÇİSİ

def structure_check(draft: Draft) -> list[str]:
    s = draft.slaytlar
    turs = [x.tur for x in s]
    issues = []
    target = config()["uretim"]["video_suresi_sn"]
    if not s:
        return ["Hiç sahne yok"]
    if turs[0] != "metin":
        issues.append("İlk sahne 'metin' (hook) olmalı")
    if turs.count("grafik") != 1:
        issues.append(f"Tam olarak 1 'grafik' sahnesi olmalı (şu an {turs.count('grafik')})")
    if turs.count("reveal") != 1:
        issues.append(f"Tam olarak 1 'reveal' (GERÇEK MALİYET) sahnesi olmalı (şu an {turs.count('reveal')})")
    if turs[-1] != "sonuc":
        issues.append("Son sahne 'sonuc' olmalı")
    if "grafik" in turs and "reveal" in turs and turs.index("reveal") < turs.index("grafik"):
        issues.append("'reveal' sahnesi grafikten SONRA gelmeli")
    lo, hi = (7, 11) if target >= 50 else (5, 9)
    if not lo <= len(s) <= hi:
        issues.append(f"Sahne sayısı {lo}-{hi} arası olmalı (şu an {len(s)})")
    words = sum(len(x.seslendirme.split()) for x in s)
    wlo, whi = int(target * 1.9), int(target * 2.8)
    if not wlo <= words <= whi:
        issues.append(f"Toplam seslendirme {wlo}-{whi} kelime olmalı (~{target} sn); şu an {words}")
    for i, x in enumerate(s, 1):
        if not x.seslendirme.strip():
            issues.append(f"Sahne {i}: seslendirme boş")
        if len(x.seslendirme.split()) > 40:
            issues.append(f"Sahne {i}: seslendirme çok uzun ({len(x.seslendirme.split())} kelime, en fazla 40)")
        if len(x.baslik.split()) > 9:
            issues.append(f"Sahne {i}: başlık çok uzun ({len(x.baslik.split())} kelime, en fazla 8)")
    return issues


# ------------------------------------------------------------------ 1b) RAKAM DENETÇİSİ

_MONEY = re.compile(r"(~|yaklaşık|civarı|neredeyse)?\s*(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?\s*(TL|lira|₺)",
                    re.IGNORECASE)


def money_check(draft: Draft, sheet: DataSheet) -> list[str]:
    """Ekranda ve seslendirmede RAKAMLA yazılmış her TL tutarı tablodaki bir değerle eşleşmeli.
    '~' / 'yaklaşık' ile yazılanlarda %3 tolerans; diğerlerinde 1 TL."""
    vals = sorted(_expected_numbers(sheet))
    # tablodan türetilebilen makul değerler: aylık↔yıllık
    derived = set(vals) | {round(v / 12, 2) for v in vals} | {round(v * 12, 2) for v in vals}
    issues = []
    for i, s in enumerate(draft.slaytlar, 1):
        for field, text in (("ekran", f"{s.baslik} {s.metin}"), ("seslendirme", s.seslendirme)):
            for m in _MONEY.finditer(text):
                approx = bool(m.group(1)) or "~" in text[max(0, m.start() - 3):m.start() + 1]
                num = float(m.group(2).replace(".", "") + ("." + m.group(3) if m.group(3) else ""))
                if num < 1:
                    continue
                ok = any(abs(num - v) <= (max(1.0, abs(v) * 0.03) if approx else 1.0) for v in derived)
                # 'bin/milyon' gibi kısaltmalar: "120 bin TL" → 120.000
                if not ok and re.search(rf"{re.escape(m.group(2))}\s*bin", text):
                    ok = any(abs(num * 1000 - v) <= abs(v) * 0.03 for v in derived)
                if not ok:
                    issues.append(f"Sahne {i} ({field}): '{m.group(0).strip()}' tablodaki hiçbir rakamla eşleşmiyor")
    return issues


# ------------------------------------------------------------------ 2) GRAFİK DENETÇİSİ

def _overlap(a, b, tol=2) -> bool:
    return a[0] < b[2] - tol and b[0] < a[2] - tol and a[1] < b[3] - tol and b[1] < a[3] - tol


def _expected_numbers(sheet: DataSheet) -> set[float]:
    exp = {round(i.tutar_tl, 2) for o in sheet.secenekler for i in o.kalemler}
    exp |= {round(o.toplam_tl, 2) for o in sheet.secenekler}
    _, hv = designer.headline_value(sheet)
    exp.add(round(hv, 2))
    items = sorted(sheet.secenekler[0].kalemler, key=lambda i: i.tutar_tl, reverse=True)
    if len(sheet.secenekler) == 1 and len(items) > 7:
        exp.add(round(sum(i.tutar_tl for i in items[7:]), 2))  # "Diğer"
    return exp


def layout_audit(draft: Draft, sheet: DataSheet, series_no: int = 0,
                 sizes: tuple = ((1080, 1920),)) -> list[str]:
    issues = []
    expected = _expected_numbers(sheet)
    shown: list[float] = []
    orig_tl = designer.tl

    def spy(x, exact=True):
        shown.append(round(x, 2))
        return orig_tl(x, exact)

    designer.tl = spy
    try:
        for size in sizes:
            c = designer.Canvas(size, series_no)
            x0, y0, x1, y1 = c.safe
            for i, s in enumerate(draft.slaytlar, 1):
                shown.clear()
                designer.render_slide(c, s, sheet, i - 1, len(draft.slaytlar), t=1.0)
                boxes = c.audit
                for b in boxes:
                    bx = b["box"]
                    if bx[0] < x0 or bx[1] < y0 or bx[2] > x1 or bx[3] > y1:
                        issues.append(f"Sahne {i} ({s.tur}): '{b['text'][:30]}' güvenli alanın dışına taşıyor")
                for a in range(len(boxes)):
                    for b in range(a + 1, len(boxes)):
                        if _overlap(boxes[a]["box"], boxes[b]["box"]):
                            issues.append(f"Sahne {i} ({s.tur}): '{boxes[a]['text'][:20]}' ile "
                                          f"'{boxes[b]['text'][:20]}' üst üste biniyor")
                wrong = [v for v in shown if v not in expected]
                if wrong:
                    issues.append(f"Sahne {i} ({s.tur}): tabloda olmayan rakam çizildi: {wrong[:3]}")
    finally:
        designer.tl = orig_tl
    return sorted(set(issues))


# ------------------------------------------------------------------ 3) SENKRON KONTROLCÜSÜ

def _stream_seconds(path: Path, sel: str) -> float:
    """Akışı baştan sona çözüp gerçek süresini ölçer (konteyner bilgisine güvenmez)."""
    from .video import FF
    p = subprocess.run([FF, "-i", str(path), "-map", f"0:{sel}:0", "-f", "null", "-"],
                       capture_output=True, text=True)
    times = re.findall(r"time=(\d+):(\d+):([\d.]+)", p.stderr)
    if not times:
        return 0.0
    h, m, s = times[-1]
    return int(h) * 3600 + int(m) * 60 + float(s)


def av_sync(video: Path) -> list[str]:
    issues = []
    tf = video.parent / "timing.json"
    if not video.exists():
        return [f"Video dosyası yok: {video}"]
    if not tf.exists():
        return ["timing.json yok: zamanlama planı doğrulanamıyor"]
    plan = json.loads(tf.read_text(encoding="utf-8"))
    fps = plan["fps"]
    planned = sum(plan["sahne_kareleri"]) / fps
    v = _stream_seconds(video, "v")
    a = _stream_seconds(video, "a")
    if abs(v - planned) > 2 * FRAME:
        issues.append(f"Görüntü süresi planla uyuşmuyor: {v:.3f} sn / plan {planned:.3f} sn")
    if abs(a - v) > 0.05:
        issues.append(f"SES KAYMASI: ses {a:.3f} sn, görüntü {v:.3f} sn (fark {abs(a - v) * 1000:.0f} ms)")
    for i, (nf, vd) in enumerate(zip(plan["sahne_kareleri"], plan["seslendirme_sn"]), 1):
        if vd and vd > nf / fps - 0.15:
            issues.append(f"Sahne {i}: seslendirme ({vd:.2f} sn) sahneye sığmıyor ({nf / fps:.2f} sn), ses kesilir")
    target = config()["uretim"]["video_suresi_sn"]
    if not (target * 0.75 <= v <= min(target * 1.35, 90)):
        issues.append(f"Süre hedef dışında: {v:.1f} sn (hedef ~{target} sn, Reels en fazla 90 sn)")
    return issues


def keyframes(video: Path, out_dir: Path) -> list[Path]:
    """Her sahnenin SON karesini (animasyon bitmiş hali) bitmiş videodan çıkarır."""
    from .video import FF
    plan = json.loads((video.parent / "timing.json").read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)
    paths, cum = [], 0
    for i, nf in enumerate(plan["sahne_kareleri"], 1):
        cum += nf
        t = (cum - 2) / plan["fps"]
        p = out_dir / f"kare{i}.jpg"
        subprocess.run([FF, "-loglevel", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video),
                        "-frames:v", "1", "-vf", "scale=540:-1", str(p)], check=True)
        paths.append(p)
    return paths


# ------------------------------------------------------------------ 4) YAYIN ÖNCESİ KONTROL

def preflight(post: dict, video_url: str | None) -> tuple[list[str], bool]:
    """(sorunlar, adres_hazir). Adres henüz yayında değilse (GitHub Pages derleniyor) hata sayılmaz."""
    issues = []
    if post.get("video"):
        issues += av_sync(ROOT / post["video"])
    for g in post.get("gorseller", []):
        if not (ROOT / g).exists():
            issues.append(f"Görsel yok: {g}")
    ready = True
    if video_url:
        try:
            r = requests.head(video_url, timeout=30, allow_redirects=True)
            ctype = r.headers.get("content-type", "")
            if r.status_code != 200:
                ready = False
            elif post.get("video") and "video/mp4" not in ctype:
                issues.append(f"Video adresi yanlış türde sunuluyor: {ctype}")
        except requests.RequestException:
            ready = False
    return issues, ready
