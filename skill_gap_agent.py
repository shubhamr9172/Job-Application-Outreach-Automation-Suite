"""
Skill Gap & Learning Agent (Agent 05)
--------------------------------------
Analyzes missing skills and requirements from a job description, compiling
a customized study schedule and listing high-quality free learning resources.

Usage:
    python skill_gap_agent.py --missing-skills "LangGraph, MLOps, Pinecone"
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
BASE_DIR = Path(__file__).parent.resolve()
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

def generate_study_plan(missing_skills_list: list[str]) -> str:
    """Generate a learning plan based on missing skills using Gemini."""
    client = get_gemini_client()
    skills_str = ", ".join(missing_skills_list)

    prompt = f"""You are a senior developer and technical mentor AI.
The candidate is applying for an AI Engineer role but has some missing technical skills or experience areas:
Missing Skills / Gaps: {skills_str}

Tasks:
1. Formulate a structured, rapid study schedule (e.g. a 2-4 week sprint roadmap) to learn these concepts.
2. Recommend specific free resources, official documentation pages, open-source repos, and free courses/tutorials for each skill.
3. Keep the schedule practical: highlight coding exercises, hands-on tasks, and project features they can build to prove their skill.

Rules for output:
- Use markdown formatting with clear headings, lists, and bold text.
- Be specific with links/names (e.g., recommend "LangGraph Conceptual Guide in official docs", or "DeepLearning.AI LangGraph course" instead of just "read about LangGraph").
- Keep it concise, focused, and action-oriented.
"""

    print(f"[*] Compiling study plan for missing skills: {skills_str}...")
    from google.genai import types
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.4
        )
    )
    return response.text.strip()

def main():
    parser = argparse.ArgumentParser(description="Generate a customized study plan for missing skills.")
    parser.add_argument("--missing-skills", required=True, help="Comma-separated list of missing skills.")
    parser.add_argument("--output-file", help="Path to write the study plan output.")

    args = parser.parse_args()

    skills_list = [s.strip() for s in args.missing_skills.split(",") if s.strip()]
    if not skills_list:
        print("[ERROR] Please provide a valid list of missing skills.")
        sys.exit(1)

    study_plan = generate_study_plan(skills_list)

    if args.output_file:
        out_path = Path(args.output_file)
        out_path.write_text(study_plan, encoding="utf-8")
        print(f"[OK] Study plan saved to {out_path}")
    else:
        print("\n" + "="*50)
        print("📚 CUSTOMIZED STUDY PLAN")
        print("="*50)
        print(study_plan)
        print("="*50)

if __name__ == "__main__":
    main()
