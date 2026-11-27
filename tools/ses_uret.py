"""Telifsiz arka plan müziği + geçiş efektlerini SIFIRDAN üretir (sentez; lisans derdi yok).
  assets/music/finans_ritim.mp3  — 110 BPM, La minör (Am–F–C–G), kick/clap/hat + bas + pad + arp, ~70 sn
  assets/sfx/whoosh.wav          — sahne geçişi
  assets/sfx/pop.wav             — rakam 'damga' anı
Kullanım: python tools/ses_uret.py   (numpy gerekir; yalnızca bir kez çalıştırılır)
"""
from __future__ import annotations

import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 48000
ROOT = Path(__file__).resolve().parent.parent
rng = np.random.default_rng(7)


def note(n: int) -> float:  # MIDI → Hz
    return 440.0 * 2 ** ((n - 69) / 12)


def env(n: int, a: float, d: float) -> np.ndarray:
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)


def lowpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / np.sqrt(1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, len(x))


def highpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    return x - lowpass(x, cutoff)


def put(buf: np.ndarray, sig: np.ndarray, at: float, gain: float = 1.0) -> None:
    i = int(at * SR)
    j = min(len(buf), i + len(sig))
    if i < len(buf):
        buf[i:j] += sig[: j - i] * gain


def kick() -> np.ndarray:
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    freq = 45 + 75 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 9)


def clap() -> np.ndarray:
    n = int(0.18 * SR)
    x = highpass(rng.standard_normal(n), 900)
    return lowpass(x, 6000) * env(n, 0.002, 0.05) * 0.6


def hat() -> np.ndarray:
    n = int(0.06 * SR)
    return highpass(rng.standard_normal(n), 7000) * env(n, 0.001, 0.012) * 0.35


def pluck(freq: float, dur: float, bright: float = 2500) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    tri = 2 * np.abs(2 * ((t * freq) % 1) - 1) - 1
    return lowpass(tri, bright) * env(n, 0.003, dur / 4)


def bass(freq: float, dur: float) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    saw = 2 * ((t * freq) % 1) - 1
    s = 0.7 * np.sin(2 * np.pi * freq * t) + 0.3 * lowpass(saw, 400)
    return s * env(n, 0.005, dur / 2.2)


def pad(freqs: list[float], dur: float) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * t * d) for f in freqs for d in (0.997, 1.003))
    a = np.minimum(1, t / 0.6) * np.minimum(1, (dur - t) / 0.4)
    return lowpass(s, 1800) * a / (2 * len(freqs))


def music(seconds: float = 70.0) -> np.ndarray:
    bpm = 110
    beat = 60 / bpm
    bar = 4 * beat
    chords = [(57, [69, 72, 76]), (53, [65, 69, 72]), (48, [64, 67, 72]), (55, [67, 71, 74])]  # Am F C G
    buf = np.zeros(int(seconds * SR) + SR)
    nbars = int(seconds / bar) + 1
    for b in range(nbars):
        t0 = b * bar
        root, tones = chords[b % 4]
        put(buf, pad([note(x) for x in tones], bar), t0, 0.22)
        for k in range(8):  # bas: 8'lik nabız
            put(buf, bass(note(root - 12), beat / 2 * 0.95), t0 + k * beat / 2, 0.42 if k % 2 == 0 else 0.3)
        for k in range(4):
            put(buf, kick(), t0 + k * beat, 0.75 if k in (0, 2) else 0.0)
            if k in (1, 3):
                put(buf, clap(), t0 + k * beat, 0.32)
        for k in range(8):
            put(buf, hat(), t0 + k * beat / 2, 0.5 if k % 2 else 0.28)
        if b >= 2:  # arp: 16'lık akorlar
            pat = [0, 1, 2, 1, 0, 2, 1, 2]
            for k in range(16):
                put(buf, pluck(note(tones[pat[k % 8]] + 12), beat / 4 * 0.9), t0 + k * beat / 4, 0.12)
    buf = buf[: int(seconds * SR)]
    fade = int(1.5 * SR)
    buf[-fade:] *= np.linspace(1, 0, fade)
    return buf / np.max(np.abs(buf)) * 0.89


def whoosh() -> np.ndarray:
    n = int(0.42 * SR)
    t = np.linspace(0, 1, n)
    x = rng.standard_normal(n)
    # süpüren bant: kısa bloklarda kesim frekansı 400 → 5000 → 600 Hz
    out = np.zeros(n)
    blk = 1024
    for i in range(0, n, blk):
        c = 400 + 4600 * np.sin(np.pi * min(1.0, i / n * 1.1)) ** 2
        seg = x[max(0, i - blk): i + blk]
        y = highpass(lowpass(seg, c * 1.4), c * 0.6)
        out[i:i + blk] = y[-min(blk, n - i):] if i else y[:min(blk, n)]
    a = np.sin(np.pi * t) ** 1.6
    return out * a / np.max(np.abs(out * a)) * 0.8


def pop() -> np.ndarray:
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    freq = 600 + 700 * np.exp(-t * 60)
    s = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 38)
    return s / np.max(np.abs(s)) * 0.8


def horn() -> np.ndarray:
    """Araba kornası: iki tonlu (≈415 + 523 Hz), doygun, 'bip-biiip'."""
    def tone(dur):
        n = int(dur * SR)
        t = np.arange(n) / SR
        s = sum(np.sign(np.sin(2 * np.pi * f * t)) * a for f, a in ((415, 1.0), (523, 0.8), (830, 0.25)))
        s = np.tanh(lowpass(s, 3200) * 1.6)
        a = np.minimum(1, t / 0.008) * np.minimum(1, (dur - t) / 0.02)
        return s * a
    out = np.concatenate([tone(0.13), np.zeros(int(0.07 * SR)), tone(0.42)])
    return out / np.max(np.abs(out)) * 0.8


