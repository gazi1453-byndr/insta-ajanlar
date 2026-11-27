"""VİDEO KURGUCU
Sahneleri 1080x1920, 60 fps dikey Reels videosuna çevirir.

MOTOR: Remotion (video/ klasörü, React) — DESIGN_SYSTEM.md'deki hareket dili:
  yaylı geçiş (damping 14, stiffness 180) + hareket bulanıklığı, hareketli ızgara/ışık arka planı,
  sayaçla gelen rakamlar, yüzdeli kalem kırılımı barları, karaoke altyazı.
  Node/Remotion yoksa aynı zamanlamayla Pillow yedek motoru çalışır.

SES:
  - Edge nöral ses (+%18) ya da ElevenLabs; her sahnenin baş/son sessizliği kelime zamanlarına göre kırpılır.
  - Kelime zamanları → karaoke altyazı (ekrandaki '29.923 TL' konuşulan 'yirmi dokuz bin...' ile eşlenir).
  - Arka plan müziği %9 seste (assets/music), her geçişte 'whoosh', rakam damgasında 'pop' (assets/sfx).

SES KAYMASI OLMAMASI İÇİN (kare-hassas zamanlama):
  - Sahne sınırları KARE cinsinden (birikimli yuvarlama, kayma birikmez).
  - Her sahnenin sesi tam o sahnenin kare süresine dolgulanıp kesilir; seslendirme kendi sahnesinin
    ilk karesinde başlar. Görüntü sessiz render edilir, ses ffmpeg ile birebir süreyle eklenir.
  - Zamanlama timing.json'a yazılır; Senkron Kontrolcüsü (qa.py) bitmiş videoyu bu planla karşılaştırır.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import ImageDraw

from . import voice
from .common import MEDIA_GENERATED, ROOT, config, log, maas_cevir
from .creator import Draft
from .data_researcher import DataSheet
from .designer import Canvas, _short, _sources, card_for, clean, headline_value, render_slide

AGENT = "Video Kurgucu"
FPS = 60
FF = imageio_ffmpeg.get_ffmpeg_exe()
ANIMATED = ("grafik", "reveal")
VIDEO_DIR = ROOT / "video"
GAP = 0.2           # sahneler arası nefes (sn)
TAIL = 0.9          # son karede kapanış/CTA için ek süre
MUSIC_GAIN = 0.09   # arka plan müziği ~%9
TRANSITION_FRAMES = 14


def media_duration(path: Path) -> float:
    err = subprocess.run([FF, "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else 0.0


def frame_plan(seconds: list[float]) -> list[int]:
    """Birikimli yuvarlama: sahne sınırları kareye oturur, toplamda kayma birikmez."""
    frames, cum, prev = [], 0.0, 0
    for d in seconds:
        cum += d
        end = round(cum * FPS)
        frames.append(max(1, end - prev))
        prev += frames[-1]
    return frames


# ------------------------------------------------------------------ ses
def _trim(src: Path, words: list[dict], out: Path) -> tuple[Path, list[dict]]:
    """Baş/son sessizliği sıfıra indir. Kelime zamanı varsa ona göre, yoksa silenceremove ile."""
    if words:
        dur = media_duration(src)
        lead = max(0.0, words[0]["s"] - 0.03)
        end = min(dur or 1e9, words[-1]["e"] + 0.08)
        af = f"atrim={lead:.3f}:{end:.3f},asetpts=PTS-STARTPTS"
        words = [{**w, "s": round(w["s"] - lead, 3), "e": round(w["e"] - lead, 3)} for w in words]
    else:
        af = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03,areverse,"
              "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.06,areverse")
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(src), "-af", af + ",aresample=48000",
                    "-ac", "2", "-c:a", "pcm_s16le", str(out)], check=True, capture_output=True)
    return out, words


def _scene_seconds(draft: Draft, audio: list[Path | None]) -> list[float]:
    durs = []
    for s, a in zip(draft.slaytlar, audio):
        if a:
            durs.append(media_duration(a) + GAP)
        else:
            words = len((s.baslik + " " + s.metin).split())
            durs.append(max(1.6, min(3.4, words / 2.6)))
    durs[-1] += TAIL
    return durs


def _build_audio(audio: list[Path | None], frames: list[int], out: Path, sfx: list[tuple] = ()) -> Path | None:
    music = sorted((ROOT / "assets" / "music").glob("*.mp3")) if (ROOT / "assets" / "music").exists() else []
    if not any(audio) and not music:
        return None
    durs = [n / FPS for n in frames]                       # sahnenin GERÇEK kare süresi
    total = sum(durs)
    args, filters, labels = [FF, "-y", "-loglevel", "error"], [], []
    for i, (a, d) in enumerate(zip(audio, durs)):
        if a:
            args += ["-i", str(a)]
        else:
            args += ["-f", "lavfi", "-t", f"{d:.6f}", "-i", "anullsrc=r=48000:cl=stereo"]
        filters.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,"
                       f"apad=whole_dur={d:.6f},atrim=0:{d:.6f},asetpts=PTS-STARTPTS[s{i}]")
        labels.append(f"[s{i}]")
    filters.append("".join(labels) + f"concat=n={len(labels)}:v=0:a=1[voice]")
    final = "[voice]"
    if any(audio):
        filters.append("[voice]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[vn]")
        final = "[vn]"
    n = len(audio)
    mix = [final]
    if music:
        args += ["-stream_loop", "-1", "-i", str(music[sum(frames) % len(music)])]
        filters.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,volume={MUSIC_GAIN if any(audio) else 0.35},"
                       f"atrim=0:{total:.6f},afade=t=out:st={max(total - 1.5, 0):.3f}:d=1.5[bg]")
        mix.append("[bg]")
        n += 1
    for k, (at, path, gain) in enumerate(s for s in sfx if Path(s[1]).exists()):
        args += ["-i", str(path)]
        ms = max(0, int(at * 1000))
        filters.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,volume={gain},adelay={ms}|{ms}[fx{k}]")
        mix.append(f"[fx{k}]")
        n += 1
    if len(mix) > 1:
        filters.append("".join(mix) + f"amix=inputs={len(mix)}:duration=first:normalize=0,"
                       f"alimiter=limit=0.95[mix]")
        final = "[mix]"
    # kesin uzunluk: hiçbir filtre (loudnorm/amix) sesi bir kare bile kısaltamasın
    # loudnorm/alimiter zaman damgasını kaydırır: damgaları ÖRNEK SAYISINDAN yeniden üret, sonra tam uzunluğa getir
    filters.append(f"{final}asetpts=N/SR/TB,apad=whole_dur={total:.6f},atrim=end_sample={round(total * 48000)}[out]")
    args += ["-filter_complex", ";".join(filters), "-map", "[out]", "-c:a", "pcm_s16le", str(out)]
    subprocess.run(args, check=True, capture_output=True)
    return out


# ------------------------------------------------------------------ Remotion verisi
_MONEY = re.compile(r"(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?\s*(?:TL|lira)\b")


def _money(text: str):
    m = _MONEY.search(text)
    if not m:
        return None
    return float(m[1].replace(".", "")) + (int(m[2].ljust(2, "0")) / 100 if m[2] else 0), m


def _rows_breakdown(sheet: DataSheet, limit: int = 6) -> list[dict]:
    o = sheet.secenekler[0]
    total = o.toplam_tl or 1
    items = sorted(o.kalemler, key=lambda i: i.tutar_tl, reverse=True)
    rows = [{"label": _short(i.kalem, 24), "value": round(i.tutar_tl, 2), "pct": round(100 * i.tutar_tl / total),
             "est": i.tahmini} for i in items[:limit]]
    if len(items) > limit:
        rest = sum(i.tutar_tl for i in items[limit:])
        rows.append({"label": "Diğer", "value": round(rest, 2), "pct": round(100 * rest / total)})
    return rows


def _rows_compare(sheet: DataSheet) -> list[dict]:
    colors = ["#22C55E", "#E2E8F0", "#94A3B8", "#86EFAC"]
    return [{"label": _short(o.ad, 24), "value": round(o.toplam_tl, 2), "color": colors[i % 4]}
            for i, o in enumerate(sheet.secenekler)]


def scene_props(s, sheet: DataSheet, i: int, n: int) -> dict:
    d = {"baslik": clean(s.baslik), "metin": clean(s.metin)}
    single = len(sheet.secenekler) == 1
    if i == 0:
        return {**d, "kind": "hook"}
    if s.tur == "grafik":
        if single:
            return {**d, "kind": "grafik", "mode": "breakdown", "rows": _rows_breakdown(sheet),
                    "totalLabel": f"TOPLAM ({_short(sheet.hesap_donemi, 20)})", "total": round(sheet.secenekler[0].toplam_tl, 2)}
        label, val = headline_value(sheet)
        return {**d, "kind": "grafik", "mode": "compare", "rows": _rows_compare(sheet), "totalLabel": label, "total": round(val, 2)}
    if s.tur == "reveal":
        label, val = headline_value(sheet)
        mc = maas_cevir(val)
        rows = _rows_breakdown(sheet, 4) if single else _rows_compare(sheet)
        return {**d, "kind": "reveal", "label": label, "value": round(val, 2), "maas": mc.get("metin", ""), "rows": rows}
    if s.tur == "sonuc":
        label, val = headline_value(sheet)
        if single:
            rows = [{"label": r["label"], "value": r["value"], "est": r.get("est")} for r in _rows_breakdown(sheet, 5)]
            rows.append({"label": "TOPLAM", "value": round(sheet.secenekler[0].toplam_tl, 2)})
        else:
            rows = _rows_compare(sheet) + [{"label": "Fark", "value": round(val, 2)}]
        seri = config().get("seri", {})
        return {**d, "kind": "sonuc", "rows": rows, "maas": maas_cevir(val).get("metin", ""),
                "question": clean(s.baslik), "cta": seri.get("kapanis", "Hangisini hesaplayalım? Yorumlara yaz")}
    hit = _money(d["baslik"])
    if hit:
        val, m = hit
        label = re.sub(r"\s{2,}", " ", (d["baslik"][:m.start()] + d["baslik"][m.end():])).strip(" :–—-")
        if len(label) >= 4:
            return {**d, "kind": "spot", "baslik": label, "spotValue": round(val, 2), "spotSuffix": " TL"}
    hit = _money(d["metin"])
    if hit:  # rakam alt metindeyse: başlık etiket olur, rakam dev sayaçla ortaya, kalan metin altına
        val, m = hit
        rest = re.sub(r"\s{2,}", " ", (d["metin"][:m.start()] + d["metin"][m.end():])).strip(" :–—-.,")
        return {**d, "kind": "spot", "spotValue": round(val, 2), "spotSuffix": " TL",
                "metin": rest[:1].upper() + rest[1:] if rest else ""}
    return {**d, "kind": "card" if i % 2 else "statement"}


def phrases_for(tokens: list[dict], offset: float) -> list[dict]:
    """Altyazı öbekleri: en çok 3 kelime / 20 karakter, noktalamada kır."""
    out, cur = [], []
    for t in tokens:
        cur.append({"t": t["t"], "s": round(t["s"] + offset, 3), "e": round(t["e"] + offset, 3)})
        text = " ".join(w["t"] for w in cur)
        if len(cur) >= 3 or len(text) >= 20 or t["t"][-1:] in ".,!?:;":
            out.append({"s": cur[0]["s"], "e": cur[-1]["e"], "words": cur})
            cur = []
    if cur:
        out.append({"s": cur[0]["s"], "e": cur[-1]["e"], "words": cur})
    return out


def remotion_available() -> bool:
    return (VIDEO_DIR / "node_modules" / "@remotion" / "cli").exists() and bool(shutil.which("npx"))


def _render_remotion(props: dict, folder: Path, out: Path) -> None:
    pfile = folder / "props.json"
    pfile.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    cmd = [shutil.which("npx"), "remotion", "render", "src/index.ts", "GercekMaliyet", str(out),
           f"--props={pfile}", "--public-dir=../assets", "--muted", "--codec=h264", "--crf=18",
           "--image-format=jpeg", "--jpeg-quality=92", "--pixel-format=yuv420p", "--color-space=bt709", "--log=error",
           f"--concurrency={os.environ.get('REMOTION_CONCURRENCY', '50%')}"]
    if os.environ.get("REMOTION_BROWSER"):
        cmd.append(f"--browser-executable={os.environ['REMOTION_BROWSER']}")
    r = subprocess.run(cmd, cwd=VIDEO_DIR, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=3600)
    if r.returncode != 0 or not out.exists():
        raise RuntimeError(f"Remotion hatası: {(r.stderr or r.stdout)[-900:]}")


def _render_pillow(draft: Draft, sheet: DataSheet, frames: list[int], series_no: int, label: str, out: Path) -> None:
    """Yedek motor (Node yoksa): Pillow kareleri + kinetik tipografi + geçiş."""
    from . import motion
    W, H = config()["gorsel"]["video_boyut"]
    accent, bg = config()["gorsel"]["vurgu"], config()["gorsel"]["arka_plan"]
    c = Canvas((W, H), series_no, label)
    total_frames = sum(frames)
    cmd = [FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-r", str(FPS), "-movflags", "+faststart", str(out)]
    errlog = out.parent / "ffmpeg.log"
    errf = open(errlog, "wb")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=errf)
    frame_no, prev_last, n = 0, None, len(draft.slaytlar)
    tr = round(motion.TRANSITION_S * FPS)
    for i, (s, nf) in enumerate(zip(draft.slaytlar, frames)):
        box = card_for(c, s, sheet, i, n)
        static = None if s.tur in ANIMATED else render_slide(c, s, sheet, i, n, card_box=box)
        blocks = motion.kinetic_plan(c.audit, (W, H)) if static is not None else []
        bgs = [motion._local_bg(static, b) for b in blocks]
        last = None
        for f in range(nf):
            t = f / FPS
            if static is None:
                img = render_slide(c, s, sheet, i, n, t=min(1.0, t / 1.8), card_box=box)
            else:
                img = motion.kinetic(static, blocks, t - (0.1 if i else 0), bgs)
            if prev_last is not None and f < tr:
                img = motion.transition(prev_last, img, (f + 1) / (tr + 1), bg)
            last = img
            img = img.copy()
            ImageDraw.Draw(img).rectangle([0, 0, int(W * frame_no / max(total_frames, 1)), 10], fill=accent)
            proc.stdin.write(img.tobytes())
            frame_no += 1
        prev_last = last
    proc.stdin.close()
    code = proc.wait()
    errf.close()
    err = errlog.read_text(errors="ignore")
    errlog.unlink(missing_ok=True)
    if code != 0:
        raise RuntimeError(f"ffmpeg hatası: {err[-800:]}")


def render(draft: Draft, sheet: DataSheet, post_id: str, series_no: int = 0, label: str = "") -> Path:
    folder = MEDIA_GENERATED / post_id
    folder.mkdir(parents=True, exist_ok=True)
    g = config()["gorsel"]
    W, H = g["video_boyut"]

    # 1) ses + kelime zamanları + sessizlik kırpma
    audio: list[Path | None] = []
    tokens: list[list[dict]] = []
    for i, s in enumerate(draft.slaytlar):
        raw, words = voice.synthesize_timed(s.seslendirme, folder / f"ham{i + 1}.mp3")
        if raw:
            wav, words = _trim(raw, words, folder / f"ses{i + 1}.wav")
            raw.unlink(missing_ok=True)
            audio.append(wav)
            tokens.append(voice.align(s.seslendirme, words, media_duration(wav)))
        else:
            audio.append(None)
            tokens.append([])
    prov = ("ElevenLabs" if os.environ.get("ELEVENLABS_API_KEY") else
            f"Edge ({config().get('ses', {}).get('edge_ses', 'tr-TR-AhmetNeural')}, {config().get('ses', {}).get('hiz', '+18%')})")
    log(AGENT, "Seslendirme: " + (prov if any(audio) else "yok (ekranda yazı)"))

    # 2) kare planı
    seconds = _scene_seconds(draft, audio)
    frames = frame_plan(seconds)
    total_frames = sum(frames)
    starts = [sum(frames[:i]) for i in range(len(frames))]
    voice_durs = [round(media_duration(a), 3) if a else 0.0 for a in audio]

    # 3) müzik + efektler + ses
    sfx_dir = ROOT / "assets" / "sfx"
    sfx = [((starts[i] - 4) / FPS, sfx_dir / "whoosh.wav", 0.35) for i in range(1, len(frames))]
    sfx += [(starts[i] / FPS + 0.8, sfx_dir / "pop.wav", 0.3)
            for i, s in enumerate(draft.slaytlar) if s.tur == "reveal"]
    track = _build_audio(audio, frames, folder / "mix.wav", sfx)

    # 4) görüntü (sessiz) → 5) ses ile birleştir
    silent = folder / "sessiz.mp4"
    engine = "Pillow"
    if remotion_available() and os.environ.get("VIDEO_MOTOR", "remotion") == "remotion":
        seri = config().get("seri", {})
        props = {
            "fps": FPS, "width": W, "height": H, "durationInFrames": total_frames,
            "palette": {"bg": g["arka_plan"], "panel": g.get("panel", "#18233A"), "accent": g["vurgu"],
                        "warn": g.get("uyari", "#F43F5E"), "text": g["yazi"], "text2": g.get("yazi_ikincil", "#94A3B8")},
            "brand": {"name": seri.get("ad", "GERÇEK MALİYET"), "no": series_no, "label": label,
                      "handle": config()["hesap"]["kullanici_adi"]},
            "period": f"{_short(sheet.hesap_donemi, 30)} · {sheet.fiyat_tarihi} fiyatları",
            "sources": _sources(sheet),
            "scenes": [{**scene_props(s, sheet, i, len(frames)), "from": starts[i], "frames": frames[i]}
                       for i, s in enumerate(draft.slaytlar)],
            "phrases": [p for i, t in enumerate(tokens) for p in phrases_for(t, starts[i] / FPS)],
        }
        try:
            _render_remotion(props, folder, silent)
            engine = "Remotion"
        except Exception as e:
            log(AGENT, f"Remotion başarısız, Pillow yedek motoruna geçiliyor: {str(e)[:300]}")
    if engine == "Pillow":
        _render_pillow(draft, sheet, frames, series_no, label, silent)

    out = folder / "video.mp4"
    dur = f"{total_frames / FPS:.6f}"
    cmd = [FF, "-y", "-loglevel", "error", "-i", str(silent)]
    cmd += ["-i", str(track)] if track else ["-f", "lavfi", "-t", dur, "-i", "anullsrc=r=48000:cl=stereo"]
    # -t YOK: Remotion videosunun başlangıç ofsetiyle birleşince sesi kısaltıyor; iki akış zaten kare-hassas uzunlukta
    cmd += ["-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)
    for p in [silent, *[a for a in audio if a], folder / "mix.wav"]:
        p.unlink(missing_ok=True)

    timing = {"fps": FPS, "sahne_kareleri": frames, "seslendirme_sn": voice_durs,
              "toplam_sn": round(total_frames / FPS, 3), "turler": [s.tur for s in draft.slaytlar], "motor": engine}
    (folder / "timing.json").write_text(json.dumps(timing, ensure_ascii=False), encoding="utf-8")
    log(AGENT, f"Video hazır ({engine}): {out.name} ({total_frames / FPS:.1f} sn, {out.stat().st_size / 1e6:.1f} MB)")
    return out
