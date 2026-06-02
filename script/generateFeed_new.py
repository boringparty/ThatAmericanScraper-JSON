#!/usr/bin/env python3

import json
import os
from datetime import timezone
from email.utils import parsedate_to_datetime, format_datetime
from xml.etree.ElementTree import Element, SubElement, ElementTree, register_namespace

# ---------------- CONFIG ----------------

DATA_FILE = "data/data.json"
OUTPUT_FILE = "feed/new.xml"

FEED_TITLE = "That American Scraper - New Episodes"
FEED_LINK = "https://www.thisamericanlife.org/"
FEED_DESCRIPTION = "Latest This American Life episodes, newest first."

# Set to None if you want every episode in the feed.
# 50 is safer for podcast/RSS readers.
MAX_ITEMS = 50

# ---------------- XML NAMESPACES ----------------

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ATOM_NS = "http://www.w3.org/2005/Atom"

register_namespace("itunes", ITUNES_NS)
register_namespace("atom", ATOM_NS)

# ---------------- HELPERS ----------------

def parse_rfc2822_date(value):
    if not value:
        return None

    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def rss_date(dt):
    if not dt:
        return None

    return format_datetime(dt)


def safe_text(value):
    if value is None:
        return ""

    return str(value).strip()


def best_pub_date(episode):
    """
    For a 'new episodes' feed, original_air_date is the important date.
    published_dates may include rebroadcasts/reposts, which is more useful
    for an 'all' or 'oldies' style feed.
    """
    return parse_rfc2822_date(episode.get("original_air_date"))


def add_text(parent, tag, text):
    el = SubElement(parent, tag)
    el.text = safe_text(text)
    return el


def add_itunes_text(parent, tag, text):
    el = SubElement(parent, f"{{{ITUNES_NS}}}{tag}")
    el.text = safe_text(text)
    return el


# ---------------- LOAD DATA ----------------

with open(DATA_FILE, "r", encoding="utf-8") as f:
    episodes = json.load(f)

# Keep only episodes that have audio and a usable date.
episodes = [
    ep for ep in episodes
    if ep.get("download") and best_pub_date(ep)
]

# Newest first.
episodes.sort(key=best_pub_date, reverse=True)

if MAX_ITEMS is not None:
    episodes = episodes[:MAX_ITEMS]

# ---------------- BUILD RSS ----------------

rss = Element("rss", {
    "version": "2.0",
    "xmlns:itunes": ITUNES_NS,
    "xmlns:atom": ATOM_NS,
})

channel = SubElement(rss, "channel")

add_text(channel, "title", FEED_TITLE)
add_text(channel, "link", FEED_LINK)
add_text(channel, "description", FEED_DESCRIPTION)
add_text(channel, "language", "en-us")
add_text(channel, "generator", "generateFeed_new.py")

atom_link = SubElement(channel, f"{{{ATOM_NS}}}link")
atom_link.set("href", "https://raw.githubusercontent.com/boringparty/ThatAmericanScraper-JSON/refs/heads/main/feed/new.xml")
atom_link.set("rel", "self")
atom_link.set("type", "application/rss+xml")

add_itunes_text(channel, "author", "This American Life")
add_itunes_text(channel, "summary", FEED_DESCRIPTION)
add_itunes_text(channel, "explicit", "false")

if episodes:
    latest_dt = best_pub_date(episodes[0])
    add_text(channel, "lastBuildDate", rss_date(latest_dt))

    image = episodes[0].get("image") or {}
    image_url = image.get("url")

    if image_url:
        itunes_image = SubElement(channel, f"{{{ITUNES_NS}}}image")
        itunes_image.set("href", image_url)

        image_el = SubElement(channel, "image")
        add_text(image_el, "url", image_url)
        add_text(image_el, "title", FEED_TITLE)
        add_text(image_el, "link", FEED_LINK)

for episode in episodes:
    item = SubElement(channel, "item")

    number = safe_text(episode.get("number"))
    title = safe_text(episode.get("title"))
    episode_title = f"{number}: {title}" if number else title

    episode_url = safe_text(episode.get("episode_url"))
    download_url = safe_text(episode.get("download"))
    synopsis = safe_text(episode.get("synopsis"))

    pub_dt = best_pub_date(episode)

    add_text(item, "title", episode_title)
    add_text(item, "link", episode_url)
    add_text(item, "guid", episode_url)
    add_text(item, "description", synopsis)
    add_text(item, "pubDate", rss_date(pub_dt))

    add_itunes_text(item, "title", episode_title)
    add_itunes_text(item, "summary", synopsis)
    add_itunes_text(item, "explicit", "true" if episode.get("explicit") else "false")

    if number:
        add_itunes_text(item, "episode", number)

    image = episode.get("image") or {}
    image_url = image.get("url")

    if image_url:
        itunes_image = SubElement(item, f"{{{ITUNES_NS}}}image")
        itunes_image.set("href", image_url)

    enclosure = SubElement(item, "enclosure")
    enclosure.set("url", download_url)
    enclosure.set("type", "audio/mpeg")
    enclosure.set("length", "0")

# ---------------- WRITE FILE ----------------

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

tree = ElementTree(rss)
tree.write(OUTPUT_FILE, encoding="utf-8", xml_declaration=True)

print(f"Wrote {OUTPUT_FILE} with {len(episodes)} episodes.")
