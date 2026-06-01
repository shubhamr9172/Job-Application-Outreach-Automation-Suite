"""
Job Search Scraper Agent (Agent 01 - Job Discovery)
--------------------------------------------------
Uses Gemini to analyze the candidate's resume/context, generate targeted search queries,
and crawls search engine pages for direct job listings (ATS, Naukri, LinkedIn, Indeed)
using Scrapling's StealthyFetcher.

Usage:
    python job_scraper.py
    python job_scraper.py --location "Remote" --keywords "Python Backend,LangGraph"
"""

import os
import sys
import io
import json
import re
import argparse
import datetime
import time
from pathlib import Path
from urllib.parse import urlparse, quote_plus
from dotenv import load_dotenv

# Force UTF-8 stdout/stderr on Windows to prevent encoding crashes
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# --- Paths & Constants --------------------------------------------------------
BASE_DIR = Path(__file__).parent.parent.parent.resolve()
DATA_DIR = BASE_DIR / "data"
CONFIG_FILE = DATA_DIR / "user_config.json"
DISCOVERED_FILE = DATA_DIR / "discovered_jobs.json"
TRACKER_FILE = DATA_DIR / "jobs_tracker.json"
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

GEMINI_MODEL = "gemini-2.5-flash"

# --- Helper Functions ---------------------------------------------------------

def load_config() -> dict:
    """Load configuration preferences from user_config.json."""
    default_config = {
        "target_location": "India",
        "experience_level": "Mid-Senior",
        "search_keywords": "",
        "resume_file_path": "resumes/Resume.tex",
        "context_file_path": "resumes/career_context.md",
        "enabled_sources": ["google_ats", "naukri", "linkedin", "indeed"]
    }
    if CONFIG_FILE.exists():
        try:
            config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            # Ensure all default keys exist
            for k, v in default_config.items():
                if k not in config:
                    config[k] = v
            return config
        except Exception as e:
            print(f"[WARN] Error loading user_config.json: {e}. Using defaults.")
    return default_config


def save_config(config: dict):
    """Save configuration preferences."""
    try:
        CONFIG_FILE.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"[ERROR] Failed to save config: {e}")


def load_jobs(file_path: Path) -> list:
    """Load job list from a JSON file."""
    if file_path.exists():
        try:
            return json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[WARN] Failed to load {file_path.name}: {e}. Returning empty list.")
    return []


def save_jobs(jobs: list, file_path: Path):
    """Save job list to a JSON file."""
    try:
        file_path.write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[OK] Saved {len(jobs)} jobs to {file_path.name}")
    except Exception as e:
        print(f"[ERROR] Failed to save jobs to {file_path.name}: {e}")


def find_resume_and_context(config: dict) -> tuple[Path, Path]:
    """Find resume and career context files, falling back to auto-discovery if needed."""
    resume_path = BASE_DIR / config.get("resume_file_path", "resumes/Resume.tex")
    context_path = BASE_DIR / config.get("context_file_path", "resumes/career_context.md")

    # Fallback resume discovery
    if not resume_path.exists():
        print(f"[INFO] Resume file not found at {resume_path.name}. Scanning for alternatives...")
        tex_files = list(BASE_DIR.glob("*.tex"))
        pdf_files = list(BASE_DIR.glob("*.pdf"))
        if tex_files:
            resume_path = tex_files[0]
            print(f"[INFO] Auto-discovered LaTeX resume: {resume_path.name}")
        elif pdf_files:
            resume_path = pdf_files[0]
            print(f"[INFO] Auto-discovered PDF resume: {resume_path.name}")
        else:
            print("[WARN] No resume files found in directory.")

    # Fallback context discovery
    if not context_path.exists():
        print(f"[INFO] Context file not found at {context_path.name}. Scanning for alternatives...")
        md_files = [f for f in BASE_DIR.glob("*.md") if "context" in f.name.lower() or "profile" in f.name.lower()]
        if md_files:
            context_path = md_files[0]
            print(f"[INFO] Auto-discovered context: {context_path.name}")
        else:
            md_all = list(BASE_DIR.glob("*.md"))
            if md_all:
                context_path = md_all[0]
                print(f"[INFO] Using markdown fallback: {context_path.name}")
            else:
                print("[WARN] No career context markdown file found.")

    return resume_path, context_path


