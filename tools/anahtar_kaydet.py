"""GEMINI_API_KEY'i yerel .env dosyasına kaydeder (gizli giriş; ekrana yazılmaz, git'e gitmez)."""
from getpass import getpass
from pathlib import Path

env = Path(__file__).resolve().parent.parent / ".env"
key = getpass("GEMINI_API_KEY (yapıştır, görünmez) ve Enter: ").strip()
if not key:
    raise SystemExit("Boş anahtar, kaydedilmedi.")
lines = [l for l in (env.read_text(encoding="utf-8").splitlines() if env.exists() else [])
         if not l.startswith("GEMINI_API_KEY=")]
env.write_text("\n".join([*lines, f"GEMINI_API_KEY={key}"]) + "\n", encoding="utf-8")
print(f"Kaydedildi: {env.name} ({len(key)} karakter). Bu pencereyi kapatabilirsin.")
