"""VİDEO KURGUCU
Sahneleri 1080x1920, 30 fps dikey Reels videosuna çevirir.

SES KAYMASI OLMAMASI İÇİN (kare-hassas zamanlama):
- Sahne sınırları KARE cinsinden hesaplanır (birikimli yuvarlama, kayma birikmez).
- Her sahnenin sesi tam o sahnenin kare süresine (kare_sayısı / 30) dolgulanıp kesilir;
  böylece her seslendirme kendi sahnesinin ilk karesinde başlar.
- Sahne süresi her zaman seslendirmeden uzundur (ses kesilmez).
- Zamanlama video ile birlikte timing.json olarak kaydedilir; Senkron Kontrolcüsü (qa.py)
  bitmiş videoyu ölçüp bu planla karşılaştırır.
Grafik ve reveal sahnelerinde rakamlar sayarak gelir; üstte ilerleme çubuğu vardır.
assets/music/ içine telifsiz bir mp3 koyarsan düşük seste arka plan müziği eklenir.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import ImageDraw

from . import voice
from .common import MEDIA_GENERATED, ROOT, config, log
from .creator import Draft
from .data_researcher import DataSheet
from .designer import Canvas, card_for, render_slide

AGENT = "Video Kurgucu"
FPS = 30
FF = imageio_ffmpeg.get_ffmpeg_exe()
ANIMATED = ("grafik", "reveal")


def media_duration(path: Path) -> float:
    err = subprocess.run([FF, "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else 0.0


def _scene_seconds(draft: Draft, audio: list[Path | None]) -> list[float]:
    target = config()["uretim"]["video_suresi_sn"]
    durs = []
    for i, (s, a) in enumerate(zip(draft.slaytlar, audio)):
        if a:
            durs.append(media_duration(a) + 0.45)          # ses + nefes payı
        else:
            words = len((s.baslik + " " + s.metin).split())
            base = 7.5 if s.tur in ANIMATED else max(3.0, min(8.0, words / 2.4))
            durs.append(3.0 if i == 0 else base)
    if not any(audio):  # sessizse hedef süreye ölçekle
        k = target / sum(durs)
        durs = [max(2.4, d * k) for d in durs]
    return durs


def frame_plan(seconds: list[float]) -> list[int]:
    """Birikimli yuvarlama: sahne sınırları kareye oturur, toplamda kayma birikmez."""
    frames, cum, prev = [], 0.0, 0
    for d in seconds:
        cum += d
        end = round(cum * FPS)
        frames.append(max(1, end - prev))
        prev += frames[-1]
    return frames


def _build_audio(audio: list[Path | None], frames: list[int], out: Path) -> Path | None:
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
    if music:
        n = len(audio)
        args += ["-stream_loop", "-1", "-i", str(music[sum(frames) % len(music)])]
        filters.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,volume={0.10 if any(audio) else 0.35},"
                       f"atrim=0:{total:.6f},afade=t=out:st={max(total - 1.5, 0):.3f}:d=1.5[bg]")
        filters.append(f"{final}[bg]amix=inputs=2:duration=first:normalize=0,atrim=0:{total:.6f}[mix]")
        final = "[mix]"
    args += ["-filter_complex", ";".join(filters), "-map", final, "-c:a", "pcm_s16le", str(out)]
    subprocess.run(args, check=True, capture_output=True)
    return out


def render(draft: Draft, sheet: DataSheet, post_id: str, series_no: int = 0) -> Path:
    folder = MEDIA_GENERATED / post_id
    folder.mkdir(parents=True, exist_ok=True)
    W, H = config()["gorsel"]["video_boyut"]
    c = Canvas((W, H), series_no)
    accent = config()["gorsel"]["vurgu"]

    audio = [voice.synthesize(s.seslendirme, folder / f"ses{i + 1}.mp3") for i, s in enumerate(draft.slaytlar)]
    import os
    prov = ("ElevenLabs" if os.environ.get("ELEVENLABS_API_KEY") else
            f"Edge ({config().get('ses', {}).get('edge_ses', 'tr-TR-AhmetNeural')})")
    log(AGENT, "Seslendirme: " + (prov if any(audio) else "yok (ekranda yazı)"))
    seconds = _scene_seconds(draft, audio)
    frames = frame_plan(seconds)
    total_frames = sum(frames)
    voice_durs = [round(media_duration(a), 3) if a else 0.0 for a in audio]
    track = _build_audio(audio, frames, folder / "ses.wav")

    out = folder / "video.mp4"
    cmd = [FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-"]
    cmd += ["-i", str(track)] if track else ["-f", "lavfi", "-t", f"{total_frames / FPS:.6f}",
                                             "-i", "anullsrc=r=48000:cl=stereo"]
    cmd += ["-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
            "-t", f"{total_frames / FPS:.6f}", "-movflags", "+faststart", str(out)]
    errlog = folder / "ffmpeg.log"
    errf = open(errlog, "wb")  # stderr'i dosyaya yaz: boru dolup kilitlenmesin
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=errf)

    frame_no = 0
    n = len(draft.slaytlar)
    for i, (s, nf) in enumerate(zip(draft.slaytlar, frames)):
        box = card_for(c, s, sheet, i, n)
        static = None if s.tur in ANIMATED else render_slide(c, s, sheet, i, n, card_box=box)
        for f in range(nf):
            t = f / FPS
            img = render_slide(c, s, sheet, i, n, t=min(1.0, t / 1.8), card_box=box) if static is None else static
            if t < 0.25 and i > 0:  # kısa giriş yakınlaşması
                z = 1.04 - 0.16 * t
                zw, zh = int(W / z), int(H / z)
                img = img.crop(((W - zw) // 2, (H - zh) // 2, (W + zw) // 2, (H + zh) // 2)).resize((W, H))
            else:
                img = img.copy()
            ImageDraw.Draw(img).rectangle([0, 0, int(W * frame_no / max(total_frames, 1)), 10], fill=accent)
            proc.stdin.write(img.tobytes())
            frame_no += 1
    proc.stdin.close()
    code = proc.wait()
    errf.close()
    err = errlog.read_text(errors="ignore")
    errlog.unlink(missing_ok=True)
    if code != 0:
        raise RuntimeError(f"ffmpeg hatası: {err[-800:]}")
    for a in audio:
        if a:
            a.unlink(missing_ok=True)
    (folder / "ses.wav").unlink(missing_ok=True)
    timing = {"fps": FPS, "sahne_kareleri": frames, "seslendirme_sn": voice_durs,
              "toplam_sn": round(total_frames / FPS, 3), "turler": [s.tur for s in draft.slaytlar]}
    (folder / "timing.json").write_text(json.dumps(timing, ensure_ascii=False), encoding="utf-8")
    log(AGENT, f"Video hazır: {out.name} ({total_frames / FPS:.1f} sn, {out.stat().st_size / 1e6:.1f} MB)")
    return out
