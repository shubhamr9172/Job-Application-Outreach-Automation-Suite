"""
Cover Letter Generator Agent (Agent 04)
----------------------------------------
Generates a highly personalized, professional cover letter tailored to a
specific job description, company name, and role title.

Usage:
    python cover_letter_generator.py --company "Luxasia" --role "AI Engineer" --jd-file path/to/jd.txt
"""

import os
import sys
import io
import json
import argparse
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
BASE_DIR = Path(__file__).parent.parent.parent.resolve()
DATA_DIR = BASE_DIR / "data"
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

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

    context_content = ""
    if context_path.exists():
        context_content = context_path.read_text(encoding="utf-8")

    return resume_content, context_content

def generate_cover_letter(company: str, role: str, jd_text: str) -> str:
    """Generate a cover letter draft using Gemini."""
    resume_content, context_content = load_profile_data()
    client = get_gemini_client()

    prompt = f"""You are a professional resume writer and career coach AI.
Generate a tailored, achievement-focused, and highly compelling Cover Letter (around 250-300 words) for the candidate.
The cover letter should directly address the company's domain, target role, and key responsibilities outlined in the Job Description.

Company Name: {company}
Role Title: {role}

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

Rules for the Cover Letter:
1. Make it professional, confident, and engaging. Avoid boring template phrases like "I am writing to express my interest". Start with a strong hook about their domain or a recent technology shift.
2. Structure:
   - Header (Date, Candidate contact info placeholder, Recipient info placeholder)
   - Salutation (Dear Hiring Team at {company}, or similar)
   - Hook: Introduce target role and connect the candidate's passion/skills to the company.
   - Body Paragraph 1: Highlight relevant Python, GenAI, and RAG/LangGraph skills, tying them directly to requirements in the JD.
   - Body Paragraph 2: Mention a concrete project or experience (like their RAG onboarding assistant or incident comment auto-generation tool) showing practical problem-solving.
   - Conclusion: Call-to-action expressing interest in an interview, closing professionally.
3. Keep the tone authentic. Do NOT sound like generic AI. Do not list every skill, only the ones that match this specific role.

Return ONLY the plain text of the cover letter. Do not include markdown headers or commentary.
"""

    print(f"[*] Generating tailored cover letter for {role} at {company}...")
    from google.genai import types
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7
        )
    )
    return response.text.strip()

def main():
    parser = argparse.ArgumentParser(description="Generate a tailored cover letter.")
    parser.add_argument("--company", required=True, help="Name of the company.")
    parser.add_argument("--role", required=True, help="Title of the role.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--jd-text", help="Raw job description text.")
    group.add_argument("--jd-file", help="Path to text file containing the job description.")
    parser.add_argument("--output-file", help="Path to write the cover letter output.")

    args = parser.parse_args()

    if args.jd_file:
        jd_path = Path(args.jd_file)
        if not jd_path.exists():
            print(f"[ERROR] Job Description file not found at {jd_path}")
            sys.exit(1)
        jd_text = jd_path.read_text(encoding="utf-8")
    else:
        jd_text = args.jd_text

    cover_letter = generate_cover_letter(args.company, args.role, jd_text)

    if args.output_file:
        out_path = Path(args.output_file)
        out_path.write_text(cover_letter, encoding="utf-8")
        print(f"[OK] Cover letter saved to {out_path}")
    else:
        print("\n" + "="*50)
        print("✍️ GENERATED COVER LETTER")
        print("="*50)
        print(cover_letter)
        print("="*50)

if __name__ == "__main__":
    main()
