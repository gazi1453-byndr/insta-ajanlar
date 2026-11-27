"""PROGRAM / GÖREV ÇUBUĞU (plan.html, GitHub Pages)
Her ajan çalışmasından sonra yeniden üretilir:
  - Bugünün görev çubuğu: 24 saatlik zaman çizgisi; ajan çalışmaları, paylaşım saatleri, kuyruktaki videolar, 'şimdi' çizgisi
  - Günlük hedef ilerlemesi (config: uretim.gunluk_gonderi)
  - Bu hafta: her günün alt serisi + o güne planlı/yayınlanan videolar
  - Sıradaki işler: onay bekleyen önizlemeler, kuyruk, son yayınlar, son retler (neden)
  - Otomatik ajanlar: GitHub Actions zamanlamaları (TR saati) ve bir sonraki çalışma
Statik HTML (dış kütüphane yok), DESIGN_SYSTEM.md renk ve tipografisiyle. Arama motorlarına kapalı (noindex).
"""
from __future__ import annotations

import html
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .common import DATA, PUBLISHED, QUEUE, REJECTED, ROOT, TR, GUNLER, config, gunun_serisi, log, now, read_json

AGENT = "Program"
WF = ROOT / ".github" / "workflows"


# ------------------------------------------------------------------ cron (UTC) → TR saatleri
def _field(expr: str, lo: int, hi: int) -> list[int]:
    out: set[int] = set()
    for part in expr.split(","):
        step = 1
        if "/" in part:
            part, s = part.split("/")
            step = int(s)
        if part in ("*", ""):
            a, b = lo, hi
        elif "-" in part:
            a, b = map(int, part.split("-"))
        else:
            a = b = int(part)
        out.update(range(a, b + 1, step))
    return sorted(out)


def schedules() -> list[dict]:
    """[{ad, dosya, crons: [(dakikalar, saatler, haftanın günleri)]}] — saatler UTC."""
    items = []
    for f in sorted(WF.glob("[0-9]*.yml"), key=lambda p: int(p.name.split("-")[0])):
        txt = f.read_text(encoding="utf-8")
        name = (re.search(r'^name:\s*"?(.*?)"?\s*$', txt, re.M) or [None, f.stem])[1]
        crons = []
        for c in re.findall(r"cron:\s*['\"]([^'\"]+)['\"]", txt):
            mi, ho, _dom, _mon, dow = c.split()
            crons.append((_field(mi, 0, 59), _field(ho, 0, 23), _field(dow, 0, 6) if dow != "*" else list(range(7))))
        items.append({"ad": name, "dosya": f.name, "crons": crons})
    return items


def runs_on(day: datetime, crons) -> list[datetime]:
    """Verilen TR gününde düşen çalışma anları (TR saati)."""
    out = []
    start = day.replace(hour=0, minute=0, second=0, microsecond=0)
    utc0 = start.astimezone(timezone.utc) - timedelta(days=1)
    for mins, hours, dows in crons:
        for d in range(3):
            base = (utc0 + timedelta(days=d)).replace(minute=0, second=0, microsecond=0)
            cron_dow = (base.weekday() + 1) % 7  # cron: 0 = pazar
            if cron_dow not in dows:
                continue
            for h in hours:
                for m in mins:
                    t = base.replace(hour=h, minute=m).astimezone(TR)
                    if t.date() == start.date():
                        out.append(t)
    return sorted(set(out))


def next_run(crons, ref: datetime) -> datetime | None:
    for d in range(8):
        for t in runs_on(ref + timedelta(days=d), crons):
            if t > ref:
                return t
    return None


# ------------------------------------------------------------------ veri
def _posts(folder: Path, limit: int = 50) -> list[dict]:
    if not folder.exists():
        return []
    fs = sorted(folder.glob("*.json"), key=lambda p: p.name, reverse=True)[:limit]
    return [p for p in (read_json(f, {}) for f in fs) if p]


