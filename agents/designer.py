"""TASARIMCI AJAN
Sahneleri markaya uygun görsellere çevirir:
- metin: büyük başlık + kısa yazı
- grafik: maliyet tablosundan çubuk grafik (videoda çubuklar büyür, rakamlar sayar)
- sonuc: kapanış + tartışma sorusu
Carousel için 1080x1350, Reels için 1080x1920 üretir. Instagram API sadece JPEG
kabul ettiği için görseller JPEG'dir.
"""
from __future__ import annotations

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


def tl(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".") + " TL"


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


def render_chart(c: Canvas, s: Slide, sheet: DataSheet, t: float = 1.0) -> Image.Image:
    """t: 0→1 animasyon ilerlemesi (çubuklar büyür, rakamlar sayar)."""
    img, d = c.base()
    max_w = c.W - 2 * c.pad
    y = c.top
    for line in wrap(d, s.baslik, font(64), max_w)[:2]:
        d.text((c.pad, y), line, font=font(64), fill=c.g["yazi"])
        y += 76
    d.text((c.pad, y + 6), f"{sheet.hesap_donemi} · {sheet.fiyat_tarihi} fiyatları", font=font(30, False), fill="#94A3B8")
    y += 80

    opts = sheet.secenekler
    if len(opts) == 1:
        items = sorted(opts[0].kalemler, key=lambda i: i.tutar_tl, reverse=True)
        rows = [(i.kalem + (" *" if i.tahmini else ""), i.tutar_tl) for i in items[:7]]
        if len(items) > 7:
            rows.append(("Diğer", sum(i.tutar_tl for i in items[7:])))
        total_label, total_val = "TOPLAM", opts[0].toplam_tl
    else:
        rows = [(o.ad, o.toplam_tl) for o in opts]
        diff = max(o.toplam_tl for o in opts) - min(o.toplam_tl for o in opts)
        total_label, total_val = "FARK", diff
    vmax = max(v for _, v in rows) or 1
    avail = (c.bottom - 220) - y
    row_h = min(150 if len(opts) > 1 else 120, avail // max(len(rows), 1))
    bar_h = int(row_h * 0.38)
    for n, (label, val) in enumerate(rows):
        local = _stage(t, n * 0.06)                # çubuklar sırayla büyür
        d.text((c.pad, y), label[:40], font=font(36 if len(opts) > 1 else 32, len(opts) > 1), fill=c.g["yazi"])
        by = y + int(row_h * 0.38)
        full = max_w - 230
        w = int(full * (val / vmax) * local)
        color = c.g["uyari"] if (len(opts) > 1 and val == vmax) else c.g["vurgu"]
        d.rounded_rectangle([c.pad, by, c.pad + max(w, 6), by + bar_h], radius=bar_h // 2, fill=color)
        d.text((c.pad + max(w, 6) + 18, by + (bar_h - 34) // 2), tl(val * local), font=font(34), fill=c.g["yazi"])
        y += row_h
    tt = _stage(t, 0.3)
    d.rounded_rectangle([c.pad, y + 20, c.W - c.pad, y + 170], radius=28, outline=c.g["vurgu"], width=4)
    d.text((c.pad + 36, y + 42), total_label, font=font(36), fill="#94A3B8")
    d.text((c.pad + 36, y + 88), tl(total_val * tt), font=font(64), fill=c.g["vurgu"])
    y += 210

    if len(opts) > 1:  # kalem kalem karşılaştırma (gizli maliyetler burada görünür)
        colors = [c.g["vurgu"], c.g["uyari"], "#60A5FA"]
        names = [i.kalem for i in sorted(opts[0].kalemler, key=lambda i: i.tutar_tl, reverse=True)]
        lookup = [{i.kalem: i for i in o.kalemler} for o in opts]
        item_h = 44 + 30 * len(opts)
        n_items = max(0, min(len(names), (c.bottom - 40 - y - 50) // item_h))
        if n_items:
            d.text((c.pad, y), "Kalem kalem", font=font(34), fill="#94A3B8")
            for k, o in enumerate(opts):  # açıklama (legend)
                lx = c.W - c.pad - (len(opts) - k) * 230
                d.rounded_rectangle([lx, y + 8, lx + 26, y + 30], radius=6, fill=colors[k % 3])
                d.text((lx + 36, y + 2), o.ad[:12], font=font(26, False), fill="#CBD5E1")
            y += 56
            imax = max((i.tutar_tl for o in opts for i in o.kalemler), default=1) or 1
            for n, name in enumerate(names[:n_items]):
                local = _stage(t, 0.45 + n * 0.05)
                item0 = lookup[0][name]
                d.text((c.pad, y), name[:34] + (" *" if item0.tahmini else ""), font=font(30), fill=c.g["yazi"])
                yy = y + 42
                for k, lk in enumerate(lookup):
                    it = lk.get(name)
                    val = it.tutar_tl if it else 0
                    w = int((max_w - 260) * (val / imax) * local)
                    d.rounded_rectangle([c.pad, yy, c.pad + max(w, 4), yy + 20], radius=10, fill=colors[k % 3])
                    d.text((c.pad + max(w, 4) + 14, yy - 6), tl(val * local) if it else "—", font=font(26, False), fill="#E2E8F0")
                    yy += 30
                y += item_h
    src = "Kaynak: " + ", ".join(k.split(" ")[0] for k in sheet.kaynaklar[:3])
    if any(i.tahmini for o in opts for i in o.kalemler):
        src += " · * tahmini"
    c.footer(d, src)
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
