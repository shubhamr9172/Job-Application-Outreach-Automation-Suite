"""
Job Application & Outreach Dashboard Server (Wrapper)
-----------------------------------------------------
Redirects execution to the professional package structure under src/server/server.py.
"""
import sys
from pathlib import Path

# Resolve directories
ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR / "src" / "server"))
sys.path.insert(0, str(ROOT_DIR / "src" / "agents"))
sys.path.insert(0, str(ROOT_DIR / "src" / "scrapers"))

import server
if __name__ == "__main__":
    server.main()
