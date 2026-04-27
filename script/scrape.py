#!/usr/bin/env python3
import os
import json
import re
import requests
from bs4 import BeautifulSoup
import feedparser
import time
from datetime import timezone, datetime
from email.utils import format_datetime
from dateutil import parser

HEADERS = {"User-Agent": "Mozilla/5.0"}
OFFICIAL_RSS = "https://thisamericanlife.org/podcast/rss.xml"
DELAY = 1

OUTPUT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data.json"
)

DEFAULT_NUM_EPISODES = 1


# -------------------------
# DATE PARSING
# -------------------------
def parse_any_date_str(s: str):
    dt = parser.parse(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_rfc(dt):
    return format_datetime(dt)


# -------------------------
# SAFE UPSERT INDEX
# -------------------------
def build_index(episodes):
    return {str(e.get("number")): e for e in episodes if isinstance(e, dict)}


def upsert(index, ep_data):
    key = str(ep_data.get("number"))
    index[key] = ep_data


# -------------------------
# SCRAPER
# -------------------------
def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        time.sleep(DELAY)
        return BeautifulSoup(r.text, "html.parser")
    except requests.RequestException:
        return None


def scrape_episode(url):
    soup = fetch(url)
    if not soup:
        return None

    title = soup.select_one("h1")
    title = title.get_text(strip=True) if title else ""

    number_elem = soup.select_one(".field-name-field-episode-number .field-item")
    number = number_elem.get_text(strip=True) if number_elem else None
    if not number:
        return None

    air_elem = soup.select_one(".field-name-field-radio-air-date .date-display-single")
    air_raw = air_elem.get_text(strip=True) if air_elem else ""

    try:
        original_air_date = format_rfc(parse_any_date_str(air_raw))
    except Exception:
        original_air_date = air_raw

    synopsis_elem = soup.select_one(".field-name-body .field-item")
    synopsis = synopsis_elem.get_text(strip=True) if synopsis_elem else ""

    download_elem = soup.select_one("li.download a")
    download = download_elem["href"] if download_elem else None
    if not download:
        return None

    clean_elem = soup.select_one(".field-name-field-notes a[href*='/clean/']")
    download_clean = clean_elem["href"] if clean_elem else None

    explicit = bool(download_clean)

    img = soup.select_one("figure.tal-episode-image img")
    image_url = img["src"] if img else None

    acts = []
    for act in soup.select("article.node-act"):
        label = act.select_one(".field-name-field-act-label .field-item")
        act_title = act.select_one("h2.act-header a")

        act_title_text = act_title.get_text(strip=True) if act_title else ""

        if not label and not act_title:
            continue

        if "prologue" in act_title_text.lower():
            act_number = 0
            number_text = "Prologue"
        else:
            word = label.get_text(strip=True).replace("Act ", "").strip() if label else "0"
            try:
                act_number = int(word) if word.isdigit() else 0
            except:
                act_number = 0
            number_text = f"Act {word}"

        summary_elem = act.select_one(".field-name-body .field-item")
        raw = summary_elem.get_text(" ", strip=True) if summary_elem else ""

        duration_match = re.search(r"\((\d+)\s*minutes?\)", raw)
        duration = int(duration_match.group(1)) if duration_match else None
        summary = re.sub(r"\s*\(\d+\s*minutes?\)", "", raw).strip()

        acts.append({
            "number": act_number,
            "number_text": number_text,
            "title": act_title_text,
            "summary": summary,
            "duration": duration
        })

    return {
        "title": title,
        "number": number,
        "original_air_date": original_air_date,
        "episode_url": url,
        "explicit": explicit,
        "synopsis": synopsis,
        "download": download,
        "download_clean": download_clean,
        "image": {"url": image_url},
        "acts": acts,
        "published_dates": [],
        "revisions": []
    }


# -------------------------
# RSS SYNC
# -------------------------
def update_published_dates(episodes, index):
    feed = feedparser.parse(OFFICIAL_RSS)

    for item in feed.entries:
        url = item.link
        pub = item.get("published") or item.get("pubDate")
        if not pub:
            continue

        try:
            dt = parse_any_date_str(pub)
        except:
            continue

        ep = index.get(str(url.split("/")[-1]))
        if ep:
            ep.setdefault("published_dates", [])
            pub_str = format_rfc(dt)
            if pub_str not in ep["published_dates"]:
                ep["published_dates"].append(pub_str)


# -------------------------
# MAIN
# -------------------------
def main():
    scrape_mode = os.environ.get("SCRAPE_MODE", "latest").lower()

    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            episodes = json.load(f)
    except FileNotFoundError:
        episodes = []

    # 🔒 ALWAYS normalize
    episodes = [e for e in episodes if isinstance(e, dict)]

    index = build_index(episodes)

    feed = feedparser.parse(OFFICIAL_RSS)

    entries = (
        feed.entries if scrape_mode == "all"
        else feed.entries[:int(scrape_mode)] if scrape_mode.isdigit()
        else feed.entries[:1]
    )

    for entry in entries:
        ep_data = scrape_episode(entry.link)
        if not ep_data:
            continue

        upsert(index, ep_data)

    episodes = list(index.values())

    update_published_dates(episodes, index)

    # FINAL SORT (THIS FIXES EVERYTHING)
    episodes.sort(key=lambda e: int(e.get("number", 0)))

    # clean published dates
    for ep in episodes:
        ep["published_dates"] = sorted(set(ep.get("published_dates", [])))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(episodes, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
