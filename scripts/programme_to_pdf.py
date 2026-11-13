#!/usr/bin/env python3
"""Make a printable PDF of the conference programme from _data/programme_<year>.yml.

    python scripts/programme_to_pdf.py            # uses _data/programme_2026.yml
    python scripts/programme_to_pdf.py 2027       # another year

Needs: pyyaml, and Google Chrome / Edge / Chromium installed (used headless to
print the PDF, so no extra Python PDF libraries are required).
Output: docs/<year>/Evolution_in_the_Gong_<year>_Programme.pdf

Run it AFTER programme_from_xlsx.py, then commit the PDF.
"""
import base64
import html
import mimetypes
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
YEAR = sys.argv[1] if len(sys.argv) > 1 else "2026"
DATA = ROOT / "_data" / f"programme_{YEAR}.yml"
OUT = ROOT / "docs" / YEAR / f"Evolution_in_the_Gong_{YEAR}_Programme.pdf"
SITE = "ausevo.github.io/schedule"

SHAPES = {"r1": "square", "r2": "circle", "r3": "leaf"}  # same cues as the web page
SPONSORS_DATA = ROOT / "_data" / "sponsors.yml"
EXEC_DATA = ROOT / "_data" / "exec.yml"
SASB_DATA = ROOT / "_data" / "sasb_council.yml"
BANNER_IMG = ROOT / "img" / "aes2026" / "ConfBanne_FINAL.png"


def esc(s):
    """Escape plain text (data may already contain &amp;)."""
    return html.escape(html.unescape(str(s or "")), quote=False)


def rich(s):
    """Titles may contain <em>...</em> from the spreadsheet; keep only that tag."""
    t = esc(s)
    return t.replace("&lt;em&gt;", "<em>").replace("&lt;/em&gt;", "</em>")


def img_data_uri(path):
    """Return a base64 data URI for a local image, or '' if not found."""
    p = Path(path)
    if not p.exists():
        return ""
    mime = mimetypes.guess_type(str(p))[0] or "image/png"
    data = base64.b64encode(p.read_bytes()).decode()
    return f"data:{mime};base64,{data}"


def load_sponsors():
    """Return list of (tier_name, [(name, img_uri)]) for tiers that have sponsors."""
    if not SPONSORS_DATA.exists():
        return []
    data = yaml.safe_load(SPONSORS_DATA.read_text(encoding="utf-8"))
    result = []
    for tier in data.get("tiers", []):
        entries = tier.get("sponsors") or []
        logos = []
        for sp in entries:
            logo_path = sp.get("logo", "")
            uri = img_data_uri(ROOT / logo_path.lstrip("/")) if logo_path else ""
            logos.append((esc(sp.get("name", "")), uri))
        if logos:
            result.append((esc(tier["name"]), logos))
    return result


def talk_cell(t):
    cls = "talk stu-talk" if t.get("student") else "talk"
    spk = f'<b>{esc(t.get("speaker"))}</b>' if t.get("speaker") else ""
    return f'<div class="{cls}">{spk}<div class="ttl">{rich(t.get("title"))}</div></div>'


def item_cell(it):
    kind = it.get("kind", "talk")
    if kind == "speed":
        rows = "".join(
            f'<li><span class="tm">{esc(s.get("start"))}</span>'
            f'<span class="spk">{esc(s.get("speaker"))}</span>'
            f'<span class="ttl">{rich(s.get("title"))}</span></li>'
            for s in it.get("talks", [])
        )
        return (f'<div class="talk speed"><div class="speed-h">{esc(it.get("title"))}</div>'
                f'<ul>{rows}</ul></div>')
    if kind == "agm":
        end = it.get("end", "")
        time_range = f'{esc(it.get("start",""))}{"&ndash;" + esc(end) if end else ""}'
        return (f'<div class="talk agm">'
                f'<div class="agm-time">{time_range}</div>'
                f'<b>{esc(it.get("title"))}</b></div>')
    return talk_cell(it)


