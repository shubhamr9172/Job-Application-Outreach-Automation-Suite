"""
Resume Fixer Agent (Wrapper)
----------------------------
Redirects execution to src/agents/resume_fixer.py.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR / "src" / "agents"))

import resume_fixer
if __name__ == "__main__":
    resume_fixer.main()
