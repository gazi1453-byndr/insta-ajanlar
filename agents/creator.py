"""4) İÇERİK ÜRETİCİ AJAN
Seçilen fikir ve hook'tan gönderinin tamamını yazar: carousel slaytları,
açıklama (caption), hashtag'ler, CTA ve erişilebilirlik metni. Kullanıcının
koyduğu bir görsel varsa onu görerek açıklama yazar. Müdür geri bildirim
verirse taslağı revize eder.
"""
from __future__ import annotations

import base64
from pathlib import Path

from pydantic import BaseModel, Field

from .common import brand_brief, config, learnings
from .llm import ask
from .strategist import Idea

AGENT = "İçerik Üretici"


class Slide(BaseModel):
    baslik: str = Field(description="Slaytın büyük yazısı, en fazla 8 kelime")
    metin: str = Field(description="Slaytın küçük açıklama yazısı, en fazla 30 kelime; boş olabilir")


class Draft(BaseModel):
    hook: str
    slaytlar: list[Slide] = Field(description="Carousel için slaytlar; ilk slayt hook, son slayt CTA. Tek görselde 1 slayt.")
    caption: str = Field(description="Instagram açıklaması: ilk satır güçlü, kısa paragraflar, sonda soru/CTA")
    hashtagler: list[str] = Field(description="3-5 alakalı hashtag, # işaretsiz")
    alt_text: str = Field(description="Görme engelliler için görsel açıklaması")
    reel_senaryosu: str = Field(description="Format reel ise saniye saniye çekim senaryosu, değilse boş")


def _image_block(path: Path) -> dict:
    media = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    return {"type": "image", "source": {"type": "base64", "media_type": media[path.suffix.lower()],
                                        "data": base64.standard_b64encode(path.read_bytes()).decode()}}


def run(idea: Idea, hook: str, user_image: Path | None = None,
        previous: Draft | None = None, feedback: str | None = None) -> Draft:
    n = config()["uretim"]["carousel_slayt_sayisi"]
    task = (
        f"## Fikir\n{idea.model_dump_json()}\n\n## Seçilen hook\n{hook}\n\n"
        f"## Öğrenilenler\n{learnings()}\n\n"
    )
    if idea.format == "carousel":
        task += f"{n} slaytlık bir carousel yaz. Her slayt tek bir fikir taşısın, okuyan bir sonrakine geçmek istesin.\n"
    elif idea.format == "tek_gorsel":
        task += "Tek görsellik gönderi yaz (1 slayt). Değer açıklamada (caption) verilsin.\n"
    else:
        task += ("Reel senaryosu yaz (15-30 sn, ilk 2 saniyede hook). Ayrıca kapak görseli için 1 slayt yaz.\n")
    if user_image:
        task += "Kullanıcının hazırladığı görsel ektedir. Açıklamayı ve slayt metnini bu görsele uygun yaz.\n"
    if previous and feedback:
        task += (f"\n## Önceki taslak\n{previous.model_dump_json()}\n\n"
                 f"## Müdürün geri bildirimi (bunları mutlaka düzelt)\n{feedback}\n")

    content: str | list[dict] = task
    if user_image:
        content = [_image_block(user_image), {"type": "text", "text": task}]

    return ask(
        AGENT,
        system=(
            "Sen kaydedilen ve paylaşılan Instagram içerikleri yazan bir içerik üreticisisin. "
            "Somut, uygulanabilir, kısa cümleler kurarsın. Hook'un verdiği sözü içerikte tutarsın. "
            "Uydurma istatistik kullanmazsın; emin olmadığın rakamı yazmazsın.\n\n" + brand_brief()
        ),
        content=content,
        schema=Draft,
    )
