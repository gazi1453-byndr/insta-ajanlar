"""VİDEO ANALİZ ARACI
Yerel video (mp4/mov/...) ya da link (YouTube, Instagram, TikTok, X ...) alır ve şunları çıkarır:
  1) Ölçümler (ffmpeg, anahtarsız): süre, çözünürlük, fps, ses/görüntü süre farkı, ses seviyesi,
     sessizlikler, sahne kesmeleri → kurgu temposu (kesme/sn, en uzun sabit sahne)
  2) Gemini (ücretsiz GEMINI_API_KEY, .env'den): videoyu sesiyle birlikte izler →
     hook (ilk 3 sn), konuşma dökümü özeti, görsel akış, ses/müzik, tempo, güçlü/zayıf yanlar,
     "Gerçek Maliyet" serisine uyarlama önerisi.
Kullanım:
  python tools/video_analiz.py <dosya|link> [--yerel] [--json]
  --yerel : sadece ffmpeg ölçümleri (anahtar gerekmez)
"""
from __future__ import annotations

import json
import mimetypes
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://generativelanguage.googleapis.com"
MODELS = ["gemini-flash-latest", "gemini-2.5-flash", "gemini-flash-lite-latest", "gemini-2.5-flash-lite"]

PROMPT = """Bu kısa videoyu sesiyle birlikte baştan sona izle ve TÜRKÇE, kısa ve somut bir analiz yaz.
Başlıklar (her biri 1-4 madde, zaman damgalı ver: [0:03]):
1. ÖZET — video ne anlatıyor (1 cümle)
2. HOOK (ilk 3 sn) — ekranda ne var, ne söyleniyor, neden durdurur/durdurmaz; 10 üzerinden puan
3. KONUŞMA — ses tonu, hız, enerji, doğallık (robotik mi?), dolgu cümleleri
4. GÖRSEL AKIŞ — sahne sahne ne değişiyor; ekranda 3 sn'den uzun sabit kalan yerler; boş alanlar
5. SES / MÜZİK / EFEKT — müzik var mı, seviyesi, geçiş efektleri, altyazı
6. TEMPO VE KURGU — kesme sıklığı, geçiş tipi, izleyiciyi tutma tekniği (açık döngü, sayaç, merak)
7. GÜÇLÜ YANLAR / ZAYIF YANLAR
8. UYARLAMA — bu videodan "Gerçek Maliyet" (rakamlı maliyet karşılaştırma) serisine alınabilecek 3 somut teknik
Ölçüm verisi (ffmpeg): {metrics}"""


# ------------------------------------------------------------------ yardımcılar
def _ff() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _key() -> str | None:
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"]
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except Exception:
        env = ROOT / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("GEMINI_API_KEY="):
                    os.environ["GEMINI_API_KEY"] = line.split("=", 1)[1].strip().strip('"\'')
    return os.environ.get("GEMINI_API_KEY")


def is_url(s: str) -> bool:
    return bool(re.match(r"https?://", s.strip()))


def download(url: str) -> Path:
    """yt-dlp ile indir (en fazla 1080p, mp4). Her indirme kendi boş klasörüne gider."""
    import yt_dlp
    out = Path(tempfile.mkdtemp(prefix="video_analiz_"))
    opts = {"outtmpl": str(out / "video.%(ext)s"), "format": "bv*[height<=1080]+ba/b[height<=1080]/b",
            "merge_output_format": "mp4", "ffmpeg_location": _ff(), "quiet": True, "no_warnings": True,
            "noplaylist": True, "max_filesize": 300 * 1024 * 1024}
    with yt_dlp.YoutubeDL(opts) as y:
        info = y.extract_info(url, download=True)
    files = sorted(out.glob("video.*"), key=lambda p: p.stat().st_size, reverse=True)
    if not files:
        raise RuntimeError("İndirme başarısız")
    (out / "info.json").write_text(json.dumps({k: info.get(k) for k in
                                               ("title", "uploader", "duration", "view_count", "like_count",
                                                "comment_count", "upload_date", "webpage_url")},
                                              ensure_ascii=False), encoding="utf-8")
    return files[0]


