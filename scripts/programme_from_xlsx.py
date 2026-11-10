#!/usr/bin/env python3
"""
Convert the conference programme spreadsheet into the data file that drives
the /schedule page.

    python scripts/programme_from_xlsx.py "docs/2026/EVOLUTION_IN_THE_GONG_PROGRAM_V4.xlsx"

Only the "Program" sheet is read. The other sheets (registrations etc.) hold
personal data and are never touched or copied. Keep the .xlsx out of git.

Spreadsheet conventions the script understands:
  * "Day N – Wednesday 2nd of December"   -> starts a new day
  * "Time | Room 1\\nTopic\\nChair: X | ..." -> room/session headers
    (also any row whose cells use the light-blue header fill)
  * Column A time + merged B:D cell       -> whole-conference item
    (plenary, break, welcome, dinner ... detected from wording / fill colour)
  * Column A time + B/C/D cells           -> parallel talks "Speaker: Title"
  * Orange fill (FFFFD481)                -> student talk
  * Empty cell                            -> open slot (hidden)
  * "Speed talks ... (5 minutes each):" followed by one "Speaker: Title" per line
  * Italic text in Excel (whole cell or part of it) is kept as italics.

Extra fixes that should survive every re-run (typos, species names to
italicise, venue names for rooms) live in scripts/programme_overrides.yml.
"""

import argparse
import datetime as dt
import html
import re
import sys
from pathlib import Path

try:
    import openpyxl
    import yaml
    from openpyxl.cell.rich_text import CellRichText
except ImportError:  # pragma: no cover
    sys.exit("Needs openpyxl and PyYAML:  pip install openpyxl pyyaml")

REPO = Path(__file__).resolve().parent.parent
OVERRIDES = Path(__file__).resolve().parent / "programme_overrides.yml"

STUDENT_FILL = "FFFFD481"
HEADER_FILL = "FFDDEBF7"
THEME_TYPES = {7: "plenary", 6: "break", 5: "admin", 8: "social"}
LAST_ITEM_MINUTES = 60  # length assumed for the last item of a day

MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}

KEYWORD_TYPES = [
    (r"^\s*registration", "admin"),
    (r"speed talks", "speed"),
    (r"\bplenary\b", "plenary"),
    (r"\bworkshop\b", "workshop"),
    (r"annual general meeting|\bAGM\b", "agm"),
    (r"\b(lunch|morning tea|afternoon tea|break)\b", "break"),
    (r"\b(dinner|mixer|party|drinks|social)\b", "social"),
]


# --------------------------------------------------------------------------- #
# Text helpers
# --------------------------------------------------------------------------- #

def demojibake(s):
    """Repair UTF-8 text that was mis-decoded as Mac Roman / cp1252."""
    def fix(m):
        run = m.group(0)
        for enc in ("mac_roman", "cp1252"):
            try:
                fixed = run.encode(enc).decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
            if len(fixed) < len(run):
                return fixed
        return run
    return re.sub(r"[\u0080-￿]{2,}", fix, s)


def tidy(s, replacements):
    s = demojibake(s).replace(" ", " ")
    for old, new in replacements.items():
        s = s.replace(old, new)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r" ?\n ?", "\n", s)
    return s


def cell_segments(cell, replacements):
    """Return the cell as a list of (text, italic) segments."""
    v = cell.value
    base_italic = bool(cell.font and cell.font.i)
    if isinstance(v, CellRichText):
        segs = []
        for block in v:
            if isinstance(block, str):
                segs.append((block, base_italic))
            else:
                segs.append((block.text, bool(getattr(block.font, "i", None)) or base_italic))
    elif v is None:
        return []
    else:
        segs = [(str(v), base_italic)]
    return [(tidy(t, replacements), i) for t, i in segs if t]


def segments_to_html(segs):
    out = []
    for text, italic in segs:
        t = html.escape(text, quote=False)
        out.append(f"<em>{t}</em>" if italic and t.strip() else t)
    return "".join(out).replace("</em><em>", "")


