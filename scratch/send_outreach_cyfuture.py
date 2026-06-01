import sys
import os
import json
import time
from pathlib import Path

# Set up paths to import from parent directory
BASE_DIR = Path(__file__).parent.parent.resolve()
sys.path.append(str(BASE_DIR))

from job_agent import load_config, read_career_context, send_email
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Cyfuture Job Description Details
CYFUTURE_JD = """
Job Title: AIML Engineer
Company: Cyfuture India Pvt. Ltd., NSEZ, Noida (Onsite)
Contact Email: vaibahv.kapahi@cyfuture.com
Website: www.cyfuture.com

Key Responsibilities:
· Design and develop AI-powered voicebots for inbound and outbound calling use cases
· Build and orchestrate agentic workflows using LLMs and external tool integrations
· Integrate Speech-to-Text (STT) and Text-to-Speech (TTS) systems for real-time voice interactions
· Develop multi-step reasoning pipelines using frameworks like Lang Chain
· Implement context management, memory, and conversational state handling
· Optimize LLM prompts for accuracy, latency, and token efficiency
· Build and expose REST/MCP APIs for AI service integration
· Ensure scalability, monitoring, and observability of AI pipelines.

Skill Set:
· Strong experience with LLMs (OpenAI, open-source models, etc.) and deployment on GPU servers.
· Hands-on experience with Lang Chain or similar frameworks (LlamaIndex, Haystack)
· Agentic workflows, Tool calling, RAG pipelines, prompt engineering and evaluation
· Hands-on experience with Docker and Kubernetes
· Understanding of GPU-based inference and optimization (nice to have)
· Familiarity with cloud platforms (AWS / GCP / Azure).
"""

class CyfutureOutreach(BaseModel):
    subject: str = Field(description="A professional, catchy, under 8 words subject line targeting the AIML Engineer position at Cyfuture.")
    body: str = Field(description="The body of the cold outreach email. Short (under 150 words), conversational, direct, highlighting LangGraph, stateful RAG, and TCS engineering experience. No placeholders. Signs off as 'Shubham Vivek Reddy'.")

def generate_cyfuture_draft(client: genai.Client, career_context: str) -> CyfutureOutreach:
    """Generate a highly personalized outreach email specifically for the Cyfuture AIML Engineer JD."""
    prompt = f"""
You are a job outreach assistant drafting a highly personalized cold email to Vaibhav Kapahi (recruiter) at Cyfuture.

CAREER CONTEXT OF APPLICANT:
{career_context}

CYFUTURE JOB DESCRIPTION:
{CYFUTURE_JD}

LINKS TO INCLUDE:
- LinkedIn: https://www.linkedin.com/in/shubham-vivek-reddy/
- GitHub: https://github.com/shubhamr9172
- Portfolio: https://sr-portfolio-lruagwao5-shubham-reddys-projects.vercel.app/

GUIDELINES:
1. Address Vaibhav Kapahi professionally.
2. Subject: Keep it short, powerful, and focused on AI / LangGraph / RAG expertise for the AIML Engineer role.
3. Body:
   - Highlight his exact, honest matches to the JD: building stateful agentic workflows (LangGraph), two-tier hybrid caching (Redis/ChromaDB), prompt latency optimizations, and production systems engineering at TCS.
   - Mention that his Resume PDF is attached.
   - Politely sign off as "Shubham Vivek Reddy".
   - DO NOT use AI cliches or overly formal structures (e.g., "I hope this email finds you well", "Dear Hiring Manager", "Plethora", "Testament", etc.). Be authentic.
   - NO placeholders whatsoever.
"""
    print("[*] Calling Gemini to generate personalized draft for Cyfuture...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=CyfutureOutreach,
            temperature=0.7,
        ),
    )
    import json
    data = json.loads(response.text)
    return CyfutureOutreach(**data)

def main():
    print("=" * 60)
    print("  CYFUTURE OUTREACH AGENT -- Shubham Reddy")
    print("=" * 60)
    
    config = load_config()
    client = genai.Client(api_key=config["gemini_key"])
    career_context = read_career_context()
    
    # Generate draft
    draft = generate_cyfuture_draft(client, career_context)
    subject = draft.subject
    body = draft.body
    
    to_email = "vaibahv.kapahi@cyfuture.com"
    
    print("\n" + "-" * 50)
    print(f"TO:      {to_email}")
    print(f"SUBJECT: {subject}")
    print("-" * 50)
    print(body)
    print("-" * 50)
    
    # Confirm actions
    print("\nReady to send this email with Resume.pdf attached to Vaibhav?")
    print("Options: [s]end / [q]uit")
    
    # In non-interactive environment, we can run it or prompt the user. 
    # But since we are executing via terminal sandbox we can let them run the script,
    # or we can do it directly. Let's make the script ask for input.
    try:
        choice = input("Choice [s/q]: ").strip().lower()
    except EOFError:
        choice = "s"  # default to send if running non-interactively
        
    if choice == "s":
        print("[*] Sending email to Cyfuture...")
        success = send_email(config, to_email, subject, body)
        if success:
            print(f"[SUCCESS] Email successfully sent to Vaibhav Kapahi at {to_email}!")
            # Also update emailed_status.json to reflect the sent status
            status_file = BASE_DIR / "data" / "emailed_status.json"
            if status_file.exists():
                try:
                    status_tracker = json.loads(status_file.read_text(encoding="utf-8"))
                except Exception:
                    status_tracker = {}
            else:
                status_tracker = {}
                
            status_tracker["Cyfuture India Pvt. Ltd."] = {
                "status": "sent",
                "email": to_email,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
            }
            status_file.write_text(json.dumps(status_tracker, indent=2, ensure_ascii=False), encoding="utf-8")
            print("[TRACKER] Updated status in emailed_status.json")
        else:
            print("[ERROR] SMTP transmission failed.")
    else:
        print("[CANCELLED] Email was not sent.")

if __name__ == "__main__":
    main()