def _run(args: list[str]) -> str:
    return subprocess.run([_ff(), "-hide_banner", "-nostats", *args], capture_output=True, text=True,
                          encoding="utf-8", errors="ignore").stderr


def _stream_dur(path: Path, sel: str) -> float | None:
    err = _run(["-i", str(path), "-map", sel, "-c", "copy", "-f", "null", "-"])
    t = re.findall(r"time=(\d+):(\d+):([\d.]+)", err)
    if not t:
        return None
    h, m, s = t[-1]
    return int(h) * 3600 + int(m) * 60 + float(s)


def metrics(path: Path) -> dict:
    info = _run(["-i", str(path)])
    m: dict = {"dosya": path.name}
    if d := re.search(r"Duration: (\d+):(\d+):([\d.]+)", info):
        m["sure_sn"] = round(int(d[1]) * 3600 + int(d[2]) * 60 + float(d[3]), 2)
    if v := re.search(r"Video: .*?, (\d{2,5})x(\d{2,5}).*?([\d.]+) fps", info):
        m["cozunurluk"] = f"{v[1]}x{v[2]}"
        m["fps"] = float(v[3])
    m["ses_var"] = "Audio:" in info
    vd, ad = _stream_dur(path, "0:v:0"), _stream_dur(path, "0:a:0") if m["ses_var"] else None
    if vd and ad:
        m["ses_goruntu_farki_ms"] = round((ad - vd) * 1000)
    if m["ses_var"]:
        vol = _run(["-i", str(path), "-vn", "-af", "volumedetect", "-f", "null", "-"])
        if x := re.search(r"mean_volume: (-?[\d.]+)", vol):
            m["ortalama_ses_db"] = float(x[1])
        if x := re.search(r"max_volume: (-?[\d.]+)", vol):
            m["tepe_ses_db"] = float(x[1])
        sil = _run(["-i", str(path), "-vn", "-af", "silencedetect=n=-35dB:d=0.4", "-f", "null", "-"])
        starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", sil)]
        durs = [float(x) for x in re.findall(r"silence_duration: ([\d.]+)", sil)]
        m["sessizlik_sayisi"] = len(starts)
        m["toplam_sessizlik_sn"] = round(sum(durs), 2)
        m["bastaki_sessizlik_sn"] = round(durs[0], 2) if starts and abs(starts[0]) < 0.05 and durs else 0.0
    sc = _run(["-i", str(path), "-an", "-vf", "select='gt(scene,0.25)',showinfo", "-f", "null", "-"])
    cuts = [round(float(x), 2) for x in re.findall(r"pts_time:([\d.]+)", sc)]
    m["sahne_kesmeleri"] = cuts[:60]
    if m.get("sure_sn"):
        edges = [0.0, *cuts, m["sure_sn"]]
        gaps = [round(b - a, 2) for a, b in zip(edges, edges[1:])]
        m["kesme_sayisi"] = len(cuts)
        m["kesme_basina_sn"] = round(m["sure_sn"] / (len(cuts) + 1), 2)
        m["en_uzun_sabit_sahne_sn"] = max(gaps)
    return m


# ------------------------------------------------------------------ Gemini
def _post(url: str, key: str, **kw):
    import requests
    return requests.post(url, headers={"x-goog-api-key": key, **kw.pop("headers", {})}, timeout=600, **kw)


