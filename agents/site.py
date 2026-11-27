"""HESAPLAYICI SİTE (GitHub Pages)
Yayınlanan her video için etkileşimli bir hesaplayıcı sayfası üretir:
  - Tablodaki her kalem düzenlenebilir; toplamlar ve fark anında yeniden hesaplanır
  - "Kaç gün çalışman gerekir?": ziyaretçi kendi net maaşını girer
  - Kaynak linkleri, fiyat tarihi, Instagram gönderisinin linki
  - config.yaml → site.ortaklik_linkleri doluysa ilgili sayfalarda satış ortaklığı kutusu
Ana sayfa (index.html) tüm hesaplayıcıları listeler → Instagram biyografisindeki link.
Statik HTML, dış kütüphane yok; serinin 60-30-10 renkleriyle.
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime

from .common import PUBLISHED, ROOT, config, log, read_json

AGENT = "Site"
SITE_DIR = ROOT / "hesap"


def _slug(post: dict) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", post["fikir"]["konu"].lower()
                  .translate(str.maketrans("çğıöşüâî", "cgiosuai")))[:50].strip("-")
    return f"{post.get('seri_no', 0)}-{base}"


def _css() -> str:
    g = config()["gorsel"]
    return f"""
:root{{--bg:{g['arka_plan']};--panel:{g.get('panel', '#18233A')};--acc:{g['vurgu']};--txt:{g['yazi']};
--sec:{g.get('yazi_ikincil', '#94A3B8')}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--txt);
font:16px/1.5 system-ui,-apple-system,'Segoe UI',Roboto,Arial,sans-serif}}
.band{{background:var(--acc);color:var(--bg);font-weight:800;padding:10px 16px;letter-spacing:.5px}}
.band a{{color:var(--bg);text-decoration:none}}
main{{max-width:720px;margin:0 auto;padding:16px}}
.card{{background:var(--panel);border-radius:20px;padding:20px;margin:16px 0;border-left:6px solid var(--acc)}}
h1{{font-size:26px;margin:.2em 0}}h2{{font-size:19px;margin:.2em 0 .6em}}
.sec{{color:var(--sec);font-size:14px}}
table{{width:100%;border-collapse:collapse}}td{{padding:8px 4px;border-bottom:1px solid #2A3650}}
td:last-child{{text-align:right;white-space:nowrap}}
input{{width:9em;max-width:100%;background:var(--bg);color:var(--txt);border:1px solid #33415C;border-radius:10px;
padding:8px;font-size:16px;text-align:right}}
.total td{{font-weight:800;color:var(--acc);border-bottom:none;font-size:18px}}
.big{{font-size:34px;font-weight:900;color:var(--acc)}}
a{{color:var(--acc)}}.list a{{display:block;padding:14px 0;border-bottom:1px solid #2A3650;text-decoration:none;color:var(--txt)}}
.list b{{color:var(--acc)}}.aff{{display:block;background:var(--acc);color:var(--bg);text-align:center;padding:14px;
border-radius:14px;font-weight:800;text-decoration:none;margin-top:8px}}
footer{{color:var(--sec);font-size:13px;text-align:center;padding:24px 16px}}
"""


def _page(title: str, desc: str, body: str, depth: int = 0) -> str:
    cfg = config()
    up = "../" * depth
    handle = cfg["hesap"]["kullanici_adi"]
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><meta name="description" content="{html.escape(desc)}">
<meta property="og:title" content="{html.escape(title)}"><meta property="og:description" content="{html.escape(desc)}">
<style>{_css()}</style></head><body>
<div class="band"><a href="{up}index.html">{html.escape(cfg.get('seri', {}).get('ad', 'GERÇEK MALİYET'))}</a>
<span style="float:right">@{html.escape(handle)}</span></div>
<main>{body}</main>
<footer>Rakamlar bilgilendirme amaçlıdır, yatırım tavsiyesi değildir. Fiyatlar belirtilen tarihe aittir ve değişebilir.<br>
<a href="https://www.instagram.com/{html.escape(handle)}/">Instagram'da takip et</a></footer>
</body></html>"""


def _affiliates(post: dict) -> str:
    links = (config().get("site") or {}).get("ortaklik_linkleri") or {}
    text = (post["fikir"]["konu"] + " " + " ".join(i["kalem"] for o in post["veri"]["secenekler"]
                                                   for i in o["kalemler"])).lower()
    out = []
    for key, v in links.items():
        if key.lower() in text and v.get("url"):
            out.append(f'<a class="aff" rel="sponsored noopener" href="{html.escape(v["url"])}">'
                       f'{html.escape(v.get("metin", key))}</a>')
    return ("<div class='card'><h2>İşine yarayabilir</h2>" + "".join(out) +
            "<p class='sec'>Bu bağlantılar satış ortaklığı içerebilir.</p></div>") if out else ""


def calculator_page(post: dict) -> str:
    v = post["veri"]
    m = config().get("maas_cevirisi") or {}
    data = {"opts": [{"ad": o["ad"], "items": [{"k": i["kalem"], "v": i["tutar_tl"], "t": i["tahmini"]}
                                               for i in o["kalemler"]]} for o in v["secenekler"]],
            "net": m.get("asgari_ucret_net", 0), "gun": m.get("aylik_calisma_gunu", 30)}
    rows = []
    for oi, o in enumerate(v["secenekler"]):
        trs = "".join(
            f"<tr><td>{html.escape(i['kalem'])}{' <span class=sec>(tahmini)</span>' if i['tahmini'] else ''}</td>"
            f"<td><input type='number' step='0.01' min='0' data-o='{oi}' data-i='{ii}' value='{i['tutar_tl']:.2f}'> TL</td></tr>"
            for ii, i in enumerate(o["kalemler"]))
        rows.append(f"<div class='card'><h2>{html.escape(o['ad'])}</h2><table>{trs}"
                    f"<tr class='total'><td>Toplam</td><td id='t{oi}'></td></tr></table></div>")
    src = "".join(f"<li><a rel='noopener' href='{html.escape(u)}'>{html.escape(u)}</a></li>"
                  if (u := (re.search(r"https?://\S+", k) or [None])[0]) else f"<li>{html.escape(k)}</li>"
                  for k in v["kaynaklar"])
    ig = post.get("permalink")
    ig_html = f'<p><a href="{html.escape(ig)}">Instagram&#39;daki videoyu izle</a></p>' if ig else ""
    body = f"""
<p class="sec">#{post.get('seri_no', '')} · {html.escape(v['hesap_donemi'])} · {html.escape(v['fiyat_tarihi'])} fiyatları</p>
<h1>{html.escape(v['baslik'])}</h1>
<p>{html.escape(v['sonuc'])}</p>
<p class="sec">Rakamları kendi durumuna göre değiştir; toplamlar anında güncellenir.</p>
{''.join(rows)}
<div class="card"><h2>Kaç gün çalışman gerekir?</h2>
<p>Aylık net maaşın: <input id="maas" type="number" step="0.01" min="0" value="{data['net']:.2f}"> TL</p>
<p class="big" id="sonuc"></p><p class="sec" id="fark"></p>
<p class="sec">Varsayılan: {html.escape(m.get('kaynak', 'net asgari ücret'))}</p></div>
{_affiliates(post)}
<div class="card"><h2>Varsayımlar ve kaynaklar</h2><ul>{''.join(f'<li>{html.escape(x)}</li>' for x in v['varsayimlar'])}</ul>
<ul>{src}</ul>{ig_html}</div>
<script>
const D={json.dumps(data, ensure_ascii=False)};
const fmt=x=>x.toLocaleString('tr-TR',{{minimumFractionDigits:0,maximumFractionDigits:2}})+' TL';
const num=s=>parseFloat(s)||0;
function calc(){{
  const tots=D.opts.map((o,oi)=>o.items.reduce((a,it,ii)=>a+num(document.querySelector(`input[data-o="${{oi}}"][data-i="${{ii}}"]`).value),0));
  tots.forEach((t,i)=>document.getElementById('t'+i).textContent=fmt(t));
  const head=tots.length>1?Math.max(...tots)-Math.min(...tots):tots[0];
  const maas=num(document.getElementById('maas').value);
  const gun=maas>0?head/(maas/D.gun):0;
  document.getElementById('sonuc').textContent=gun>=1?'≈ '+Math.round(gun)+' gün çalışma':'≈ '+Math.max(1,Math.round(gun*D.gun*7.5))+' saat çalışma';
  document.getElementById('fark').textContent=(tots.length>1?'Fark: ':'Toplam: ')+fmt(head);
}}
document.querySelectorAll('input').forEach(i=>i.addEventListener('input',calc));calc();
</script>"""
    return _page(f"{v['baslik']} — Gerçek Maliyet Hesaplayıcı", v["sonuc"], body, depth=1)


def build() -> int:
    if not (config().get("site") or {}).get("aktif", True):
        return 0
    SITE_DIR.mkdir(exist_ok=True)
    posts = []
    for f in PUBLISHED.glob("*.json"):
        p = read_json(f)
        if p.get("veri") and p.get("fikir"):
            slug = _slug(p)
            (SITE_DIR / f"{slug}.html").write_text(calculator_page(p), encoding="utf-8")
            posts.append((p.get("yayin_zamani", ""), slug, p))
    posts.sort(reverse=True)
    items = "".join(
        f"<a href='hesap/{s}.html'><b>#{p.get('seri_no', '')}</b> {html.escape(p['veri']['baslik'])}"
        f"<br><span class='sec'>{html.escape(p['veri']['fiyat_tarihi'])} · {html.escape(p['veri']['sonuc'][:110])}</span></a>"
        for _, s, p in posts) or "<p class='sec'>İlk hesaplayıcılar çok yakında.</p>"
    body = (f"<h1>Gerçek Maliyet Hesaplayıcıları</h1><p>Videolardaki her tabloyu kendi rakamlarınla hesapla. "
            f"Her gün yenileri ekleniyor.</p><div class='card list'>{items}</div>"
            f"<p class='sec'>Güncelleme: {datetime.now():%d.%m.%Y %H:%M}</p>")
    (ROOT / "index.html").write_text(
        _page("Gerçek Maliyet — Rakamlarla Hesaplayıcılar",
              "Araba, ev, abonelik, iş kurmak: gerçek maliyetleri kendi rakamlarınla hesapla.", body), encoding="utf-8")
    log(AGENT, f"Site güncellendi: {len(posts)} hesaplayıcı")
    return len(posts)


def link_for(post: dict) -> str:
    base = (config().get("site") or {}).get("adres", "").rstrip("/")
    return f"{base}/hesap/{_slug(post)}.html" if base else ""