def parallel(block):
    tracks = block["tracks"]
    n = len(tracks)
    head = "".join(
        f'<th><span class="chip {SHAPES.get(tr.get("rid"), "square")}">{esc(str(tr.get("rid", "")).replace("r", ""))}</span>'
        f'<span class="rt">{esc(tr.get("room"))}</span>'
        f'<span class="topic">{esc(tr.get("topic"))}</span>'
        + (f'<span class="chair">Chair: {esc(tr["chair"])}</span>' if tr.get("chair") else "")
        + "</th>"
        for tr in tracks
    )
    starts = sorted({i["start"] for tr in tracks for i in tr.get("items", [])})
    body = []
    for s in starts:
        cells = []
        for tr in tracks:
            hit = [i for i in tr.get("items", []) if i["start"] == s]
            cells.append("<td>" + "".join(item_cell(i) for i in hit) + "</td>")
        body.append(f'<tr><th class="time">{esc(s)}</th>{"".join(cells)}</tr>')
    return (f'<table class="par n{n}"><thead><tr><th class="time"></th>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table>')


def event(it):
    typ = it.get("type", "admin")
    when = esc(it.get("start")) + ("" if it.get("open_end") or not it.get("end") else "&ndash;" + esc(it["end"]))
    title_low = str(it.get("title", "")).lower()
    feat = "meal" if typ == "break" else "social" if typ == "social" else "closing" if "closing" in title_low else "plenary" if typ == "plenary" else ""
    cls = f"ev ev-{typ}" + (f" feat feat-{feat}" if feat else "")

    if typ == "plenary":
        lbl = esc(it.get("label", "Plenary"))
        who = f'<b>{esc(it["speaker"])}</b> &middot; ' if it.get("speaker") else ""
        loc = f' <span class="eloc">{esc(it["location"])}</span>' if it.get("location") else ""
        ebody = (f'<div class="ebody">'
                 f'<span class="plenary-lbl">{lbl}</span>'
                 f'<span class="plenary-st">{who}{rich(it.get("title"))}{loc}</span>'
                 f'</div>')
        return f'<div class="{cls}"><span class="etime">{when}</span>{ebody}</div>'

    who = f'<b>{esc(it["speaker"])}</b> &middot; ' if it.get("speaker") else ""
    lab = f'<span class="elabel">{esc(it["label"])}</span>' if it.get("label") else ""
    loc = f'<span class="eloc">{esc(it["location"])}</span>' if it.get("location") and typ == "workshop" else ""
    return (f'<div class="{cls}"><span class="etime">{when}</span>'
            f'<span class="ebody">{lab}{who}{rich(it.get("title"))}</span>{loc}</div>')


