"""
Master Orchestrator Agent (Orchestrator)
----------------------------------------
Coordinates the execution of JD Analyzer, Cover Letter Generator, and
Skill Gap Agent. Saves the structured optimization outputs to jobs_tracker.json.

Usage:
    python orchestrator.py --link "https://jobs.workable.com/view/..." --jd-text "Raw description..."
    python orchestrator.py --link "https://jobs.workable.com/view/..." --run-all
"""

import os
import sys
import io
import json
import argparse
import datetime
from pathlib import Path
from dotenv import load_dotenv

# Force UTF-8 encoding on Windows to prevent output print crashes
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# --- Constants & Paths --------------------------------------------------------
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
TRACKER_FILE = DATA_DIR / "jobs_tracker.json"
DISCOVERED_FILE = DATA_DIR / "discovered_jobs.json"
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

# Import our agents
import jd_analyzer
import cover_letter_generator
import skill_gap_agent

def load_jobs_list(file_path: Path) -> list:
    """Load JSON jobs list."""
    if file_path.exists():
        try:
            return json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[WARN] Failed to load {file_path.name}: {e}. Returning empty list.")
    return []

def save_jobs_list(jobs: list, file_path: Path):
    """Save JSON jobs list."""
    try:
        file_path.write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"[ERROR] Failed to save {file_path.name}: {e}")

def run_pipeline(link: str, jd_text: str = None) -> dict:
    """Run the full analysis pipeline for a job by link."""
    # 1. Locate the job in either tracker or discovered files
    tracked_jobs = load_jobs_list(TRACKER_FILE)
    discovered_jobs = load_jobs_list(DISCOVERED_FILE)

    job_entry = None
    target_list = None

    # Check tracker list first
    for j in tracked_jobs:
        if j.get("link") == link:
            job_entry = j
            target_list = tracked_jobs
            break

    # Check discovered list if not found
    if not job_entry:
        for j in discovered_jobs:
            if j.get("link") == link:
                job_entry = j
                target_list = discovered_jobs
                break

    # If the job is entirely new, create a mock entry
    if not job_entry:
        print(f"[*] Job link not found in database. Creating a new entry...")
        job_entry = {
            "title": "Unknown Role",
            "company": "Unknown Company",
            "location": "Unknown",
            "link": link,
            "source": "manual",
            "description": jd_text or "",
            "status": "pending_apply",
            "added_at": datetime.datetime.now().isoformat()
        }
        tracked_jobs.append(job_entry)
        target_list = tracked_jobs

    # Use provided jd_text or fall back to description in entry
    final_jd_text = jd_text or job_entry.get("description") or ""
    if not final_jd_text.strip():
        raise ValueError("Job description text is empty. Cannot analyze without job description.")

    # 2. Run Agent 02: JD Analyzer
    print(f"[*] Step 1/3: Analyzing Job Description...")
    analysis = jd_analyzer.analyze_job_description(final_jd_text)

    # 3. Run Agent 04: Cover Letter Generator
    print(f"[*] Step 2/3: Drafting Tailored Cover Letter...")
    cover_letter = cover_letter_generator.generate_cover_letter(
        analysis.company_name,
        analysis.role_title,
        final_jd_text
    )

    # 4. Run Agent 05: Skill Gap Agent (if missing skills exist)
    study_plan = ""
    if analysis.missing_skills:
        print(f"[*] Step 3/3: Mapping Learning Roadmap...")
        study_plan = skill_gap_agent.generate_study_plan(analysis.missing_skills)
    else:
        print("[*] Step 3/3: No missing skills detected. Skipping study plan.")
        study_plan = "No missing skills identified! You are 100% matched for this role."

    # 5. Update the job entry with all metadata
    job_entry["company"] = analysis.company_name
    job_entry["title"] = analysis.role_title
    job_entry["description"] = final_jd_text
    job_entry["suitability_score"] = analysis.suitability_score
    job_entry["matching_skills"] = analysis.matching_skills
    job_entry["missing_skills"] = analysis.missing_skills
    job_entry["key_responsibilities"] = analysis.key_responsibilities
    job_entry["resume_suggestions"] = analysis.resume_suggestions
    job_entry["typical_interview_questions"] = analysis.typical_interview_questions
    job_entry["cover_letter"] = cover_letter
    job_entry["study_plan"] = study_plan
    job_entry["updated_at"] = datetime.datetime.now().isoformat()

    # Save changes
    if target_list is tracked_jobs:
        save_jobs_list(tracked_jobs, TRACKER_FILE)
    else:
        save_jobs_list(discovered_jobs, DISCOVERED_FILE)

    print(f"[OK] Pipeline complete. Job '{analysis.role_title}' at '{analysis.company_name}' updated successfully.")
    return job_entry

def main():
    parser = argparse.ArgumentParser(description="Orchestrate JD analysis, cover letter, and study plan generation.")
    parser.add_argument("--link", required=True, help="Job posting link (URL) acting as unique identifier.")
    parser.add_argument("--jd-text", help="Raw job description text (optional if job already has description in DB).")
    parser.add_argument("--run-all", action="store_true", help="Run analysis, cover letter, and learning plan stages.")

    args = parser.parse_args()

    try:
        updated_job = run_pipeline(args.link, args.jd_text)
        print(f"\nMatch Score: {updated_job.get('suitability_score')}/100")
        print(f"Resume Suggestions count: {len(updated_job.get('resume_suggestions', []))}")
        print("Done!")
    except Exception as e:
        print(f"[ERROR] Pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
