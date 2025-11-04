import json
from datetime import datetime

with open("data_fixed.json", "r", encoding="utf-8") as f:
    data = json.load(f)

def latest_date(ep):
    # Use the most recent published_date for sorting
    dates = ep.get("published_dates", [])
    if not dates:
        return datetime.min
    # parse RFC-822 format
    parsed_dates = []
    for d in dates:
        try:
            parsed_dates.append(datetime.strptime(d, "%a, %d %b %Y %H:%M:%S +0000"))
        except ValueError:
            continue
    return max(parsed_dates) if parsed_dates else datetime.min

# sort descending (newest first)
data_sorted = sorted(data, key=latest_date, reverse=True)

with open("data_fixed_sorted.json", "w", encoding="utf-8") as f:
    json.dump(data_sorted, f, indent=2, ensure_ascii=False)
