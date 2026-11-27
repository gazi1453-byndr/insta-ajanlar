"""5) TASARIMCI AJAN
Slayt metinlerinden markaya uygun şablon görseller üretir (1080x1350 JPEG).
Kullanıcı görseli varsa onu Instagram ölçüsüne kırpar. Instagram API sadece
JPEG kabul ettiği için tüm çıktılar JPEG'dir.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .common import MEDIA_GENERATED, config, log
from .creator import Draft

AGENT = "Tasarımcı"

_FONT_CANDIDATES = {
    True: [  # kalın
        "assets/fonts/bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ],
    False: [
        "assets/fonts/regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ],
}


def _font(size: int, bold: bool) -> ImageFont.FreeTypeFont:
    root = Path(__file__).resolve().parent.parent
    for cand in _FONT_CANDIDATES[bold]:
        p = Path(cand) if Path(cand).is_absolute() else root / cand
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def _slide(title: str, body: str, idx: int, total: int, out: Path) -> Path:
    g = config()["gorsel"]
    handle = "@" + config()["hesap"]["kullanici_adi"]
    W, H = g["boyut"]
    img = Image.new("RGB", (W, H), g["arka_plan"])
    d = ImageDraw.Draw(img)
    pad = 90
    max_w = W - 2 * pad

    first = idx == 0
    tsize = 96 if first else 72
    tfont, bfont, small = _font(tsize, True), _font(42, False), _font(32, True)
    # Başlık çok uzunsa küçült
    while len(_wrap(d, title, tfont, max_w)) > 5 and tsize > 48:
        tsize -= 6
        tfont = _font(tsize, True)

    t_lines = _wrap(d, title, tfont, max_w)
    b_lines = _wrap(d, body, bfont, max_w) if body else []
    t_h = len(t_lines) * int(tsize * 1.2)
    b_h = len(b_lines) * 58
    y = (H - t_h - (b_h + 60 if b_lines else 0)) // 2

    d.rectangle([pad, y - 50, pad + 120, y - 38], fill=g["vurgu"])  # vurgu çizgisi
    for line in t_lines:
        d.text((pad, y), line, font=tfont, fill=g["yazi"])
        y += int(tsize * 1.2)
    y += 60
    for line in b_lines:
        d.text((pad, y), line, font=bfont, fill=g["yazi"])
        y += 58

    d.text((pad, H - 110), handle, font=small, fill=g["vurgu"])
    if total > 1:
        label = f"{idx + 1}/{total}"
        d.text((W - pad - d.textlength(label, font=small), 80), label, font=small, fill=g["yazi"])
        if idx < total - 1:
            arrow = "kaydır →"
            d.text((W - pad - d.textlength(arrow, font=small), H - 110), arrow, font=small, fill=g["yazi"])
    img.save(out, "JPEG", quality=92)
    return out


def from_user_image(src: Path, post_id: str) -> Path:
    W, H = config()["gorsel"]["boyut"]
    out = MEDIA_GENERATED / post_id / "1.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    img = ImageOps.fit(ImageOps.exif_transpose(Image.open(src)).convert("RGB"), (W, H))
    img.save(out, "JPEG", quality=92)
    return out


def run(draft: Draft, post_id: str) -> list[Path]:
    folder = MEDIA_GENERATED / post_id
    folder.mkdir(parents=True, exist_ok=True)
    slides = draft.slaytlar[:10] or []
    paths = [_slide(s.baslik, s.metin, i, len(slides), folder / f"{i + 1}.jpg") for i, s in enumerate(slides)]
    log(AGENT, f"{len(paths)} görsel üretildi → {folder.name}/")
    return paths
