#!/usr/bin/env python3
import os
import requests
from bs4 import BeautifulSoup
import feedparser
import json
import re
import time
from datetime import timezone, timedelta, datetime
from email.utils import format_datetime, parsedate_to_datetime
from dateutil import parser

HEADERS = {"User-Agent": "Mozilla/5.0"}
OFFICIAL_RSS = "https://thisamericanlife.org/podcast/rss.xml"
DELAY = 1
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data.json")
DEFAULT_NUM_EPISODES = 1

ACT_WORDS = {
    "Prologue": 0, "One": 1, "Two": 2, "Three": 3, "Four": 4,
    "Five": 5, "Six": 6, "Seven": 7, "Eight": 8, "Nine": 9, "Ten": 10
}

ARCHIVE_KEYS = ("title", "synopsis", "acts", "explicit", "image")


def parse_any_date_str(s: str):
    try:
        dt = parsedate_to_datetime(s)
    except Exception:
        dt = parser.parse(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def to_week_sunday(dt):
    days_ahead = 6 - dt.weekday()
    sunday = dt + timedelta(days=days_ahead)
    return sunday.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)


def fetch_episode_page(url):
    try:
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        time.sleep(DELAY)
        return BeautifulSoup(r.text, "html.parser")
    except requests.RequestException:
        return None


def snapshot(ep):
    return {k: ep.get(k) for k in ARCHIVE_KEYS}


def scrape_episode(url):
    soup = fetch_episode_page(url)
    if not soup:
        return None

    title = soup.select_one("h1").get_text(strip=True) if soup.select_one("h1") else ""
    number_elem = soup.select_one(".field-name-field-episode-number .field-item")
    number = number_elem.get_text(strip=True) if number_elem else ""

    original_air_elem = soup.select_one(".field-name-field-radio-air-date .date-display-single")
    original_air_date_raw = original_air_elem.get_text(strip=True) if original_air_elem else ""
    try:
        original_air_date = format_datetime(parse_any_date_str(original_air_date_raw))
    except Exception:
        original_air_date = original_air_date_raw

    synopsis_elem = soup.select_one(".field-name-body .field-item")
    synopsis = synopsis_elem.get_text(strip=True) if synopsis_elem else ""

    download_elem = soup.select_one("li.download a")
    download = download_elem["href"] if download_elem else None
    if not download:
        return None

    clean_elem = soup.select_one(".field-name-field-notes a[href*='/clean/']")
    download_clean = clean_elem["href"] if clean_elem else None
    explicit = bool(download_clean)

    img_elem = soup.select_one("figure.tal-episode-image img")
    image_url = img_elem["src"] if img_elem else None
    credit_elem = soup.select_one("figure.tal-episode-image .credit a")
    image_credit = credit_elem.get_text(strip=True) if credit_elem else None

    acts = []
    for act in soup.select("article.node-act"):
        label_elem = act.select_one(".field-name-field-act-label .field-item")
        act_title_elem = act.select_one("h2.act-header a")
        act_title = act_title_elem.get_text(strip=True) if act_title_elem else ""
        is_prologue = "prologue" in act_title.lower()

        if not label_elem and not is_prologue:
            continue

        if is_prologue:
            act_number = 0
            number_text = "Prologue"
        else:
            word = label_elem.get_text(strip=True).replace("Act ", "").replace("Part ", "").strip()
            act_number = ACT_WORDS.get(word, int(word) if word.isdigit() else 0)
            number_text = f"Act {word}"

        act_summary_elem = act.select_one(".field-name-body .field-item")
        raw = act_summary_elem.get_text(" ", strip=True) if act_summary_elem else ""
        duration_match = re.search(r"\((\d+)\s*minutes?\)", raw)
        duration = int(duration_match.group(1)) if duration_match else None
        summary = re.sub(r"\s*\(\d+\s*minutes?\)", "", raw).strip()

        contributors = [
            a.get_text(strip=True)
            for div in act.select("div.field-name-field-contributor")
            for a in div.select("a")
        ]

        full_title = act_title if is_prologue else f"{number_text}: {act_title}"

        acts.append({
            "number": act_number,
            "number_text": number_text,
            "title": full_title,
            "summary": summary,
            "duration": duration,
            "contributors": contributors
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
        "image": {"url": image_url, "credit": image_credit},
        "acts": acts,
        "published_dates": [],
        "revisions": []
    }


def update_published_dates(episodes):
    feed = feedparser.parse(OFFICIAL_RSS)
    for item in feed.entries:
        url = item.link
        pub_date = item.get("published") or item.get("pubDate")
        if not pub_date:
            continue

        try:
            dt = parse_any_date_str(pub_date)
        except Exception:
            continue

        pub_str = format_datetime(to_week_sunday(dt))
        ep = next((e for e in episodes if e["episode_url"] == url), None)
        if ep and pub_str not in ep["published_dates"]:
            ep["published_dates"].append(pub_str)


def main():
    scrape_mode = os.environ.get("SCRAPE_MODE", "latest").lower()

    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            episodes = json.load(f)
    except FileNotFoundError:
        episodes = []

    feed = feedparser.parse(OFFICIAL_RSS)
    entries = (
        feed.entries if scrape_mode == "all"
        else feed.entries[:int(scrape_mode)] if scrape_mode.isdigit()
        else feed.entries[:DEFAULT_NUM_EPISODES]
    )

    for entry in entries:
        url = entry.link
        ep_data = scrape_episode(url)
        if not ep_data:
            continue

        existing = next((e for e in episodes if e["episode_url"] == url), None)
        if existing:
            old = snapshot(existing)
            new = snapshot(ep_data)

            if old != new:
                existing.setdefault("revisions", []).append({
                    "timestamp": format_datetime(datetime.now(timezone.utc)),
                    "data": old
                })

            for k, v in ep_data.items():
                if k not in ("published_dates", "revisions"):
                    existing[k] = v
        else:
            episodes.append(ep_data)

    update_published_dates(episodes)

    episodes.sort(key=lambda e: parse_any_date_str(e["original_air_date"]))
    for ep in episodes:
        ep["published_dates"] = sorted(set(ep["published_dates"]), key=parse_any_date_str)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(episodes, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
