"""TASARIMCI AJAN
Sahneleri SABİT SERİ ŞABLONUNA göre görsellere çevirir (her videoda aynı kimlik):
- metin:  büyük başlık + kısa yazı
- grafik: maliyet tablosundan çubuk grafik (videoda çubuklar büyür, rakamlar sayar)
- reveal: "GERÇEK MALİYET" sahnesi: tek büyük rakam (tablodan, asla elle yazılmaz)
- sonuc:  kapanış + tartışma sorusu + seri imzası
Her sahnede sol üstte seri rozeti ("GERÇEK MALİYET #12").
Çizilen HER yazı Canvas.audit listesine kaydedilir; Grafik Denetçisi (qa.py) taşma ve
üst üste binme olup olmadığını bu kayıtla kontrol eder.
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .common import MEDIA_GENERATED, config, log
from .creator import Draft, Slide
from .data_researcher import DataSheet

AGENT = "Tasarımcı"

_FONTS = {
    True: ["assets/fonts/bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
           "C:/Windows/Fonts/arialbd.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"],
    False: ["assets/fonts/regular.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "C:/Windows/Fonts/arial.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf"],
}
_font_cache: dict = {}
OPT_COLORS = ["#22C55E", "#60A5FA", "#F59E0B", "#A78BFA"]
ITEM_COLORS = ["#22C55E", "#60A5FA", "#F59E0B", "#A78BFA", "#F43F5E", "#14B8A6", "#EAB308", "#64748B"]


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    key = (size, bold)
    if key not in _font_cache:
        root = Path(__file__).resolve().parent.parent
        for cand in _FONTS[bold]:
            p = Path(cand) if Path(cand).is_absolute() else root / cand
            if p.exists():
                _font_cache[key] = ImageFont.truetype(str(p), size)
                break
        else:
            _font_cache[key] = ImageFont.load_default(size)
    return _font_cache[key]


def tl(x: float, exact: bool = True) -> str:
    """Türkçe para biçimi. Kuruş varsa tam yazılır (421.132,50 TL); animasyon sırasında tam sayı."""
    if exact and abs(x - round(x)) >= 0.005:
        s = f"{x:,.2f}"
    else:
        s = f"{round(x):,.0f}"
    return s.replace(",", "#").replace(".", ",").replace("#", ".") + " TL"


def wrap(d: ImageDraw.ImageDraw, text: str, f, max_w: int) -> list[str]:
    lines, cur = [], ""
    for w in text.split():
        test = f"{cur} {w}".strip()
        if d.textlength(test, font=f) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def _ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def _stage(t: float, start: float, length: float = 0.4) -> float:
    """Animasyon aşaması: t=1 olduğunda HER ZAMAN tam değere (1.0) ulaşır."""
    start = min(start, 0.95)
    length = min(length, 1.0 - start)
    return 1.0 if t >= 1.0 else _ease((t - start) / length)


class Canvas:
    def __init__(self, size: tuple[int, int], series_no: int = 0):
        self.g = config()["gorsel"]
        self.seri = config().get("seri", {})
        self.W, self.H = size
        self.vertical = self.H / self.W > 1.5
        self.pad = 80
        self.top = 260 if self.vertical else 130      # Reels arayüzü üstte/altta yer kaplar
        self.bottom = self.H - (330 if self.vertical else 120)
        self.series_no = series_no
        self.audit: list[dict] = []                   # çizilen her yazının kutusu

    # --- güvenli alan: Reels arayüzünün (üst bar, alt açıklama, sağ butonlar) altında kalmayan bölge
    @property
    def safe(self) -> tuple[int, int, int, int]:
        if self.vertical:
            return (40, 120, self.W - 40, self.H - 150)
        return (30, 25, self.W - 30, self.H - 25)

    def base(self) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        img = Image.new("RGB", (self.W, self.H), self.g["arka_plan"])
        return img, ImageDraw.Draw(img)

    def text(self, d, xy, s: str, f, fill, role: str = "metin") -> None:
        d.text(xy, s, font=f, fill=fill)
        self.audit.append({"box": d.textbbox(xy, s, font=f), "text": s, "role": role})

    def badge(self, d) -> None:
        name = self.seri.get("ad", "GERÇEK MALİYET")
        label = f"{name} #{self.series_no}" if self.series_no else name
        f = font(28)
        y = self.top - 105 if self.vertical else 40
        w = d.textlength(label, font=f)
        d.rounded_rectangle([self.pad, y, self.pad + w + 36, y + 46], radius=23, fill=self.g["vurgu"])
        self.text(d, (self.pad + 18, y + 8), label, f, self.g["arka_plan"], "rozet")

    def footer(self, d, text: str = "") -> None:
        handle = "@" + config()["hesap"]["kullanici_adi"]
        self.text(d, (self.pad, self.bottom + 30), handle, font(34), self.g["vurgu"], "imza")
        if text:
            for i, line in enumerate(wrap(d, text, font(24, False), self.W - 2 * self.pad)[:2]):
                self.text(d, (self.pad, self.bottom + 80 + i * 32), line, font(24, False), "#94A3B8", "kaynak")


def _fit(d, text: str, size: int, max_w: int, bold: bool = True, max_lines: int = 2):
    """Metni KESMEDEN sığdır: önce küçült, olmazsa satırlara böl."""
    while size > 24 and len(wrap(d, text, font(size, bold), max_w)) > max_lines:
        size -= 2
    f = font(size, bold)
    return f, wrap(d, text, f, max_w), size


def _short(name: str, limit: int = 26) -> str:
    base = name.split(" (")[0].strip()
    if len(base) <= limit:
        return base
    out = ""
    for w in base.split():
        if len(out) + len(w) + 1 > limit:
            break
        out = f"{out} {w}".strip()
    return out or base[:limit]


def _sources(sheet: DataSheet) -> str:
    names = []
    for k in sheet.kaynaklar:
        m = re.search(r"https?://(?:www\.)?([^/\s]+)", k)
        name = m.group(1) if m else k.split(":")[0].strip()
        if name and name not in names:
            names.append(name)
    return "Kaynak: " + ", ".join(names[:4])


def headline_value(sheet: DataSheet) -> tuple[str, float]:
    """Reveal sahnesinin tek büyük rakamı: tek seçenekte toplam, karşılaştırmada fark."""
    opts = sheet.secenekler
    if len(opts) == 1:
        return "GERÇEK MALİYET", opts[0].toplam_tl
    hi = max(opts, key=lambda o: o.toplam_tl)
    lo = min(opts, key=lambda o: o.toplam_tl)
    return f"FARK: {_short(hi.ad)} − {_short(lo.ad)}", hi.toplam_tl - lo.toplam_tl


# ------------------------------------------------------------------ sahneler

def render_text(c: Canvas, s: Slide, idx: int, total: int, first: bool, text_bottom: int | None = None) -> Image.Image:
    img, d = c.base()
    c.badge(d)
    max_w = c.W - 2 * c.pad
    tf, tl_, tsize = _fit(d, s.baslik, 104 if first else 80, max_w, max_lines=4)
    bf, bl, bsize = _fit(d, s.metin, 46, max_w, bold=False, max_lines=4) if s.metin else (None, [], 0)
    block = len(tl_) * int(tsize * 1.18) + (len(bl) * int(bsize * 1.35) + 50 if bl else 0)
    y = c.top + ((text_bottom or c.bottom) - c.top - block) // 2
    d.rectangle([c.pad, y - 46, c.pad + 130, y - 32], fill=c.g["vurgu"])
    for line in tl_:
        c.text(d, (c.pad, y), line, tf, c.g["yazi"], "baslik")
        y += int(tsize * 1.18)
    y += 50
    for line in bl:
        c.text(d, (c.pad, y), line, bf, "#CBD5E1")
        y += int(bsize * 1.35)
    if total > 1 and not c.vertical:
        lab = f"{idx + 1}/{total}"
        c.text(d, (c.W - c.pad - d.textlength(lab, font=font(32)), 45), lab, font(32), c.g["yazi"], "sayac")
    c.footer(d)
    return img


def render_reveal(c: Canvas, s: Slide, sheet: DataSheet, t: float = 1.0) -> Image.Image:
    """Serinin imza sahnesi: tek büyük rakam, sayarak gelir ve 'damga' gibi oturur."""
    img, d = c.base()
    c.badge(d)
    max_w = c.W - 2 * c.pad
    label, value = headline_value(sheet)
    exact = t >= 1.0
    k = _stage(t, 0.0, 0.7)
    lf, llines, ls = _fit(d, label, 40, max_w)
    y = c.top + (c.bottom - c.top) // 2 - 170
    for line in llines:
        c.text(d, (c.pad, y), line, lf, "#94A3B8", "etiket")
        y += ls + 10
    y += 20
    num = tl(value * k, exact)
    nf, _, ns = _fit(d, num, 120, max_w, max_lines=1)
    pop = 1.0 + 0.12 * (1 - _stage(t, 0.7, 0.3)) if t < 1 else 1.0   # sona doğru 'damga' etkisi
    nf = font(max(24, int(ns * pop)))
    c.text(d, (c.pad, y), num, nf, c.g["vurgu"], "rakam")
    y += int(ns * 1.35) + 30
    d.rectangle([c.pad, y, c.pad + int(max_w * k), y + 10], fill=c.g["vurgu"])
    y += 50
    sub = s.metin or f"{sheet.hesap_donemi} · {sheet.fiyat_tarihi} fiyatları"
    sf, sl, ss = _fit(d, sub, 40, max_w, bold=False, max_lines=3)
    for line in sl:
        c.text(d, (c.pad, y), line, sf, "#CBD5E1")
        y += int(ss * 1.35)
    c.footer(d, _sources(sheet))
    return img


def _row_head(c: Canvas, d, y: int, label: str, amount: str, color: str) -> int:
    af = font(34)
    aw = d.textlength(amount, font=af)
    room = c.W - 2 * c.pad - aw - 30
    if len(wrap(d, label, font(26), room)) > 2:
        label = _short(label)
    lf, lines, size = _fit(d, label, 32, room)
    for i, line in enumerate(lines):
        c.text(d, (c.pad, y + i * (size + 6)), line, lf, c.g["yazi"], "etiket")
    c.text(d, (c.W - c.pad - aw, y), amount, af, color, "rakam")
    return max(len(lines) * (size + 6), 40)


def render_chart(c: Canvas, s: Slide, sheet: DataSheet, t: float = 1.0) -> Image.Image:
    """t: 0->1 animasyon ilerlemesi. t=1'de her rakam tablodakiyle birebir aynıdır."""
    img, d = c.base()
    c.badge(d)
    max_w = c.W - 2 * c.pad
    y = c.top
    tf, lines, ts = _fit(d, s.baslik, 64, max_w)
    for line in lines:
        c.text(d, (c.pad, y), line, tf, c.g["yazi"], "baslik")
        y += ts + 12
    c.text(d, (c.pad, y + 6), f"{_short(sheet.hesap_donemi, 30)} · {sheet.fiyat_tarihi} fiyatları",
           font(30, False), "#94A3B8", "alt")
    y += 70
    exact = t >= 1.0
    opts = sheet.secenekler
    star_used = False

    if len(opts) == 1:
        items = sorted(opts[0].kalemler, key=lambda i: i.tutar_tl, reverse=True)
        rows = [(i.kalem + (" *" if i.tahmini else ""), i.tutar_tl) for i in items[:7]]
        star_used = any(i.tahmini for i in items[:7])
        if len(items) > 7:
            rows.append(("Diğer", sum(i.tutar_tl for i in items[7:])))
        vmax = max(v for _, v in rows) or 1
        row_h = min(170 if c.vertical else 118, ((c.bottom - 260) - y) // max(len(rows), 1))
        for n, (label, val) in enumerate(rows):
            local = _stage(t, n * 0.06)
            hh = _row_head(c, d, y, label, tl(val * local, exact), c.g["yazi"])
            by = y + hh + 4
            bh = 34 if c.vertical else 22
            w = int(max_w * (val / vmax) * local)
            d.rounded_rectangle([c.pad, by, c.pad + max(w, 6), by + bh], radius=bh // 2, fill=c.g["vurgu"])
            y += max(row_h, hh + bh + 18)
        box_label, box_val = "TOPLAM", opts[0].toplam_tl
    else:
        order: list[str] = []
        for o in opts:
            for i in sorted(o.kalemler, key=lambda i: i.tutar_tl, reverse=True):
                if i.kalem not in order:
                    order.append(i.kalem)
        shown = order[:7]
        icolor = {k: ITEM_COLORS[n % len(ITEM_COLORS)] for n, k in enumerate(shown)}
        est = {i.kalem for o in opts for i in o.kalemler if i.tahmini}
        lx, ly = c.pad, y
        for k in shown + (["Diğer"] if len(order) > 7 else []):
            label = k + (" *" if k in est else "")
            star_used = star_used or k in est
            lw = d.textlength(label, font=font(26, False)) + 60
            if lx + lw > c.W - c.pad:
                lx, ly = c.pad, ly + 40
            d.rounded_rectangle([lx, ly + 6, lx + 24, ly + 30], radius=6, fill=icolor.get(k, "#64748B"))
            c.text(d, (lx + 34, ly), label, font(26, False), "#CBD5E1", "aciklama")
            lx += lw
        y = ly + 64
        vmax = max(o.toplam_tl for o in opts) or 1
        for n, o in enumerate(opts):
            local = _stage(t, n * 0.08)
            hh = _row_head(c, d, y, o.ad, tl(o.toplam_tl * local, exact), OPT_COLORS[n % 4])
            by = y + hh + 6
            bh = 52 if c.vertical else 34
            x = float(c.pad)
            for i in sorted(o.kalemler, key=lambda i: order.index(i.kalem)):
                w = max_w * (i.tutar_tl / vmax) * local
                if w >= 1:
                    d.rectangle([int(x), by, int(x + w), by + bh], fill=icolor.get(i.kalem, "#64748B"))
                x += w
            d.rectangle([c.pad - 14, by, c.pad - 6, by + bh], fill=OPT_COLORS[n % 4])
            y += hh + bh + (110 if c.vertical else 30)
        box_label, box_val = headline_value(sheet)
        box_label = f"{box_label} ({_short(sheet.hesap_donemi, 30)})"
    tt = _stage(t, 0.3)
    y += 10
    bf, blines, bs = _fit(d, box_label, 32, max_w - 72, max_lines=3)
    box_h = 28 + len(blines) * (bs + 6) + 96
    d.rounded_rectangle([c.pad, y, c.W - c.pad, y + box_h], radius=28, outline=c.g["vurgu"], width=4)
    for i, line in enumerate(blines):
        c.text(d, (c.pad + 36, y + 20 + i * (bs + 6)), line, bf, "#94A3B8", "etiket")
    c.text(d, (c.pad + 36, y + 28 + len(blines) * (bs + 6)), tl(box_val * tt, exact), font(60), c.g["vurgu"], "rakam")
    c.footer(d, _sources(sheet) + (" · * tahmini" if star_used else ""))
    return img


def render_outro(c: Canvas, s: Slide) -> Image.Image:
    img = render_text(c, s, 0, 1, first=False, text_bottom=c.bottom - 120)
    d = ImageDraw.Draw(img)
    sig = c.seri.get("kapanis", "Her gün gerçek rakamlar · Takip et")
    f = font(30)
    w = d.textlength(sig, font=f)
    y = c.bottom - 70
    d.rounded_rectangle([c.pad, y - 12, c.pad + w + 40, y + 46], radius=29, outline=c.g["vurgu"], width=3)
    c.text(d, (c.pad + 20, y), sig, f, c.g["vurgu"], "imza")
    return img


def clean(text: str) -> str:
    """Yazı tipinde olmayan emoji/sembolleri ekrandan çıkarır (aksi halde □ kutu görünür)."""
    import unicodedata
    out = "".join(ch for ch in text if not (ord(ch) > 0xFFFF or 0x2190 <= ord(ch) <= 0x2BFF
                                            or 0xFE00 <= ord(ch) <= 0xFE0F or unicodedata.category(ch) == "So"))
    return re.sub(r"\s{2,}", " ", out).strip()


def render_slide(c: Canvas, s: Slide, sheet: DataSheet, idx: int, total: int, t: float = 1.0) -> Image.Image:
    c.audit = []
    s = s.model_copy(update={"baslik": clean(s.baslik), "metin": clean(s.metin)})
    if s.tur == "grafik":
        return render_chart(c, s, sheet, t)
    if s.tur == "reveal":
        return render_reveal(c, s, sheet, t)
    if s.tur == "sonuc":
        return render_outro(c, s)
    return render_text(c, s, idx, total, first=(idx == 0))


def carousel(draft: Draft, sheet: DataSheet, post_id: str, series_no: int = 0) -> list[Path]:
    folder = MEDIA_GENERATED / post_id
    folder.mkdir(parents=True, exist_ok=True)
    c = Canvas(tuple(config()["gorsel"]["boyut"]), series_no)
    slides = draft.slaytlar[:10]
    paths = []
    for i, s in enumerate(slides):
        p = folder / f"{i + 1}.jpg"
        render_slide(c, s, sheet, i, len(slides)).save(p, "JPEG", quality=92)
        paths.append(p)
    log(AGENT, f"{len(paths)} carousel görseli üretildi → {folder.name}/")
    return paths


def stills_vertical(draft: Draft, sheet: DataSheet, post_id: str, series_no: int = 0) -> list[Path]:
    """Video sahnelerinin son halleri (müdürün incelemesi ve kapak için)."""
    folder = MEDIA_GENERATED / post_id
    folder.mkdir(parents=True, exist_ok=True)
    c = Canvas(tuple(config()["gorsel"]["video_boyut"]), series_no)
    paths = []
    for i, s in enumerate(draft.slaytlar):
        p = folder / f"sahne{i + 1}.jpg"
        render_slide(c, s, sheet, i, len(draft.slaytlar)).save(p, "JPEG", quality=90)
        paths.append(p)
    return paths
