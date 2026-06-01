"""
Job Application & Cold Emailing Agent
-------------------------------------
Parses Consultancies.xlsx, generates personalized cold emails using Gemini,
and sends them from your Gmail account with Resume.pdf attached.

Tracks emailed consultancies in emailed_status.json to avoid duplicates.
Allows reviewing, skipping, editing (via Notepad), or sending each email.

Usage:
    python job_agent.py
"""

import sys
import os
import io
import json
import tempfile
import subprocess
import smtplib
import datetime
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Force UTF-8 stdout/stderr on Windows to avoid cp1252 encoding crashes
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# --- Constants & Paths --------------------------------------------------------
AGENT_DIR = Path(__file__).parent.parent.parent.resolve()
DATA_DIR = AGENT_DIR / "data"
ENV_FILE = AGENT_DIR / ".env"
CONFIG_FILE = DATA_DIR / "user_config.json"

# Default fallback paths (now in subfolders)
EXCEL_PATH = DATA_DIR / "Consultancies.xlsx"
STATUS_FILE = DATA_DIR / "emailed_status.json"
RESUME_PDF = AGENT_DIR / "resumes" / "Resume.pdf"
CONTEXT_FILE = AGENT_DIR / "resumes" / "career_context.md"

# Load customized paths from config if present
if CONFIG_FILE.exists():
    try:
        config_data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        if "resume_file_path" in config_data:
            tex_path = AGENT_DIR / config_data["resume_file_path"]
            RESUME_PDF = tex_path.with_suffix(".pdf")
        if "context_file_path" in config_data:
            CONTEXT_FILE = AGENT_DIR / config_data["context_file_path"]
    except Exception as e:
        print(f"[WARN] Failed to load config path: {e}")

GEMINI_MODEL = "gemini-2.5-flash"
REPLY_TO_EMAIL = "shubhamreddy9172@gmail.com"  # Shubham's primary inbox

# --- AI Schema ----------------------------------------------------------------
class EmailDraft(BaseModel):
    subject: str = Field(description="A highly professional and catchy subject line for recruiter outreach. Keep it under 8 words.")
    body: str = Field(description="The body of the cold outreach email. Short (under 150 words), conversational, direct, and highlighting relevant skills. No placeholders (like [Name] or [Date]) in the final text.")

# --- Config & Helpers ---------------------------------------------------------
def load_config():
    """Load config and verify all variables."""
    load_dotenv(ENV_FILE)
    gemini_key = os.getenv("GEMINI_API_KEY")
    gmail_user = os.getenv("GMAIL_USER")
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD")
    
    if not gemini_key:
        print("[ERROR] GEMINI_API_KEY is not set in .env")
        sys.exit(1)
    if not gmail_user or not gmail_pass:
        print("[ERROR] GMAIL_USER or GMAIL_APP_PASSWORD not set in .env")
        sys.exit(1)
        
    return {
        "gemini_key": gemini_key,
        "gmail_user": gmail_user,
        "gmail_pass": gmail_pass.replace(" ", "")
    }

def read_career_context() -> str:
    """Read career context for Gemini generation context."""
    if CONTEXT_FILE.exists():
        return CONTEXT_FILE.read_text(encoding="utf-8")
    return "Name: Shubham Reddy\nTarget: AI / GenAI Developer\nSkills: Python, LangChain, LangGraph, RAG, Gemini API\nExperience: Systems Engineer at TCS Pune since May 2024."

def load_status() -> dict:
    """Load the emailed status JSON tracking file."""
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_status(status_data: dict):
    """Save the emailed status tracker."""
    STATUS_FILE.write_text(json.dumps(status_data, indent=2, ensure_ascii=False), encoding="utf-8")

def parse_consultancies() -> pd.DataFrame:
    """Parse Consultancies.xlsx, finding header row dynamically."""
    if not EXCEL_PATH.exists():
        print(f"[ERROR] Consultancies.xlsx not found at {EXCEL_PATH}")
        sys.exit(1)
        
    df = pd.read_excel(EXCEL_PATH, header=None)
    header_row_idx = None
    for idx, row in df.iterrows():
        if any(isinstance(val, str) and "Company Name" in val for val in row):
            header_row_idx = idx
            break
            
    if header_row_idx is None:
        print("[ERROR] Could not find header row (containing 'Company Name') in Excel sheet.")
        sys.exit(1)
        
    df_data = df.iloc[header_row_idx+1:].copy()
    df_data.columns = df.iloc[header_row_idx].tolist()
    df_data.columns = [str(c).strip() for c in df_data.columns]
    df_data = df_data.dropna(subset=["Company Name"])
    return df_data

