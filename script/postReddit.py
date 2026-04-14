#!/usr/bin/env python3
import os
import feedparser
import praw

FEED_URL = "https://YOUR_DOMAIN/feed.xml"
SUBREDDIT = "tomflint"


def is_clean(entry):
    return "(Clean)" in entry.get("title", "")


def build_post(entry):
    ep = entry.get("itunes_episode", "")
    title = entry.get("title", "").replace("(Clean)", "").strip()
    link = entry.get("link", "")
    desc = entry.get("description", "")
    audio = entry.get("enclosure", {}).get("url", "")

    post_title = f"#{ep}: {title}"

    post_body = f"""### [{post_title}]({link})

{desc}

---

🎧 [Download audio]({audio})
"""

    return post_title, post_body


def main():
    reddit = praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        username=os.environ["REDDIT_USERNAME"],
        password=os.environ["REDDIT_PASSWORD"],
        user_agent="tal-reddit-bot"
    )

    feed = feedparser.parse(FEED_URL)

    for entry in feed.entries:
        # skip clean episodes entirely
        if is_clean(entry):
            continue

        title, body = build_post(entry)

        reddit.subreddit(SUBREDDIT).submit(
            title=title,
            selftext=body
        )

        # only post ONE per run
        break


if __name__ == "__main__":
    main()
