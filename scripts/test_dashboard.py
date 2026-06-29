from app.main import app
from fastapi.testclient import TestClient
from app.core.security import create_access_token
from app.database import SessionLocal
from app.modules.hr.models import Employee

client = TestClient(app)

db = SessionLocal()
user = db.query(Employee).filter(Employee.role == "super_admin").first()
db.close()
print(f"Super admin: {user.email}")

token = create_access_token({"sub": user.email, "role": "super_admin", "id": user.id})
headers = {"Authorization": f"Bearer {token}"}
r = client.get("/super-admin/dashboard", headers=headers)
print(f"Dashboard status: {r.status_code}")

if r.status_code == 200:
    data = r.json()
    for k in ["total_organizations", "total_users", "enabled_users", "disabled_users", "locked_users", "pending_invitations"]:
        val = data.get(k, "MISSING")
        print(f"  {k}: {val}")
else:
    print(r.text[:800])
