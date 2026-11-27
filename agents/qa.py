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
from .common import ROOT, config, maas_cevir
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
    lo, hi = 7, 11
    if not lo <= len(s) <= hi:
        issues.append(f"Sahne sayısı {lo}-{hi} arası olmalı (şu an {len(s)})")
    words = sum(len(x.seslendirme.split()) for x in s)
    wlo, whi = int(target * 1.4), int(target * 2.3)   # gerçek ölçüm: +%18 seste ~71 kelime ≈ 41 sn (rakamlar okununca uzar)
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


# ------------------------------------------------------------------ 1a) DERİNLİK DENETÇİSİ

def depth_check(sheet: DataSheet) -> list[str]:
    """'Gerçek maliyet' vaadi: tek bir etiket fiyatı değil, kalem kalem hesap olmalı."""
    issues = []
    n_items = sum(len(o.kalemler) for o in sheet.secenekler)
    if len(sheet.secenekler) == 1 and n_items < 4:
        issues.append(f"Tablo çok sığ: {n_items} kalem var. Gerçek maliyet için en az 4 kalem gerekli "
                      "(etiket fiyatının yanında vergi, sigorta, bakım, komisyon, yıllık/aylık toplam gibi gizli kalemler)")
    if len(sheet.secenekler) > 1 and any(len(o.kalemler) < 2 for o in sheet.secenekler):
        issues.append("Karşılaştırmada her seçeneğin en az 2 kalemi olmalı")
    domains = {re.sub(r"^www\.", "", m.group(1)) for k in sheet.kaynaklar
               for m in [re.search(r"https?://([^/\s]+)", k)] if m}
    if len(domains) < 2:
        issues.append(f"En az 2 farklı kaynak site gerekli (şu an {len(domains)})")
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
            for m in re.finditer(r"(\d+)\s*(gün|saat)(?:lük)?\s*(?:çalış|emek|mesai|maaş)", text, re.IGNORECASE):
                n, unit = int(m.group(1)), m.group(2).lower()
                valid = {mc["deger"] for mc in (maas_cevir(v) for v in vals) if mc and mc["birim"] == unit}
                if valid and not any(abs(n - x) <= 1 for x in valid):
                    issues.append(f"Sahne {i} ({field}): '{m.group(0)}' maaş çevirisiyle uyuşmuyor (doğru: {sorted(valid)[:3]})")
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
                 sizes: tuple = ((1080, 1920),), label: str = "") -> list[str]:
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
            c = designer.Canvas(size, series_no, label)
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


# ------------------------------------------------------------------ 2b) RENK DENETÇİSİ (60-30-10)

