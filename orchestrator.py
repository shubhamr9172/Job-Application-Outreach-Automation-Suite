"""
Master Orchestrator Agent (Wrapper)
-----------------------------------
Redirects execution to src/agents/orchestrator.py.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR / "src" / "agents"))

import orchestrator
if __name__ == "__main__":
    orchestrator.main()
