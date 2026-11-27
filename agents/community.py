"""8) TOPLULUK YÖNETİCİSİ AJAN
Son gönderilere gelen yorumları (ve açıksa DM'leri) okur; hesabın tonunda
kısa, samimi yanıtlar yazar. Hassas konuları yanıtlamaz, rapora ekler.
"""
from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from . import instagram as ig
from .common import DATA, brand_brief, config, dry_run, log, now, read_json, write_json
from .llm import ask

AGENT = "Topluluk Yöneticisi"
STATE = DATA / "community_state.json"


class Reply(BaseModel):
    id: str = Field(description="Yanıtlanan yorumun ya da konuşmanın ID'si")
    eylem: Literal["yanitla", "atla", "insana_bildir"]
    yanit: str = Field(description="eylem 'yanitla' ise yanıt metni, en fazla 2 cümle; değilse boş")
    neden: str
    istek: str = Field(default="", description="Yorumcu bir şeyin maliyetinin hesaplanmasını istiyorsa kısa konu "
                                               "(ör. 'iPhone 17 Pro 2 yıllık maliyeti'), istemiyorsa boş")


class ReplyBatch(BaseModel):
    yanitlar: list[Reply]


def _decide(items: list[dict], kind: str) -> list[Reply]:
    cfg = config()
    skip = "\n".join(f"- {s}" for s in cfg["topluluk"].get("yanitlanmayacak_konular", []))
    return ask(
        AGENT,
        system=(
            "Sen bu Instagram hesabının topluluk yöneticisisin. Takipçilere hesabın sesiyle, kısa, "
            "sıcak ve yardımcı yanıtlar verirsin. Etkileşimi artırmak için uygun yerde soru sorarsın. "
            "Spam, hakaret ve bot yorumlarını 'atla'. Aşağıdaki konuları 'insana_bildir'.\n"
            "Yorumcu bir şeyin hesaplanmasını istiyorsa (ör. 'X'i de hesaplayın', 'Y kaça mal olur?') istek alanına "
            "kısa konuyu yaz ve sıcak bir yanıt ver: 'Not aldık, yakında hesaplıyoruz!' gibi (tarih verme).\n"
            f"{skip}\nKişisel bilgi isteme, link verme, söz verme.\n\n" + brand_brief()
        ),
        content=f"Şu {kind} için karar ver:\n{json.dumps(items, ensure_ascii=False)}",
        schema=ReplyBatch,
    ).yanitlar


def _save_request(topic: str, user: str) -> None:
    """Takipçi isteklerini biriktirir; aynı konu tekrar istenirse 'sayi' artar (en çok isteneni öne çıkar)."""
    f = DATA / "izleyici_istekleri.json"
    data = read_json(f, {"istekler": []})
    key = topic.lower()
    for r in data["istekler"]:
        if r["konu"].lower() == key or (len(key) > 8 and key[:20] in r["konu"].lower()):
            r["sayi"] = r.get("sayi", 1) + 1
            r.setdefault("isteyenler", []).append(user)
            break
    else:
        data["istekler"].append({"konu": topic, "kullanici": user, "isteyenler": [user], "sayi": 1,
                                 "tarih": now().isoformat(), "kullanildi": False})
    data["istekler"] = data["istekler"][-300:]
    if not dry_run():
        write_json(f, data)


def run() -> dict:
    cfg = config()["topluluk"]
    state = read_json(STATE, {"yanitlanan_yorumlar": [], "yanitlanan_mesajlar": [], "bildirimler": []})
    me = ig.account_info()["username"]
    summary = {"yorum_yaniti": 0, "dm_yaniti": 0, "bildirim": 0}

    if cfg.get("yorum_yaniti"):
        pending = []
        for m in ig.recent_media(8):
            for c in ig.comments(m["id"]):
                replied = any(r.get("username") == me for r in c.get("replies", {}).get("data", []))
                if c.get("username") == me or replied or c["id"] in state["yanitlanan_yorumlar"]:
                    continue
                pending.append({"id": c["id"], "kullanici": c.get("username"), "yorum": c.get("text"),
                                "gonderi": (m.get("caption") or "")[:200]})
        if pending:
            for r in _decide(pending[:25], "yorumlar"):
                if r.eylem == "yanitla" and r.yanit:
                    ig.reply_comment(r.id, r.yanit)
                    summary["yorum_yaniti"] += 1
                elif r.eylem == "insana_bildir":
                    state["bildirimler"].append({"tur": "yorum", "id": r.id, "neden": r.neden, "zaman": now().isoformat()})
                    summary["bildirim"] += 1
                state["yanitlanan_yorumlar"].append(r.id)
                if r.istek.strip():   # İZLEYİCİ SORUSU serisi için isteği kaydet
                    user = next((p["kullanici"] for p in pending if p["id"] == r.id), "") or ""
                    _save_request(r.istek.strip(), user)
                    summary["istek"] = summary.get("istek", 0) + 1

    if cfg.get("dm_yaniti"):
        pending = []
        for conv in ig.conversations():
            msgs = conv.get("messages", {}).get("data", [])
            if not msgs:
                continue
            last = msgs[0]
            if last.get("from", {}).get("username") == me or last["id"] in state["yanitlanan_mesajlar"]:
                continue
            pending.append({"id": last["id"], "gonderen_id": last.get("from", {}).get("id"),
                            "mesaj": last.get("message"),
                            "onceki": [m.get("message") for m in msgs[1:4]]})
        if pending:
            by_id = {p["id"]: p for p in pending}
            for r in _decide(pending[:20], "direkt mesajlar"):
                if r.eylem == "yanitla" and r.yanit and r.id in by_id:
                    ig.send_dm(by_id[r.id]["gonderen_id"], r.yanit)
                    summary["dm_yaniti"] += 1
                elif r.eylem == "insana_bildir":
                    state["bildirimler"].append({"tur": "dm", "id": r.id, "neden": r.neden, "zaman": now().isoformat()})
                    summary["bildirim"] += 1
                state["yanitlanan_mesajlar"].append(r.id)

    state["yanitlanan_yorumlar"] = state["yanitlanan_yorumlar"][-2000:]
    state["yanitlanan_mesajlar"] = state["yanitlanan_mesajlar"][-2000:]
    state["bildirimler"] = state["bildirimler"][-200:]
    if not dry_run():  # deneme çalışmasında "yanıtlandı" diye işaretleme
        write_json(STATE, state)
    log(AGENT, f"Özet: {summary}")
    return summary
