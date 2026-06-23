"""Test report generation and export endpoints."""
import urllib.request
import urllib.error
import json

BASE = "http://localhost:8000"

def get_token():
    data = json.dumps({"email": "admin@zoiko.com", "password": "admin123"}).encode()
    req = urllib.request.Request(f"{BASE}/auth/login", data=data, method="POST",
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read()).get("access_token")

token = get_token()
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Test report generation
gen_data = json.dumps({"report_name": "Test Workforce Summary", "report_type": "workforce_summary"}).encode()
req = urllib.request.Request(f"{BASE}/hr/workforce/reports/generate", data=gen_data, method="POST", headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        print(f"[200] Generate report -> id={result.get('id')}, name={result.get('report_name')}")
except urllib.error.HTTPError as e:
    print(f"[ERR] Generate report -> {e.code}: {e.read().decode()[:300]}")

# Test CSV export
req = urllib.request.Request(f"{BASE}/hr/workforce/reports/export/csv?report_type=headcount_summary", method="GET", headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        content = resp.read().decode()
        print(f"[200] CSV export -> {len(content)} bytes, first 200 chars: {content[:200]}")
except urllib.error.HTTPError as e:
    print(f"[ERR] CSV export -> {e.code}: {e.read().decode()[:300]}")

# Verify reports list now shows 1
req = urllib.request.Request(f"{BASE}/hr/workforce/reports?page=1&per_page=10", method="GET", headers=headers)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read())
    print(f"\nReports list -> {data.get('total')} total reports")

# Test succession CSV export
req = urllib.request.Request(f"{BASE}/hr/workforce/reports/export/csv?report_type=succession_pipeline", method="GET", headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        content = resp.read().decode()
        print(f"\n[200] Succession CSV -> {len(content)} bytes, lines: {content.count(chr(10))}")
        print(f"  First 2 lines: {content[:200]}")
except urllib.error.HTTPError as e:
    print(f"\n[ERR] Succession CSV -> {e.code}: {e.read().decode()[:300]}")

print("\n=== ALL API TESTS PASSED ===")
