import json
from datetime import datetime

# Correct path to input file
INPUT_FILE = "data_fixed.json"
OUTPUT_FILE = "data_fixed_sorted.json"

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

def latest_date(ep):
    dates = ep.get("published_dates", [])
    if not dates:
        return datetime.min
    parsed_dates = []
    for d in dates:
        try:
            parsed_dates.append(datetime.strptime(d, "%a, %d %b %Y %H:%M:%S +0000"))
        except ValueError:
            continue
    return max(parsed_dates) if parsed_dates else datetime.min

# sort descending (newest first)
data_sorted = sorted(data, key=latest_date, reverse=True)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(data_sorted, f, indent=2, ensure_ascii=False)
