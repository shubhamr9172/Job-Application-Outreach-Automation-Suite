import json
from pathlib import Path

def main():
    tracker_path = Path("data/jobs_tracker.json")
    if not tracker_path.exists():
        print("jobs_tracker.json does not exist")
        return
    
    with open(tracker_path, "r", encoding="utf-8") as f:
        jobs = json.load(f)
        
    analyzed = [j for j in jobs if "suitability_score" in j]
    print(f"Total jobs: {len(jobs)}")
    print(f"Analyzed jobs: {len(analyzed)}")
    for j in analyzed:
        print(f"- {j.get('title')} at {j.get('company')}: {j.get('suitability_score')}% match")

if __name__ == "__main__":
    main()