def italicise(html_text, terms):
    """Wrap each listed term in <em>, skipping text already in <em>."""
    for term in terms:
        pat = re.compile(r"(?<![\w-])" + re.escape(html.escape(term, quote=False)) + r"(?![\w-])")
        parts = re.split(r"(<em>.*?</em>)", html_text)
        html_text = "".join(p if p.startswith("<em>") else pat.sub(lambda m: f"<em>{m.group(0)}</em>", p)
                            for p in parts)
    return html_text


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s))


def html_lines(h):
    return [ln.strip() for ln in h.split("\n") if strip_tags(ln).strip()]


def split_speaker(line):
    """'Speaker: Title' -> (speaker, title). Splits on the first colon."""
    m = re.match(r"^([^:<]{2,80}?)\s*:\s*(.+)$", line, re.S)
    if not m:
        return None, line.strip()
    return m.group(1).strip(), m.group(2).strip()


# --------------------------------------------------------------------------- #
# Time helpers
# --------------------------------------------------------------------------- #

def to_minutes(t):
    return t.hour * 60 + t.minute


class Clock(str):
    """A HH:MM string that is always written quoted (Jekyll's YAML parser
    would otherwise read 09:10 as a base-60 number)."""


yaml.SafeDumper.add_representer(
    Clock, lambda d, v: d.represent_scalar("tag:yaml.org,2002:str", str(v), style='"'))


def fmt(mins):
    return Clock(f"{mins // 60:02d}:{mins % 60:02d}")


def parse_time_cell(v):
    """Return (start, end|None) in minutes, or None if the cell isn't a time."""
    if isinstance(v, dt.time):
        return to_minutes(v), None
    if isinstance(v, dt.datetime):
        return to_minutes(v.time()), None
    if isinstance(v, str):
        m = re.match(r"^\s*(\d{1,2})[:.](\d{2})\s*(?:[-–]\s*(\d{1,2})[:.](\d{2}))?\s*$", v)
        if m:
            start = int(m.group(1)) * 60 + int(m.group(2))
            end = int(m.group(3)) * 60 + int(m.group(4)) if m.group(3) else None
            return start, end
    return None


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #

def fill_of(cell):
    f = cell.fill
    if not f or f.fill_type is None:
        return None
    fg = f.fgColor
    if fg.type == "rgb":
        return fg.rgb
    if fg.type == "theme":
        return f"theme{fg.theme}"
    return None


def classify(text, fill):
    for pat, kind in KEYWORD_TYPES:
        if re.search(pat, text, re.I):
            return kind
    if fill and fill.startswith("theme"):
        return THEME_TYPES.get(int(fill[5:]), "admin")
    return "admin"


def parse_room_header(h):
    lines = html_lines(h)
    room = strip_tags(lines[0]) if lines else ""
    chair, topic = "", []
    for ln in lines[1:]:
        m = re.match(r"^Chairs?\s*:\s*(.+)$", ln, re.I)
        if m:
            chair = m.group(1).strip()
        else:
            topic.append(ln)
    return {"room": room, "topic": " ".join(topic), "chair": chair}


def parse_whole_row(h, kind):
    """Plenaries: 'Plenary Dr X\\nTitle'. Others: 'Title\\nmore detail'."""
    lines = html_lines(h)
    item = {"type": kind}
    if kind == "plenary" and lines:
        m = re.match(r"^(.*?\bPlenary)\s*:?\s*(.*?)\s*:?\s*$", lines[0], re.I)
        if m:
            item["label"] = m.group(1).strip()
            item["speaker"] = m.group(2).strip()
            item["title"] = " ".join(lines[1:])
            return item
    if kind == "workshop" and lines:
        m = re.match(r"^(.*?\bworkshop)\s*:\s*(.+)$", lines[0], re.I)
        if m:
            item["label"] = m.group(1).strip()
            item["title"] = m.group(2).strip()
            if lines[1:]:
                item["detail"] = " ".join(lines[1:])
            return item
    item["title"] = lines[0] if lines else ""
    if lines[1:]:
        item["detail"] = " ".join(lines[1:])
    return item


