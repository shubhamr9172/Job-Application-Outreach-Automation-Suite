"""
Job Application & Outreach Dashboard Server
-------------------------------------------
A lightweight, zero-dependency Python backend server using http.server.
Integrates Consultancies.xlsx and emailed_status.json to serve outreach status,
allows updating statuses/notes, and securely fetches replies from Gmail via IMAP.

Usage:
    python dashboard_server.py
"""

import sys
import os
import io
import json
import re
import imaplib
import email
from email.header import decode_header
import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

import pandas as pd
from dotenv import load_dotenv
import pypdf

# Force UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# --- Constants & Paths --------------------------------------------------------
AGENT_DIR = Path(__file__).parent.resolve()
ENV_FILE = AGENT_DIR / ".env"
EXCEL_PATH = AGENT_DIR / "Consultancies.xlsx"
DATA_DIR = AGENT_DIR / "data"
STATUS_FILE = DATA_DIR / "emailed_status.json"
DISCOVERED_FILE = DATA_DIR / "discovered_agencies.json"
USER_CONFIG_FILE = DATA_DIR / "user_config.json"
DISCOVERED_JOBS_FILE = DATA_DIR / "discovered_jobs.json"
TRACKED_JOBS_FILE = DATA_DIR / "jobs_tracker.json"
PUBLIC_DIR = AGENT_DIR / "dashboard_public"

PORT = 8000

# --- Helper Functions ---------------------------------------------------------
def load_config():
    """Load config and verify variables."""
    load_dotenv(ENV_FILE)
    gmail_user = os.getenv("GMAIL_USER")
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD")
    return {
        "gmail_user": gmail_user,
        "gmail_pass": gmail_pass.replace(" ", "") if gmail_pass else None
    }

def load_status() -> dict:
    """Load the emailed status tracker."""
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[WARN] Failed to load {STATUS_FILE}: {e}")
            return {}
    return {}

def save_status(status_data: dict):
    """Save the emailed status tracker."""
    STATUS_FILE.write_text(json.dumps(status_data, indent=2, ensure_ascii=False), encoding="utf-8")

def parse_consultancies() -> list:
    """Parse Consultancies.xlsx dynamically and return as list of dicts."""
    if not EXCEL_PATH.exists():
        return []
    try:
        df = pd.read_excel(EXCEL_PATH, header=None)
        header_row_idx = None
        for idx, row in df.iterrows():
            if any(isinstance(val, str) and "Company Name" in val for val in row):
                header_row_idx = idx
                break
                
        if header_row_idx is None:
            return []
            
        df_data = df.iloc[header_row_idx+1:].copy()
        df_data.columns = df.iloc[header_row_idx].tolist()
        df_data.columns = [str(c).strip() for c in df_data.columns]
        df_data = df_data.dropna(subset=["Company Name"])
        
        records = []
        for _, row in df_data.iterrows():
            records.append({
                "name": str(row.get("Company Name", "")).strip(),
                "email": str(row.get("Contact Email", "")).strip() if pd.notna(row.get("Contact Email")) else "",
                "website": str(row.get("Website URL", "")).strip() if pd.notna(row.get("Website URL")) else "",
                "category": str(row.get("Category", "")).strip() if pd.notna(row.get("Category")) else "Recruitment Agency",
                "excel_note": str(row.get("Note", "")).strip() if pd.notna(row.get("Note")) else ""
            })
        return records
    except Exception as e:
        print(f"[ERROR] Failed to parse Excel: {e}")
        return []

def get_clean_domain(s: str) -> str:
    """Extract clean base domain from email address or URL."""
    if not s:
        return ""
    s = s.strip().lower()
    if "@" in s:
        s = s.split("@")[-1]
    # Remove protocol and subdomains like www
    s = re.sub(r'^(https?://)?(www\d?\.)?', '', s)
    s = s.split("/")[0]
    return s

