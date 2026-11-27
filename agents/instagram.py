"""Resmi Instagram Graph API istemcisi (Facebook Login ile, Business/Creator hesap).

Gerekli ortam değişkenleri (GitHub Secrets):
  IG_ACCESS_TOKEN  Süresiz sistem kullanıcısı tokeni (zorunlu)
  IG_USER_ID       (isteğe bağlı) boşsa token'dan otomatik bulunur
  FB_PAGE_ID       (isteğe bağlı) boşsa token'dan otomatik bulunur
  GRAPH_API_VERSION (isteğe bağlı) ör. v25.0
"""
from __future__ import annotations

import os
import time
from typing import Any

import requests

from .common import dry_run, log


class InstagramError(RuntimeError):
    pass


def _ver() -> str:
    return os.environ.get("GRAPH_API_VERSION") or "v25.0"


def _base() -> str:
    return f"https://graph.facebook.com/{_ver()}"


def configured() -> bool:
    return bool(os.environ.get("IG_ACCESS_TOKEN"))


_ids: dict = {}


def _discover() -> dict:
    """Token'ın eriştiği Facebook sayfasını ve ona bağlı Instagram hesabını bulur."""
    if not _ids:
        pages = _req("GET", "me/accounts", fields="id,name,instagram_business_account{id,username}").get("data", [])
        for p in pages:
            iga = p.get("instagram_business_account")
            if iga:
                _ids.update(page=p["id"], ig=iga["id"], username=iga.get("username"))
                log("instagram", f"Hesap bulundu: @{iga.get('username')} (sayfa: {p.get('name')})")
                break
        else:
            raise InstagramError("Token'a bağlı, Instagram hesabı olan bir Facebook sayfası bulunamadı")
    return _ids


def _uid() -> str:
    return os.environ.get("IG_USER_ID") or _discover()["ig"]


def _page_id() -> str:
    return os.environ.get("FB_PAGE_ID") or _discover()["page"]


def _token() -> str:
    t = os.environ.get("IG_ACCESS_TOKEN")
    if not t:
        raise InstagramError("IG_ACCESS_TOKEN tanımlı değil")
    return t


def _req(method: str, path: str, **params: Any) -> dict:
    params["access_token"] = _token()
    url = f"{_base()}/{path.lstrip('/')}"
    for attempt in range(3):
        r = requests.request(method, url, params=params if method == "GET" else None,
                             data=params if method != "GET" else None, timeout=60)
        if r.status_code < 500:
            break
        time.sleep(5 * (attempt + 1))
    data = r.json() if r.content else {}
    if r.status_code >= 400 or "error" in data:
        err = data.get("error", {})
        raise InstagramError(f"{method} {path}: {err.get('message', r.text)} (kod {err.get('code')})")
    return data


# ---------------------------------------------------------------- Araştırma

def business_discovery(username: str, media_limit: int = 25) -> dict:
    """Başka bir Business/Creator hesabın herkese açık verilerini getirir."""
    fields = (
        f"business_discovery.username({username})"
        "{username,name,biography,followers_count,media_count,"
        f"media.limit({media_limit})"
        "{caption,like_count,comments_count,media_type,media_product_type,permalink,timestamp}}"
    )
    return _req("GET", _uid(), fields=fields)["business_discovery"]


def hashtag_top_media(tag: str) -> list[dict]:
    hid = _req("GET", "ig_hashtag_search", user_id=_uid(), q=tag)["data"][0]["id"]
    res = _req("GET", f"{hid}/top_media", user_id=_uid(),
               fields="caption,like_count,comments_count,media_type,permalink,timestamp")
    return res.get("data", [])


# ---------------------------------------------------------------- Yayın

def _wait_container(cid: str, timeout: int = 600) -> None:
    start = time.time()
    while time.time() - start < timeout:
        st = _req("GET", cid, fields="status_code").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise InstagramError(f"Medya hazırlanamadı: {st}")
        time.sleep(5)
    raise InstagramError("Medya hazırlama zaman aşımı")


