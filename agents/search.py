"""WEB ARAMA (yapay zeka modelinden bağımsız)
Tavily arama API'si ile güncel sayfaları bulur ve metinlerini getirir.
Ücretsiz: ayda 1000 arama, kart gerekmez → https://app.tavily.com (TAVILY_API_KEY)

Neden ayrı? Ücretsiz Gemini katmanında Google arama kotası çok düşük/sıfır.
Arama burada yapılır, bulunan sayfa metinleri modele verilir; model sadece bu
kaynaklardan yazar → kaynak linkleri her zaman gerçektir.
"""
from __future__ import annotations

import os

import requests

from .common import log

URL = "https://api.tavily.com/search"


class SearchError(RuntimeError):
    pass


def enabled() -> bool:
    return bool(os.environ.get("TAVILY_API_KEY"))


def search(query: str, max_results: int = 5, days: int | None = None,
           domains: list[str] | None = None) -> list[dict]:
    """[{title, url, content}] döndürür.
    days: sadece son N günün haberleri (gündem). domains: sadece bu sitelerde ara (ör. reddit.com)."""
    key = os.environ["TAVILY_API_KEY"]
    body: dict = {"query": query, "max_results": max_results, "search_depth": "basic",
                  "include_raw_content": "text"}
    if days:
        body.update(topic="news", days=days)
    else:
        body["time_range"] = "week" if domains else "month"   # sosyal medya: son hafta; fiyatlar: son ay
    if domains:
        body["include_domains"] = domains
    r = requests.post(URL, headers={"Authorization": f"Bearer {key}"}, json=body, timeout=60)
    if r.status_code in (400, 401, 422):  # sade gövdeyle (eski API biçimi) bir kez daha dene
        simple = {"api_key": key, "query": query, "max_results": max_results, "include_raw_content": True}
        if days:
            simple.update(topic="news", days=days)
        if domains:
            simple["include_domains"] = domains
        r = requests.post(URL, json=simple, timeout=60)
    if r.status_code != 200:
        raise SearchError(f"Tavily {r.status_code}: {r.text[:200]}")
    out = []
    for it in r.json().get("results", []):
        text = (it.get("raw_content") or it.get("content") or "").strip()
        out.append({"title": it.get("title", ""), "url": it.get("url", ""), "content": text[:3500]})
    return out


def gather(queries: list[str], per_query: int = 4, days: int | None = None, max_chars: int = 26000) -> list[dict]:
    """Birden çok sorguyu arar, aynı linkleri tekilleştirir, toplam metni sınırlar."""
    seen, results, total = set(), [], 0
    for q in queries:
        try:
            for it in search(q, per_query, days):
                if it["url"] in seen or not it["content"]:
                    continue
                seen.add(it["url"])
                room = max_chars - total
                if room < 400:
                    return results
                it["content"] = it["content"][:min(3500, room)]
                total += len(it["content"])
                results.append(it)
        except (SearchError, requests.RequestException) as e:
            log("arama", f"'{q}' aranamadı: {e}")
    log("arama", f"{len(queries)} sorgu → {len(results)} kaynak sayfa")
    return results
