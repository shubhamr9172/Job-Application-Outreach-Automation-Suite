import json
from pathlib import Path

def main():
    tracker_path = Path("data/jobs_tracker.json")
    with open(tracker_path, "r", encoding="utf-8") as f:
        jobs = json.load(f)
    print(f"Total jobs: {len(jobs)}")
    lengths = [len(j.get("description", "")) for j in jobs]
    print(f"Max len: {max(lengths)}")
    print(f"Non-empty descriptions: {len([l for l in lengths if l > 0])}")
    for i, j in enumerate(jobs[:5]):
        print(f"{i}: {j.get('title')} at {j.get('company')} (len: {len(j.get('description', ''))})")

if __name__ == "__main__":
    main()
