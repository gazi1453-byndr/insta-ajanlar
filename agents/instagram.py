"""Resmi Instagram Graph API istemcisi (Facebook Login ile, Business/Creator hesap).

Gerekli ortam değişkenleri (GitHub Secrets):
  IG_USER_ID       Instagram profesyonel hesabının ID'si
  IG_ACCESS_TOKEN  Uzun ömürlü erişim tokeni
  FB_PAGE_ID       (sadece DM için) bağlı Facebook sayfasının ID'si
  GRAPH_API_VERSION (isteğe bağlı) ör. v23.0
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
    return os.environ.get("GRAPH_API_VERSION", "v23.0")


def _base() -> str:
    return f"https://graph.facebook.com/{_ver()}"


def configured() -> bool:
    return bool(os.environ.get("IG_USER_ID") and os.environ.get("IG_ACCESS_TOKEN"))


def _uid() -> str:
    uid = os.environ.get("IG_USER_ID")
    if not uid:
        raise InstagramError("IG_USER_ID tanımlı değil")
    return uid


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

def _wait_container(cid: str, timeout: int = 300) -> None:
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
    page = os.environ.get("FB_PAGE_ID")
    if not page:
        raise InstagramError("DM için FB_PAGE_ID gerekli")
    return _req("GET", f"{page}/conversations", platform="instagram", limit=limit,
                fields="id,updated_time,messages.limit(5){id,message,from,created_time}").get("data", [])


def send_dm(recipient_id: str, text: str) -> None:
    if dry_run():
        log("instagram", f"[DRY_RUN] DM: {text[:60]}")
        return
    import json
    _req("POST", f"{os.environ['FB_PAGE_ID']}/messages",
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