def edit_email_body(body_text: str) -> str:
    """Open default editor (Notepad on Windows) for interactive body edits."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as tf:
        tf.write(body_text)
        temp_name = tf.name
    try:
        if sys.platform == "win32":
            subprocess.run(["notepad.exe", temp_name], check=True)
        else:
            # Fallback to nano/vi or default editor for non-Windows if needed
            editor = os.environ.get("EDITOR", "nano")
            subprocess.run([editor, temp_name], check=True)
            
        with open(temp_name, "r", encoding="utf-8") as f:
            edited = f.read()
        return edited.strip()
    except Exception as e:
        print(f"[ERROR] Failed to open editor: {e}")
        return body_text
    finally:
        try:
            os.unlink(temp_name)
        except Exception:
            pass

# --- Email & AI Actions -------------------------------------------------------
def generate_draft(client: genai.Client, career_context: str, company: str, category: str) -> EmailDraft:
    """Call Gemini with structured output configuration to draft personalized cold outreach email."""
    prompt = f"""
You are a job outreach assistant drafting a highly personalized cold email to a recruiter or accounts manager at a staffing consultancy.
Generate a professional, short, and conversion-focused cold email.

CAREER CONTEXT OF APPLICANT:
{career_context}

TARGET CONSULTANCY DETAILS:
- Company Name: {company}
- Category: {category}

LINKS TO INCLUDE IN BODY:
- LinkedIn: https://www.linkedin.com/in/shubham-vivek-reddy/
- GitHub: https://github.com/shubhamr9172
- Portfolio: https://sr-portfolio-lruagwao5-shubham-reddys-projects.vercel.app/

GUIDELINES:
1. Subject line: Keep it catchy, short (under 8 words), and focused on AI / GenAI / Python capabilities. Do NOT use generic subjects like "Job Application".
2. Email Body:
   - Personalize it by mentioning the consultancy name ({company}) and reference their category ({category}) naturally.
   - Keep it short, direct, and conversational (max 150 words). Recruiters read hundreds of emails.
   - Highlight: Python, LangGraph, LangChain, RAG Systems, Gemini API, and his Systems Engineer background at TCS.
   - Mention that his Resume PDF is attached.
   - Politely sign off as "Shubham Vivek Reddy".
   - DO NOT use AI cliches or overly formal structures (e.g., "I hope this email finds you well", "Dear Hiring Manager", "Plethora", "Testament", etc.). Be authentic.
   - Output must contain NO placeholders (e.g., [insert name]). Populate all details.
