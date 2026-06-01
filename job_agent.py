"""
Job Application & Cold Emailing Agent (Wrapper)
-----------------------------------------------
Redirects execution to src/agents/job_agent.py.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR / "src" / "agents"))

import job_agent
if __name__ == "__main__":
    job_agent.main()
