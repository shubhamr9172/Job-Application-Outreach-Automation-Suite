"""
Job Description Analyzer Agent (Agent 02)
------------------------------------------
Analyzes job descriptions against the candidate's resume (Resume.tex) and
career context (# Shubham — Career Context File.md), computing match scores,
skills lists, resume recommendations, and potential interview questions.

Usage:
    python jd_analyzer.py --jd-text "Job Description content..."
    python jd_analyzer.py --jd-file path/to/jd.txt
"""

import os
import sys
import io
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

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

load_dotenv(ENV_FILE)

# Pydantic schema for structured output from Gemini
class JobAnalysis(BaseModel):
    company_name: str = Field(description="Name of the hiring company or Agency.")
    role_title: str = Field(description="Job title / role name.")
    seniority_level: str = Field(description="Target seniority level: Junior, Mid, Senior, Lead, or Principal.")
    suitability_score: int = Field(description="Suitability rating from 0 to 100 based on comparison with candidate's profile.")
    matching_skills: List[str] = Field(description="Technical skills requested in the JD that the candidate already has.")
    missing_skills: List[str] = Field(description="Technical skills requested in the JD that the candidate does not have or needs to highlight.")
    key_responsibilities: List[str] = Field(description="Top 3-5 core duties / responsibilities.")
    resume_suggestions: List[str] = Field(description="Concrete editing recommendations for the LaTeX resume (e.g., 'Update skills section to highlight X', 'Add Y to Project Z').")
    typical_interview_questions: List[str] = Field(description="3-5 typical technical interview questions based on the role and stack.")

def get_gemini_client():
    """Initialize Google GenAI client."""
    from google import genai
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY not found in environment or .env file.")
        sys.exit(1)
    return genai.Client(api_key=api_key)

def load_profile_data() -> tuple[str, str]:
    """Load the LaTeX resume and career context files."""
    # Find user config to see custom paths
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
        print(f"[WARN] Resume file not found at {resume_path}")

    context_content = ""
    if context_path.exists():
        context_content = context_path.read_text(encoding="utf-8")
    else:
        print(f"[WARN] Context file not found at {context_path}")

    return resume_content, context_content

def analyze_job_description(jd_text: str) -> JobAnalysis:
    """Analyze job description text against candidate resume and career context."""
    resume_content, context_content = load_profile_data()
    client = get_gemini_client()

    prompt = f"""You are a professional recruitment AI agent.
Analyze the following Job Description against the candidate's current LaTeX resume and their additional career context.

Candidate's LaTeX Resume:
\"\"\"
{resume_content}
\"\"\"

Candidate's Career Context:
\"\"\"
{context_content}
\"\"\"

Job Description:
\"\"\"
{jd_text}
\"\"\"

Tasks:
1. Identify the company name and role title.
2. Estimate the seniority level (Junior, Mid, Senior, Lead, Principal).
3. Compute a suitability match score (0-100) based on tech stack, experience, and domain alignment.
4. Extract matching skills between candidate profile and JD.
5. Extract missing skills that are required by the JD but not found or not highlighted in the candidate's profile.
6. Extract key responsibilities of the role.
7. Formulate 3-5 concrete suggestions for updates to Resume.tex that will optimize the candidate's resume for this specific job.
8. Generate 3-5 typical technical interview questions targeted to this job's requirements and stack that the candidate should prepare.

Provide the response in the requested JSON structure.
"""

    print("[*] Contacting Gemini for JD analysis...")
    from google.genai import types
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=JobAnalysis,
            temperature=0.0
        )
    )

    try:
        data = json.loads(response.text)
        return JobAnalysis(**data)
    except Exception as e:
        print(f"[ERROR] Failed to parse Gemini response: {e}")
        print("Raw text returned:")
        print(response.text)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Analyze a Job Description against candidate resume and career context.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--jd-text", help="Raw job description text to analyze.")
    group.add_argument("--jd-file", help="Path to a text file containing the job description.")
    
    args = parser.parse_args()

    if args.jd_file:
        jd_path = Path(args.jd_file)
        if not jd_path.exists():
            print(f"[ERROR] Job Description file not found at {jd_path}")
            sys.exit(1)
        jd_text = jd_path.read_text(encoding="utf-8")
    else:
        jd_text = args.jd_text

    analysis = analyze_job_description(jd_text)

    print("\n" + "="*50)
    print("📋 JOB ANALYSIS RESULTS")
    print("="*50)
    print(f"Company:         {analysis.company_name}")
    print(f"Role Title:      {analysis.role_title}")
    print(f"Seniority Level: {analysis.seniority_level}")
    print(f"Match Score:     {analysis.suitability_score}/100")
    print("-"*50)
    print("✅ Matching Skills:")
    for skill in analysis.matching_skills:
        print(f"  - {skill}")
    print("\n❌ Missing Skills:")
    for skill in analysis.missing_skills:
        print(f"  - {skill}")
    print("-"*50)
    print("📌 Key Responsibilities:")
    for resp in analysis.key_responsibilities:
        print(f"  - {resp}")
    print("-"*50)
    print("💡 LaTeX Resume Suggestions:")
    for sug in analysis.resume_suggestions:
        print(f"  - {sug}")
    print("-"*50)
    print("❓ Typical Interview Questions:")
    for q in analysis.typical_interview_questions:
        print(f"  - {q}")
    print("="*50)

if __name__ == "__main__":
    main()
