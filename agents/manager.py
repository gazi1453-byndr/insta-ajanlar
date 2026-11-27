"""6) MÜDÜR AJAN (Yayın Yönetmeni)
Her gönderiyi yayına çıkmadan önce inceler ve "bu içerik tutar mı?" sorusuna
puanlı bir karar verir: ONAY, REVİZYON (geri bildirimle üreticiye geri gönder)
ya da RED. Görselleri de görerek değerlendirir.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from .common import DATA, brand_brief, config, learnings, read_json
from .creator import Draft
from .llm import ask
from .strategist import Idea

AGENT = "Müdür"


class Scores(BaseModel):
    hook_gucu: int = Field(description="0-25: ilk 1 saniyede kaydırmayı durdurur mu?")
    deger: int = Field(description="0-25: okuyan bir şey öğrenir/kazanır mı, kaydetmeye değer mi?")
    trend_uyumu: int = Field(description="0-15: şu anki trendler ve kitle ilgisiyle uyumlu mu?")
    ozgunluk: int = Field(description="0-15: büyük sayfaların kopyası değil, farklı bir açı var mı?")
    marka_ve_dogruluk: int = Field(description="0-10: tona, kurallara uygun ve bilgiler doğru mu?")
    gorsel_okunurluk: int = Field(description="0-10: görseller telefonda kolay okunuyor mu?")


class Verdict(BaseModel):
    puanlar: Scores
    toplam: int = Field(description="Puanların toplamı, 0-100")
    karar: Literal["ONAY", "REVIZYON", "RED"]
    tutar_mi: str = Field(description="Bu içerik neden tutar ya da tutmaz, 2-3 cümle")
    geri_bildirim: str = Field(description="REVİZYON ise somut, maddeli düzeltme talimatları")


def _img(path: Path) -> dict:
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                        "data": base64.standard_b64encode(path.read_bytes()).decode()}}


def run(idea: Idea, draft: Draft, images: list[Path], attempt: int) -> Verdict:
    cfg = config()["uretim"]
    research = read_json(DATA / "research" / "latest.json", {}).get("rapor", {})
    text = (
        f"## Fikir\n{idea.model_dump_json()}\n\n## Taslak\n{draft.model_dump_json()}\n\n"
        f"## Güncel araştırma\n{json.dumps(research, ensure_ascii=False)[:20000]}\n\n"
        f"## Geçmiş verilerden öğrenilenler\n{learnings()}\n\n"
        f"Bu {attempt}. deneme. Onay eşiği {cfg['onay_esigi']}/100. "
        f"Eşik altındaysa ve düzeltilebilirse REVIZYON, fikir temelden zayıfsa RED ver. "
        "İlk görseller ektedir."
    )
    content = [*[_img(p) for p in images[:3]], {"type": "text", "text": text}]
    v = ask(
        AGENT,
        system=(
            "Sen büyük bir medya şirketinde Instagram yayın yönetmenisin. Yüzlerce viral içerik "
            "yönettin. Sert ama adilsin: ortalama içeriği onaylamazsın, çünkü yeni bir hesapta "
            "her vasat gönderi erişimi düşürür. Puanları gerçekçi verirsin.\n\n" + brand_brief()
        ),
        content=content,
        schema=Verdict,
    )
    # Karar puanla tutarlı olsun
    total = sum(v.puanlar.model_dump().values())
    v.toplam = total
    if v.karar == "ONAY" and total < cfg["onay_esigi"]:
        v.karar = "REVIZYON"
    return v
