"""HAREKET MOTORU (Apple HIG tarzı) — DESIGN_SYSTEM.md §5
Pillow + ffmpeg üzerinde çalışan saf Python hareket katmanı (moviepy eşdeğeri, ek bağımlılık yok):
  - Eğriler: ease_out_cubic, ease_in_out_cubic, spring (yaylı, hafif taşmalı)
  - glass_card: buzlu cam kart (arka planı bulanıklaştır + yarı saydam panel + ince üst ışık + yumuşak gölge)
  - kinetic: sahnedeki yazı bloklarını sırayla aşağıdan kaydırıp belirginleştirir (kinetik tipografi)
  - transition: sahne geçişi (eski sahne hafif küçülüp kararır, yenisi aşağıdan yükselir)
Her fonksiyon saf: aynı girdi → aynı kare (QA tekrarlanabilir kalsın).
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageFilter

# DESIGN_SYSTEM.md §5 süreleri (saniye)
TRANSITION_S = 0.35
KINETIC_S = 0.45       # bir blok için giriş süresi
KINETIC_STAGGER = 0.07  # bloklar arası gecikme
KINETIC_RISE = 28       # px
STATIC_ROLES = {"rozet", "imza", "kaynak"}  # marka şeridi ve alt bilgi sabit kalır


def clamp(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def ease_out_cubic(t: float) -> float:
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in_out_cubic(t: float) -> float:
    t = clamp(t)
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def spring(t: float, damping: float = 7.0, freq: float = 1.6) -> float:
    """Kritik altı sönümlü yay: 0→1, hafif taşar ve oturur (iOS 'bouncy' hissi)."""
    t = clamp(t)
    if t >= 1:
        return 1.0
    return 1 - math.exp(-damping * t) * math.cos(2 * math.pi * freq * t)


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def glass_card(img: Image.Image, box, radius: int = 40, tint: str = "#18233A", alpha: int = 236,
               blur: int = 24, shadow: int = 70, highlight: int = 26) -> Image.Image:
    """Buzlu cam kart: gölge → arka plan bulanıklığı → yarı saydam dolgu → ince üst kenar ışığı."""
    x0, y0, x1, y1 = map(int, box)
    W, H = img.size
    base = img.convert("RGBA")
    # 1) yumuşak, aşağı düşen gölge
    sh = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sh).rounded_rectangle([x0 + 6, y0 + 18, x1 - 6, y1 + 18], radius=radius, fill=shadow)
    sh = sh.filter(ImageFilter.GaussianBlur(28))
    base = Image.composite(Image.new("RGBA", (W, H), (0, 0, 0, 255)), base, sh)
    # 2) kartın altındaki alanı bulanıklaştır (cam)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=255)
    blurred = base.crop((x0, y0, x1, y1)).filter(ImageFilter.GaussianBlur(blur))
    frosted = base.copy()
    frosted.paste(blurred, (x0, y0))
    base = Image.composite(frosted, base, mask)
    # 3) yarı saydam dolgu + 4) üstte 1.5 px ışık (hairline)
    over = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=(*_hex(tint), alpha))
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, outline=(255, 255, 255, highlight), width=2)
    return Image.alpha_composite(base, over).convert("RGB")


def _local_bg(img: Image.Image, box) -> tuple:
    """Kutunun hemen dışındaki çevre piksellerinin en sık rengi = yazının oturduğu zemin."""
    x0, y0, x1, y1 = box
    px = img.load()
    W, H = img.size
    counts: dict = {}
    for x in range(x0, x1, 3):
        for y in (y0, y1 - 1):
            if 0 <= x < W and 0 <= y < H:
                counts[px[x, y]] = counts.get(px[x, y], 0) + 1
    for y in range(y0, y1, 3):
        for x in (x0, x1 - 1):
            if 0 <= x < W and 0 <= y < H:
                counts[px[x, y]] = counts.get(px[x, y], 0) + 1
    return max(counts, key=counts.get) if counts else (0, 0, 0)


def kinetic_plan(audit: list[dict], size) -> list[tuple]:
    """Canlandırılacak yazı blokları (yukarıdan aşağı), zemin rengiyle birlikte."""
    W, H = size
    blocks = []
    for b in audit:
        if b.get("role") in STATIC_ROLES:
            continue
        x0, y0, x1, y1 = b["box"]
        box = (max(0, int(x0) - 4), max(0, int(y0) - 4), min(W, int(x1) + 4), min(H, int(y1) + 4))
        if box[2] > box[0] and box[3] > box[1]:
            blocks.append(box)
    blocks.sort(key=lambda bx: (bx[1], bx[0]))
    return blocks


def kinetic_duration(n_blocks: int) -> float:
    return KINETIC_S + KINETIC_STAGGER * max(0, n_blocks - 1)


def kinetic(final: Image.Image, blocks: list[tuple], t: float, bgs: list[tuple] | None = None) -> Image.Image:
    """t saniyesindeki kare: her blok sırayla KINETIC_RISE px aşağıdan yükselir ve belirir.
    t ≥ kinetic_duration → final ile birebir aynı kare."""
    if not blocks or t >= kinetic_duration(len(blocks)):
        return final
    bgs = bgs or [_local_bg(final, b) for b in blocks]
    frame = final.copy()
    d = ImageDraw.Draw(frame)
    crops = [final.crop(b) for b in blocks]
    for b, bg in zip(blocks, bgs):
        d.rectangle(b, fill=bg)
    for i, (b, bg, crop) in enumerate(zip(blocks, bgs, crops)):
        p = ease_out_cubic((t - i * KINETIC_STAGGER) / KINETIC_S)
        if p <= 0:
            continue
        dy = round(KINETIC_RISE * (1 - p))
        bgimg = Image.new("RGB", crop.size, bg)
        piece = Image.blend(bgimg, crop, p)
        # yükselirken kutunun dışına taşmasın: kutuya kırp
        h = crop.size[1] - dy
        if h > 0:
            frame.paste(piece.crop((0, 0, crop.size[0], h)), (b[0], b[1] + dy))
    return frame


def transition(prev: Image.Image, cur: Image.Image, p: float, bg: str = "#0B1220") -> Image.Image:
    """Sahne geçişi (p: 0→1): eski sahne %94'e küçülüp kararır, yeni sahne 80 px aşağıdan yükselerek gelir."""
    p = ease_in_out_cubic(p)
    if p >= 1:
        return cur
    W, H = cur.size
    s = 1 - 0.06 * p
    old = prev.resize((int(W * s), int(H * s)), Image.BILINEAR)
    canvas = Image.new("RGB", (W, H), bg)
    canvas.paste(old, ((W - old.size[0]) // 2, (H - old.size[1]) // 2))
    canvas = Image.blend(canvas, Image.new("RGB", (W, H), bg), 0.5 * p)
    dy = round(80 * (1 - p))
    moved = Image.new("RGB", (W, H), bg)
    moved.paste(cur, (0, dy))
    return Image.blend(canvas, moved, p)
