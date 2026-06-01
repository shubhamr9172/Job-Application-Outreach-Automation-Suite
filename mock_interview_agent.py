"""
Mock Interview Agent (Agent 07)
--------------------------------
Handles turn-based interactive mock interview chat sessions using Gemini,
tailored specifically to the job description and candidate's resume/profile.
"""

import os
import sys
import io
import json
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
        raise ValueError("GEMINI_API_KEY not found in environment or .env file.")
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
        except Exception:
            pass

    resume_content = ""
    if resume_path.exists():
        resume_content = resume_path.read_text(encoding="utf-8")

    context_content = ""
    if context_path.exists():
        context_content = context_path.read_text(encoding="utf-8")

    return resume_content, context_content

def conduct_interview_turn(company: str, role: str, description: str, chat_history: list, user_message: str = None) -> tuple[str, list]:
    """
    Conduct a single turn of the mock interview.
    
    Args:
        company: The name of the company hiring for the role.
        role: The title of the role.
        description: The raw job description text.
        chat_history: A list of dicts with keys 'role' ('user'|'model') and 'text'.
        user_message: The candidate's reply. If None, initiates the interview.
        
    Returns:
        (interviewer_response, updated_chat_history)
    """
    resume_content, context_content = load_profile_data()
    client = get_gemini_client()
    from google.genai import types

    system_instruction = f"""You are a senior technical interviewer at {company} conducting a rigorous mock interview for the position of {role}.
The candidate's LaTeX resume is:
\"\"\"
{resume_content}
\"\"\"

The candidate's additional career context is:
\"\"\"
{context_content}
\"\"\"

The job description is:
\"\"\"
{description}
\"\"\"

Your goal is to simulate a realistic, challenging, yet encouraging mock interview:
1. Ask standard technical, system design, or behavioral questions relevant to this job description and the candidate's stated experience.
2. Ask only ONE question at a time.
3. If the candidate answers a question, critically but constructively analyze their response. Provide brief feedback pointing out any gaps, inaccuracies, or strong points, then ask a logical follow-up question or proceed to a new topic.
4. If they ask for feedback, guidance, or clarification, explain it clearly and guide them back into the interview flow.
5. Keep your responses concise (1-2 paragraphs, maximum 3) so that the user interface conversation feels interactive and natural.
"""

    updated_history = list(chat_history)
    
    # If this is the start of the interview and history is empty
    if not updated_history and not user_message:
        init_prompt = "Hello. I am ready for my mock interview. Please introduce yourself and start with the first question."
        updated_history.append({"role": "user", "text": init_prompt})
    elif user_message:
        updated_history.append({"role": "user", "text": user_message})

    # Build Content objects for the client
    contents = []
    for msg in updated_history:
        contents.append(
            types.Content(
                role=msg["role"],
                parts=[types.Part.from_text(text=msg["text"])]
            )
        )

    # Call Gemini API
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.7
        )
    )

    interviewer_response = response.text.strip()
    updated_history.append({"role": "model", "text": interviewer_response})

    return interviewer_response, updated_history
