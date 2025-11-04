import json
from pathlib import Path

# Paths relative to the script
INPUT_FILE = Path(__file__).parent.parent / "data_fixed.json"
OUTPUT_FILE = Path(__file__).parent.parent / "data_fixed_sorted.json"

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

def episode_number(ep):
    """
    Returns the numeric episode number.
    Missing or invalid numbers are treated as 0 (bottom of the list).
    """
    try:
        return int(ep.get("number") or 0)
    except ValueError:
        return 0

# Sort descending by episode number (highest first)
data_sorted = sorted(data, key=episode_number, reverse=True)

# Optional debug output
print("Top 10 episodes after sorting by number:")
for ep in data_sorted[:10]:
    print(f"{ep.get('number', '')}: {ep.get('title', '')}")

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(data_sorted, f, indent=2, ensure_ascii=False)
