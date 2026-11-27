"""VİDEO ANALİZ MCP SUNUCUSU (stdio, yalnızca standart kütüphane)
Claude Code'a 'video_analiz' aracını sunar. .mcp.json içinde tanımlıdır.
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import video_analiz  # noqa: E402

TOOLS = [{
    "name": "video_analiz",
    "description": ("Yerel video dosyasını ya da video linkini (YouTube, Instagram, TikTok, X) analiz eder: "
                    "ses, konuşma, görsel akış, hook (ilk 3 sn), tempo, ölçümler (süre, fps, ses/görüntü kayması, "
                    "sessizlik, sahne kesmeleri). Gemini (ücretsiz) ile çalışır; kısa Türkçe özet döndürür."),
    "inputSchema": {"type": "object", "properties": {
        "kaynak": {"type": "string", "description": "Video dosya yolu ya da URL"},
        "sadece_olcum": {"type": "boolean", "description": "true: Gemini'siz, sadece ffmpeg ölçümleri"}},
        "required": ["kaynak"]},
}]


def send(msg: dict) -> None:
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def handle(req: dict) -> dict | None:
    mid, method, params = req.get("id"), req.get("method"), req.get("params") or {}
    if mid is None:  # bildirim (ör. notifications/initialized): yanıt yok
        return None
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": params.get("protocolVersion", "2025-06-18"),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "video-analiz", "version": "1.0.0"}}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        args = params.get("arguments") or {}
        try:
            res = video_analiz.analyze(args["kaynak"], local_only=bool(args.get("sadece_olcum")))
            return {"jsonrpc": "2.0", "id": mid, "result": {
                "content": [{"type": "text", "text": video_analiz.as_text(res)}], "isError": False}}
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            return {"jsonrpc": "2.0", "id": mid, "result": {
                "content": [{"type": "text", "text": f"Analiz başarısız: {e}"}], "isError": True}}
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Bilinmeyen metot: {method}"}}


def main() -> None:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            out = handle(json.loads(line))
        except Exception as e:
            out = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(e)}}
        if out:
            send(out)


if __name__ == "__main__":
    main()
