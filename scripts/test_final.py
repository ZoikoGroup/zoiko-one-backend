from app.main import app
from fastapi.testclient import TestClient
from app.core.security import create_access_token
from app.database import SessionLocal
from app.modules.hr.models import Employee

client = TestClient(app)

db = SessionLocal()
user = db.query(Employee).filter(Employee.role == "super_admin").first()
db.close()

token = create_access_token({"sub": user.email, "role": "super_admin", "id": user.id})
headers = {"Authorization": f"Bearer {token}"}

# Dashboard
r = client.get("/super-admin/dashboard", headers=headers)
print(f"DASHBOARD: {r.status_code}")
d = r.json()
for f in ["total_organizations", "total_users", "enabled_users", "disabled_users", "locked_users", "pending_invitations"]:
    print(f"  {f}: {d.get(f)}")

# Users list
r = client.get("/super-admin/users", headers=headers)
print(f"USERS LIST: {r.status_code}")
d = r.json()
if d.get("users"):
    u = d["users"][0]
    print(f"  First user: {u['email']} status={u.get('status','missing')}")
else:
    print(f"  No users: {d}")
