#!/usr/bin/env python3
import json
import re
from datetime import datetime, timezone

INPUT_FILE = "data.json"

OUTPUT_FILE_ALL = "feed_all.xml"
OUTPUT_FILE_MAIN = "feed_main.xml"
OUTPUT_FILE_CLEAN = "feed_clean.xml"


# -------------------------
# DATE PARSING
# -------------------------
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


def format_rfc822(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")


def format_duration(total_minutes: int) -> str:
    h, m = divmod(total_minutes, 60)
    return f"{h:02}:{m:02}:00"


# -------------------------
# DESCRIPTION BUILDER
# -------------------------
def build_description(ep):
    lines = [
        f'<a href="{ep["episode_url"]}">{ep["episode_url"]}</a>',
        "",
        ep["synopsis"].strip(),
        ""
    ]

    for act in ep.get("acts", []):
        lines.append(act["number_text"])
        summary = act["summary"].strip()

        if act.get("duration"):
            summary += f" ({act['duration']} minutes)"
        if act.get("contributors"):
            summary += " by " + ", ".join(act["contributors"])

        lines.append(summary)
        lines.append("")

    orig_dt = parse_any_date(ep["original_air_date"])
    lines.append(f"Originally Aired: {orig_dt.strftime('%Y-%m-%d')}")

    return "<br>\n".join(lines)


# -------------------------
# CORE ITEM BUILDER
# -------------------------
def build_item(ep, latest_pub_dt, clean=False, mode="all"):
    orig_dt = parse_any_date(ep["original_air_date"])
    total_minutes = sum(a.get("duration") or 0 for a in ep.get("acts", []))
    padded = ep["number"].zfill(4)

    # Title logic
    title_suffix = ""
    if clean:
        title_suffix += " (Clean)"
    if latest_pub_dt.year != orig_dt.year:
        title_suffix += " - Repeat"

    # Clean handling
    is_clean = clean and ep.get("download_clean")

    guid_suffix = "-C" if is_clean else ""
    guid = f"{padded}-{latest_pub_dt.strftime('%Y%m%d')}{guid_suffix}"

    enclosure = ep["download_clean"] if is_clean else ep["download"]
    explicit_val = "clean" if is_clean else ("true" if ep.get("explicit") else "false")

    # LINK LOGIC (ONLY MAIN FEED MODIFIED)
    link = ep["episode_url"]
    if mode == "main":
        link = f"{link}?{orig_dt.year}"

    return f"""    <item>
      <title><![CDATA[{ep["number"]}: {ep["title"]}{title_suffix}]]></title>
      <link>{link}</link>
      <guid>{guid}</guid>
      <itunes:season>{orig_dt.year}</itunes:season>
      <itunes:episode>{ep["number"]}</itunes:episode>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:explicit>{explicit_val}</itunes:explicit>
      <description><![CDATA[{build_description(ep)}]]></description>
      <pubDate>{format_rfc822(latest_pub_dt)}</pubDate>
      <enclosure url="{enclosure}" type="audio/mpeg"/>
      <itunes:duration>{format_duration(total_minutes)}</itunes:duration>
    </item>"""


# -------------------------
# FEED BUILDER
# -------------------------
def build_feed(episodes, mode):
    items = []

    for ep in episodes:
        if not ep.get("download"):
            continue

        latest_pub_dt = max(
            (parse_any_date(d) for d in ep.get("published_dates", [])),
            default=parse_any_date(ep["original_air_date"])
        )

        # ALL
        if mode == "all":
            items.append(build_item(ep, latest_pub_dt, clean=False, mode=mode))
            if ep.get("download_clean"):
                items.append(build_item(ep, latest_pub_dt, clean=True, mode=mode))

        # MAIN (exclude clean titles entirely)
        elif mode == "main":
            if "clean" not in ep.get("title", "").lower():
                items.append(build_item(ep, latest_pub_dt, clean=False, mode=mode))

        # CLEAN (fallback to normal if missing)
        elif mode == "clean":
            if ep.get("download_clean"):
                items.append(build_item(ep, latest_pub_dt, clean=True, mode=mode))
            else:
                items.append(build_item(ep, latest_pub_dt, clean=False, mode=mode))

    # newest first
    items.sort(
        key=lambda x: parse_any_date(
            re.search(r"<pubDate>(.*?)</pubDate>", x).group(1)
        ),
        reverse=True
    )

    return "\n".join(items)


# -------------------------
# WRITE FEED
# -------------------------
def write_feed(path, body):
    header = """<?xml version="1.0" ?>
<rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">
  <channel>
    <title>That American Archive</title>
    <link>https://www.thisamericanlife.org</link>
    <description>Auto-generated feed</description>
    <language>en</language>"""

    footer = "  </channel>\n</rss>"

    with open(path, "w", encoding="utf-8") as f:
        f.write(header + "\n")
        f.write(body + "\n")
        f.write(footer + "\n")


# -------------------------
# MAIN
# -------------------------
def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        episodes = json.load(f)

    write_feed(OUTPUT_FILE_ALL, build_feed(episodes, "all"))
    write_feed(OUTPUT_FILE_MAIN, build_feed(episodes, "main"))
    write_feed(OUTPUT_FILE_CLEAN, build_feed(episodes, "clean"))


if __name__ == "__main__":
    main()
