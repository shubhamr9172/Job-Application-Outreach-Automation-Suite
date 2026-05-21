"""
Agency Discovery Scraper
------------------------
Uses Scrapling to discover new IT/AI recruitment agencies from Google Search
and saves them for review in the dashboard.

Usage (from venv):
    python agency_scraper.py                    # Run all sources
    python agency_scraper.py --source google    # Google only
    python agency_scraper.py --limit 30         # Limit results

Requirements:
    pip install "scrapling[fetchers]"
    scrapling install
"""

import sys
import os
import io
import json
import re
import argparse
import datetime
from pathlib import Path

from dotenv import load_dotenv

# Force UTF-8 stdout/stderr on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# --- Constants ----------------------------------------------------------------
AGENT_DIR = Path(__file__).parent.resolve()
DATA_DIR = AGENT_DIR / "data"
EXCEL_PATH = AGENT_DIR / "Consultancies.xlsx"
DISCOVERED_FILE = DATA_DIR / "discovered_agencies.json"
STATUS_FILE = DATA_DIR / "emailed_status.json"
ENV_FILE = AGENT_DIR / ".env"

load_dotenv(ENV_FILE)

# Google search queries targeted at finding recruitment agencies with contact info
SEARCH_QUERIES = [
    "top IT recruitment agencies India contact email 2025",
    "AI ML recruitment agencies India email address",
    "tech staffing companies India HR email",
    "IT headhunters India Pune Bangalore email",
    "recruitment consultancies India AI engineer jobs contact",
    "best placement agencies India for software engineers email",
    "international remote recruitment agencies India email",
    "AI job placement firms India contact details",
    "top recruitment consultancies India HR contact email",
    "technical staffing agencies Bangalore Pune contact email",
    "list of IT placement consultancies in India with email",
    "AI startup recruiters India contact email",
    "software engineer headhunters India email address",
    "direct hire recruitment agencies India HR email",
]

# --- Helper Functions ---------------------------------------------------------

def load_existing_companies() -> set:
    """Load company names already in Consultancies.xlsx and emailed_status.json."""
    existing = set()

    # From emailed_status.json
    if STATUS_FILE.exists():
        try:
            data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
            for name in data.keys():
                existing.add(name.strip().lower())
        except Exception:
            pass

    # From Excel
    try:
        import pandas as pd
        if EXCEL_PATH.exists():
            df = pd.read_excel(EXCEL_PATH, header=None)
            header_row_idx = None
            for idx, row in df.iterrows():
                if any(isinstance(val, str) and "Company Name" in val for val in row):
                    header_row_idx = idx
                    break
            if header_row_idx is not None:
                df_data = df.iloc[header_row_idx+1:].copy()
                df_data.columns = df.iloc[header_row_idx].tolist()
                df_data.columns = [str(c).strip() for c in df_data.columns]
                for _, row in df_data.iterrows():
                    name = str(row.get("Company Name", "")).strip().lower()
                    if name:
                        existing.add(name)
    except Exception as e:
        print(f"[WARN] Could not load Excel: {e}")

    # From discovered_agencies.json
    if DISCOVERED_FILE.exists():
        try:
            data = json.loads(DISCOVERED_FILE.read_text(encoding="utf-8"))
            for agency in data:
                existing.add(agency.get("name", "").strip().lower())
        except Exception:
            pass

    return existing