"""
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=EmailDraft,
                temperature=0.7,
            ),
        )
        # Parse JSON output using EmailDraft schema
        data = json.loads(response.text)
        return EmailDraft(**data)
    except Exception as e:
        print(f"[WARN] Failed to generate email using Gemini: {e}")
        # Return fallback email draft
        return EmailDraft(
            subject=f"AI / GenAI Developer Profile - Shubham Vivek Reddy",
            body=(
                f"Hi team,\n\n"
                f"I am reaching out to share my profile for AI and Generative AI developer roles at {company}.\n\n"
                f"Currently working as a Systems Engineer at TCS, I specialize in building end-to-end LLM applications "
                f"using Python, LangGraph, LangChain, RAG architectures, and the Gemini API. "
                f"I have attached my resume for your review.\n\n"
                f"Portfolio: https://sr-portfolio-lruagwao5-shubham-reddys-projects.vercel.app/\n"
                f"GitHub: https://github.com/shubhamr9172\n"
                f"LinkedIn: https://www.linkedin.com/in/shubham-vivek-reddy/\n\n"
                f"Regards,\nShubham Vivek Reddy"
            )
        )

def send_email(config: dict, to_email: str, subject: str, body: str) -> bool:
    """Build and send a multipart email with Resume.pdf attached."""
    if not RESUME_PDF.exists():
        print(f"[ERROR] Resume.pdf not found at {RESUME_PDF}. Compile it first.")
        return False
        
    msg = MIMEMultipart()
    msg["From"] = config["gmail_user"]
    msg["To"] = to_email
    msg["Subject"] = subject
    msg["Reply-To"] = REPLY_TO_EMAIL  # Standard Reply-To redirect
    
    msg.attach(MIMEText(body, "plain", "utf-8"))
    
    # Attach Resume.pdf
    try:
        with open(RESUME_PDF, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={RESUME_PDF.name}",
            )
            msg.attach(part)
    except Exception as e:
        print(f"[ERROR] Failed to attach Resume.pdf: {e}")
        return False

    # Connect and send
    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30)
        server.login(config["gmail_user"], config["gmail_pass"])
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"[ERROR] SMTP Send failed: {e}")
        return False

# --- Main CLI Flow -----------------------------------------------------------
def main():
    print("=" * 60)
    print("  COLD EMAIL & JOB APPLICATION AGENT")
    print("=" * 60)
    
    config = load_config()
    client = genai.Client(api_key=config["gemini_key"])
    career_context = read_career_context()
    status_tracker = load_status()
    df_consultancies = parse_consultancies()
    
    excel_companies = set()
    all_candidates = []
    
    # Process Excel consultancies
    for _, row in df_consultancies.iterrows():
        comp_name = str(row.get("Company Name", "")).strip()
        if not comp_name:
            continue
        excel_companies.add(comp_name.lower())
        
        email = str(row.get("Contact Email", "")).strip()
        website = str(row.get("Website URL", "")).strip()
        category = str(row.get("Category", "Recruitment Agency")).strip()
        if not pd.notna(row.get("Category")) or not category:
            category = "Recruitment Agency"
            
        all_candidates.append({
            "name": comp_name,
            "email": email if (pd.notna(row.get("Contact Email")) and "@" in email) else "",
            "website": website if pd.notna(row.get("Website URL")) else "",
            "category": category,
            "excel_note": str(row.get("Note", "")) if pd.notna(row.get("Note")) else ""
        })
        
    # Process approved/discovered companies from emailed_status.json that are NOT in Excel
    for comp_name, entry in status_tracker.items():
        if comp_name.lower() not in excel_companies:
            status = entry.get("status", "")
            # Only include approved/outreach candidates (exclude raw discovered or rejected)
            if status in ("pending_email", "pending_web_form", "sent", "responded", "interviewing", "skipped"):
                all_candidates.append({
                    "name": comp_name,
                    "email": entry.get("email", ""),
                    "website": entry.get("website", ""),
                    "category": entry.get("category", "Discovered Agency"),
                    "excel_note": entry.get("note", "")
                })

    # Record/sync non-email companies to status tracker to stay clean
    updated_tracker = False
    for item in all_candidates:
        comp_name = item["name"]
        email = item["email"]
        if not email or "@" not in email:
            if comp_name not in status_tracker:
                status_tracker[comp_name] = {
                    "status": "pending_web_form",
                    "email": "",
                    "website": item["website"],
                    "note": item["excel_note"],
                    "timestamp": datetime.datetime.now().isoformat()
                }
                updated_tracker = True
            elif status_tracker[comp_name].get("status") == "pending_email":
                status_tracker[comp_name]["status"] = "pending_web_form"
                updated_tracker = True
    if updated_tracker:
        save_status(status_tracker)

    # Filter candidates for pending emails (must have email, and status not sent/skipped/responded/interviewing)
    pending_emails = []
    for item in all_candidates:
        comp_name = item["name"]
        email = item["email"]
        if email and "@" in email:
            current_status = status_tracker.get(comp_name, {}).get("status")
            if not current_status:
                current_status = "pending_email"
            if current_status == "pending_email":
                pending_emails.append(item)

    # Stats calculation
    total_companies = len(all_candidates)
    total_emails = len([c for c in all_candidates if c["email"] and "@" in c["email"]])
    processed_emails = len([c for c in all_candidates if c["email"] and "@" in c["email"] and status_tracker.get(c["name"], {}).get("status") in ("sent", "skipped")])

    print(f"[LOADED] Unified list: {total_companies} companies total (Excel + Approved Discovered).")
    print(f"[LOADED] Found {total_emails} companies with valid email addresses.")
    print(f"[REPLY-TO] Directing all responses to: {REPLY_TO_EMAIL}")
    print(f"[TRACKER] Emailed/Processed: {processed_emails} / {total_emails}")
    print(f"[TRACKER] Pending emails to review: {len(pending_emails)}")
    print("-" * 60)
    
    if not pending_emails:
        print("[OK] All available consultancies with email addresses have been processed!")
        return

    # Loop through pending entries
    for i, item in enumerate(pending_emails):
        comp_name = item["name"]
        to_email = item["email"]
        category = item["category"]
        
        print(f"\n[{i+1}/{len(pending_emails)}] Preparing email for: {comp_name}")
        print(f"To:      {to_email}")
        print(f"Company: {comp_name} ({category})")
        print("[AI] Calling Gemini to generate personalized draft...")
        
        draft = generate_draft(client, career_context, comp_name, category)
        subject = draft.subject
        body = draft.body
        
        # 4-second safety delay to respect Gemini free tier API rate limits (15 RPM)
        import time
        time.sleep(4.0)
        
        while True:
            print("\n" + "-" * 50)
            print(f"SUBJECT: {subject}")
            print("-" * 50)
            print(body)
            print("-" * 50)
            
            choice = input("\nAction: [s]end / [e]dit body / [n]ext (skip) / [q]uit: ").strip().lower()
            
            if choice == "s":
                print("[*] Sending email...")
                success = send_email(config, to_email, subject, body)
                if success:
                    print(f"[OK] Email sent to {comp_name} ({to_email})")
                    status_tracker[comp_name] = {
                        "status": "sent",
                        "email": to_email,
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                    save_status(status_tracker)
                else:
                    print(f"[ERROR] Failed to send email to {comp_name}")
                break
                
            elif choice == "e":
                print("[*] Opening Notepad to edit the body... Close Notepad when finished.")
                body = edit_email_body(body)
                
            elif choice == "n":
                print(f"[*] Skipping {comp_name}")
                status_tracker[comp_name] = {
                    "status": "skipped",
                    "email": to_email,
                    "timestamp": datetime.datetime.now().isoformat()
                }
                save_status(status_tracker)
                break
                
            elif choice == "q":
                print("\n[*] Exiting job agent. Progress saved.")
                return
            else:
                print("[WARN] Invalid option. Enter s, e, n, or q.")
                
    print("\n[DONE] Finished processing all pending consultancies.")

if __name__ == "__main__":
    main()
