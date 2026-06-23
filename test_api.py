"""Test all workforce API endpoints with authentication."""
import urllib.request
import urllib.error
import json

BASE = "http://localhost:8000"

def get_token():
    """Login as admin and get JWT token."""
    data = json.dumps({"email": "admin@zoiko.com", "password": "admin123"}).encode()
    req = urllib.request.Request(f"{BASE}/auth/login", data=data, method="POST",
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        return result.get("access_token")

def test_api(method, path, token):
    url = BASE + path
    headers = {"Authorization": f"Bearer {token}"}
    req = urllib.request.Request(url, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return resp.status, data
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:500]
    except Exception as e:
        return None, str(e)

token = get_token()
print(f"Got token: {token[:20]}...\n")

endpoints = [
    ("GET", "/hr/workforce/dashboard"),
    ("GET", "/hr/workforce/plans?page=1&per_page=10"),
    ("GET", "/hr/workforce/headcount?page=1&per_page=10"),
    ("GET", "/hr/workforce/succession?page=1&per_page=10"),
    ("GET", "/hr/workforce/reports?page=1&per_page=10"),
]

for method, path in endpoints:
    status, data = test_api(method, path, token)
    
    if isinstance(data, dict):
        if "items" in data:
            items = data.get("items", [])
            total = data.get("total", "N/A")
            print(f"[{status}] {path}")
            print(f"         -> {len(items)} items of {total} total")
            for item in items[:3]:
                if "title" in item:
                    print(f"            [{item['id']}] {item['title']} | {item.get('status','')} | Dept={item.get('department_name','-')}")
                elif "fiscal_year" in item:
                    print(f"            [{item['id']}] FY={item['fiscal_year']} | Approved={item['approved_positions']} | Filled={item['filled_positions']}")
                elif "readiness_level" in item:
                    print(f"            [{item['id']}] Emp={item.get('employee_name','-')} -> Succ={item.get('successor_name','-')} | Readiness={item['readiness_level']}")
                elif "report_name" in item:
                    print(f"            [{item['id']}] {item['report_name']} | {item['report_type']}")
        elif "total_plans" in data:
            print(f"[{status}] {path} (DASHBOARD)")
            print(f"         Plans: {data.get('total_plans')} | Active: {data.get('active_plans')} | Budget: ${data.get('total_budget')}")
            print(f"         Headcount: {data.get('total_current_headcount')}/{data.get('total_headcount_target')} | Vacant: {data.get('total_vacant_positions')}")
            print(f"         Succession: {data.get('succession_count')} | Ready: {data.get('ready_successors')} | High Risk: {data.get('high_risk_count')}")
            print(f"         Dept breakdown: {len(data.get('department_breakdown', []))} depts")
            print(f"         Recent plans: {len(data.get('recent_plans', []))}")
            print(f"         Headcount by dept: {len(data.get('headcount_by_dept', []))}")
        else:
            print(f"[{status}] {path} -> {str(data)[:200]}")
    else:
        print(f"[{status}] {path} -> {data}")