def parse(path, overrides):
    wb = openpyxl.load_workbook(path, rich_text=True, data_only=True)
    if "Program" not in wb.sheetnames:
        sys.exit(f"No 'Program' sheet in {path}")
    ws = wb["Program"]
    repl = overrides.get("replace") or {}
    terms = sorted(overrides.get("italicise") or [], key=len, reverse=True)
    problems = []

    def cell_html(c):
        return italicise(segments_to_html(cell_segments(c, repl)), terms)

    merged_rows = {r.min_row for r in ws.merged_cells.ranges
                   if r.min_col == 2 and r.max_col >= 4}

    # Header text (first rows) -> year, names
    top = " ".join(str(ws.cell(r, 1).value or "") for r in range(1, 6))
    year_m = re.search(r"\b(20\d\d)\b", top)
    if not year_m:
        sys.exit("Couldn't find the conference year in the first rows of the sheet.")
    year = int(year_m.group(1))

    days, day, rooms, location = [], None, {}, None

    for r in range(1, ws.max_row + 1):
        a = ws.cell(r, 1).value
        cells = {col: ws.cell(r, col) for col in (2, 3, 4)}
        filled = {col: c for col, c in cells.items()
                  if c.value is not None and str(c.value).strip()}
        if not filled:
            continue
        first_text = strip_tags(cell_html(next(iter(filled.values()))))

        # New day
        m = re.match(r"^\s*Day\s+\d+\s*[–-]\s*(\w+)\s+(\d{1,2})\w*\s+(?:of\s+)?(\w+)", first_text, re.I)
        if m:
            weekday, dnum, month = m.group(1), int(m.group(2)), MONTHS.get(m.group(3).lower())
            if not month:
                problems.append(f"row {r}: unknown month in '{first_text}'")
                continue
            date = dt.date(year, month, dnum)
            day = {"date": date.isoformat(),
                   "label": f"{weekday} {dnum} {date.strftime('%B')}",
                   "short": f"{weekday[:3]} {dnum}",
                   "items": []}
            days.append(day)
            rooms, location = {}, None
            continue

        if day is None:
            continue  # title rows / notes above the first day

        # Room / session header
        is_header = (isinstance(a, str) and a.strip().lower() == "time") or \
            any(fill_of(c) == HEADER_FILL for c in filled.values())
        if is_header:
            if len(filled) == 1 and 2 in filled and "\n" not in str(filled[2].value):
                location = first_text.strip()
                rooms = {}
            else:
                rooms = {col: parse_room_header(cell_html(c)) for col, c in filled.items()}
                location = None
            continue

        t = parse_time_cell(a)
        if t is None:
            problems.append(f"row {r}: no time in column A for '{first_text[:60]}'")
            continue
        start, end = t

        whole_row = r in merged_rows or (len(filled) == 1 and 2 in filled and not rooms)
        if whole_row:
            c = filled.get(2) or next(iter(filled.values()))
            h = cell_html(c)
            kind = classify(strip_tags(h), fill_of(c))
            item = parse_whole_row(h, kind)
            item["start"] = start
            if end is not None:
                item["end"] = end
            if location:
                item["location"] = location
            day["items"].append(item)
            continue

        # Parallel row
        block = day["items"][-1] if day["items"] else None
        if not block or block.get("type") != "parallel" or block.get("_rooms") is not rooms:
            block = {"type": "parallel", "_rooms": rooms, "rooms": {}}
            day["items"].append(block)
        for col, c in filled.items():
            h = cell_html(c)
            info = rooms.get(col) or {"room": f"Room {col - 1}", "topic": "", "chair": ""}
            track = block["rooms"].setdefault(col, dict(info, items=[]))
            text = strip_tags(h)
            if re.match(r"^\s*speed talks", text, re.I):
                lines = html_lines(h)
                heading = re.sub(r"\s*:\s*$", "", lines[0])
                each = re.search(r"\((\d+)\s*min", strip_tags(heading))
                talks = []
                for i, ln in enumerate(lines[1:]):
                    sp, ti = split_speaker(ln)
                    if not sp:
                        problems.append(f"row {r}: speed talk without 'Speaker:' -> '{strip_tags(ln)[:60]}'")
                    talk = {"speaker": sp or "", "title": ti}
                    if each:
                        talk["start"] = start + i * int(each.group(1))
                        talk["end"] = talk["start"] + int(each.group(1))
                    talks.append(talk)
                track["items"].append({"kind": "speed", "start": start, "title": heading, "talks": talks})
            elif classify(text, None) == "agm":
                track["items"].append({"kind": "agm", "start": start, "title": html_lines(h)[0]})
            else:
                sp, ti = split_speaker(h.replace("\n", " "))
                if not sp:
                    problems.append(f"row {r}: talk without 'Speaker:' -> '{text[:60]}'")
                talk = {"kind": "talk", "start": start, "speaker": sp or "", "title": ti}
                if fill_of(c) == STUDENT_FILL:
                    talk["student"] = True
                track["items"].append(talk)

    return year, days, problems