def _hex(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def color_balance(images: list) -> dict:
    """Karelerdeki piksel payları: baskın (arka plan), ikincil (panel), vurgu, yazı/diğer.
    images: PIL Image ya da dosya yolu listesi."""
    from PIL import Image
    g = config()["gorsel"]
    pal = {"baskin": _hex(g["arka_plan"]), "ikincil": _hex(g.get("panel", "#18233A")), "vurgu": _hex(g["vurgu"])}
    accents = [_hex(x) for x in ("#86EFAC", "#15803D", "#BBF7D0")]  # vurgu tonları
    counts = {"baskin": 0, "ikincil": 0, "vurgu": 0, "yazi": 0}
    for im in images:
        im = (Image.open(im) if not hasattr(im, "resize") else im).convert("RGB").resize((108, 192))
        for px in im.getdata():
            dist = {k: sum((a - b) ** 2 for a, b in zip(px, v)) for k, v in pal.items()}
            dist["vurgu"] = min([dist["vurgu"]] + [sum((a - b) ** 2 for a, b in zip(px, v)) for v in accents])
            k = min(dist, key=dist.get)
            counts[k if dist[k] < 2500 else "yazi"] += 1
    tot = sum(counts.values()) or 1
    return {k: round(v / tot * 100, 1) for k, v in counts.items()}


def color_check(images: list) -> list[str]:
    b = color_balance(images)
    issues = []
    if not 50 <= b["baskin"] <= 72:
        issues.append(f"Baskın renk payı %{b['baskin']} (hedef ~%60)")
    if not 20 <= b["ikincil"] <= 40:
        issues.append(f"İkincil renk payı %{b['ikincil']} (hedef ~%30)")
    if not 5 <= b["vurgu"] <= 15:
        issues.append(f"Vurgu rengi payı %{b['vurgu']} (hedef ~%10)")
    return issues


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


def av_sync(video: Path, check_length: bool = True) -> list[str]:
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
    u = config()["uretim"]
    target = u["video_suresi_sn"]
    lo, hi = u.get("video_sure_araligi") or [target * 0.85, target * 1.1]
    if check_length and not (lo - 0.5 <= v <= hi + 0.5):
        issues.append(f"Süre hedef dışında: {v:.1f} sn (hedef {lo}-{hi} sn)")
    longest = u.get("sahne_en_uzun_sn", 4.0)
    n = len(plan["sahne_kareleri"])
    turler = plan.get("turler") or []
    for i, nf in enumerate(plan["sahne_kareleri"], 1):
        animated = i <= len(turler) and turler[i - 1] in ("grafik", "reveal")  # sayaç/bar: sahne durağan değil
        limit = longest + (3.0 if animated else 0.3)
        if 1 < i < n and nf / fps > limit:
            issues.append(f"Sahne {i} çok uzun ({nf / fps:.1f} sn > {limit:.1f} sn): seslendirmesini kısalt (rakamları yuvarla, dolguyu at)")
    return issues


# ------------------------------------------------------------------ 3b) SES DENETÇİSİ

def _norm_words(text: str) -> list[str]:
    tr = str.maketrans("ÇĞİIÖŞÜçğıöşü", "cgiiosucgiosu")
    text = text.replace("İ", "i").replace("I", "ı").lower().translate(tr)
    return re.findall(r"[a-z0-9]+", text)


def voice_check(video: Path, draft: Draft, transcribe: bool = True) -> list[str]:
    """Sesi DİNLER gibi kontrol eder: ses seviyesi, bozulma (clipping), konuşma hızı ve
    sesi yazıya döküp senaryoyla karşılaştırma (yanlış/eksik okunan kelimeler)."""
    import difflib

    from . import llm, voice
    from .video import FF
    issues = []
    plan = json.loads((video.parent / "timing.json").read_text(encoding="utf-8"))
    if not any(plan.get("seslendirme_sn", [])):
        return []  # sessiz video: kontrol edilecek ses yok
    p = subprocess.run([FF, "-i", str(video), "-map", "0:a:0", "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    mean = re.search(r"mean_volume: (-?[\d.]+) dB", p.stderr)
    peak = re.search(r"max_volume: (-?[\d.]+) dB", p.stderr)
    if mean and not -26 <= float(mean[1]) <= -10:
        issues.append(f"Ses seviyesi uygun değil: ortalama {mean[1]} dB (hedef -26 ile -10 dB arası)")
    if peak and float(peak[1]) > -0.3:
        issues.append(f"Ses patlıyor (clipping): tepe {peak[1]} dB")
    for i, (s, sec) in enumerate(zip(draft.slaytlar, plan["seslendirme_sn"]), 1):
        if sec:
            wps = len(voice.speakable(s.seslendirme).split()) / sec
            if not 1.4 <= wps <= 4.4:
                issues.append(f"Sahne {i}: konuşma hızı anormal ({wps:.1f} kelime/sn)")
    if transcribe:
        mp3 = video.parent / "ses_kontrol.mp3"
        subprocess.run([FF, "-loglevel", "error", "-y", "-i", str(video), "-map", "0:a:0", "-ac", "1",
                        "-ar", "16000", "-b:a", "48k", str(mp3)], check=True)
        try:
            heard = llm.transcribe("Ses Denetçisi", mp3)
            # döküm rakamla yazılmış olabilir ("135 319 lira"): grupları birleştir, sonra yazıya çevir
            heard = re.sub(r"\b(\d{1,3})((?:[ .]\d{3})+)\b",
                           lambda m: m[1] + m[2].replace(" ", "").replace(".", ""), heard)
            heard = voice.speakable(heard)
            expected = _norm_words(" ".join(voice.speakable(s.seslendirme) for s in draft.slaytlar))
            got = _norm_words(heard)
            ratio = difflib.SequenceMatcher(None, expected, got).ratio()
            if ratio < 0.80:
                issues.append(f"Ses senaryoyla uyuşmuyor: benzerlik %{ratio * 100:.0f} (en az %80). "
                              f"Duyulan: '{' '.join(got[:25])}…'")
        except llm.LLMError as e:
            from .common import log
            log("Ses Denetçisi", f"Ses yazıya dökülemedi, sadece ölçüm kontrolleri yapıldı: {str(e)[:120]}")
        finally:
            mp3.unlink(missing_ok=True)
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
        # senaryo videolarında süreyi kullanıcı belirler; senkron yine denetlenir
        issues += av_sync(ROOT / post["video"], check_length=post.get("kaynak") != "senaryo")
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