def publish(image_urls: list[str], caption: str) -> str:
    """Tek görsel ya da carousel (2-10 görsel) paylaşır, yayınlanan medya ID'sini döndürür."""
    if dry_run():
        log("instagram", f"[DRY_RUN] {len(image_urls)} görselli gönderi paylaşılacaktı")
        return "dry-run"
    if len(image_urls) == 1:
        cid = _req("POST", f"{_uid()}/media", image_url=image_urls[0], caption=caption)["id"]
    else:
        children = []
        for url in image_urls[:10]:
            child = _req("POST", f"{_uid()}/media", image_url=url, is_carousel_item="true")["id"]
            _wait_container(child)
            children.append(child)
        cid = _req("POST", f"{_uid()}/media", media_type="CAROUSEL",
                   children=",".join(children), caption=caption)["id"]
    _wait_container(cid)
    return _req("POST", f"{_uid()}/media_publish", creation_id=cid)["id"]


def publish_reel(video_url: str, caption: str, cover_url: str | None = None) -> str:
    """Dikey videoyu Reels olarak paylaşır (akışta da görünür)."""
    if dry_run():
        log("instagram", "[DRY_RUN] Reels paylaşılacaktı")
        return "dry-run"
    params = dict(media_type="REELS", video_url=video_url, caption=caption, share_to_feed="true")
    if cover_url:
        params["cover_url"] = cover_url
    cid = _req("POST", f"{_uid()}/media", **params)["id"]
    _wait_container(cid, timeout=900)
    return _req("POST", f"{_uid()}/media_publish", creation_id=cid)["id"]


def permalink(media_id: str) -> str:
    try:
        return _req("GET", media_id, fields="permalink").get("permalink", "")
    except InstagramError:
        return ""


def pin_comment(media_id: str, text: str) -> None:
    """İlk yorumu (tartışma sorusu) hesabın kendisi yazar."""
    if dry_run():
        log("instagram", f"[DRY_RUN] ilk yorum: {text[:60]}")
        return
    try:
        _req("POST", f"{media_id}/comments", message=text)
    except InstagramError as e:
        log("instagram", f"İlk yorum yazılamadı: {e}")


# ---------------------------------------------------------------- Topluluk

def recent_media(limit: int = 10) -> list[dict]:
    return _req("GET", f"{_uid()}/media", limit=limit,
                fields="id,caption,timestamp,permalink,media_type").get("data", [])


def comments(media_id: str) -> list[dict]:
    return _req("GET", f"{media_id}/comments", limit=50,
                fields="id,text,username,timestamp,replies{id,username,text}").get("data", [])


def reply_comment(comment_id: str, message: str) -> None:
    if dry_run():
        log("instagram", f"[DRY_RUN] yoruma yanıt: {message[:60]}")
        return
    _req("POST", f"{comment_id}/replies", message=message)


def conversations(limit: int = 20) -> list[dict]:
    return _req("GET", f"{_page_id()}/conversations", platform="instagram", limit=limit,
                fields="id,updated_time,messages.limit(5){id,message,from,created_time}").get("data", [])


def send_dm(recipient_id: str, text: str) -> None:
    if dry_run():
        log("instagram", f"[DRY_RUN] DM: {text[:60]}")
        return
    import json
    _req("POST", f"{_page_id()}/messages",
         recipient=json.dumps({"id": recipient_id}), message=json.dumps({"text": text}),
         messaging_type="RESPONSE")


# ---------------------------------------------------------------- Analiz

def account_info() -> dict:
    return _req("GET", _uid(), fields="username,followers_count,follows_count,media_count")


def media_insights(media_id: str) -> dict:
    """Gönderi metrikleri. Meta metrik adlarını zaman zaman değiştirir; hatada boş döner."""
    try:
        res = _req("GET", f"{media_id}/insights", metric="reach,likes,comments,saved,shares,total_interactions")
        return {m["name"]: m["values"][0]["value"] for m in res.get("data", [])}
    except InstagramError as e:
        log("instagram", f"Metrik alınamadı ({media_id}): {e}")
        return {}
