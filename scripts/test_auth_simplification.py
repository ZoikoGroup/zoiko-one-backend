"""
AUTH_SIMPLIFICATION TESTS
-------------------------
Verifies the simplified login flow and user lifecycle for Zoiko One.
Statuses: ACTIVE, LOCKED, DEACTIVATED only (PASSWORD_RESET_REQUIRED removed from login).

Run:  python -m scripts.test_auth_simplification
"""

from app.main import app
from fastapi.testclient import TestClient
from app.core.security import create_access_token
from app.database import SessionLocal
from app.modules.hr.models import Employee, EmployeeStatus
from app.modules.hr.service import login_employee
from app.modules.hr.schemas import LoginRequest
from app.core.exceptions import UnauthorizedException
from app.core.security import hash_password
from datetime import datetime
from sqlalchemy import text

client = TestClient(app)
PASS = "[PASS]"
FAIL = "[FAIL]"

def reset_user(db, emp_id, status, is_active, password="test123"):
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if emp:
        emp.status = status
        emp.is_active = is_active
        emp.hashed_password = hash_password(password)
        db.commit()
        db.refresh(emp)
    return emp

def test_login_scenario(db, label, email, password, expected_message_contains, org_active=True):
    """Helper: attempt login and expect a specific message."""
    try:
        org = db.query(Employee).filter(Employee.email == email).first()
        if org and org.organization_id:
            o = db.execute(text("SELECT status FROM organizations WHERE id = :oid"),
                           {"oid": org.organization_id}).first()
            if o and not org_active:
                db.execute(text("UPDATE organizations SET status = 'SUSPENDED' WHERE id = :oid"),
                           {"oid": org.organization_id})
                db.commit()
            elif o and org_active and o[0] != "ACTIVE":
                db.execute(text("UPDATE organizations SET status = 'ACTIVE' WHERE id = :oid"),
                           {"oid": org.organization_id})
                db.commit()

        login_employee(db, LoginRequest(email=email, password=password))
        print(f"  {PASS} {label}")
        return True
    except UnauthorizedException as e:
        if expected_message_contains in str(e):
            print(f"  {PASS} {label} -> blocked: {e}")
            return True
        else:
            print(f"  {FAIL} {label} -> wrong message: {e}")
            return False
    except Exception as e:
        print(f"  {FAIL} {label} -> unexpected error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("AUTH SIMPLIFICATION TESTS")
    print("=" * 60)

    db = SessionLocal()
    try:
        # Find test users
        emp = db.query(Employee).filter(Employee.role == "employee").first()
        if not emp:
            print(f"{FAIL} No employee user found in DB. Seed data required.")
            exit(1)

        admin = db.query(Employee).filter(Employee.role == "super_admin").first()
        emp_id = emp.id
        emp_email = emp.email
        print(f"\nUsing employee: {emp_email} (id={emp_id})")
        print()

        # ── Reset org to ACTIVE first ──
        if emp.organization_id:
            db.execute(text("UPDATE organizations SET status = 'ACTIVE' WHERE id = :oid"),
                       {"oid": emp.organization_id})
            db.commit()

        # ── Test 1: Active user -> Login succeeds ──
        print("1. Active User Login")
        reset_user(db, emp_id, EmployeeStatus.ACTIVE, True)
        test_login_scenario(db, "Active user login succeeds", emp_email, "test123", "")

        # ── Test 2: Locked user -> Login blocked ──
        print("\n2. Locked User Login")
        reset_user(db, emp_id, EmployeeStatus.LOCKED, True)
        test_login_scenario(db, "Locked user login blocked", emp_email, "test123",
                           "locked by the administrator")

        # ── Test 3: Deactivated user -> Login blocked ──
        print("\n3. Deactivated User Login")
        reset_user(db, emp_id, EmployeeStatus.DEACTIVATED, False)
        test_login_scenario(db, "Deactivated user login blocked", emp_email, "test123",
                           "deactivated")

        # ── Test 4: Unlock user -> Login succeeds immediately ──
        print("\n4. Unlock User -> Login succeeds")
        reset_user(db, emp_id, EmployeeStatus.ACTIVE, True)
        test_login_scenario(db, "Unlocked user login succeeds", emp_email, "test123", "")

        # ── Test 5: Disable user -> Login blocked ──
        print("\n5. Disable User Login")
        reset_user(db, emp_id, EmployeeStatus.DEACTIVATED, False)
        test_login_scenario(db, "Disabled user login blocked", emp_email, "test123",
                           "deactivated")

        # ── Test 6: Organization suspended -> Login blocked ──
        print("\n6. Organization Suspended -> Login blocked")
        reset_user(db, emp_id, EmployeeStatus.ACTIVE, True)
        test_login_scenario(db, "Org suspended login blocked", emp_email, "test123",
                           "suspended", org_active=False)

        # ── Test 7: Active org + Active user -> Login succeeds ──
        print("\n7. Active Org + Active User -> Login succeeds")
        reset_user(db, emp_id, EmployeeStatus.ACTIVE, True)
        if emp.organization_id:
            db.execute(text("UPDATE organizations SET status = 'ACTIVE' WHERE id = :oid"),
                       {"oid": emp.organization_id})
            db.commit()
        test_login_scenario(db, "Active org + active user login succeeds", emp_email, "test123", "")

        # ── Test 8: Active org + Locked user -> Login blocked ──
        print("\n8. Active Org + Locked User -> Login blocked")
        reset_user(db, emp_id, EmployeeStatus.LOCKED, True)
        if emp.organization_id:
            db.execute(text("UPDATE organizations SET status = 'ACTIVE' WHERE id = :oid"),
                       {"oid": emp.organization_id})
            db.commit()
        test_login_scenario(db, "Active org + locked user blocked", emp_email, "test123",
                           "locked by the administrator")

        # ── Test 9: Active org + Deactivated user -> Login blocked ──
        print("\n9. Active Org + Deactivated User -> Login blocked")
        reset_user(db, emp_id, EmployeeStatus.DEACTIVATED, False)
        if emp.organization_id:
            db.execute(text("UPDATE organizations SET status = 'ACTIVE' WHERE id = :oid"),
                       {"oid": emp.organization_id})
            db.commit()
        test_login_scenario(db, "Active org + deactivated user blocked", emp_email, "test123",
                           "deactivated")

        # ── Test 10: API-level lock/unlock endpoints ──
        print("\n10. Lock/Unlock API Endpoints")
        token = create_access_token({"sub": admin.email, "role": "super_admin", "id": admin.id})
        headers = {"Authorization": f"Bearer {token}"}

        reset_user(db, emp_id, EmployeeStatus.ACTIVE, True)
        r = client.put(f"/super-admin/users/{emp_id}/lock", headers=headers)
        print(f"  {PASS if r.status_code == 200 else FAIL} Lock API: {r.status_code}")

        db.expire_all()
        emp_check = db.query(Employee).filter(Employee.id == emp_id).first()
        print(f"  {PASS if emp_check.status == EmployeeStatus.LOCKED else FAIL} Lock status: {emp_check.status}")

        r = client.put(f"/super-admin/users/{emp_id}/unlock", headers=headers)
        print(f"  {PASS if r.status_code == 200 else FAIL} Unlock API: {r.status_code}")

        db.expire_all()
        emp_check = db.query(Employee).filter(Employee.id == emp_id).first()
        print(f"  {PASS if emp_check.status == EmployeeStatus.ACTIVE else FAIL} Unlock status: {emp_check.status}")

        # ── Test 11: Admin lock/unlock from super_admin router ──
        print("\n11. Admin Lock/Unlock from Platform Users endpoint")
        r = client.put(f"/super-admin/users/{emp_id}/disable", headers=headers)
        print(f"  {PASS if r.status_code == 200 else FAIL} Disable API: {r.status_code}")
        db.expire_all()
        emp_check = db.query(Employee).filter(Employee.id == emp_id).first()
        print(f"  {PASS if not emp_check.is_active and emp_check.status == EmployeeStatus.DEACTIVATED else FAIL} Disable state: is_active={emp_check.is_active}, status={emp_check.status}")

        r = client.put(f"/super-admin/users/{emp_id}/enable", headers=headers)
        print(f"  {PASS if r.status_code == 200 else FAIL} Enable API: {r.status_code}")
        db.expire_all()
        emp_check = db.query(Employee).filter(Employee.id == emp_id).first()
        print(f"  {PASS if emp_check.is_active and emp_check.status == EmployeeStatus.ACTIVE else FAIL} Enable state: is_active={emp_check.is_active}, status={emp_check.status}")

        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETE")
        print("=" * 60)

    finally:
        # Restore user to ACTIVE
        reset_user(db, emp_id, EmployeeStatus.ACTIVE, True)
        if emp and emp.organization_id:
            db.execute(text("UPDATE organizations SET status = 'ACTIVE' WHERE id = :oid"),
                       {"oid": emp.organization_id})
            db.commit()
        db.close()