CSS = """
@page { size: A4 landscape; margin: 11mm 12mm 14mm; }
@page { @bottom-right { content: counter(page); font-size: 7.5pt; color: #55626f; } }
@page :first { @bottom-right { content: none; } }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; font: 8.6pt/1.3 Helvetica, Arial, sans-serif; color: #1c2733; }
em { font-style: italic; }
/* --- cover: full banner, no cropping --- */
.cover { text-align: center; }
.cover img { max-width: 100%; max-height: 185mm; object-fit: contain; display: block; margin: 0 auto; }
/* --- sponsors page --- */
.sponsors { break-before: page; display: flex; flex-direction: column; justify-content: center; height: 183mm; }
.sp-blurb { text-align: center; font-size: 11pt; color: #1c2733; margin-bottom: 22px; line-height: 1.5; }
.sp-blurb strong { color: #0d3b66; }
.sp-tier-block { margin-bottom: 18px; }
.sp-tier-header { display: flex; align-items: center; gap: 8px; padding: 7px 14px; border-radius: 6px; margin-bottom: 12px;
  font-size: 9pt; font-weight: 800; letter-spacing: .07em; text-transform: uppercase; color: #fff; }
.sp-tier-header--platinum { background: linear-gradient(135deg, #5b21b6 0%, #7c3aed 100%); }
.sp-tier-header--gold     { background: linear-gradient(135deg, #92400e 0%, #d97706 100%); }
.sp-tier-header--silver   { background: linear-gradient(135deg, #374151 0%, #6b7280 100%); }
.sp-tier-header--bronze   { background: linear-gradient(135deg, #78350f 0%, #b45309 100%); }
.sp-tier-header .icon { font-size: 10pt; }
.sp-logo-row { display: flex; align-items: stretch; gap: 16px; flex-wrap: wrap; margin-bottom: 6px; }
.sp-logo-card { background: #fff; border: 1px solid #dde2e7; border-radius: 6px;
  display: flex; align-items: center; justify-content: center; }
.sp-logo-card--platinum { padding: 16px 28px; }
.sp-logo-card--platinum img { max-height: 80px; max-width: 240px; object-fit: contain; }
.sp-logo-card--gold     { padding: 12px 20px; }
.sp-logo-card--gold     img { max-height: 55px; max-width: 180px; object-fit: contain; }
.sp-logo-card--bronze   { padding: 10px 16px; }
.sp-logo-card--bronze   img { max-height: 38px; max-width: 130px; object-fit: contain; }
/* --- schedule days --- */
.day { break-before: page; }
.dayhead { display: flex; justify-content: space-between; align-items: flex-end; background: #0d3b66; color: #fff;
  padding: 7px 12px; border-radius: 6px; margin-bottom: 8px; }
.dayhead h2 { margin: 0; font-size: 15pt; letter-spacing: .01em; }
.dayhead span { font-size: 8pt; opacity: .85; }
table.par { width: 100%; border-collapse: separate; border-spacing: 4px 4px; table-layout: fixed; margin: 6px 0; }
.par thead { display: table-header-group; }
.par tr { break-inside: avoid; }
.par th.time { width: 40px; text-align: right; vertical-align: top; font-size: 8.4pt; color: #0d3b66; padding: 5px 4px 0 0; }
.par thead th:not(.time) { text-align: left; vertical-align: top; background: #eef3f8; border-radius: 5px; padding: 5px 8px; border-top: 4px solid #0d3b66; }
.par thead th:nth-child(3) { border-top-color: #1f7a6f; }
.par thead th:nth-child(4) { border-top-color: #9a5414; }
.par td { vertical-align: top; padding: 0; height: 1px; }
.chip { display: inline-block; width: 15px; height: 15px; line-height: 15px; text-align: center; color: #fff; font-weight: 800; font-size: 8pt;
  background: #0d3b66; margin-right: 5px; }
.par thead th:nth-child(3) .chip { background: #1f7a6f; }
.par thead th:nth-child(4) .chip { background: #9a5414; }
.chip.square { border-radius: 2px; } .chip.circle { border-radius: 50%; } .chip.leaf { border-radius: 8px 0 8px 0; }
.rt { font-weight: 700; font-size: 8.6pt; }
.topic { display: block; font-weight: 600; margin-top: 2px; font-size: 8.4pt; }
.chair { display: block; color: #55626f; font-size: 7.6pt; }
.talk { border: 1px solid #d5dde5; border-radius: 4px; padding: 3px 6px 4px; background: #fff; height: 100%; }
.stu-talk { border-left: 4px dashed #c2570c; background: #fff6ec; }
.ttl { font-size: 8pt; color: #33404d; }
.speed { background: #f4f7fa; }
.speed-h { font-weight: 800; color: #0d3b66; margin-bottom: 4px; font-size: 8.6pt; }
.speed ul { list-style: none; margin: 0; padding: 0; }
.speed li { display: flex; gap: 6px; align-items: baseline; margin: 0 0 4px; font-size: 8pt; line-height: 1.35; }
.speed .ttl { font-size: 8pt; }
.tm { color: #0d3b66; font-weight: 700; min-width: 32px; flex-shrink: 0; }
.spk { font-weight: 700; min-width: 110px; flex-shrink: 0; }
.agm { background: #0d3b66; color: #fff; border-radius: 4px; padding: 10px 12px; height: 100%; }
.agm-time { font-size: 9pt; font-weight: 800; color: #cfe0f1; margin-bottom: 4px; }
.agm b { font-size: 10pt; }
.ev { display: flex; gap: 10px; align-items: baseline; margin: 4px 0; padding: 5px 10px; border-radius: 5px; break-inside: avoid;
  background: #f1f3f5; border: 1px solid #dde2e7; }
.etime { font-weight: 800; min-width: 80px; color: #0d3b66; }
.ebody { flex: 1; }
.elabel { display: inline-block; font-size: 6.8pt; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; margin-right: 8px; }
.eloc { color: #55626f; font-size: 7.6pt; }
.ev-plenary { background: #0d3b66; border-color: #0d3b66; color: #fff; }
.ev-workshop { background: #0d3b66; border-color: #0d3b66; color: #fff; }
.ev-workshop .etime, .ev-workshop .eloc { color: #cfe0f1; }
.ev-social { background: #e3f4f1; border-color: #2a9d8f; }
.ev-break { background: #fff; border-style: dashed; color: #55626f; }
.ev.feat { padding: 8px 12px; margin: 6px 0; border-width: 1.5px; border-style: solid; font-size: 11pt; font-weight: 800; }
.ev.feat .etime { font-size: 10.5pt; min-width: 90px; }
.ev.feat-meal { background: #fde3c4; border-color: #d9822b; color: #5a2c04; }
.ev.feat-meal .etime { color: #7a3f08; }
.ev.feat-social { background: #1f7a6f; border-color: #14584f; color: #fff; }
.ev.feat-closing { background: #b83f24; border-color: #8f2f19; color: #fff; }
.ev.feat-social .etime, .ev.feat-closing .etime { color: #fff; }
.ev.feat-plenary { background: #0d3b66; border-color: #0d3b66; color: #fff; align-items: flex-start; }
.ev.feat-plenary .etime { color: #cfe0f1; padding-top: 2px; }
.ev.feat-plenary .ebody { display: flex; flex-direction: column; gap: 3px; }
.plenary-lbl { font-size: 8pt; font-weight: 800; text-transform: uppercase; letter-spacing: .07em; opacity: 0.65; line-height: 1; }
.plenary-st { font-size: 11pt; font-weight: 700; line-height: 1.25; }
.plenary-st .eloc { font-size: 8pt; font-weight: 400; color: #cfe0f1; }
.ev-admin { background: #fff; color: #44505c; }
.foot { margin-top: 10px; font-size: 7.4pt; color: #55626f; display: flex; justify-content: space-between; }
/* --- committees page --- */
.committees { break-before: page; }
.committees-head { background: #0d3b66; color: #fff; padding: 7px 12px; border-radius: 6px; margin-bottom: 16px; font-size: 15pt; font-weight: 700; letter-spacing: .01em; }
.committees-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.committee-block { border: 1px solid #dde2e7; border-radius: 6px; padding: 12px 14px; }
.committee-name { font-size: 10pt; font-weight: 800; color: #0d3b66; border-bottom: 2px solid #0d3b66; padding-bottom: 5px; margin-bottom: 10px; }
.committee-role { display: flex; gap: 8px; margin-bottom: 5px; font-size: 8.6pt; line-height: 1.35; }
.crole { font-weight: 700; color: #33404d; min-width: 140px; flex-shrink: 0; }
.cmembers { color: #1c2733; }
"""


