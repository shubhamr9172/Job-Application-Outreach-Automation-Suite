"""
Skill Gap Agent (Wrapper)
-------------------------
Redirects execution to src/agents/skill_gap_agent.py.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR / "src" / "agents"))

import skill_gap_agent
if __name__ == "__main__":
    skill_gap_agent.main()
