from app.main import app
from fastapi.testclient import TestClient
from app.core.security import create_access_token
from app.database import SessionLocal
from app.modules.hr.models import Employee

client = TestClient(app)

db = SessionLocal()
user = db.query(Employee).filter(Employee.role == "super_admin").first()
print(f"Super admin: {user.email}")

# Get a regular employee to test on
target = db.query(Employee).filter(Employee.role == "employee").first()
db.close()
print(f"Target user: {target.id} - {target.email} (status={target.status}, active={target.is_active})")

token = create_access_token({"sub": user.email, "role": "super_admin", "id": user.id})
headers = {"Authorization": f"Bearer {token}"}
base = f"/super-admin/users/{target.id}"

tests = [
    ("disable", "put", f"{base}/disable"),
    ("enable", "put", f"{base}/enable"),
    ("lock", "put", f"{base}/lock"),
    ("unlock", "put", f"{base}/unlock"),
    ("reset-password", "post", f"{base}/reset-password"),
    ("audit-history", "get", f"{base}/audit-history"),
]

for label, method, url in tests:
    if method == "get":
        r = client.get(url, headers=headers)
    elif method == "post":
        r = client.post(url, headers=headers)
    else:
        r = client.put(url, headers=headers)
    status = "OK" if r.status_code == 200 else f"FAIL({r.status_code})"
    try:
        data = r.json()
        msg = data.get("message", data.get("detail", ""))
    except:
        msg = r.text[:100]
    print(f"  {label:15s} -> {status:15s} {msg}")
