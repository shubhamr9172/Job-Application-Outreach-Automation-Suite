import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from agency_scraper import find_email_on_website

url = "https://www.2softsolutions.com/"
email = find_email_on_website(url)
print(f"\nFinal extracted email for {url}: '{email}'")

url2 = "https://rtns.in/recruitment-agency-pune/"
email2 = find_email_on_website(url2)
print(f"\nFinal extracted email for {url2}: '{email2}'")
