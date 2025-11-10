#!/usr/bin/env python3
import json
import re
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "data.json"
OUTPUT_FILE = BASE_DIR / "episodes.md"

def parse_any_date(s: str) -> datetime:
    s = s.strip()
    try:
        return datetime.strptime(s, "%a, %d %b %Y %H:%M:%S %z").astimezone(timezone.utc)
    except ValueError:
        pass
    try:
        dt = datetime.strptime(s, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    m = re.match(r"([A-Za-z]+) (\d{1,2}), (\d{4})", s)
    if m:
        month_str, day, year = m.groups()
        dt = datetime.strptime(f"{month_str} {day} {year}", "%B %d %Y")
        return dt.replace(tzinfo=timezone.utc)
    raise ValueError(f"Unknown date format: {s}")

def format_date(s: str) -> str:
    return parse_any_date(s).strftime("%Y-%m-%d")

def build_segments(acts: list) -> str:
    parts = []
    for act in acts:
        title = act.get("title", "").strip()
        if not title:
            continue
        if ":" not in title and act.get("number_text"):
            title = f"{act['number_text']}: {title}"
        parts.append(title.replace("\n", " ").strip())
    return "; ".join(parts)

def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        episodes = json.load(f)

    # Sort by episode number ascending (numeric)
    episodes.sort(key=lambda e: int(e["number"]))

    rows = []
    for ep in episodes:
        title = f"[{ep['number']}: {ep['title']}]({ep['episode_url']})"
        date = format_date(ep["original_air_date"])
        dl = f"[dl]({ep['download']})" if ep.get("download") else "-"
        clean = f"[dl]({ep['download_clean']})" if ep.get("download_clean") else "-"
        segments = build_segments(ep.get("acts", []))
        rows.append(f"{title}|{date}|{dl}|{clean}|{segments}")

    header = "Title|Release Date|Download|Clean|Segments\n---|:-:|:-:|:-:|-|"
    markdown = "\n".join([header] + rows)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(markdown + "\n")

if __name__ == "__main__":
    main()
