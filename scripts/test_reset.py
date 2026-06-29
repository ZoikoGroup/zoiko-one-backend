from app.main import app
from fastapi.testclient import TestClient
from app.core.security import create_access_token
from app.database import SessionLocal
from app.modules.hr.models import Employee

client = TestClient(app)

db = SessionLocal()
admin = db.query(Employee).filter(Employee.role == "super_admin").first()
target = db.query(Employee).filter(Employee.role == "employee").first()
db.close()

token = create_access_token({"sub": admin.email, "role": "super_admin", "id": admin.id})
headers = {"Authorization": f"Bearer {token}"}

# Test 1: Normal reset (no send_email)
r = client.post(f"/super-admin/users/{target.id}/reset-password", headers=headers)
print(f"Status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    for k in ["temporary_password", "must_change_password", "user_id", "message"]:
        print(f"  {k}: {data.get(k)}")
else:
    print(f"  Error: {r.text[:300]}")

# Test 2: With send_email=true
r2 = client.post(f"/super-admin/users/{target.id}/reset-password?send_email=true", headers=headers)
print(f"\nWith send_email=true — Status: {r2.status_code}")
if r2.status_code == 200:
    data = r2.json()
    print(f"  temporary_password: {data.get('temporary_password')}")
    print(f"  must_change_password: {data.get('must_change_password')}")
    print(f"  user_id: {data.get('user_id')}")
else:
    print(f"  Error: {r2.text[:300]}")

# Test 3: Verify user was set to PASSWORD_RESET_REQUIRED
db = SessionLocal()
user = db.query(Employee).filter(Employee.id == target.id).first()
print(f"\nUser status after reset: {user.status} (expected: EmployeeStatus.PASSWORD_RESET_REQUIRED)")
db.close()