def kaching() -> np.ndarray:
    """Yazar kasa: mekanik 'ka' + parlak 'ching' zil."""
    n = int(1.0 * SR)
    t = np.arange(n) / SR
    click = np.zeros(n)
    k = int(0.05 * SR)
    click[:k] = lowpass(rng.standard_normal(k), 2500) * np.exp(-np.arange(k) / SR * 90) * 0.9
    d = int(0.09 * SR)  # zil 'ka'dan 90 ms sonra
    tb = t[: n - d]
    bell = sum(a * np.sin(2 * np.pi * f * tb) * np.exp(-tb * dec)
               for f, a, dec in ((2093, 1.0, 4.5), (2637, 0.7, 5.5), (3136, 0.6, 6.5), (4186, 0.35, 9), (5274, 0.2, 12)))
    out = click.copy()
    out[d:] += bell * 0.55
    return out / np.max(np.abs(out)) * 0.85


def coin() -> np.ndarray:
    """Kısa metalik 'çınk' (madeni para)."""
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    s = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * dec)
            for f, a, dec in ((2960, 1.0, 9), (4150, 0.7, 12), (5620, 0.45, 16), (7080, 0.3, 22)))
    s[: int(0.003 * SR)] += rng.standard_normal(int(0.003 * SR)) * 0.4
    return s / np.max(np.abs(s)) * 0.8


def impact() -> np.ndarray:
    """Büyük rakam 'damga' darbesi: alçak bum + kısa gövde."""
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    freq = 38 + 90 * np.exp(-t * 14)
    boom = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 4.5)
    body = lowpass(rng.standard_normal(n), 900) * np.exp(-t * 30) * 0.5
    s = np.tanh((boom + body) * 1.4)
    return s / np.max(np.abs(s)) * 0.9


def subbass() -> np.ndarray:
    """Açılış kancası: derin sinematik sub-bass vuruşu (60→32 Hz kayan sinüs + kısa tık ataklı)."""
    n = int(1.3 * SR)
    t = np.arange(n) / SR
    freq = 32 + 30 * np.exp(-t * 6)
    sub = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 2.6) * np.minimum(1, t / 0.004)
    click = lowpass(rng.standard_normal(n), 2200) * np.exp(-t * 90) * 0.35
    s = np.tanh((sub + click) * 1.6)
    return s / np.max(np.abs(s)) * 0.95


def tick() -> np.ndarray:
    """Kırmızı maliyet kartı: kısa, keskin dijital uyarı tıkı (punch)."""
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    tone = np.sign(np.sin(2 * np.pi * 1850 * t)) * 0.35 + np.sin(2 * np.pi * 3700 * t) * 0.3
    punch = np.sin(2 * np.pi * (140 * np.exp(-t * 40) + 60) * t) * np.exp(-t * 45)
    s = lowpass(tone, 6000) * np.exp(-t * 55) + punch * 0.8
    return s / np.max(np.abs(s)) * 0.8


def chime() -> np.ndarray:
    """Yeşil taksi sahnesi: temiz, pozitif onay çınlaması (majör üçlü, çan zarfı)."""
    n = int(1.1 * SR)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for f0, start, a in ((1318.5, 0.0, 1.0), (1975.5, 0.07, 0.8)):  # E6 → B6
        k = t >= start
        tt = t[k] - start
        s[k] += a * (np.sin(2 * np.pi * f0 * tt) + 0.25 * np.sin(2 * np.pi * f0 * 2.76 * tt) * np.exp(-tt * 9)) * np.exp(-tt * 4.2)
    s *= np.minimum(1, t / 0.003)
    return s / np.max(np.abs(s)) * 0.7


def thud() -> np.ndarray:
    """Final özet kartı: hafif, tok kart oturma sesi."""
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * (95 * np.exp(-t * 9) + 55) * t) * np.exp(-t * 16)
    slap = lowpass(rng.standard_normal(n), 1400) * np.exp(-t * 70) * 0.45
    s = np.tanh((body + slap) * 1.3)
    return s / np.max(np.abs(s)) * 0.85


NEW_SFX = (("subbass", subbass), ("tik", tick), ("onay", chime), ("kart", thud))


def save_wav(x: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    st = np.repeat(pcm[:, None], 2, axis=1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(st.tobytes())


if __name__ == "__main__":
    import imageio_ffmpeg
    import sys
    for name, fn in (("korna", horn), ("kasa", kaching), ("cink", coin), ("darbe", impact), *NEW_SFX):
        save_wav(fn(), ROOT / "assets" / "sfx" / f"{name}.wav")
    if "--efekt" in sys.argv:  # sadece efektleri üret
        print("ok efektler")
        raise SystemExit
    tmp = ROOT / "assets" / "music" / "_tmp.wav"
    save_wav(music(), tmp)
    mp3 = ROOT / "assets" / "music" / "finans_ritim.mp3"
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(tmp),
                    "-c:a", "libmp3lame", "-b:a", "160k", str(mp3)], check=True)
    tmp.unlink()
    save_wav(whoosh(), ROOT / "assets" / "sfx" / "whoosh.wav")
    save_wav(pop(), ROOT / "assets" / "sfx" / "pop.wav")
    print("ok", mp3.name, mp3.stat().st_size // 1024, "KB")
