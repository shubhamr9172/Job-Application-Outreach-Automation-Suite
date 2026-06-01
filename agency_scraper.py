"""
Agency Discovery Scraper (Wrapper)
----------------------------------
Redirects execution to src/scrapers/agency_scraper.py.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR / "src" / "scrapers"))
sys.path.insert(0, str(ROOT_DIR / "src" / "agents"))

import agency_scraper
if __name__ == "__main__":
    agency_scraper.main()
