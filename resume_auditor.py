"""
Resume Auditor Agent
---------------------
Scans the current LaTeX resume against your career context and target goals,
identifying mistakes, inconsistencies, and formatting/style violations.
Writes the findings to data/resume_audit_results.json.

Usage:
    python resume_auditor.py --goal "AI Engineer"
"""

import os
import sys
import json
import argparse
import datetime
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List

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
ENV_FILE = BASE_DIR / ".env"
AUDIT_RESULTS_FILE = DATA_DIR / "resume_audit_results.json"

load_dotenv(ENV_FILE)

# --- Pydantic Schemas for Structured Response ----------------------------------
class AuditFinding(BaseModel):
    description: str = Field(description="Description of the issue, discrepancy, mistake, or improvement opportunity.")
    severity: str = Field(description="Severity of the issue: 'critical' (breaks compilation or strict rules), 'warning' (inconsistencies, missing details), or 'suggestion' (stylistic tweaks, better formatting).")
    location: str = Field(description="File location (e.g., approximate line number, line text, or section name) where the issue is found.")
    recommended_correction: str = Field(description="Specific, actionable correction or rewrite to resolve the issue.")

class ResumeAudit(BaseModel):
    overall_quality_score: int = Field(description="Overall quality score of the resume from 0 to 100 based on target alignment and correctness.")
    general_feedback: str = Field(description="High-level feedback and assessment of the resume against the target goals.")
    findings: List[AuditFinding] = Field(description="List of specific issues, mistakes, or suggestions found.")

# --- Helpers ------------------------------------------------------------------
def get_gemini_client():
    """Initialize Google GenAI client."""
    from google import genai
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY not found in environment or .env file.")
        sys.exit(1)
    return genai.Client(api_key=api_key)

def load_profile_data() -> tuple[str, str, Path]:
    """Load the LaTeX resume and career context files based on user config."""
    config_file = DATA_DIR / "user_config.json"
    resume_path = BASE_DIR / "resumes" / "Resume.tex"
    context_path = BASE_DIR / "resumes" / "career_context.md"

    if config_file.exists():
        try:
            config = json.loads(config_file.read_text(encoding="utf-8"))
            if "resume_file_path" in config:
                resume_path = BASE_DIR / config["resume_file_path"]
            if "context_file_path" in config:
                context_path = BASE_DIR / config["context_file_path"]
        except Exception as e:
            print(f"[WARN] Error loading user_config.json: {e}. Using defaults.")

    resume_content = ""
    if resume_path.exists():
        resume_content = resume_path.read_text(encoding="utf-8")
    else:
        print(f"[ERROR] Resume file not found at {resume_path}")
        sys.exit(1)

    context_content = ""
    if context_path.exists():
        context_content = context_path.read_text(encoding="utf-8")
    else:
        print(f"[WARN] Context file not found at {context_path}")

    return resume_content, context_content, resume_path

# --- Auditor Logic -----------------------------------------------------------
def audit_resume(goal: str) -> ResumeAudit:
    """Audit the active resume content against target goal and career context."""
    resume_content, context_content, resume_path = load_profile_data()
    client = get_gemini_client()

    current_time = datetime.datetime.now().strftime("%B %Y")

    system_instruction = f"""You are a professional resume auditor, technical editor, and recruiter.
Your objective is to inspect the candidate's LaTeX resume and cross-reference it with their career context file and target career goal to identify all discrepancies, formatting errors, styling infractions, and quality improvements.

STRICT AUDIT RULES:
1. **Copilot Studio Constraint**: The TCS Copilot Studio agent MUST be described as 100% no-code. It should NEVER imply it was built with Python, LangChain, or Gemini API.
2. **Experience Calculation**: The candidate joined TCS in May 2024. The current time is {current_time}. Calculate experience duration precisely (~24 months / 2 years as of May 2026). Ensure consistency across summary and dates.
3. **LaTeX Escape Syntax**: Look for math symbols used incorrectly outside math mode, particularly `\\sim` (tilde/about) or `\\approx`. In LaTeX text, `\\sim` must be inside math delimiters, e.g., `$\\sim$`. Using `\\sim` in regular text causes compilation errors.
4. **Consistency check**: Make sure project tech stacks and responsibilities in the resume align with actual knowledge, projects, and learning statuses in the career context file. Do not invent/fabricate experience.
5. **Aesthetics & Readability**: Identify repetitive skills, visual clutter, or poorly formatted bullet points.
"""

    prompt = f"""Here is my target goal: "{goal}"

Here is my current LaTeX resume:
\"\"\"
{resume_content}
\"\"\"

Here is my master career context:
\"\"\"
{context_content}
\"\"\"

Perform a deep audit on the LaTeX resume to identify all mistakes, inconsistencies, and improvements.
Pay close attention to LaTeX escaping (like `\\sim` outside math mode), the no-code constraint on Copilot Studio, and chronological/experience details.

Return the results in the requested structured JSON format.
"""

    print(f"[*] Auditing resume: {resume_path.name} against goal: '{goal}'...")
    from google.genai import types
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=ResumeAudit,
            temperature=0.0
        )
    )

    try:
        data = json.loads(response.text)
        return ResumeAudit(**data)
    except Exception as e:
        print(f"[ERROR] Failed to parse auditor response: {e}")
        print("Raw response:")
        print(response.text)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Audit LaTeX resume against goals and context.")
    parser.add_argument("--goal", default="AI Engineer / Gen AI Developer",
                        help="Target role/career goal to analyze against.")
    
    args = parser.parse_args()

    audit_results = audit_resume(args.goal)

    # Save results
    DATA_DIR.mkdir(exist_ok=True)
    try:
        AUDIT_RESULTS_FILE.write_text(audit_results.model_dump_json(indent=2), encoding="utf-8")
        print(f"[OK] Audit findings saved to: {AUDIT_RESULTS_FILE.relative_to(BASE_DIR)}")
    except Exception as e:
        print(f"[ERROR] Failed to save audit findings: {e}")

    # Display summary
    print("\n" + "="*60)
    print("📊 RESUME AUDIT RESULTS SUMMARY")
    print("="*60)
    print(f"Overall Quality Score: {audit_results.overall_quality_score}/100")
    print(f"General Feedback:      {audit_results.general_feedback}")
    print("-"*60)
    print(f"Detected {len(audit_results.findings)} findings:")
    for idx, finding in enumerate(audit_results.findings, 1):
        print(f"\n{idx}. [{finding.severity.upper()}] @ {finding.location}")
        print(f"   Issue:      {finding.description}")
        print(f"   Suggestion: {finding.recommended_correction}")
    print("="*60)

if __name__ == "__main__":
    main()