def read_resume_text(resume_path: Path) -> str:
    """Read resume content from file (supports .tex, .md, .txt; warns on .pdf)."""
    if not resume_path.exists():
        return ""
    suffix = resume_path.suffix.lower()
    if suffix in (".tex", ".md", ".txt"):
        return resume_path.read_text(encoding="utf-8")
    elif suffix == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(resume_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        except ImportError:
            print("[WARN] pypdf library not installed. Cannot parse PDF resume content.")
            return "PDF Resume (raw text extraction skipped; please install pypdf or use .tex)"
        except Exception as e:
            print(f"[WARN] Error reading PDF resume: {e}")
            return "PDF Resume (error reading)"
    return ""


# --- LLM Query Generation -----------------------------------------------------

def get_gemini_client():
    """Initialize Google GenAI client."""
    from google import genai
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY not found in environment or .env file.")
        sys.exit(1)
    return genai.Client(api_key=api_key)


def generate_search_keywords_with_gemini(resume_content: str, context_content: str, experience_level: str) -> list[str]:
    """Call Gemini to generate tailored job search keywords based on candidate profile."""
    print("[*] Contacting Gemini to analyze profile and generate search queries...")
    try:
        client = get_gemini_client()
        prompt = f"""You are a professional recruitment AI agent.
Analyze the following resume and career context of the candidate.
Candidate Experience Level Target: {experience_level}

Resume:
\"\"\"
{resume_content}
\"\"\"

Career Context:
\"\"\"
{context_content}
\"\"\"

Task:
Generate a list of 3 to 5 optimized job search keyword queries that best match the candidate's technical skills, experience, and target roles.
The keywords should be specific (e.g. "Generative AI Engineer", "Python Backend Developer", "LangGraph RAG Developer", "Machine Learning Engineer").
Do not generate generic terms like "Software Engineer" or "Developer" unless paired with specific stack details.

Return ONLY a valid JSON list of strings, e.g. ["Query 1", "Query 2", "Query 3"].
Do NOT wrap the response in markdown blocks or include any commentary. Return only the JSON string.
"""
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        text = response.text.strip()
        # Clean markdown code blocks if the model returned them
        if text.startswith("```"):
            # Strip first line
            text = re.sub(r"^```(?:json)?\n", "", text)
            # Strip trailing backticks
            text = re.sub(r"\n```$", "", text)
            text = text.strip()

        queries = json.loads(text)
        if isinstance(queries, list):
            print(f"[OK] Gemini generated search keywords: {queries}")
            return [q.strip() for q in queries if isinstance(q, str) and q.strip()]
    except Exception as e:
        print(f"[WARN] Failed to generate queries with Gemini: {e}. Falling back to default keywords.")
    
    return ["AI Engineer", "Python Backend Developer", "Machine Learning Developer"]


# --- Scraper Details Extractor -------------------------------------------------

def parse_company_and_title(title_text: str, url: str) -> tuple[str, str]:
    """Extract job title and company name from search result title and URL."""
    # Common separators
    separators = [r"\s+-\s+", r"\s+\|\s+", r"\s+at\s+", r"\s+@\s+", r"\s+:\s+", r"\s+–\s+"]
    title = title_text.strip()
    company = ""

    # Split by separators
    for sep in separators:
        parts = re.split(sep, title, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2:
            title = parts[0].strip()
            company = parts[1].strip()
            break

    # Clean title/company
    # Remove trailing dot or pipeline artifacts
    title = title.rstrip('.,;:')
    company = company.rstrip('.,;:')

    # Extract company name from URL if not found in title
    if not company:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        path = parsed_url.path

        if "greenhouse.io" in domain:
            # e.g. boards.greenhouse.io/companyname/jobs/123
            match = re.search(r"/([^/]+)/jobs", path)
            if match:
                company = match.group(1)
        elif "lever.co" in domain:
            # e.g. jobs.lever.co/companyname/123
            parts = [p for p in path.split("/") if p]
            if parts:
                company = parts[0]
        elif "workable.com" in domain:
            # e.g. apply.workable.com/companyname/j/123
            parts = [p for p in path.split("/") if p]
            if parts:
                company = parts[0]
        elif "naukri.com" in domain:
            # e.g. www.naukri.com/job-listings-job-title-companyname-id
            match = re.search(r"job-listings-[a-z0-9-]+-([a-z0-9]+)-\d+", path)
            if match:
                company = match.group(1)
        elif "linkedin.com" in domain:
            # Fallback domain name parsing
            company = "LinkedIn Posting"
        elif "indeed.com" in domain:
            company = "Indeed Posting"
        
        if not company:
            # Fallback to domain name itself without subdomains
            domain_parts = domain.split(".")
            if len(domain_parts) >= 2:
                company = domain_parts[-2].capitalize()
            else:
                company = "Unknown Company"
    
    # Capitalize / clean company names
    company = re.sub(r'[-_]', ' ', company).strip()
    # Normalize acronyms/casing
    company_words = [w.capitalize() for w in company.split()]
    company = " ".join(company_words)
    
    return title, company


def is_job_duplicate(title: str, company: str, url: str, existing_discovered: list, existing_tracker: list) -> bool:
    """Check if the job is already present in discovered or tracked databases."""
    title_norm = title.lower().replace(" ", "")
    company_norm = company.lower().replace(" ", "")
    url_norm = url.lower().strip()

    # Check url match and fuzzy title+company match
    for job in existing_discovered + existing_tracker:
        j_url = job.get("link", "").lower().strip()
        if j_url == url_norm:
            return True
        
        j_title_norm = job.get("title", "").lower().replace(" ", "")
        j_company_norm = job.get("company", "").lower().replace(" ", "")
        if j_title_norm == title_norm and j_company_norm == company_norm:
            return True
            
    return False


# --- Core Scraping ------------------------------------------------------------

def run_google_search_jobs(queries: list[str], location: str, enabled_sources: list[str], limit_per_source: int = 15) -> list[dict]:
    """Execute Google search targeting specified job platforms."""
    try:
        from scrapling.fetchers import StealthyFetcher
    except ImportError:
        print("[ERROR] Scrapling is not installed. Run: pip install \"scrapling[fetchers]\"")
        return []

    discovered_results = []
    
    # Compile platforms
    platforms_query = []
    if "google_ats" in enabled_sources:
        platforms_query.append("site:greenhouse.io OR site:lever.co OR site:workable.com")
    if "linkedin" in enabled_sources:
        platforms_query.append("site:linkedin.com/jobs/view")
    if "indeed" in enabled_sources:
        platforms_query.append("site:indeed.com/viewjob")
    if "naukri" in enabled_sources and "india" in location.lower():
        platforms_query.append("site:naukri.com/job-listings")

    if not platforms_query:
        print("[INFO] No platform sources enabled or matching location requirements.")
        return []

    # Combine into search expressions
    for query in queries:
        for platform_site in platforms_query:
            search_str = f'{platform_site} "{query}" "{location}"'
            print(f"\n[*] Searching Google: {search_str}")
            
            try:
                search_url = f"https://www.google.com/search?q={quote_plus(search_str)}&num={limit_per_source}"
                page = StealthyFetcher.fetch(search_url, headless=True, network_idle=True)
                
                if not page or page.status != 200:
                    status_code = getattr(page, 'status', 'Unknown')
                    print(f"[WARN] Google Search returned status: {status_code}")
                    continue

                h3_elements = page.css("h3")
                print(f"[INFO] Found {len(h3_elements)} search results")

                for h3 in h3_elements:
                    title_text = (h3.text or "").strip()
                    if not title_text or len(title_text) < 5:
                        continue

                    # Extract link
                    ancestor_a = h3.xpath("./ancestor::a")
                    link = ancestor_a[0].attrib.get("href", "") if ancestor_a else ""
                    if not link or "google.com" in link:
                        continue

                    # Extract snippet/description
                    snippet = ""
                    # Locate Google's search result description block
                    parent_div = h3.xpath("./ancestor::div[3]")
                    if parent_div:
                        snippet = parent_div[0].text or ""
                        # Try children if raw text empty
                        if not snippet:
                            snippet = " ".join([t.text for t in parent_div[0].css("*") if t.text])
                    
                    # Clean snippet
                    snippet = re.sub(r'\s+', ' ', snippet).strip()

                    # Deduce source platform
                    source_name = "other"
                    for p_key in ["greenhouse", "lever", "workable", "naukri", "linkedin", "indeed"]:
                        if p_key in link.lower():
                            source_name = p_key
                            break

                    parsed_title, company = parse_company_and_title(title_text, link)

                    # Determine job location (default to config location, or parse from snippet)
                    job_loc = location
                    loc_matches = re.findall(r'(Bangalore|Bengaluru|Pune|Mumbai|Noida|Hyderabad|Remote|Chennai|Delhi|San Francisco|New York|London)', snippet, re.IGNORECASE)
                    if loc_matches:
                        job_loc = loc_matches[0]

                    discovered_results.append({
                        "title": parsed_title,
                        "company": company,
                        "location": job_loc,
                        "link": link,
                        "source": source_name,
                        "description": snippet[:300] + ("..." if len(snippet) > 300 else ""),
                        "discovered_at": datetime.datetime.now().isoformat(),
                        "status": "discovered",
                        "notes": ""
                    })
                    print(f"  [FOUND] {parsed_title} at {company} ({job_loc}) | Platform: {source_name}")

            except Exception as e:
                print(f"[ERROR] Search failed: {e}")
            
            # Rate limit politeness delay
            time.sleep(5)

    return discovered_results


# --- Main Runner --------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Job Discovery Scraper - Agent 01")
    parser.add_argument("--location", type=str, help="Override target location")
    parser.add_argument("--keywords", type=str, help="Comma-separated custom keywords to override Gemini generation")
    args = parser.parse_args()

    print("=" * 60)
    print("  JOB DISCOVERY SCRAPER AGENT (AGENT 01)")
    print("=" * 60)

    # 1. Load config
    config = load_config()
    location = args.location or config.get("target_location", "India")
    experience_level = config.get("experience_level", "Mid-Senior")
    enabled_sources = config.get("enabled_sources", ["google_ats", "naukri", "linkedin", "indeed"])

    print(f"[INFO] Location: {location}")
    print(f"[INFO] Experience Level: {experience_level}")
    print(f"[INFO] Enabled Sources: {enabled_sources}")

    # 2. Get search keywords (CLI override OR LLM dynamic generation)
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
        print(f"[INFO] Using CLI override keywords: {keywords}")
    elif config.get("search_keywords"):
        keywords = [k.strip() for k in config["search_keywords"].split(",") if k.strip()]
        print(f"[INFO] Using saved config override keywords: {keywords}")
    else:
        # Load resume & context
        resume_path, context_path = find_resume_and_context(config)
        resume_text = read_resume_text(resume_path)
        context_text = context_path.read_text(encoding="utf-8") if context_path.exists() else ""
        
        if not resume_text:
            print("[WARN] Resume content empty or file not readable. Falling back to default keywords.")
            keywords = ["AI Engineer", "Python Backend Developer", "Machine Learning Developer"]
        else:
            keywords = generate_search_keywords_with_gemini(resume_text, context_text, experience_level)

    # 3. Load existing listings to prevent duplicates
    existing_discovered = load_jobs(DISCOVERED_FILE)
    existing_tracker = load_jobs(TRACKER_FILE)
    print(f"[INFO] Existing discovered: {len(existing_discovered)} | Tracked: {len(existing_tracker)}")

    # 4. Scrape jobs
    scraped_jobs = run_google_search_jobs(keywords, location, enabled_sources)

    # 5. Filter and save
    new_jobs_added = 0
    for job in scraped_jobs:
        if not is_job_duplicate(job["title"], job["company"], job["link"], existing_discovered, existing_tracker):
            existing_discovered.append(job)
            new_jobs_added += 1

    if new_jobs_added > 0:
        save_jobs(existing_discovered, DISCOVERED_FILE)
        print(f"\n[SUMMARY] Discovered {new_jobs_added} NEW job listings!")
    else:
        print("\n[SUMMARY] No new unique jobs discovered this run.")

    print("[DONE] Scraping job listings complete.")


if __name__ == "__main__":
    main()