def domain_matches(d1: str, d2: str) -> bool:
    """Check if two domains match or share a primary name (e.g. randstad.in and randstad.co.in)."""
    if not d1 or not d2:
        return False
    d1 = d1.strip().lower()
    d2 = d2.strip().lower()
    if d1 == d2:
        return True
    if d1.endswith("." + d2) or d2.endswith("." + d1):
        return True
        
    # Extract base names (ignoring common extensions)
    def base_name(domain):
        parts = domain.split(".")
        common_tlds = {'com', 'in', 'co', 'net', 'org', 'info', 'biz', 'us', 'uk', 'global'}
        filtered = [p for p in parts if p not in common_tlds]
        return filtered[0] if filtered else domain
        
    b1 = base_name(d1)
    b2 = base_name(d2)
    if len(b1) > 3 and len(b2) > 3 and (b1 == b2 or b1 in b2 or b2 in b1):
        return True
    return False

def decode_mime_words(s: str) -> str:
    """Safely decode RFC 2047 MIME encoded headers."""
    if not s:
        return ""
    try:
        decoded_words = decode_header(s)
        parts = []
        for word, encoding in decoded_words:
            if isinstance(word, bytes):
                parts.append(word.decode(encoding or 'utf-8', errors='replace'))
            else:
                parts.append(str(word))
        return "".join(parts)
    except Exception:
        return str(s)

def extract_email_address(from_str: str) -> str:
    """Extract clean email address from 'From' header (e.g. 'Name <email@domain.com>')."""
    if not from_str:
        return ""
    match = re.search(r'<([^>]+)>', from_str)
    if match:
        return match.group(1).strip().lower()
    return from_str.strip().lower()

