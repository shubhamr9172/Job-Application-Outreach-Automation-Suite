import urllib.request
import json
import sys

def test_api():
    print("Testing dashboard server endpoints...")
    
    # 1. Test GET /api/status
    try:
        req = urllib.request.Request("http://localhost:8000/api/status")
        with urllib.request.urlopen(req, timeout=5) as response:
            status_code = response.getcode()
            body = response.read().decode('utf-8')
            print(f"[GET /api/status] Response code: {status_code}")
            
            data = json.loads(body)
            print(f"[GET /api/status] Loaded {len(data)} records successfully.")
            if len(data) > 0:
                print(f"[GET /api/status] First item company name: {data[0].get('name')}")
    except Exception as e:
        print(f"[GET /api/status] Failed: {e}")
        sys.exit(1)

    # 2. Test GET /index.html (Static File)
    try:
        req = urllib.request.Request("http://localhost:8000/")
        with urllib.request.urlopen(req, timeout=5) as response:
            status_code = response.getcode()
            body = response.read().decode('utf-8')
            print(f"[GET /] Response code: {status_code}")
            if "Job Application & Outreach Dashboard" in body:
                print("[GET /] Static page loaded correctly.")
            else:
                print("[GET /] Static page contents mismatched.")
    except Exception as e:
        print(f"[GET /] Failed: {e}")
        sys.exit(1)

    print("[SUCCESS] All basic dashboard verification tests passed!")

if __name__ == "__main__":
    test_api()
