#!/usr/bin/env python3
"""Make a printable PDF of the conference programme from _data/programme_<year>.yml.

    python scripts/programme_to_pdf.py            # uses _data/programme_2026.yml
    python scripts/programme_to_pdf.py 2027       # another year

Needs: pyyaml, and Google Chrome / Edge / Chromium installed (used headless to
print the PDF, so no extra Python PDF libraries are required).
Output: docs/<year>/Evolution_in_the_Gong_<year>_Programme.pdf

Run it AFTER programme_from_xlsx.py, then commit the PDF.
"""
import html
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


def esc(s):
    """Escape plain text (data may already contain &amp;)."""
    return html.escape(html.unescape(str(s or "")), quote=False)


def rich(s):
    """Titles may contain <em>...</em> from the spreadsheet; keep only that tag."""
    t = esc(s)
    return t.replace("&lt;em&gt;", "<em>").replace("&lt;/em&gt;", "</em>")


def student_tag(t):
    return '<span class="stu">Student</span>' if t.get("student") else ""


def talk_cell(t):
    cls = "talk stu-talk" if t.get("student") else "talk"
    spk = f'<b>{esc(t.get("speaker"))}</b>' if t.get("speaker") else ""
    return f'<div class="{cls}">{spk} {student_tag(t)}<div class="ttl">{rich(t.get("title"))}</div></div>'


def item_cell(it):
    kind = it.get("kind", "talk")
    if kind == "speed":
        rows = "".join(
            f'<li><span class="tm">{esc(s.get("start"))}</span> <b>{esc(s.get("speaker"))}</b> {student_tag(s)}'
            f'<span class="ttl"> {rich(s.get("title"))}</span></li>'
            for s in it.get("talks", [])
        )
        return (f'<div class="talk speed"><div class="speed-h">{esc(it.get("title"))}</div>'
                f'<ul>{rows}</ul></div>')
    if kind == "agm":
        return f'<div class="talk agm"><b>{esc(it.get("title"))}</b></div>'
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
    t = it.get("type", "admin")
    when = esc(it.get("start")) + ("" if it.get("open_end") or not it.get("end") else "&ndash;" + esc(it["end"]))
    who = f'<b>{esc(it["speaker"])}</b> &middot; ' if it.get("speaker") else ""
    lab = f'<span class="elabel">{esc(it["label"])}</span>' if it.get("label") else ""
    loc = f'<span class="eloc">{esc(it["location"])}</span>' if it.get("location") and t in ("plenary", "workshop") else ""
    title = str(it.get("title", "")).lower()
    feat = "meal" if t == "break" else "social" if t == "social" else "closing" if "closing" in title else ""
    if feat:
        t += f" feat feat-{feat}"
    return (f'<div class="ev ev-{t}"><span class="etime">{when}</span>'
            f'<span class="ebody">{lab}{who}{rich(it.get("title"))}</span>{loc}</div>')


CSS = """
@page { size: A4 landscape; margin: 11mm 12mm 12mm; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; font: 8.6pt/1.3 Inter, "Segoe UI", Helvetica, Arial, sans-serif; color: #1c2733; }
em { font-style: italic; }
.day { break-before: page; }
.day:first-of-type { break-before: auto; }
.dayhead { display: flex; justify-content: space-between; align-items: flex-end; background: #0d3b66; color: #fff;
  padding: 7px 12px; border-radius: 6px; margin-bottom: 8px; }
.dayhead h2 { margin: 0; font-size: 15pt; letter-spacing: .01em; }
.dayhead span { font-size: 8pt; opacity: .85; }
.legend { font-size: 7.4pt; color: #55626f; margin: 0 0 7px; }
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
.stu { display: inline-block; font-size: 6.6pt; font-weight: 800; text-transform: uppercase; letter-spacing: .04em; color: #8a3f05;
  border: 1px solid #c2570c; border-radius: 8px; padding: 0 4px; vertical-align: 1px; }
.ttl { font-size: 8pt; color: #33404d; }
.speed { background: #f4f7fa; }
.speed-h { font-weight: 800; color: #0d3b66; margin-bottom: 2px; }
.speed ul { list-style: none; margin: 0; padding: 0; columns: 1; }
.speed li { margin: 0 0 1.5px; font-size: 7.4pt; line-height: 1.25; }
.speed .ttl { font-size: 7.4pt; }
.tm { color: #0d3b66; font-weight: 700; }
.agm { background: #eef3f8; }
.ev { display: flex; gap: 10px; align-items: baseline; margin: 4px 0; padding: 5px 10px; border-radius: 5px; break-inside: avoid;
  background: #f1f3f5; border: 1px solid #dde2e7; }
.etime { font-weight: 800; min-width: 80px; color: #0d3b66; }
.ebody { flex: 1; }
.elabel { display: inline-block; font-size: 6.8pt; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; margin-right: 8px; }
.eloc { color: #55626f; font-size: 7.6pt; }
.ev-plenary { background: #0d3b66; border-color: #0d3b66; color: #fff; font-size: 9.6pt; }
.ev-plenary .etime, .ev-plenary .eloc { color: #cfe0f1; }
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
.ev-admin { background: #fff; color: #44505c; }
.foot { margin-top: 10px; font-size: 7.4pt; color: #55626f; display: flex; justify-content: space-between; }
.cover { display: flex; flex-direction: column; justify-content: center; height: 178mm; }
.cover h1 { font-size: 30pt; margin: 0 0 4px; color: #0d3b66; }
.cover h3 { font-size: 13pt; margin: 0 0 22px; color: #2a9d8f; font-weight: 600; }
.cover p { font-size: 10pt; margin: 3px 0; }
.cover .bar { height: 6px; width: 120px; background: #e76f51; border-radius: 3px; margin: 0 0 18px; }
"""


def build(prog):
    conf = esc(prog.get("conference", "Conference programme"))
    days = prog["days"]
    first, last = days[0], days[-1]
    parts = [f"<!doctype html><html><head><meta charset='utf-8'><title>{conf} programme</title><style>{CSS}</style></head><body>"]
    parts.append(
        f'<section class="cover"><div class="bar"></div><h1>{conf}</h1>'
        f'<h3>Programme &middot; Australasian Evolution Society &amp; SASB &middot; University of Wollongong</h3>'
        f'<p>{esc(first["label"])} &ndash; {esc(last["label"])}</p>'
        f'<p>Interactive schedule with a live &ldquo;now &amp; next&rdquo; view and your own starred talks: <b>{SITE}</b></p>'
        f'<p>Times are local Wollongong time. Programme last updated {esc(prog.get("updated", ""))}; please check the website for changes.</p>'
        f'<p style="margin-top:16px"><span class="stu">Student</span> and a dashed orange edge mark student talks. '
        f'Rooms are numbered 1 (square), 2 (circle), 3 (leaf).</p></section>'
    )
    for d in days:
        parts.append(f'<section class="day"><div class="dayhead"><h2>{esc(d["label"])}</h2><span>{conf}</span></div>')
        for it in d["items"]:
            parts.append(parallel(it) if it["type"] == "parallel" else event(it))
        parts.append(f'<div class="foot"><span>{conf}</span><span>Live version: {SITE}</span></div></section>')
    parts.append("</body></html>")
    return "".join(parts)


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
