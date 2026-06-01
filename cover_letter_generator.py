"""
Cover Letter Generator Agent (Wrapper)
--------------------------------------
Redirects execution to src/agents/cover_letter_generator.py.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR / "src" / "agents"))

import cover_letter_generator
if __name__ == "__main__":
    cover_letter_generator.main()