def load_discovered() -> list:
    """Load existing discovered agencies."""
    if DISCOVERED_FILE.exists():
        try:
            return json.loads(DISCOVERED_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_discovered(agencies: list):
    """Save discovered agencies to JSON."""
    DISCOVERED_FILE.write_text(
        json.dumps(agencies, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"[OK] Saved {len(agencies)} discovered agencies to {DISCOVERED_FILE.name}")


def clean_company_name(raw: str) -> str:
    """Clean up a scraped company name."""
    name = raw.strip()
    # Remove common suffixes/artifacts
    name = re.sub(r'\s*[-|–—:]\s*.*$', '', name)  # Remove everything after dash/pipe
    name = re.sub(r'\s*\(.*?\)\s*', ' ', name)     # Remove parenthetical
    name = re.sub(r'\s+', ' ', name).strip()
    # Remove trailing dots, commas
    name = name.rstrip('.,;:')
    return name


def extract_emails_from_text(text: str) -> list:
    """Extract email addresses from a block of text."""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(pattern, text)
    # Filter out common false positives
    filtered = []
    for e in emails:
        e_lower = e.lower()
        if not any(skip in e_lower for skip in [
            'example.com', 'test.com', 'domain.com', 'email.com',
            'yourcompany', 'sentry.io', 'schema.org', 'w3.org',
            '.png', '.jpg', '.gif', '.svg', 'wixpress'
        ]):
            filtered.append(e_lower)
    return list(set(filtered))


def extract_urls_from_text(text: str) -> list:
    """Extract website URLs from text."""
    pattern = r'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s<>"]*)?'
    urls = re.findall(pattern, text)
    # Clean and deduplicate
    cleaned = []
    for url in urls:
        url = url.rstrip('.,;:)')
        domain = re.sub(r'^https?://(www\.)?', '', url).split('/')[0]
        if len(domain) > 4 and not any(skip in domain for skip in [
            'google.', 'facebook.', 'twitter.', 'youtube.',
            'instagram.', 'linkedin.', 'wikipedia.',
            'github.', 'reddit.', 'quora.'
        ]):
            cleaned.append(url)
    return list(set(cleaned))


def find_email_on_website(url: str) -> str:
    """Attempt to fetch the website homepage (and contact page if needed) to extract an email address."""
    from urllib.parse import urljoin
    if not url or not isinstance(url, str) or not url.startswith("http"):
        return ""
    
    print(f"    [WEB] Checking website for email: {url}")
    try:
        from scrapling.fetchers import StealthyFetcher
        page = StealthyFetcher.fetch(url, headless=True, timeout=10000, network_idle=False)
        if page:
            html_text = str(page.html_content or "")
            emails = extract_emails_from_text(html_text)
            if not emails:
                try:
                    all_text = page.get_all_text() or ""
                    emails = extract_emails_from_text(all_text)
                except Exception:
                    pass
            
            if emails:
                print(f"    [WEB] Found email on homepage: {emails[0]}")
                return emails[0]
                
            # If no email, look for contact page links
            contact_hrefs = []
            for a in page.css("a") or []:
                href = a.attrib.get("href", "")
                if not href:
                    continue
                href_lower = href.strip().lower()
                text_lower = (a.text or "").strip().lower()
                if any(kw in href_lower or kw in text_lower for kw in ["contact", "about", "career"]):
                    if not any(skip in href_lower for skip in ["javascript:", "mailto:", "tel:"]):
                        full_href = urljoin(url, href.strip())
                        if full_href.startswith("http"):
                            contact_hrefs.append(full_href)
            
            # Check unique contact page urls (max 2)
            unique_contact_urls = list(set(contact_hrefs))
            for c_url in unique_contact_urls[:2]:
                print(f"    [WEB] Checking contact/about page: {c_url}")
                c_page = StealthyFetcher.fetch(c_url, headless=True, timeout=8000, network_idle=False)
                if c_page:
                    c_html = str(c_page.html_content or "")
                    c_emails = extract_emails_from_text(c_html)
                    if not c_emails:
                        try:
                            c_text = c_page.get_all_text() or ""
                            c_emails = extract_emails_from_text(c_text)
                        except Exception:
                            pass
                    if c_emails:
                        print(f"    [WEB] Found email on contact page: {c_emails[0]}")
                        return c_emails[0]
    except Exception as e:
        print(f"    [WARN] Failed to scrape website {url}: {e}")
        
    return ""


def is_duplicate(name: str, existing: set) -> bool:
    """Check if an agency name is already known."""
    name_lower = name.strip().lower()
    if not name_lower or len(name_lower) < 3:
        return True
    if name_lower in existing:
        return True
    # Fuzzy check: see if any existing name contains or is contained in this name
    for ex in existing:
        if len(ex) > 4 and (ex in name_lower or name_lower in ex):
            return True
    return False


# --- Scraping Functions -------------------------------------------------------

def scrape_google_search(queries: list, existing: set, limit: int = 50) -> list:
    """Scrape Google Search results for recruitment agency information."""
    from scrapling.fetchers import StealthyFetcher

    discovered = []
    seen_names = set()

    for query in queries:
        if len(discovered) >= limit:
            break

        print(f"\n[GOOGLE] Searching: '{query}'")
        try:
            url = f"https://www.google.com/search?q={query.replace(' ', '+')}&num=20"
            page = StealthyFetcher.fetch(url, headless=True, network_idle=True)

            if not page or not page.status == 200:
                print(f"[WARN] Google returned status {getattr(page, 'status', 'N/A')}")
                continue

            h3_elements = page.css("h3")
            print(f"[GOOGLE] Found {len(h3_elements)} h3 elements")

            for h3 in h3_elements:
                if len(discovered) >= limit:
                    break

                title = (h3.text or "").strip()
                if not title or len(title) < 5:
                    continue

                # Find link
                ancestor_a = h3.xpath("./ancestor::a")
                link = ancestor_a[0].attrib.get("href", "") if ancestor_a else ""
                if not link or "google.com" in link:
                    continue

                # Extract snippet
                snippet = ""
                level5 = h3.xpath("./ancestor::div[contains(@class, 'kb0PBd') and contains(@class, 'jGGQ5e')][1]")
                if level5:
                    sib = level5[0].xpath("./following-sibling::div[contains(@class, 'kb0PBd')][1]")
                    if sib:
                        snippet = sib[0].text or ""
                        if not snippet:
                            snippet = " ".join([t.text for t in sib[0].css("*") if t.text])
                
                # Sibling fallback
                if not snippet:
                    grandparent = h3.xpath("./ancestor::div[3]")
                    if grandparent:
                        snippet = grandparent[0].text or ""

                # Combine all text for email extraction
                full_text = f"{title} {snippet} {link}"

                # Try to identify if this is a recruitment/staffing company
                recruitment_keywords = [
                    'recruit', 'staffing', 'placement', 'headhunt', 'talent',
                    'hiring', 'consultanc', 'manpower', 'hr ', 'human resource',
                    'job agency', 'employment', 'workforce', 'personnel', 'placement'
                ]
                is_agency = any(kw in full_text.lower() for kw in recruitment_keywords)

                if not is_agency:
                    continue

                # Extract company name from title
                company_name = clean_company_name(title)
                if not company_name or len(company_name) < 3:
                    continue

                # Skip duplicates
                if company_name.lower() in seen_names:
                    continue
                if is_duplicate(company_name, existing):
                    print(f"  [SKIP] Already known: {company_name}")
                    continue

                # Extract emails and URLs
                emails = extract_emails_from_text(full_text)
                urls = extract_urls_from_text(full_text)

                website = ""
                if urls:
                    website = urls[0]
                elif link and 'google' not in link:
                    website = link

                email = emails[0] if emails else ""
                if not email and website:
                    # Attempt website crawl to extract email
                    email = find_email_on_website(website)

                seen_names.add(company_name.lower())
                discovered.append({
                    "name": company_name,
                    "email": email,
                    "website": website,
                    "category": "Discovered - Google Search",
                    "source": "google",
                    "snippet": snippet[:200].strip() if snippet else "",
                    "status": "discovered",
                    "discovered_at": datetime.datetime.now().isoformat()
                })
                print(f"  [NEW] {company_name} | {email if email else 'no email'} | {website}")

        except Exception as e:
            print(f"[ERROR] Google search failed for '{query}': {e}")

        # Delay between searches to avoid rate limiting
        import time
        time.sleep(4)

    return discovered



def scrape_naukri_recruiters(existing: set, limit: int = 30) -> list:
    """Scrape Naukri.com recruiter/company listings."""
    try:
        from scrapling.fetchers import StealthyFetcher
    except ImportError:
        print("[WARN] StealthyFetcher not available. Install with: pip install 'scrapling[fetchers]'")
        return []

    discovered = []
    seen_names = set()

    search_terms = [
        "IT recruitment agency",
        "AI ML recruitment",
        "tech staffing company",
    ]

    for term in search_terms:
        if len(discovered) >= limit:
            break

        print(f"\n[NAUKRI] Searching recruiters: '{term}'")
        try:
            url = f"https://www.naukri.com/recruiters?searchType=company&keyword={term.replace(' ', '+')}"
            page = StealthyFetcher.fetch(url, headless=True, network_idle=True)

            if not page:
                print("[WARN] Naukri returned empty page")
                continue

            # Check if Naukri redirected to login or homepage
            if page.url and "recruiters" not in page.url.lower():
                print(f"[INFO] Naukri redirected to {page.url}. Naukri's public recruiter directory is not accessible without an authenticated session/login.")
                break

            # Try to find recruiter cards/listings
            cards = page.css('.rec-card') or page.css('.company-card') or page.css('[class*="recruiter"]') or []
            print(f"[NAUKRI] Found {len(cards)} recruiter cards")

            for card in cards:
                if len(discovered) >= limit:
                    break

                # Extract company name
                name_el = card.css('h2') or card.css('h3') or card.css('a')
                if not name_el:
                    continue
                name = clean_company_name(name_el[0].text or "")
                if not name or len(name) < 3:
                    continue

                if name.lower() in seen_names or is_duplicate(name, existing):
                    continue

                # Extract any email/url from the card text
                card_text = card.text or ""
                emails = extract_emails_from_text(card_text)
                urls = extract_urls_from_text(card_text)

                # Try to get the link
                link_el = card.css('a')
                website = urls[0] if urls else (link_el[0].attrib.get('href', '') if link_el else "")

                seen_names.add(name.lower())
                discovered.append({
                    "name": name,
                    "email": emails[0] if emails else "",
                    "website": website,
                    "category": "Discovered - Naukri",
                    "source": "naukri",
                    "snippet": card_text[:200].strip() if card_text else "",
                    "status": "discovered",
                    "discovered_at": datetime.datetime.now().isoformat()
                })
                print(f"  [NEW] {name} | {emails[0] if emails else 'no email'}")

        except Exception as e:
            print(f"[ERROR] Naukri scrape failed: {e}")

        import time
        time.sleep(5)

    return discovered


# --- Main Entry Point ---------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Discover new recruitment agencies via web scraping")
    parser.add_argument("--source", choices=["google", "naukri", "all"], default="all",
                        help="Which source to scrape (default: all)")
    parser.add_argument("--limit", type=int, default=50,
                        help="Maximum agencies to discover per source (default: 50)")
    args = parser.parse_args()

    print("=" * 60)
    print("  AGENCY DISCOVERY SCRAPER")
    print("=" * 60)

    # Load existing companies to avoid duplicates
    existing = load_existing_companies()
    print(f"[INFO] Loaded {len(existing)} existing companies to skip")

    # Load any previously discovered agencies
    all_discovered = load_discovered()
    existing_discovered_count = len(all_discovered)
    print(f"[INFO] Previously discovered: {existing_discovered_count} agencies")

    new_agencies = []

    # --- Google Search ---
    if args.source in ("google", "all"):
        print("\n" + "=" * 40)
        print("  SOURCE: Google Search")
        print("=" * 40)
        google_results = scrape_google_search(SEARCH_QUERIES, existing, limit=args.limit)
        new_agencies.extend(google_results)
        print(f"\n[GOOGLE] Discovered {len(google_results)} new agencies")

        # Add to existing set to avoid cross-source duplicates
        for a in google_results:
            existing.add(a["name"].lower())

    # --- Naukri ---
    if args.source in ("naukri", "all"):
        print("\n" + "=" * 40)
        print("  SOURCE: Naukri Recruiter Directory")
        print("=" * 40)
        naukri_results = scrape_naukri_recruiters(existing, limit=args.limit)
        new_agencies.extend(naukri_results)
        print(f"\n[NAUKRI] Discovered {len(naukri_results)} new agencies")

    # --- Save Results ---
    if new_agencies:
        all_discovered.extend(new_agencies)
        save_discovered(all_discovered)
        print(f"\n[SUMMARY] Discovered {len(new_agencies)} NEW agencies this run")
        print(f"[SUMMARY] Total discovered agencies: {len(all_discovered)}")
    else:
        print("\n[SUMMARY] No new agencies discovered this run")

    print("\n[TIP] Open the dashboard at http://localhost:8000 to review and approve discovered agencies")
    print("[DONE] Scraping complete.")


if __name__ == "__main__":
    main()
