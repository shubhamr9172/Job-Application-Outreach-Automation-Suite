import json
from pathlib import Path

def main():
    tracker_path = Path("data/jobs_tracker.json")
    with open(tracker_path, "r", encoding="utf-8") as f:
        jobs = json.load(f)
        
    for i, j in enumerate(jobs):
        desc = j.get("description", "")
        if len(desc) > 300:
            print(f"Index {i}: {j.get('title')} at {j.get('company')} (Desc len: {len(desc)})")
            print(f"Link: {j.get('link')}")
            print(f"Snippet: {desc[:100]}...\n")

if __name__ == "__main__":
    main()
