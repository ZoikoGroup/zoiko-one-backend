"""Test fixed reports list."""
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
headers = {"Authorization": f"Bearer {token}"}

# Test reports list
req = urllib.request.Request(f"{BASE}/hr/workforce/reports?page=1&per_page=10", method="GET", headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        print("SUCCESS: total=" + str(result.get('total')))
        for r in result.get('items', []):
            print(f'  Report id={r.get("id")}, name={r.get("report_name")}, by={r.get("generated_by_name")}')
except urllib.error.HTTPError as e:
    print('ERROR:', e.code, e.read().decode()[:300])