def upload(path: Path, key: str) -> dict:
    import requests
    mime = mimetypes.guess_type(path.name)[0] or "video/mp4"
    size = path.stat().st_size
    r = _post(f"{API}/upload/v1beta/files", key, json={"file": {"display_name": path.name}},
              headers={"X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start",
                       "X-Goog-Upload-Header-Content-Length": str(size),
                       "X-Goog-Upload-Header-Content-Type": mime})
    r.raise_for_status()
    up = r.headers["x-goog-upload-url"]
    with open(path, "rb") as fh:
        r = requests.post(up, data=fh, timeout=900, headers={
            "Content-Length": str(size), "X-Goog-Upload-Offset": "0",
            "X-Goog-Upload-Command": "upload, finalize"})
    r.raise_for_status()
    f = r.json()["file"]
    for _ in range(90):  # video işlenene kadar bekle
        if f.get("state") == "ACTIVE":
            return f
        if f.get("state") == "FAILED":
            raise RuntimeError("Gemini videoyu işleyemedi")
        time.sleep(2)
        f = requests.get(f"{API}/v1beta/{f['name']}", headers={"x-goog-api-key": key}, timeout=60).json()
    raise RuntimeError("Gemini video işleme zaman aşımı")


def gemini(part: dict, key: str, met: dict) -> tuple[str, str]:
    body = {"contents": [{"parts": [part, {"text": PROMPT.format(metrics=json.dumps(met, ensure_ascii=False))}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096}}
    last = ""
    for model in MODELS:
        for attempt in range(2):
            r = _post(f"{API}/v1beta/models/{model}:generateContent", key, json=body)
            if r.status_code == 200:
                cand = r.json().get("candidates") or [{}]
                text = "".join(p.get("text", "") for p in cand[0].get("content", {}).get("parts", []))
                if text.strip():
                    return text.strip(), model
            last = f"{model}: {r.status_code} {r.text[:200]}"
            if r.status_code in (404, 400):
                break
            time.sleep(4 * (attempt + 1))
    raise RuntimeError(f"Gemini yanıt vermedi ({last})")


def analyze(source: str, local_only: bool = False) -> dict:
    src = source.strip().strip('"')
    path = download(src) if is_url(src) else Path(src).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(src)
    met = metrics(path)
    out = {"kaynak": src, "yerel_dosya": str(path), "olcumler": met}
    info = path.parent / "info.json"
    if is_url(src) and info.exists():
        out["platform_bilgisi"] = json.loads(info.read_text(encoding="utf-8"))
    if local_only:
        return out
    key = _key()
    if not key:
        out["analiz"] = "GEMINI_API_KEY bulunamadı (.env). Sadece ölçümler verildi: python tools/anahtar_kaydet.py"
        return out
    f = upload(path, key)
    out["analiz"], out["model"] = gemini({"file_data": {"mime_type": f.get("mimeType", "video/mp4"),
                                                        "file_uri": f["uri"]}}, key, met)
    try:  # yüklenen dosyayı Gemini'den sil
        import requests
        requests.delete(f"{API}/v1beta/{f['name']}", headers={"x-goog-api-key": key}, timeout=30)
    except Exception:
        pass
    return out


def as_text(r: dict) -> str:
    m = r["olcumler"]
    keys = ["sure_sn", "cozunurluk", "fps", "ses_goruntu_farki_ms", "ortalama_ses_db", "tepe_ses_db",
            "bastaki_sessizlik_sn", "toplam_sessizlik_sn", "kesme_sayisi", "kesme_basina_sn", "en_uzun_sabit_sahne_sn"]
    lines = [f"# Video analizi: {r['kaynak']}", "", "## Ölçümler",
             *[f"- {k}: {m[k]}" for k in keys if k in m]]
    if p := r.get("platform_bilgisi"):
        lines += [f"- platform: {p.get('uploader')} · {p.get('view_count')} izlenme · {p.get('like_count')} beğeni"]
    if r.get("analiz"):
        lines += ["", f"## Analiz ({r.get('model', '-')})", r["analiz"]]
    return "\n".join(lines)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(1)
    res = analyze(args[0], local_only="--yerel" in sys.argv)
    print(json.dumps(res, ensure_ascii=False, indent=2) if "--json" in sys.argv else as_text(res))
