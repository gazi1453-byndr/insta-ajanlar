"""TASARIMCI AJAN
Sahneleri markaya uygun görsellere çevirir:
- metin: büyük başlık + kısa yazı
- grafik: maliyet tablosundan çubuk grafik (videoda çubuklar büyür, rakamlar sayar)
- sonuc: kapanış + tartışma sorusu
Carousel için 1080x1350, Reels için 1080x1920 üretir. Instagram API sadece JPEG
kabul ettiği için görseller JPEG'dir.
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
    def __init__(self, size: tuple[int, int]):
        g = config()["gorsel"]
        self.W, self.H = size
        self.g = g
        self.vertical = self.H / self.W > 1.5
        self.pad = 80
        self.top = 230 if self.vertical else 110      # Reels arayüzü üstte/altta yer kaplar
        self.bottom = self.H - (330 if self.vertical else 120)

    def base(self) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        img = Image.new("RGB", (self.W, self.H), self.g["arka_plan"])
        return img, ImageDraw.Draw(img)

    def footer(self, d, text: str = ""):
        handle = "@" + config()["hesap"]["kullanici_adi"]
        d.text((self.pad, self.bottom + 30), handle, font=font(34), fill=self.g["vurgu"])
        if text:
            for i, line in enumerate(wrap(d, text, font(24, False), self.W - 2 * self.pad)[:2]):
                d.text((self.pad, self.bottom + 80 + i * 32), line, font=font(24, False), fill="#94A3B8")


def render_text(c: Canvas, s: Slide, idx: int, total: int, first: bool) -> Image.Image:
    img, d = c.base()
    max_w = c.W - 2 * c.pad
    tsize = 104 if first else 80
    tf = font(tsize)
    while len(wrap(d, s.baslik, tf, max_w)) > 4 and tsize > 50:
        tsize -= 6
        tf = font(tsize)
    tl_ = wrap(d, s.baslik, tf, max_w)
    bf = font(46, False)
    bl = wrap(d, s.metin, bf, max_w) if s.metin else []
    block = len(tl_) * int(tsize * 1.18) + (len(bl) * 62 + 50 if bl else 0)
    y = c.top + (c.bottom - c.top - block) // 2
    d.rectangle([c.pad, y - 46, c.pad + 130, y - 32], fill=c.g["vurgu"])
    for line in tl_:
        d.text((c.pad, y), line, font=tf, fill=c.g["yazi"])
        y += int(tsize * 1.18)
    y += 50
    for line in bl:
        d.text((c.pad, y), line, font=bf, fill="#CBD5E1")
        y += 62
    if total > 1 and not c.vertical:
        lab = f"{idx + 1}/{total}"
        d.text((c.W - c.pad - d.textlength(lab, font=font(32)), 60), lab, font=font(32), fill=c.g["yazi"])
    c.footer(d)
    return img


OPT_COLORS = ["#22C55E", "#60A5FA", "#F59E0B", "#A78BFA"]
ITEM_COLORS = ["#22C55E", "#60A5FA", "#F59E0B", "#A78BFA", "#F43F5E", "#14B8A6", "#EAB308", "#64748B"]


def _sources(sheet: DataSheet) -> str:
    names = []
    for k in sheet.kaynaklar:
        m = re.search(r"https?://(?:www\.)?([^/\s]+)", k)
        name = m.group(1) if m else k.split(":")[0].strip()
        if name and name not in names:
            names.append(name)
    return "Kaynak: " + ", ".join(names[:4])


def _short(name: str, limit: int = 26) -> str:
    """Parantezden önceki kısmı al; hâlâ uzunsa kelime sınırında kısalt."""
    base = name.split(" (")[0].strip()
    if len(base) <= limit:
        return base
    out = ""
    for w in base.split():
        if len(out) + len(w) + 1 > limit:
            break
        out = f"{out} {w}".strip()
    return out or base[:limit]


def _fit(d, text: str, size: int, max_w: int, bold: bool = True):
    """Metni kesmeden sığdır: önce küçült, olmazsa iki satıra böl."""
    while size > 24 and d.textlength(text, font=font(size, bold)) > max_w:
        size -= 2
    f = font(size, bold)
    return f, wrap(d, text, f, max_w)[:2], size


def _row_head(c: Canvas, d, y: int, label: str, amount: str, color: str) -> int:
    """Sol: etiket, sağ: tutar (sağa hizalı, asla taşmaz). Kullanılan yüksekliği döndürür."""
    af = font(34)
    aw = d.textlength(amount, font=af)
    room = c.W - 2 * c.pad - aw - 30
    if len(wrap(d, label, font(26), room)) > 2:
        label = _short(label)
    lf, lines, size = _fit(d, label, 32, room)
    for i, line in enumerate(lines):
        d.text((c.pad, y + i * (size + 6)), line, font=lf, fill=c.g["yazi"])
    d.text((c.W - c.pad - aw, y), amount, font=af, fill=color)
    return max(len(lines) * (size + 6), 40)


def render_chart(c: Canvas, s: Slide, sheet: DataSheet, t: float = 1.0) -> Image.Image:
    """t: 0->1 animasyon ilerlemesi. t=1'de her rakam tablodakiyle birebir aynıdır."""
    img, d = c.base()
    max_w = c.W - 2 * c.pad
    y = c.top
    tf, lines, ts = _fit(d, s.baslik, 64, max_w)
    for line in lines:
        d.text((c.pad, y), line, font=tf, fill=c.g["yazi"])
        y += ts + 12
    d.text((c.pad, y + 6), f"{sheet.hesap_donemi} · {sheet.fiyat_tarihi} fiyatları", font=font(30, False), fill="#94A3B8")
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
            w = int(max_w * (val / vmax) * local)
            bh = 34 if c.vertical else 22
            d.rounded_rectangle([c.pad, by, c.pad + max(w, 6), by + bh], radius=bh // 2, fill=c.g["vurgu"])
            y += max(row_h, hh + bh + 18)
        box_label, box_val = "TOPLAM", opts[0].toplam_tl
    else:
        # Yığılmış çubuk: aynı kalem her seçenekte aynı renkte; seçenek rengi soldaki işarette ve tutarda
        order = []
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
            d.text((lx + 34, ly), label, font=font(26, False), fill="#CBD5E1")
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
        hi = max(opts, key=lambda o: o.toplam_tl)
        lo = min(opts, key=lambda o: o.toplam_tl)
        box_label = f"FARK: {_short(hi.ad)} − {_short(lo.ad)} ({_short(sheet.hesap_donemi, 30)})"
        box_val = hi.toplam_tl - lo.toplam_tl
    tt = _stage(t, 0.3)
    y += 10
    bf, blines, bs = _fit(d, box_label, 32, max_w - 72)
    blines = wrap(d, box_label, bf, max_w - 72)[:3]
    box_h = 28 + len(blines) * (bs + 6) + 96
    d.rounded_rectangle([c.pad, y, c.W - c.pad, y + box_h], radius=28, outline=c.g["vurgu"], width=4)
    for i, line in enumerate(blines):
        d.text((c.pad + 36, y + 20 + i * (bs + 6)), line, font=bf, fill="#94A3B8")
    d.text((c.pad + 36, y + 28 + len(blines) * (bs + 6)), tl(box_val * tt, exact), font=font(60), fill=c.g["vurgu"])
    c.footer(d, _sources(sheet) + (" · * tahmini" if star_used else ""))
    return img


def render_slide(c: Canvas, s: Slide, sheet: DataSheet, idx: int, total: int, t: float = 1.0) -> Image.Image:
    if s.tur == "grafik":
        return render_chart(c, s, sheet, t)
    return render_text(c, s, idx, total, first=(idx == 0))


def carousel(draft: Draft, sheet: DataSheet, post_id: str) -> list[Path]:
    folder = MEDIA_GENERATED / post_id
    folder.mkdir(parents=True, exist_ok=True)
    c = Canvas(tuple(config()["gorsel"]["boyut"]))
    slides = draft.slaytlar[:10]
    paths = []
    for i, s in enumerate(slides):
        p = folder / f"{i + 1}.jpg"
        render_slide(c, s, sheet, i, len(slides)).save(p, "JPEG", quality=92)
        paths.append(p)
    log(AGENT, f"{len(paths)} carousel görseli üretildi → {folder.name}/")
    return paths


def stills_vertical(draft: Draft, sheet: DataSheet, post_id: str) -> list[Path]:
    """Video sahnelerinin son halleri (müdürün incelemesi ve kapak için)."""
    folder = MEDIA_GENERATED / post_id
    folder.mkdir(parents=True, exist_ok=True)
    c = Canvas(tuple(config()["gorsel"]["video_boyut"]))
    paths = []
    for i, s in enumerate(draft.slaytlar):
        p = folder / f"sahne{i + 1}.jpg"
        render_slide(c, s, sheet, i, len(draft.slaytlar)).save(p, "JPEG", quality=90)
        paths.append(p)
    return paths
