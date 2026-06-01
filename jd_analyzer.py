"""
JD Analyzer Agent (Wrapper)
---------------------------
Redirects execution to src/agents/jd_analyzer.py.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR / "src" / "agents"))

import jd_analyzer
if __name__ == "__main__":
    jd_analyzer.main()
