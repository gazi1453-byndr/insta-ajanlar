"""VİDEO KURGUCU
Sahneleri 1080x1920, 30 fps dikey Reels videosuna çevirir:
- Grafik sahnelerinde çubuklar büyür, rakamlar sayar (gerçek animasyon)
- Sahne geçişlerinde kısa yakınlaşma, üstte ilerleme çubuğu (izlenme süresini artırır)
- Seslendirme varsa sahne süresi sese göre ayarlanır; yoksa okuma süresine göre
- assets/music/ içine telifsiz bir mp3 koyarsan düşük seste arka plan müziği eklenir
ffmpeg, imageio-ffmpeg paketiyle birlikte gelir (ayrı kurulum gerekmez).
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw

from . import voice
from .common import MEDIA_GENERATED, ROOT, config, log
from .creator import Draft
from .data_researcher import DataSheet
from .designer import Canvas, render_slide

AGENT = "Video Kurgucu"
FPS = 30
FF = imageio_ffmpeg.get_ffmpeg_exe()


def _duration(path: Path) -> float:
    err = subprocess.run([FF, "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else 0.0


def _scene_durations(draft: Draft, audio: list[Path | None]) -> list[float]:
    target = config()["uretim"]["video_suresi_sn"]
    durs = []
    for i, (s, a) in enumerate(zip(draft.slaytlar, audio)):
        if a:
            durs.append(_duration(a) + 0.35)
        else:
            words = len((s.baslik + " " + s.metin).split())
            base = 7.0 if s.tur == "grafik" else max(2.6, min(7.5, words / 2.6))
            durs.append(2.8 if i == 0 else base)
    if not any(audio):  # sessizse hedef süreye ölçekle
        k = target / sum(durs)
        durs = [max(2.2, d * k) for d in durs]
    return durs


def _build_audio(audio: list[Path | None], durs: list[float], out: Path) -> Path | None:
    music = sorted((ROOT / "assets" / "music").glob("*.mp3")) if (ROOT / "assets" / "music").exists() else []
    if not any(audio) and not music:
        return None
    total = sum(durs)
    args, filters, labels = [FF, "-y"], [], []
    for i, (a, d) in enumerate(zip(audio, durs)):
        if a:
            args += ["-i", str(a)]
        else:
            args += ["-f", "lavfi", "-t", f"{d:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
        filters.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,apad=whole_dur={d:.3f},atrim=0:{d:.3f}[s{i}]")
        labels.append(f"[s{i}]")
    filters.append("".join(labels) + f"concat=n={len(labels)}:v=0:a=1[voice]")
    final = "[voice]"
    if music:
        n = len(audio)
        args += ["-stream_loop", "-1", "-i", str(music[hash(out.name) % len(music)])]
        filters.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,volume={0.10 if any(audio) else 0.35},"
                       f"atrim=0:{total:.3f},afade=t=out:st={max(total - 1.5, 0):.3f}:d=1.5[bg]")
        filters.append("[voice][bg]amix=inputs=2:duration=first:normalize=0[mix]")
        final = "[mix]"
    args += ["-filter_complex", ";".join(filters), "-map", final, "-c:a", "aac", "-b:a", "160k", str(out)]
    subprocess.run(args, check=True, capture_output=True)
    return out


def render(draft: Draft, sheet: DataSheet, post_id: str) -> Path:
    folder = MEDIA_GENERATED / post_id
    folder.mkdir(parents=True, exist_ok=True)
    W, H = config()["gorsel"]["video_boyut"]
    c = Canvas((W, H))
    accent = config()["gorsel"]["vurgu"]

    audio = [voice.synthesize(s.seslendirme, folder / f"ses{i + 1}.mp3") for i, s in enumerate(draft.slaytlar)]
    log(AGENT, "Seslendirme: " + ("ElevenLabs" if any(audio) else "yok (ekranda yazı)"))
    durs = _scene_durations(draft, audio)
    total_frames = int(sum(durs) * FPS)
    track = _build_audio(audio, durs, folder / "ses.m4a")

    out = folder / "video.mp4"
    cmd = [FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    cmd += ["-i", str(track)] if track else ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    cmd += ["-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
            "-shortest", "-movflags", "+faststart", str(out)]
    errlog = folder / "ffmpeg.log"
    errf = open(errlog, "wb")  # stderr'i dosyaya yaz: boru dolup kilitlenmesin
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=errf)

    frame_no = 0
    n = len(draft.slaytlar)
    for i, (s, d) in enumerate(zip(draft.slaytlar, durs)):
        nf = int(d * FPS)
        static = None if s.tur == "grafik" else render_slide(c, s, sheet, i, n)
        for f in range(nf):
            t = f / FPS
            img = render_slide(c, s, sheet, i, n, t=min(1.0, t / 1.8)) if static is None else static
            if t < 0.25 and i > 0:  # kısa giriş yakınlaşması
                z = 1.04 - 0.16 * t
                zw, zh = int(W / z), int(H / z)
                img = img.crop(((W - zw) // 2, (H - zh) // 2, (W + zw) // 2, (H + zh) // 2)).resize((W, H))
            else:
                img = img.copy()
            dr = ImageDraw.Draw(img)
            dr.rectangle([0, 0, int(W * frame_no / max(total_frames, 1)), 10], fill=accent)
            proc.stdin.write(img.tobytes())
            frame_no += 1
    proc.stdin.close()
    code = proc.wait()
    errf.close()
    err = errlog.read_text(errors="ignore")
    errlog.unlink(missing_ok=True)
    if code != 0:
        raise RuntimeError(f"ffmpeg hatası: {err[-800:]}")
    (folder / "ses.m4a").unlink(missing_ok=True)
    for a in audio:
        if a:
            a.unlink(missing_ok=True)
    log(AGENT, f"Video hazır: {out.name} ({sum(durs):.1f} sn, {out.stat().st_size / 1e6:.1f} MB)")
    return out
