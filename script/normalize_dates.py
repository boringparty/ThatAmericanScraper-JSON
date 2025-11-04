import json
from datetime import datetime

INPUT_FILE = "data_fixed.json"
OUTPUT_FILE = "data_fixed_sorted.json"

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

def parse_rfc822(d):
    try:
        return datetime.strptime(d, "%a, %d %b %Y %H:%M:%S +0000")
    except ValueError:
        return None

def latest_date(ep):
    dates = ep.get("published_dates", [])
    parsed_dates = [parse_rfc822(d) for d in dates if parse_rfc822(d)]
    return max(parsed_dates) if parsed_dates else datetime.min

# sort descending (newest first)
data_sorted = sorted(data, key=latest_date, reverse=True)

# debug output
print("Sorting episodes by latest published date:")
for ep in data_sorted[:10]:  # show top 10 for sanity check
    print(ep.get("title"), latest_date(ep))

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(data_sorted, f, indent=2, ensure_ascii=False)