def build(prog):
    conf = esc(prog.get("conference", "Conference programme"))
    days = prog["days"]
    parts = [f"<!doctype html><html><head><meta charset='utf-8'><title>{conf} programme</title><style>{CSS}</style></head><body>"]

    # --- page 1: banner only ---
    banner_uri = img_data_uri(BANNER_IMG)
    if banner_uri:
        parts.append(f'<section class="cover"><img src="{banner_uri}" alt="{conf}" /></section>')

    # --- page 2: sponsors ---
    # tier slug → (css modifier, unicode icon)
    TIER_STYLE = {
        "platinum": ("platinum", "\u2666"),   # ♦ gem-like diamond
        "gold":     ("gold",     "\u2605"),   # ★ medal
        "silver":   ("silver",   "\u2606"),   # ☆ award
        "bronze":   ("bronze",   "\u2605"),   # ★ star
    }

    all_sponsors = load_sponsors()
    tier_blocks = ""
    for tier_name, logos in all_sponsors:
        slug = tier_name.lower()
        mod, icon = TIER_STYLE.get(slug, ("bronze", "\u2605"))
        cards = "".join(
            f'<div class="sp-logo-card sp-logo-card--{mod}">'
            f'<img src="{uri}" alt="{nm}" title="{nm}" /></div>'
            if uri else
            f'<div class="sp-logo-card sp-logo-card--{mod}"><span>{esc(nm)}</span></div>'
            for nm, uri in logos
        )
        tier_blocks += (
            f'<div class="sp-tier-block">'
            f'<div class="sp-tier-header sp-tier-header--{mod}">'
            f'<span class="icon">{icon}</span> {tier_name}'
            f'</div>'
            f'<div class="sp-logo-row">{cards}</div>'
            f'</div>'
        )

    parts.append(
        f'<section class="sponsors">'
        f'<p class="sp-blurb">We thank our generous sponsors for supporting <strong>Evolution in the Gong 2026</strong>.</p>'
        f'{tier_blocks}'
        f'</section>'
    )
    for d in days:
        parts.append(f'<section class="day"><div class="dayhead"><h2>{esc(d["label"])}</h2><span>{conf}</span></div>')
        for it in d["items"]:
            parts.append(parallel(it) if it["type"] == "parallel" else event(it))
        parts.append(f'<div class="foot"><span>{conf}</span><span>Live version: {SITE}</span></div></section>')

    # --- last page: committees ---
    parts.append(committee_page())

    parts.append("</body></html>")
    return "".join(parts)