def finalise(days, overrides):
    """Work out end times, ids, and turn internal structures into plain data."""
    locations = overrides.get("rooms") or {}
    for d in days:
        starts = sorted({it["start"] for it in d["items"] if it["type"] != "parallel"} |
                        {x["start"] for it in d["items"] if it["type"] == "parallel"
                         for tr in it["rooms"].values() for x in tr["items"]})

        def next_start(s):
            later = [x for x in starts if x > s]
            return later[0] if later else None

        dkey = d["date"].replace("-", "")
        out = []
        for it in d["items"]:
            if it["type"] == "parallel":
                tracks = []
                for col in sorted(it["rooms"]):
                    tr = it["rooms"][col]
                    for x in tr["items"]:
                        nxt = next_start(x["start"])
                        x["end"] = nxt if nxt else x["start"] + 15
                        if x["kind"] == "speed":
                            x["end"] = max([x["end"]] + [t.get("end", 0) for t in x["talks"]])
                    rnum = re.search(r"\d+", tr["room"])
                    rid = f"r{rnum.group(0) if rnum else col - 1}"
                    items = []
                    for x in tr["items"]:
                        x = dict(x)
                        x["id"] = f"{dkey}-{rid}-{fmt(x['start']).replace(':', '')}"
                        if x["kind"] == "speed":
                            x["talks"] = [dict(t, id=f"{x['id']}-{i + 1}",
                                               **({"start": fmt(t["start"]), "end": fmt(t["end"])} if "start" in t else {}))
                                          for i, t in enumerate(x["talks"])]
                        x["start"], x["end"] = fmt(x["start"]), fmt(x["end"])
                        items.append(x)
                    track = {"room": tr["room"], "rid": rid}
                    if tr["topic"]:
                        track["topic"] = tr["topic"]
                    if tr["chair"]:
                        track["chair"] = tr["chair"]
                    if locations.get(tr["room"]):
                        track["location"] = locations[tr["room"]]
                    track["items"] = items
                    tracks.append(track)
                all_items = [x for tr in tracks for x in tr["items"]]
                out.append({"type": "parallel",
                            "start": min(x["start"] for x in all_items),
                            "end": max(x["end"] for x in all_items),
                            "tracks": tracks})
            else:
                it = dict(it)
                if "end" not in it:
                    nxt = next_start(it["start"])
                    if nxt:
                        it["end"] = nxt
                    else:
                        it["end"] = it["start"] + LAST_ITEM_MINUTES
                        it["open_end"] = True
                it["id"] = f"{dkey}-x-{fmt(it['start']).replace(':', '')}"
                it["start"], it["end"] = fmt(it["start"]), fmt(it["end"])
                out.append(it)
        d["items"] = out
    return days


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #

