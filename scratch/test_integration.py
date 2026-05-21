import sys
import os
import json
import time
import subprocess
import shutil
import urllib.request
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# Paths
DISCOVERED_FILE = PROJECT_ROOT / "discovered_agencies.json"
STATUS_FILE = PROJECT_ROOT / "emailed_status.json"
EXCEL_PATH = PROJECT_ROOT / "Consultancies.xlsx"

# Backups
DISCOVERED_BAK = PROJECT_ROOT / "discovered_agencies.json.bak"
STATUS_BAK = PROJECT_ROOT / "emailed_status.json.bak"

def setup_test_data():
    print("[TEST] Backing up original JSON files...")
    if DISCOVERED_FILE.exists():
        shutil.copy2(DISCOVERED_FILE, DISCOVERED_BAK)
    if STATUS_FILE.exists():
        shutil.copy2(STATUS_FILE, STATUS_BAK)
        
    # Write mock discovered agencies
    mock_discovered = [
        {
            "name": "Test Agency 1",
            "email": "hr@testagency1.com",
            "website": "https://testagency1.com",
            "category": "Discovered - Google Search",
            "source": "google",
            "status": "discovered",
            "discovered_at": "2026-05-20T12:00:00"
        },
        {
            "name": "Test Agency 2",
            "email": "",
            "website": "https://testagency2.com",
            "category": "Discovered - Naukri",
            "source": "naukri",
            "status": "discovered",
            "discovered_at": "2026-05-20T12:00:00"
        }
    ]
    DISCOVERED_FILE.write_text(json.dumps(mock_discovered, indent=2, ensure_ascii=False), encoding="utf-8")
    
    # Write fresh empty status file for test predictability
    STATUS_FILE.write_text(json.dumps({}, indent=2, ensure_ascii=False), encoding="utf-8")

def restore_data():
    print("[TEST] Restoring original JSON files...")
    for file, bak in [(DISCOVERED_FILE, DISCOVERED_BAK), (STATUS_FILE, STATUS_BAK)]:
        if bak.exists():
            shutil.copy2(bak, file)
            os.remove(bak)
        elif file.exists():
            os.remove(file)

def run_tests():
    # 1. Start Server
    print("[TEST] Starting dashboard server...")
    python_exe = str(PROJECT_ROOT / "venv" / "Scripts" / "python.exe")
    print(f"[TEST] Python path: {python_exe}")
    print(f"[TEST] Working directory: {PROJECT_ROOT}")
    server_process = subprocess.Popen(
        [python_exe, "dashboard_server.py"],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(2) # Give it time to bind and start
    print(f"[TEST] Server PID: {server_process.pid}, Poll status: {server_process.poll()}")
    
    try:
        # 2. Get pending discovered list
        print("[TEST] Fetching pending discovered agencies...")
        res_data = None
        for i in range(10):
            try:
                req = urllib.request.Request("http://127.0.0.1:8000/api/discovered")
                with urllib.request.urlopen(req) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    break
            except Exception as e:
                print(f"[TEST] Server not ready yet (attempt {i+1}/10): {e}")
                time.sleep(1)
                
        assert res_data is not None, "Server did not respond within timeout"
        print(f"[TEST] Received discovered: {res_data}")
        assert len(res_data) == 2, "Should have 2 pending agencies"
            
        # 3. Approve Test Agency 1
        print("[TEST] Approving 'Test Agency 1'...")
        payload = json.dumps({"name": "Test Agency 1"}).encode('utf-8')
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/discovered/approve",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            print(f"[TEST] Approve response: {res_data}")
            assert res_data.get("success") is True
            
        # 4. Verify in emailed_status.json
        status_data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        print(f"[TEST] Status data: {status_data}")
        assert "Test Agency 1" in status_data
        assert status_data["Test Agency 1"]["status"] == "pending_email"
        assert status_data["Test Agency 1"]["category"] == "Discovered - Google Search"
        
        # 5. Verify in /api/status endpoint
        print("[TEST] Fetching status list from server...")
        req = urllib.request.Request("http://127.0.0.1:8000/api/status")
        with urllib.request.urlopen(req) as response:
            status_list = json.loads(response.read().decode('utf-8'))
            test_agency_in_list = [item for item in status_list if item["name"] == "Test Agency 1"]
            print(f"[TEST] Matched agency in /api/status: {test_agency_in_list}")
            assert len(test_agency_in_list) == 1
            assert test_agency_in_list[0]["status"] == "pending_email"
            assert test_agency_in_list[0]["category"] == "Discovered - Google Search"
            
        # 6. Verify that job_agent.py loads the approved candidate correctly
        print("[TEST] Verifying job_agent.py loading...")
        import pandas as pd
        from job_agent import load_status, parse_consultancies
        
        status_tracker = load_status()
        excel_companies = set()
        
        # Read Excel consultancies
        df_consultancies = parse_consultancies()
        for _, row in df_consultancies.iterrows():
            comp_name = str(row.get("Company Name", "")).strip()
            if comp_name:
                excel_companies.add(comp_name.lower())
                
        all_candidates = []
        for comp_name, entry in status_tracker.items():
            if comp_name.lower() not in excel_companies:
                status = entry.get("status", "")
                if status in ("pending_email", "pending_web_form", "sent", "responded", "interviewing", "skipped"):
                    all_candidates.append({
                        "name": comp_name,
                        "email": entry.get("email", ""),
                        "website": entry.get("website", ""),
                        "category": entry.get("category", "Discovered Agency"),
                        "excel_note": entry.get("note", "")
                    })
        
        matched_job_agent = [c for c in all_candidates if c["name"] == "Test Agency 1"]
        print(f"[TEST] Matched agency in job_agent candidate list: {matched_job_agent}")
        assert len(matched_job_agent) == 1
        assert matched_job_agent[0]["email"] == "hr@testagency1.com"
        assert matched_job_agent[0]["category"] == "Discovered - Google Search"
        
        print("\n[SUCCESS] All integration tests passed successfully!")
        
    finally:
        print("[TEST] Terminating server...")
        server_process.terminate()
        stdout, stderr = server_process.communicate()
        if stdout:
            print("\n--- Server Stdout ---")
            print(stdout.decode('utf-8', errors='replace'))
        if stderr:
            print("\n--- Server Stderr ---")
            print(stderr.decode('utf-8', errors='replace'))
        server_process.wait()

if __name__ == "__main__":
    try:
        setup_test_data()
        run_tests()
    except Exception as e:
        print(f"\n[FAILURE] Integration tests failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        restore_data()