def strip_title(name):
    import re
    return re.sub(r"^(Dr\.?|Prof\.?|A/Prof\.?|Assoc\.?\s+Prof\.?)\s+", "", str(name)).strip()


def committee_rows(roles, strip_titles=False):
    rows = ""
    for r in roles:
        members = r.get("members") or []
        names = ", ".join(
            esc(strip_title(m.get("name") if isinstance(m, dict) else m) if strip_titles else (m.get("name") if isinstance(m, dict) else m))
            for m in members
        )
        rows += (f'<div class="committee-role">'
                 f'<span class="crole">{esc(r["title"])}</span>'
                 f'<span class="cmembers">{names}</span>'
                 f'</div>')
    return rows


def committee_page():
    aes_roles, sasb_roles = [], []
    if EXEC_DATA.exists():
        aes_roles = yaml.safe_load(EXEC_DATA.read_text(encoding="utf-8")).get("roles", [])
    if SASB_DATA.exists():
        sasb_roles = yaml.safe_load(SASB_DATA.read_text(encoding="utf-8")).get("roles", [])

    aes_html = f'<div class="committee-block"><div class="committee-name">AES Executive Committee 2026</div>{committee_rows(aes_roles, strip_titles=True)}</div>'
    sasb_html = f'<div class="committee-block"><div class="committee-name">SASB Council 2026</div>{committee_rows(sasb_roles)}</div>'

    return (f'<section class="committees">'
            f'<div class="committees-head">Conference Committees 2026</div>'
            f'<div class="committees-cols">{aes_html}{sasb_html}</div>'
            f'</section>')


def find_browser():
    env = os.environ.get("CHROME")
    cands = [env] if env else []
    cands += [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    for name in ("google-chrome", "chromium", "chromium-browser", "chrome", "msedge"):
        w = shutil.which(name)
        if w:
            cands.append(w)
    for c in cands:
        if c and Path(c).exists():
            return c
    sys.exit("Could not find Chrome/Edge. Set the CHROME environment variable to its path.")


def main():
    prog = yaml.safe_load(DATA.read_text(encoding="utf-8"))
    # Day 0 (workshop only) is kept: it is part of the programme
    page = build(prog)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "programme.html"
        src.write_text(page, encoding="utf-8")
        cmd = [find_browser(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
               f"--user-data-dir={Path(tmp) / 'profile'}", f"--print-to-pdf={OUT}", src.as_uri()]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")
    print(f"Set  pdf: \"/docs/{YEAR}/{OUT.name}\"  in scripts/programme_overrides.yml, then re-run programme_from_xlsx.py.")


if __name__ == "__main__":
    main()
