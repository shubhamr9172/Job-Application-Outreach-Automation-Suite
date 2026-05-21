import subprocess
import sys
import time
import urllib.request
import urllib.error

p = subprocess.Popen(
    [sys.executable, "dashboard_server.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

time.sleep(2)

print("Checking server status...")
try:
    with urllib.request.urlopen("http://localhost:8000/api/discovered") as response:
        print("Status Code:", response.getcode())
        print("Headers:", response.headers.items())
        print("Body:", response.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code, e.reason)
    print("Error Headers:", e.headers.items())
    try:
        print("Error Body:", e.read().decode('utf-8'))
    except Exception:
        pass
except Exception as e:
    print("Other Error:", e)

p.terminate()
stdout, stderr = p.communicate()
print("\n--- Server Stdout ---")
print(stdout)
print("\n--- Server Stderr ---")
print(stderr)