# --- HTTP Request Handler ------------------------------------------------------
class DashboardHandler(BaseHTTPRequestHandler):
    scraper_process = None
    
    def end_headers(self):
        # Restrict CORS to localhost to prevent malicious external websites from querying local data
        self.send_header('Access-Control-Allow-Origin', 'http://localhost:8000')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        # Route API Calls
        if path == "/api/status":
            self.handle_get_status()
        elif path == "/api/replies":
            self.handle_get_replies()
        elif path == "/api/discovered":
            self.handle_get_discovered()
        elif path == "/api/config":
            self.handle_get_config()
        elif path == "/api/jobs/status":
            self.handle_get_jobs_status()
        elif path == "/api/jobs/discovered":
            self.handle_get_jobs_discovered()
        else:
            # Serve Static Files
            self.handle_serve_static(path)

    def do_POST(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        if path == "/api/update":
            self.handle_post_update()
        elif path == "/api/test-imap":
            self.handle_test_imap()
        elif path == "/api/discovered/approve":
            self.handle_discovered_approve()
        elif path == "/api/discovered/reject":
            self.handle_discovered_reject()
        elif path == "/api/config":
            self.handle_post_config()
        elif path == "/api/config/parse-resume":
            self.handle_parse_resume()
        elif path == "/api/jobs/update":
            self.handle_post_jobs_update()
        elif path == "/api/jobs/discovered/approve":
            self.handle_jobs_approve()
        elif path == "/api/jobs/discovered/reject":
            self.handle_jobs_reject()
        elif path == "/api/jobs/scrape":
            self.handle_jobs_scrape()
        elif path == "/api/jobs/external-add":
            self.handle_external_add()
        else:
            self.send_error(404, "Endpoint not found")

    # --- API Handlers ----------------------------------------------------------
    def handle_get_status(self):
        """Unified list of all consultancies from Excel merged with emailed_status.json."""
        consultancies = parse_consultancies()
        statuses = load_status()
        
        merged = []
        excel_names = set()
        for item in consultancies:
            name = item["name"]
            excel_names.add(name.lower())
            # Look up in emailed_status.json
            status_entry = statuses.get(name, {})
            
            # Determine status: default to 'pending_email' if email is available, else 'pending_web_form'
            default_status = "pending_email" if "@" in item["email"] else "pending_web_form"
            current_status = status_entry.get("status", default_status)
            
            # Use JSON note if available, else fallback to Excel note
            note = status_entry.get("note", item["excel_note"])
            timestamp = status_entry.get("timestamp", "")
            
            merged.append({
                "name": name,
                "email": item["email"],
                "website": item["website"],
                "category": item["category"],
                "status": current_status,
                "note": note,
                "timestamp": timestamp
            })
            
        # Add approved/discovered companies from emailed_status.json that are NOT in Excel
        for name, status_entry in statuses.items():
            if name.lower() not in excel_names:
                status = status_entry.get("status", "")
                # Only show approved/processed agencies (skip raw discovered/rejected)
                if status in ("pending_email", "pending_web_form", "sent", "responded", "interviewing", "skipped"):
                    merged.append({
                        "name": name,
                        "email": status_entry.get("email", ""),
                        "website": status_entry.get("website", ""),
                        "category": status_entry.get("category", "Discovered Agency"),
                        "status": status,
                        "note": status_entry.get("note", ""),
                        "timestamp": status_entry.get("timestamp", "")
                    })
            
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(merged, ensure_ascii=False).encode('utf-8'))

    def handle_post_update(self):
        """Save manual updates (status / notes) to emailed_status.json."""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            payload = json.loads(post_data.decode('utf-8'))
            name = payload.get("name")
            status = payload.get("status")
            note = payload.get("note")
            
            if not name:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing 'name' in request payload")
                return

            statuses = load_status()
            
            # Initialize entry if not present
            if name not in statuses:
                statuses[name] = {}
                
            if status is not None:
                statuses[name]["status"] = status
            if note is not None:
                statuses[name]["note"] = note
                
            statuses[name]["timestamp"] = datetime.datetime.now().isoformat()
            
            save_status(statuses)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode('utf-8'))

    def handle_test_imap(self):
        """Quickly checks IMAP login using credentials from .env."""
        config = load_config()
        if not config["gmail_user"] or not config["gmail_pass"]:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": "Credentials not set in .env"}).encode('utf-8'))
            return
            
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(config["gmail_user"], config["gmail_pass"])
            mail.logout()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
        except Exception as e:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))

    def handle_get_replies(self):
        """Fetches last 50 inbox emails and matches domains against consultancies list."""
        config = load_config()
        if not config["gmail_user"] or not config["gmail_pass"]:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Gmail configuration missing in .env"}).encode('utf-8'))
            return
            
        # Get consultancy list to get matching domains
        consultancies = parse_consultancies()
        
        # Build mapping of domain -> consultancy details
        domain_to_consultancy = {}
        for c in consultancies:
            name = c["name"]
            c_domains = []
            if c["email"]:
                c_domains.append(get_clean_domain(c["email"]))
            if c["website"]:
                c_domains.append(get_clean_domain(c["website"]))
                
            for d in c_domains:
                if d and len(d) > 3:
                    if d not in domain_to_consultancy:
                        domain_to_consultancy[d] = []
                    domain_to_consultancy[d].append(c)

        replies = []
        try:
            # Login and Fetch
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(config["gmail_user"], config["gmail_pass"])
            mail.select("INBOX")
            
            # Fetch last 50 messages from inbox
            status, messages = mail.search(None, "ALL")
            if status != "OK":
                raise Exception("Failed to search inbox")
                
            mail_ids = messages[0].split()
            # Get last 50 ids
            recent_ids = mail_ids[-50:]
            recent_ids.reverse() # Process newest first
            
            # Fetch all headers in a single batch request
            headers_dict = {}
            if recent_ids:
                batch_ids = b",".join(recent_ids)
                res, data = mail.fetch(batch_ids, "(RFC822.HEADER)")
                if res == "OK" and data:
                    for part in data:
                        if isinstance(part, tuple):
                            meta = part[0].decode('utf-8', errors='replace')
                            match = re.match(r'^(\d+)', meta)
                            if match:
                                msg_seq = match.group(1)
                                msg = email.message_from_bytes(part[1])
                                headers_dict[msg_seq] = msg

            for m_id in recent_ids:
                msg_seq_str = m_id.decode('utf-8')
                msg = headers_dict.get(msg_seq_str)
                if not msg:
                    continue
                    
                # Parse Headers
                sender_raw = msg.get("From", "")
                sender_email = extract_email_address(sender_raw)
                sender_domain = get_clean_domain(sender_email)
                
                if not sender_domain:
                    continue
                    
                # Check for domain matches in our consultancies list
                matched_company = None
                for c_domain, c_list in domain_to_consultancy.items():
                    if domain_matches(sender_domain, c_domain):
                        matched_company = c_list[0]["name"]
                        break
                
                # Fallback substring matching for agency name in sender/email
                if not matched_company:
                    for c in consultancies:
                        comp_name = c["name"].lower()
                        clean_comp = comp_name.replace("india", "").replace("services", "").replace("consultants", "").replace("talent", "").replace("group", "").strip()
                        if len(clean_comp) > 3:
                            if clean_comp in sender_email or clean_comp in sender_raw.lower():
                                matched_company = c["name"]
                                break

                if matched_company:
                    # Fetch snippet/body using partial fetch (saves bandwidth and is faster)
                    body_res, body_data = mail.fetch(m_id, "(BODY[TEXT]<0.1000>)")
                    snippet = ""
                    if body_res == "OK" and body_data:
                        body_bytes = body_data[0][1]
                        try:
                            # Try simple decode
                            text = body_bytes.decode('utf-8', errors='replace')
                            # Strip HTML if present (crude regex strip for snippet)
                            text = re.sub(r'<[^>]+>', ' ', text)
                            text = re.sub(r'\s+', ' ', text).strip()
                            snippet = text[:200] + "..." if len(text) > 200 else text
                        except Exception:
                            snippet = "[Encrypted or Non-Text Content]"
                            
                    subject = decode_mime_words(msg.get("Subject", "(No Subject)"))
                    date_str = msg.get("Date", "")
                    sender_name = decode_mime_words(sender_raw)
                    
                    replies.append({
                        "id": msg_seq_str,
                        "company": matched_company,
                        "sender": sender_name,
                        "email": sender_email,
                        "subject": subject,
                        "date": date_str,
                        "snippet": snippet
                    })
                    
            mail.logout()
            
            # Update status to "responded" for matched companies in emailed_status.json
            if replies:
                statuses = load_status()
                updated_any = False
                for r in replies:
                    comp = r["company"]
                    if comp in statuses and statuses[comp].get("status") not in ("responded", "interviewing"):
                        statuses[comp]["status"] = "responded"
                        statuses[comp]["timestamp"] = datetime.datetime.now().isoformat()
                        updated_any = True
                if updated_any:
                    save_status(statuses)
                    
        except Exception as e:
            print(f"[ERROR] IMAP Fetch error: {e}")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"IMAP Fetch failed: {str(e)}"}).encode('utf-8'))
            return
            
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(replies, ensure_ascii=False).encode('utf-8'))

    # --- Discovered Agencies Handlers ------------------------------------------
    def _load_discovered(self) -> list:
        """Load discovered agencies from JSON file."""
        if DISCOVERED_FILE.exists():
            try:
                return json.loads(DISCOVERED_FILE.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _save_discovered(self, data: list):
        """Save discovered agencies to JSON file."""
        DISCOVERED_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def handle_get_discovered(self):
        """Return all discovered agencies that haven't been approved or rejected."""
        agencies = self._load_discovered()
        # Filter to only show pending ones (status == 'discovered')
        pending = [a for a in agencies if a.get("status") == "discovered"]
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(pending, ensure_ascii=False).encode('utf-8'))

    def handle_discovered_approve(self):
        """Approve a discovered agency — move it to emailed_status.json as pending_email."""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            payload = json.loads(post_data.decode('utf-8'))
            name = payload.get("name", "").strip()
            if not name:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing 'name'")
                return

            # Update discovered_agencies.json status
            agencies = self._load_discovered()
            approved_agency = None
            for a in agencies:
                if a["name"] == name:
                    a["status"] = "approved"
                    approved_agency = a
                    break
            self._save_discovered(agencies)

            # Add to emailed_status.json as pending_email
            if approved_agency:
                statuses = load_status()
                if name not in statuses:
                    statuses[name] = {
                        "status": "pending_email" if approved_agency.get("email") else "pending_web_form",
                        "email": approved_agency.get("email", ""),
                        "website": approved_agency.get("website", ""),
                        "category": approved_agency.get("category", "Discovered Agency"),
                        "note": f"Discovered via {approved_agency.get('source', 'scraper')} on {approved_agency.get('discovered_at', '')}",
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                    save_status(statuses)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "name": name}).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode('utf-8'))

    def handle_discovered_reject(self):
        """Reject a discovered agency — mark it so it won't show up again."""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            payload = json.loads(post_data.decode('utf-8'))
            name = payload.get("name", "").strip()
            if not name:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing 'name'")
                return

            agencies = self._load_discovered()
            for a in agencies:
                if a["name"] == name:
                    a["status"] = "rejected"
                    break
            self._save_discovered(agencies)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "name": name}).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode('utf-8'))

    # --- Job and Config Handlers -----------------------------------------------
    def handle_get_config(self):
        """Get the user config, plus scraper status."""
        config = {
            "target_location": "India",
            "experience_level": "Mid-Senior",
            "search_keywords": "",
            "resume_file_path": "Resume.tex",
            "context_file_path": "# Shubham — Career Context File.md",
            "enabled_sources": ["google_ats", "naukri", "linkedin", "indeed"],
            "profile": {
                "full_name": "",
                "email": "",
                "phone": "",
                "linkedin": "",
                "github": "",
                "portfolio": "",
                "current_company": "",
                "experience_years": ""
            }
        }
        if USER_CONFIG_FILE.exists():
            try:
                loaded = json.loads(USER_CONFIG_FILE.read_text(encoding="utf-8"))
                # Merge profile specifically to prevent partial missing keys
                if "profile" in loaded and isinstance(loaded["profile"], dict):
                    config["profile"].update(loaded["profile"])
                    del loaded["profile"]
                config.update(loaded)
            except Exception:
                pass
        
        # Add running status
        running = False
        if DashboardHandler.scraper_process is not None:
            if DashboardHandler.scraper_process.poll() is None:
                running = True
            else:
                DashboardHandler.scraper_process = None
        
        config["scraper_running"] = running
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(config, ensure_ascii=False).encode('utf-8'))

    def handle_post_config(self):
        """Update user configuration."""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            payload = json.loads(post_data.decode('utf-8'))
            USER_CONFIG_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode('utf-8'))

    def handle_parse_resume(self):
        """Parse uploaded resume PDF or text file and extract profile details."""
        content_type = self.headers.get('Content-Type', '')
        content_length = int(self.headers.get('Content-Length', 0))
        
        if 'multipart/form-data' not in content_type:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Expected multipart/form-data content type")
            return
            
        boundary_match = re.search(r'boundary=([^;\s]+)', content_type)
        if not boundary_match:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing boundary in multipart content type")
            return
            
        boundary = boundary_match.group(1).encode('utf-8')
        body_bytes = self.rfile.read(content_length)
        
        try:
            filename, content = self._parse_multipart_data(boundary, body_bytes)
            if not filename or not content:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"No file content found in request")
                return
                
            text = ""
            if filename.lower().endswith(".pdf"):
                reader = pypdf.PdfReader(io.BytesIO(content))
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            else:
                text = content.decode('utf-8', errors='replace')
                
            if not text.strip():
                self.send_response(422)
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "No text could be extracted from file"}).encode('utf-8'))
                return
                
            profile = self._extract_profile_from_text(text)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "profile": profile}, ensure_ascii=False).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))

    def _parse_multipart_data(self, boundary, body_bytes):
        parts = body_bytes.split(b'--' + boundary)
        for part in parts:
            if b'filename=' in part:
                header_body = part.split(b'\r\n\r\n', 1)
                if len(header_body) < 2:
                    continue
                header, content = header_body
                if content.endswith(b'\r\n'):
                    content = content[:-2]
                elif content.endswith(b'\r\n--'):
                    content = content[:-4]
                
                filename_match = re.search(br'filename="([^"]+)"', header)
                filename = filename_match.group(1).decode('utf-8', errors='replace') if filename_match else "file"
                return filename, content
        return None, None

    def _extract_profile_from_text(self, text):
        profile = {
            "full_name": "",
            "email": "",
            "phone": "",
            "linkedin": "",
            "github": "",
            "portfolio": "",
            "current_company": "",
            "experience_years": ""
        }
        
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if email_match:
            profile["email"] = email_match.group(0).strip()
            
        phone_match = re.search(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{3,6}', text)
        if phone_match:
            profile["phone"] = phone_match.group(0).strip()
            
        linkedin_match = re.search(r'(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+', text, re.IGNORECASE)
        if linkedin_match:
            profile["linkedin"] = linkedin_match.group(0).strip()
            if not profile["linkedin"].startswith("http"):
                profile["linkedin"] = "https://" + profile["linkedin"]

        github_match = re.search(r'(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_-]+', text, re.IGNORECASE)
        if github_match:
            profile["github"] = github_match.group(0).strip()
            if not github_match.group(0).startswith("http"):
                profile["github"] = "https://" + profile["github"]

        # Remove email address from text before matching other links
        text_no_email = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', text)
        links = re.findall(r'(?:https?://)?(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,6}(?:/[a-zA-Z0-9-_./?%&=]*)?', text_no_email)
        for link in links:
            link_lower = link.lower()
            if "linkedin.com" not in link_lower and "github.com" not in link_lower and "gmail.com" not in link_lower and "outlook.com" not in link_lower and "yahoo.com" not in link_lower and "hotmail.com" not in link_lower:
                profile["portfolio"] = link.strip()
                if not profile["portfolio"].startswith("http"):
                    profile["portfolio"] = "https://" + profile["portfolio"]
                break

        lines = [line.strip() for line in text.split('\n') if line.strip()]
        for line in lines[:8]:
            cleaned_line = re.sub(r'(?i)^(resume\s+of|cv\s+of|curriculum\s+vitae\s+of|name:?)\s+', '', line).strip()
            cleaned_lower = cleaned_line.lower()
            if any(term in cleaned_lower for term in ["email", "phone", "contact", "address", "resume", "cv", "curriculum", "github", "linkedin", "portfolio", "http", "education", "experience"]):
                continue
            words = cleaned_line.split()
            if 1 <= len(words) <= 4 and all(w[0].isupper() if w[0].isalpha() else True for w in words if w):
                clean_name = re.sub(r'[^a-zA-Z\s.-]', '', cleaned_line).strip()
                if clean_name:
                    profile["full_name"] = clean_name
                    break

        exp_match = re.search(r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp|work)', text, re.IGNORECASE)
        if exp_match:
            profile["experience_years"] = exp_match.group(1)
            
        company_match = re.search(r'(?:at|with)\s+([A-Z][a-zA-Z0-9 ,&.]{2,40})\s+(?:\(|from|since|present|current|\d{4})', text)
        if company_match:
            profile["current_company"] = company_match.group(1).strip()
        else:
            for i, line in enumerate(lines):
                if "present" in line.lower() or "current" in line.lower():
                    prev_line = lines[i-1] if i > 0 else ""
                    for candidate in [line, prev_line]:
                        cand_lower = candidate.lower()
                        if not any(term in cand_lower for term in ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december", "present", "201", "202", "experience", "education", "project"]):
                            words = candidate.split()
                            if 1 <= len(words) <= 5:
                                profile["current_company"] = candidate.strip()
                                break
                    if profile["current_company"]:
                        break

        return profile

    def handle_get_jobs_status(self):
        """Get all tracked jobs (active applications)."""
        jobs = []
        if TRACKED_JOBS_FILE.exists():
            try:
                jobs = json.loads(TRACKED_JOBS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(jobs, ensure_ascii=False).encode('utf-8'))

    def handle_get_jobs_discovered(self):
        """Get discovered jobs waiting for approval."""
        jobs = []
        if DISCOVERED_JOBS_FILE.exists():
            try:
                all_discovered = json.loads(DISCOVERED_JOBS_FILE.read_text(encoding="utf-8"))
                jobs = [j for j in all_discovered if j.get("status") == "discovered"]
            except Exception:
                pass
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(jobs, ensure_ascii=False).encode('utf-8'))

    def handle_post_jobs_update(self):
        """Update status or notes of a tracked job."""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            payload = json.loads(post_data.decode('utf-8'))
            link = payload.get("link")
            status = payload.get("status")
            notes = payload.get("notes")
            
            if not link:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing 'link'")
                return

            jobs = []
            if TRACKED_JOBS_FILE.exists():
                try:
                    jobs = json.loads(TRACKED_JOBS_FILE.read_text(encoding="utf-8"))
                except Exception:
                    pass
            
            updated = False
            for j in jobs:
                if j.get("link") == link:
                    if status is not None:
                        j["status"] = status
                    if notes is not None:
                        j["notes"] = notes
                    j["updated_at"] = datetime.datetime.now().isoformat()
                    updated = True
                    break
            
            if updated:
                TRACKED_JOBS_FILE.write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": updated}).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode('utf-8'))

    def handle_jobs_approve(self):
        """Approve a discovered job posting -> moves to jobs_tracker.json."""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            payload = json.loads(post_data.decode('utf-8'))
            link = payload.get("link")
            if not link:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing 'link'")
                return

            # Find and update status in discovered_jobs.json
            discovered_jobs = []
            if DISCOVERED_JOBS_FILE.exists():
                try:
                    discovered_jobs = json.loads(DISCOVERED_JOBS_FILE.read_text(encoding="utf-8"))
                except Exception:
                    pass
            
            approved_job = None
            for j in discovered_jobs:
                if j.get("link") == link:
                    j["status"] = "approved"
                    approved_job = j
                    break
            
            if approved_job:
                DISCOVERED_JOBS_FILE.write_text(json.dumps(discovered_jobs, indent=2, ensure_ascii=False), encoding="utf-8")
                
                # Add to jobs_tracker.json
                tracked_jobs = []
                if TRACKED_JOBS_FILE.exists():
                    try:
                        tracked_jobs = json.loads(TRACKED_JOBS_FILE.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                
                # Check for duplicates first
                exists = any(tj.get("link") == link for tj in tracked_jobs)
                if not exists:
                    new_tracked = {
                        "title": approved_job.get("title", ""),
                        "company": approved_job.get("company", ""),
                        "location": approved_job.get("location", ""),
                        "link": approved_job.get("link", ""),
                        "source": approved_job.get("source", ""),
                        "description": approved_job.get("description", ""),
                        "status": "pending_apply",
                        "notes": "",
                        "added_at": datetime.datetime.now().isoformat()
                    }
                    tracked_jobs.append(new_tracked)
                    TRACKED_JOBS_FILE.write_text(json.dumps(tracked_jobs, indent=2, ensure_ascii=False), encoding="utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": approved_job is not None}).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode('utf-8'))

    def handle_jobs_reject(self):
        """Reject a discovered job posting."""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            payload = json.loads(post_data.decode('utf-8'))
            link = payload.get("link")
            if not link:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing 'link'")
                return

            discovered_jobs = []
            if DISCOVERED_JOBS_FILE.exists():
                try:
                    discovered_jobs = json.loads(DISCOVERED_JOBS_FILE.read_text(encoding="utf-8"))
                except Exception:
                    pass
            
            updated = False
            for j in discovered_jobs:
                if j.get("link") == link:
                    j["status"] = "rejected"
                    updated = True
                    break
            
            if updated:
                DISCOVERED_JOBS_FILE.write_text(json.dumps(discovered_jobs, indent=2, ensure_ascii=False), encoding="utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": updated}).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode('utf-8'))

    def handle_external_add(self):
        """Add a job posting directly from external source (e.g. Chrome Extension)."""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            payload = json.loads(post_data.decode('utf-8'))
            link = payload.get("link", "").strip()
            title = payload.get("title", "").strip()
            company = payload.get("company", "").strip()
            location = payload.get("location", "").strip()
            source = payload.get("source", "").strip() or "extension"
            description = payload.get("description", "").strip()
            status = payload.get("status", "pending_apply").strip()
            notes = payload.get("notes", "").strip()

            if not link or not title:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing required fields 'link' or 'title'")
                return

            tracked_jobs = []
            if TRACKED_JOBS_FILE.exists():
                try:
                    tracked_jobs = json.loads(TRACKED_JOBS_FILE.read_text(encoding="utf-8"))
                except Exception:
                    pass

            # Check for duplicates first
            exists = any(tj.get("link") == link for tj in tracked_jobs)
            if not exists:
                new_tracked = {
                    "title": title,
                    "company": company,
                    "location": location,
                    "link": link,
                    "source": source,
                    "description": description,
                    "status": status,
                    "notes": notes,
                    "added_at": datetime.datetime.now().isoformat()
                }
                tracked_jobs.append(new_tracked)
                TRACKED_JOBS_FILE.write_text(json.dumps(tracked_jobs, indent=2, ensure_ascii=False), encoding="utf-8")
                message = "Job added successfully"
                success = True
            else:
                message = "Job is already being tracked"
                success = False

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": success, "message": message}).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode('utf-8'))

    def handle_jobs_scrape(self):
        """Trigger background job scraping."""
        if DashboardHandler.scraper_process is not None and DashboardHandler.scraper_process.poll() is None:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": "Job scraper is already running"}).encode('utf-8'))
            return

        try:
            import subprocess
            # Start scraper in background
            DashboardHandler.scraper_process = subprocess.Popen(
                [sys.executable, str(AGENT_DIR / "job_scraper.py")],
                cwd=str(AGENT_DIR)
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "message": "Job scraper started in background"}).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))

    # --- Static Files Handler --------------------------------------------------
    def handle_serve_static(self, path):
        """Serves dashboard files (HTML, CSS, JS) from the dashboard_public directory."""
        if path == "/":
            path = "/index.html"
            
        # Security check: resolve clean path
        safe_path = (PUBLIC_DIR / path.lstrip('/')).resolve()
        
        # Ensure path is within PUBLIC_DIR
        if not safe_path.is_relative_to(PUBLIC_DIR):
            self.send_error(403, "Forbidden")
            return
            
        if not safe_path.exists() or safe_path.is_dir():
            self.send_error(404, "File not found")
            return
            
        # Determine content type
        content_type = "text/plain"
        if safe_path.suffix == ".html":
            content_type = "text/html; charset=utf-8"
        elif safe_path.suffix == ".css":
            content_type = "text/css"
        elif safe_path.suffix == ".js":
            content_type = "application/javascript"
        elif safe_path.suffix == ".json":
            content_type = "application/json"
        elif safe_path.suffix in (".png", ".jpg", ".jpeg", ".gif"):
            content_type = f"image/{safe_path.suffix[1:]}"
        elif safe_path.suffix == ".svg":
            content_type = "image/svg+xml"
            
        try:
            with open(safe_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Internal server error: {e}")

# --- Run Server ----------------------------------------------------------------
def main():
    if not PUBLIC_DIR.exists():
        PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
        
    print("=" * 60)
    print(f"  JOB OUTREACH DASHBOARD BACKEND SERVER")
    print(f"  Listening on: http://localhost:{PORT}")
    print("=" * 60)
    
    server = HTTPServer(('localhost', PORT), DashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        sys.exit(0)

if __name__ == "__main__":
    main()
