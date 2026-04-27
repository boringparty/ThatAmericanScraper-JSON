import json
import random
from datetime import datetime, timedelta, timezone

JSON_URL = "https://raw.githubusercontent.com/boringparty/ThatAmericanScraper-JSON/refs/heads/main/data.json"


def parse_date(s):
    return datetime.strptime(s, "%a, %d %b %Y %H:%M:%S %z")


def main():
    import requests

    data = requests.get(JSON_URL).json()

    cutoff = datetime.now(timezone.utc) - timedelta(days=365 * 10)

    old_eps = [
        ep for ep in data
        if parse_date(ep["original_air_date"]) < cutoff
    ]

    if not old_eps:
        raise Exception("No old episodes found")

    ep = random.choice(old_eps)

    ep_num = ep["number"]
    title = ep["title"]
    date = parse_date(ep["original_air_date"]).strftime("%Y-%m-%d")

    url = ep["episode_url"]
    mp3 = ep["download"]
    synopsis = ep.get("synopsis", "")

    post_title = f"[Oldies] #{ep_num} {title} ({date})"

    post_body = (
        f"We're digging through the archives! This week's episode is "
        f"[#{ep_num} {title} ({date})]({url}) "
        f"([Download]({mp3}))\n\n"
        f"{synopsis}"
    )

    csv_row = [
        "",
        post_title,
        post_body,
        "/r/thisamericanlife",
        datetime.now().strftime("%Y-%m-%d"),
        "06:00",
        "GMT-0700",
        "0", "0", "0"
    ]

    # Write output
    with open("output.csv", "w", encoding="utf-8") as f:
        f.write(",".join(csv_row))


if __name__ == "__main__":
    main()