def _dt(s: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(s).astimezone(TR) if s else None
    except ValueError:
        return None


def _title(p: dict) -> str:
    return (p.get("veri") or {}).get("baslik") or (p.get("fikir") or {}).get("konu") or p.get("id", "?")


# ------------------------------------------------------------------ HTML
CSS = """
:root{--bg:#0B1220;--panel:#18233A;--acc:#22C55E;--txt:#F8FAFC;--sec:#94A3B8;--warn:#F43F5E;--line:#26324A}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:15px/1.5 Inter,system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}
.band{background:var(--acc);color:var(--bg);font-weight:800;padding:10px 16px;display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap}
main{max-width:1100px;margin:0 auto;padding:16px}
.card{background:linear-gradient(180deg,#18233AEE,#18233AC0);border:1px solid #ffffff14;border-radius:22px;padding:18px 20px;margin:14px 0;box-shadow:0 18px 50px #0006}
h1{font-size:26px;margin:4px 0 2px;letter-spacing:-.5px}h2{font-size:17px;margin:0 0 12px;letter-spacing:.3px;color:var(--sec);text-transform:uppercase}
.sec{color:var(--sec);font-size:13px}.big{font-size:34px;font-weight:900;color:var(--acc);font-variant-numeric:tabular-nums}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}
.prog{height:14px;border-radius:7px;background:#ffffff12;overflow:hidden;margin:8px 0 4px}.prog>i{display:block;height:100%;background:var(--acc);border-radius:7px}
.tl{position:relative;height:150px;margin:8px 4px 0;border-top:1px solid var(--line)}
.tl .h{position:absolute;top:0;bottom:22px;border-left:1px dashed #ffffff14}.tl .hl{position:absolute;bottom:0;font-size:11px;color:var(--sec);transform:translateX(-50%)}
.ev{position:absolute;transform:translateX(-50%);white-space:nowrap;font-size:11px;font-weight:700;padding:3px 7px;border-radius:999px;cursor:default}
.ev.agent{background:#ffffff14;color:var(--txt)}.ev.slot{background:transparent;border:1.5px solid var(--acc);color:var(--acc)}
.ev.post{background:var(--acc);color:var(--bg)}.ev.done{background:#86EFAC;color:var(--bg)}
.now{position:absolute;top:-6px;bottom:18px;width:2px;background:var(--warn);box-shadow:0 0 12px var(--warn)}
.now::before{content:'ŞİMDİ';position:absolute;top:-16px;left:-18px;font-size:10px;font-weight:800;color:var(--warn)}
.week{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:8px}
.day{background:#ffffff08;border:1px solid #ffffff10;border-radius:16px;padding:10px;min-height:120px}
.day.today{border:2px solid var(--acc)}.day b{display:block;font-size:13px}.day .th{font-size:11px;color:var(--acc);font-weight:800;margin:2px 0 8px}
.pill{display:inline-block;font-size:11px;font-weight:700;border-radius:999px;padding:2px 8px;margin:2px 0}
.p-kuyrukta{background:var(--acc);color:var(--bg)}.p-yayinlandi{background:#86EFAC;color:var(--bg)}.p-onizleme{background:#FACC15;color:var(--bg)}.p-reddedildi{background:#ffffff14;color:var(--sec)}
table{width:100%;border-collapse:collapse}td,th{padding:8px 6px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{font-size:12px;color:var(--sec);font-weight:600}
a{color:var(--acc)}.why{color:var(--sec);font-size:12px}
@media (max-width:720px){.week{grid-template-columns:repeat(2,1fr)}.tl{height:190px}}
"""

STATUS = {"kuyrukta": "Kuyrukta", "yayinlandi": "Yayınlandı", "onizleme": "Onay bekliyor", "reddedildi": "Reddedildi"}


def build() -> Path:
    cfg = config()
    u = cfg["uretim"]
    target = int(u.get("gunluk_gonderi", 3))
    t0 = now()
    today = t0.date()
    week0 = (t0 - timedelta(days=t0.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)

    queue = _posts(QUEUE)
    pub = _posts(PUBLISHED, 80)
    prev = _posts(DATA / "onizleme")
    rej = _posts(REJECTED, 12)
    for p in queue:
        p.setdefault("durum", "kuyrukta")
    for p in pub:
        p["durum"] = "yayinlandi"
    for p in prev:
        p["durum"] = "onizleme"

    def when(p):
        return _dt(p.get("yayin_zamani")) or _dt(p.get("planlanan_zaman"))

    today_posts = [p for p in queue + pub if (w := when(p)) and w.date() == today]
    done_today = sum(1 for p in today_posts if p["durum"] == "yayinlandi")
    planned_today = len(today_posts)

    # ---- bugünün görev çubuğu
    def pos(t: datetime) -> float:
        return (t.hour * 60 + t.minute) / 1440 * 100

    sch = schedules()
    evs = []
    for s in sch:
        short = re.sub(r"^\d+\s*·\s*", "", s["ad"]).split(" (")[0]
        times = runs_on(t0, s["crons"])
        if len(times) > 6:  # sık çalışan (ör. yayıncı her 30 dk): tek etiket
            evs.append((times[0], f"{short} · her 30 dk", "agent", 0))
            continue
        for k, t in enumerate(times):
            evs.append((t, f"{t:%H:%M} {short}", "agent", 0))
    for sl in u.get("paylasim_saatleri", []):
        h, m = map(int, sl.split(":"))
        evs.append((t0.replace(hour=h, minute=m), f"{sl} paylaşım", "slot", 1))
    for p in today_posts:
        w = when(p)
        evs.append((w, f"{w:%H:%M} #{p.get('seri_no', '')} {_title(p)[:22]}", "done" if p["durum"] == "yayinlandi" else "post", 2))
    rows_used: dict[int, list[float]] = {}
    chips = []
    for t, label, kind, base_row in sorted(evs, key=lambda e: (e[3], e[0])):
        x = pos(t)
        row = base_row * 2
        while any(abs(x - o) < 9 for o in rows_used.get(row, [])):
            row += 1
        rows_used.setdefault(row, []).append(x)
        chips.append(f'<span class="ev {kind}" style="left:{x:.2f}%;top:{6 + row * 21}px" title="{html.escape(label)}">'
                     f'{html.escape(label)}</span>')
    hours = "".join(f'<div class="h" style="left:{h / 24 * 100:.2f}%"></div><div class="hl" style="left:{h / 24 * 100:.2f}%">{h:02d}</div>'
                    for h in range(0, 25, 3))
    height = 40 + (max(rows_used) + 1 if rows_used else 1) * 21

    # ---- hafta
    days = []
    for d in range(7):
        day = week0 + timedelta(days=d)
        theme = gunun_serisi(day)
        items = [p for p in queue + pub if (w := when(p)) and w.date() == day.date()]
        items.sort(key=lambda p: when(p))
        li = "".join(f'<div><span class="pill p-{p["durum"]}">{when(p):%H:%M}</span> {html.escape(_title(p)[:34])}</div>'
                     for p in items) or '<div class="sec">—</div>'
        cls = "day today" if day.date() == today else "day"
        days.append(f'<div class="{cls}"><b>{GUNLER[d]} {day:%d.%m}</b><div class="th">{html.escape(theme)}</div>{li}'
                    f'<div class="sec">{len(items)}/{target} video</div></div>')

    # ---- sıradaki işler
    def row(p, extra=""):
        w = when(p)
        link = f' · <a href="{html.escape(p["permalink"])}">izle</a>' if p.get("permalink") else ""
        return (f'<tr><td><span class="pill p-{p["durum"]}">{STATUS.get(p["durum"], p["durum"])}</span></td>'
                f'<td>{w:%d.%m %H:%M}</td>' if w else
                f'<tr><td><span class="pill p-{p["durum"]}">{STATUS.get(p["durum"], p["durum"])}</span></td><td>—</td>') + \
               (f'<td>#{p.get("seri_no", "")} {html.escape(_title(p))}{link}{extra}</td>'
                f'<td>{html.escape(p.get("alt_seri") or "")}</td></tr>')

    todo = []
    for p in prev:
        todo.append(row(p, '<div class="why">Aksiyon: videoyu izle → Actions’ta “8 · Önizlemeyi onayla”</div>'))
    for p in sorted(queue, key=lambda p: when(p) or t0):
        todo.append(row(p))
    for p in sorted(pub, key=lambda p: when(p) or t0, reverse=True)[:6]:
        todo.append(row(p))
    for p in rej[:5]:
        p["durum"] = "reddedildi"
        todo.append(row(p, f'<div class="why">{html.escape((p.get("red_nedeni") or "")[:160])}</div>'))

    agents = "".join(
        f'<tr><td>{html.escape(s["ad"])}</td><td>'
        + (", ".join(sorted({f"{t:%H:%M}" for t in runs_on(t0, s["crons"])})[:6]) or "elle")
        + (f' <span class="sec">(her 30 dk)</span>' if len(runs_on(t0, s["crons"])) > 6 else "")
        + "</td><td>" + ((lambda n: f"{GUNLER[n.weekday()][:3]} {n:%H:%M}" if n else "—")(next_run(s["crons"], t0)) if s["crons"] else "—")
        + "</td></tr>" for s in sch)

    pct = min(100, round(100 * planned_today / max(1, target)))
    body = f"""
<div class="band"><span>{html.escape(cfg.get('seri', {}).get('ad', 'GERÇEK MALİYET'))} · PROGRAM</span><span>@{html.escape(cfg['hesap']['kullanici_adi'])}</span></div>
<main>
<h1>{GUNLER[t0.weekday()]}, {t0:%d.%m.%Y} · {html.escape(gunun_serisi(t0))}</h1>
<p class="sec">Son güncelleme: {t0:%H:%M} (her ajan çalışmasından sonra yenilenir)</p>
<div class="grid">
 <div class="card"><h2>Bugünkü hedef</h2><div class="big">{planned_today}/{target}</div>
  <div class="prog"><i style="width:{pct}%"></i></div><div class="sec">{done_today} yayınlandı · {planned_today - done_today} kuyrukta</div></div>
 <div class="card"><h2>Onay bekleyen</h2><div class="big">{len(prev)}</div><div class="sec">önizleme videosu</div></div>
 <div class="card"><h2>Kuyruk</h2><div class="big">{len(queue)}</div><div class="sec">yayın bekleyen video</div></div>
 <div class="card"><h2>Toplam yayın</h2><div class="big">{len(pub)}</div><div class="sec">son {len(rej)} ret kayıtlı</div></div>
</div>
<div class="card"><h2>Bugünün görev çubuğu</h2>
 <div class="tl" id="tl" style="height:{height}px">{hours}{''.join(chips)}<div class="now" id="now" style="left:{pos(t0):.2f}%"></div></div>
</div>
<div class="card"><h2>Bu hafta</h2><div class="week">{''.join(days)}</div></div>
<div class="card"><h2>Sıradaki işler</h2><table><tr><th>Durum</th><th>Zaman</th><th>Video</th><th>Alt seri</th></tr>
{''.join(todo) or '<tr><td colspan=4 class="sec">Henüz iş yok</td></tr>'}</table></div>
<div class="card"><h2>Otomatik ajanlar (TR saati)</h2><table><tr><th>Ajan</th><th>Bugün</th><th>Sonraki</th></tr>{agents}</table></div>
</main>
<script>
// 'şimdi' çizgisi canlı (Türkiye saati)
function tick(){{const d=new Date(new Date().toLocaleString('en-US',{{timeZone:'Europe/Istanbul'}}));
const el=document.getElementById('now');if(el)el.style.left=((d.getHours()*60+d.getMinutes())/1440*100)+'%';}}
tick();setInterval(tick,60000);
</script>"""
    page = (f'<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta name="robots" content="noindex"><title>Program · Gerçek Maliyet</title><style>{CSS}</style></head><body>{body}</body></html>')
    out = ROOT / "plan.html"
    out.write_text(page, encoding="utf-8")
    log(AGENT, f"Program sayfası güncellendi: bugün {planned_today}/{target}, kuyruk {len(queue)}, onay bekleyen {len(prev)}")
    return out
