"""
Resume Update Agent (Wrapper)
-----------------------------
Redirects execution to src/agents/resume_agent.py.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR / "src" / "agents"))

import resume_agent
if __name__ == "__main__":
    resume_agent.main()