LATIN_END = re.compile(r"^[A-Z][a-z]{3,}(us|a|ae|ia|is|um|es|ops|opsis|oda|odon|ella|ax|ster|yces|ii|ix|ea|ina)$")
NOT_TAXA = {"Australia", "Asia", "America", "Africa", "Tasmania", "Data", "Diversity", "Indonesia",
            "Oceania", "Antarctica", "Zealand", "Malaysia", "India", "China", "Victoria", "Papua",
            "Analyses", "Species", "Genus", "Insecta", "Evidence", "Bayes", "Dynamics", "Genomics"}


def report(days, problems, terms):
    print("\nSummary")
    for d in days:
        talks = students = speed = 0
        for it in d["items"]:
            if it["type"] != "parallel":
                continue
            for tr in it["tracks"]:
                for x in tr["items"]:
                    if x["kind"] == "talk":
                        talks += 1
                        students += bool(x.get("student"))
                    elif x["kind"] == "speed":
                        speed += len(x["talks"])
        other = sum(1 for it in d["items"] if it["type"] != "parallel")
        print(f"  {d['label']:<28} {talks:3d} talks ({students} student)  {speed:2d} speed talks  {other:2d} other items")

    print("\nProblems")
    for p in problems or ["  none"]:
        print("  " + p if not p.startswith("  ") else p)

    # Possible taxon names not yet in italics
    known = {t.split()[0] for t in terms}
    hits = {}
    for d in days:
        for it in d["items"]:
            titles = [it.get("title", "")]
            if it["type"] == "parallel":
                titles = [x.get("title", "") for tr in it["tracks"] for x in tr["items"]] + \
                         [t["title"] for tr in it["tracks"] for x in tr["items"] for t in x.get("talks", [])]
            for t in titles:
                plain = re.sub(r"<em>.*?</em>", " ", t)
                words = re.findall(r"[A-Za-z][\w-]*", strip_tags(plain))
                for i, w in enumerate(words[1:], 1):
                    if LATIN_END.match(w) and w not in NOT_TAXA and w not in known:
                        nxt = words[i + 1] if i + 1 < len(words) and words[i + 1].islower() else ""
                        hits.setdefault(w, set()).add(f"{w} {nxt}".strip())
    print("\nPossible genus/species names not in italics (check, then add to")
    print("'italicise:' in scripts/programme_overrides.yml or italicise in Excel)")
    if hits:
        for w in sorted(hits):
            print("  - " + " | ".join(sorted(hits[w])))
    else:
        print("  none found")


# --------------------------------------------------------------------------- #

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("xlsx", help="programme spreadsheet (.xlsx)")
    ap.add_argument("-o", "--out", help="output YAML (default: _data/programme_<year>.yml)")
    args = ap.parse_args()

    overrides = {}
    if OVERRIDES.exists():
        overrides = yaml.safe_load(OVERRIDES.read_text(encoding="utf-8")) or {}

    year, days, problems = parse(args.xlsx, overrides)
    days = finalise(days, overrides)
    terms = overrides.get("italicise") or []

    data = {
        "conference": overrides.get("conference") or f"Conference {year}",
        "year": year,
        "timezone": overrides.get("timezone") or "Australia/Sydney",
        "pdf": overrides.get("pdf") or "",
        "updated": dt.date.today().isoformat(),
        "source": Path(args.xlsx).name,
        "days": days,
    }

    out = Path(args.out) if args.out else REPO / "_data" / f"programme_{year}.yml"
    header = ("# GENERATED FILE - do not edit by hand.\n"
              "# Edit the programme spreadsheet (and scripts/programme_overrides.yml), then run:\n"
              f"#   python scripts/programme_from_xlsx.py \"<spreadsheet>.xlsx\"\n\n")
    out.write_text(header + yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=1000),
                   encoding="utf-8", newline="\n")
    print(f"Wrote {out.relative_to(REPO) if out.is_relative_to(REPO) else out}")
    report(days, problems, terms)


if __name__ == "__main__":
    main()
