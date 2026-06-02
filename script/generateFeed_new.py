#!/usr/bin/env python3

import json
import os
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.sax.saxutils import escape

# -------------------------
# CONFIG
# -------------------------

INPUT_FILE = "data/data.json"
OUTPUT_FILE = "feed/new.xml"

FEED_TITLE = "New TAL Feed"
FEED_LINK = "https://www.thisamericanlife.org"
FEED_DESCRIPTION = "All episodes, newest first"

# -------------------------
# XML HELPERS
# -------------------------

def xml_escape(value):
    if value is None:
        return ""

    return escape(str(value).strip(), {
        '"': "&quot;",
        "'": "&apos;",
    })


def cdata(value):
    if value is None:
        value = ""

    text = str(value).strip()

    # Prevent accidental CDATA breakage
    text = text.replace("]]>", "]]]]><![CDATA[>")

    return f"<![CDATA[{text}]]>"


def clean_html(value):
    if value is None:
        return ""

    text = str(value).strip()

    # Optional light cleanup
    text = re.sub(r"\s+", " ", text)

    return text


# -------------------------
# DATE PARSER
# -------------------------

def parse_date(value):
    if not value:
        return None

    value = str(value).strip()

    # RSS / RFC822
    try:
        dt = parsedate_to_datetime(value)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    # ISO fallback
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        pass

    return None


def rss_date(dt):
    if not dt:
        return ""

    return dt.strftime("%a, %d %b %Y %H:%M:%S %z")


def episode_date(episode):
    """
    For the new/all episodes feed, use original_air_date.

    This keeps actual newest episodes at the top instead of pushing old
    rebroadcasts upward because of newer repost/published dates.
    """
    return parse_date(episode.get("original_air_date"))


# -------------------------
# EPISODE HELPERS
# -------------------------

def get_episode_number(episode):
    number = episode.get("number")

    if number is None:
        return ""

    return str(number).strip()


def get_title(episode):
    number = get_episode_number(episode)
    title = str(episode.get("title") or "").strip()

    if number and title:
        return f"{number}: {title}"

    return title or number


def get_guid(episode):
    return (
        episode.get("episode_url")
        or episode.get("download")
        or get_title(episode)
    )


def build_item(episode):
    title = get_title(episode)
    link = episode.get("episode_url") or ""
    guid = get_guid(episode)
    description = clean_html(episode.get("synopsis"))
    download = episode.get("download") or ""
    number = get_episode_number(episode)

    dt = episode_date(episode)
    pub_date = rss_date(dt)

    image = episode.get("image") or {}
    image_url = image.get("url") or ""

    item = f"""    <item>
      <title>{cdata(title)}</title>
      <link>{xml_escape(link)}</link>
      <guid isPermaLink="false">{xml_escape(guid)}</guid>
      <description>{cdata(description)}</description>
      <pubDate>{xml_escape(pub_date)}</pubDate>
      <enclosure url="{xml_escape(download)}" length="0" type="audio/mpeg" />
      <itunes:title>{cdata(title)}</itunes:title>
      <itunes:summary>{cdata(description)}</itunes:summary>
      <itunes:explicit>false</itunes:explicit>"""

    if number:
        item += f"""
      <itunes:episode>{xml_escape(number)}</itunes:episode>"""

    if image_url:
        item += f"""
      <itunes:image href="{xml_escape(image_url)}" />"""

    item += """
    </item>"""

    return item


# -------------------------
# MAIN
# -------------------------

def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        episodes = json.load(f)

    episodes = [
        episode
        for episode in episodes
        if episode.get("download") and episode_date(episode)
    ]

    episodes.sort(key=episode_date, reverse=True)

    if not episodes:
        raise Exception("No valid episodes found")

    latest_date = episode_date(episodes[0])
    latest_image = episodes[0].get("image") or {}
    latest_image_url = latest_image.get("url") or ""

    items_xml = "\n".join(build_item(episode) for episode in episodes)

    image_xml = ""

    if latest_image_url:
        image_xml = f"""
    <itunes:image href="{xml_escape(latest_image_url)}" />
    <image>
      <url>{xml_escape(latest_image_url)}</url>
      <title>{cdata(FEED_TITLE)}</title>
      <link>{xml_escape(FEED_LINK)}</link>
    </image>"""

    output_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>{cdata(FEED_TITLE)}</title>
    <link>{xml_escape(FEED_LINK)}</link>
    <description>{cdata(FEED_DESCRIPTION)}</description>
    <language>en-us</language>
    <lastBuildDate>{xml_escape(rss_date(latest_date))}</lastBuildDate>
    <generator>generateFeed_new.py</generator>
    <itunes:author>This American Life</itunes:author>
    <itunes:summary>{cdata(FEED_DESCRIPTION)}</itunes:summary>
    <itunes:explicit>false</itunes:explicit>{image_xml}
{items_xml}
  </channel>
</rss>
"""

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output_xml)

    print(f"Successfully generated {OUTPUT_FILE}")
    print(f"Episodes included: {len(episodes)}")


if __name__ == "__main__":
    main()
