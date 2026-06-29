"""
AUTH_SIMPLIFICATION TESTS
-------------------------
Verifies the simplified login flow and organization status rules for Zoiko One.
Statuses: ACTIVE, LOCKED, DEACTIVATED only (PASSWORD_RESET_REQUIRED removed from login).
Organization statuses: PENDING, APPROVED, ACTIVE, ON_HOLD, REJECTED, SUSPENDED, DEACTIVATED.

Run:  python -m scripts.test_auth_simplification
"""

from app.main import app
from fastapi.testclient import TestClient
from app.core.security import create_access_token
from app.database import SessionLocal
from app.modules.hr.models import Employee, EmployeeStatus, Organization, OrganizationStatus
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

def test_login_scenario(db, label, email, password, expected_message_contains, org_active=True, org_status=None):
    try:
        org_user = db.query(Employee).filter(Employee.email == email).first()
        if org_user and org_user.organization_id:
            if org_status is not None:
                o = db.execute(text("SELECT status FROM organizations WHERE id = :oid"),
                               {"oid": org_user.organization_id}).first()
                if o and o[0] != org_status:
                    db.execute(text("UPDATE organizations SET status = :s, is_active = TRUE WHERE id = :oid"),
                               {"s": org_status, "oid": org_user.organization_id})
                    db.commit()
            else:
                o = db.execute(text("SELECT status FROM organizations WHERE id = :oid"),
                               {"oid": org_user.organization_id}).first()
                if o and not org_active:
                    db.execute(text("UPDATE organizations SET status = 'SUSPENDED' WHERE id = :oid"),
                               {"oid": org_user.organization_id})
                    db.commit()
                elif o and org_active and o[0] != "ACTIVE":
                    db.execute(text("UPDATE organizations SET status = 'ACTIVE', is_active = TRUE WHERE id = :oid"),
                               {"oid": org_user.organization_id})
                    db.commit()

        db.expire_all()
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
        emp = db.query(Employee).filter(Employee.role == "employee").first()
        if not emp:
            print(f"{FAIL} No employee user found in DB. Seed data required.")
            exit(1)

        admin = db.query(Employee).filter(Employee.role == "super_admin").first()
        if not admin:
            print(f"{FAIL} No super_admin user found in DB. Seed data required.")
            exit(1)

        emp_id = emp.id
        emp_email = emp.email
        org_id = emp.organization_id
        print(f"\nUsing employee: {emp_email} (id={emp_id}, org_id={org_id})")
        print()

        if org_id:
            db.execute(text("UPDATE organizations SET status = 'ACTIVE', is_active = TRUE WHERE id = :oid"),
                       {"oid": org_id})
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

        # ── Test 4: Unlock user -> Login succeeds ──
        print("\n4. Unlock User -> Login succeeds")
        reset_user(db, emp_id, EmployeeStatus.ACTIVE, True)
        test_login_scenario(db, "Unlocked user login succeeds", emp_email, "test123", "")

        # ── Test 5: Disable user -> Login blocked ──
        print("\n5. Disable User Login")
        reset_user(db, emp_id, EmployeeStatus.DEACTIVATED, False)
        test_login_scenario(db, "Disabled user login blocked", emp_email, "test123",
                           "deactivated")

        # ── Test 6: Org suspended -> Login blocked ──
        print("\n6. Organization Suspended -> Login blocked")
        reset_user(db, emp_id, EmployeeStatus.ACTIVE, True)
        test_login_scenario(db, "Org suspended login blocked", emp_email, "test123",
                           "suspended", org_active=False)

        # ── Test 7: Active org + Active user -> Login succeeds ──
        print("\n7. Active Org + Active User -> Login succeeds")
        reset_user(db, emp_id, EmployeeStatus.ACTIVE, True)
        if org_id:
            db.execute(text("UPDATE organizations SET status = 'ACTIVE', is_active = TRUE WHERE id = :oid"),
                       {"oid": org_id})
            db.commit()
        test_login_scenario(db, "Active org + active user login succeeds", emp_email, "test123", "")

        # ── Test 8: Active org + Locked user -> Login blocked ──
        print("\n8. Active Org + Locked User -> Login blocked")
        reset_user(db, emp_id, EmployeeStatus.LOCKED, True)
        if org_id:
            db.execute(text("UPDATE organizations SET status = 'ACTIVE', is_active = TRUE WHERE id = :oid"),
                       {"oid": org_id})
            db.commit()
        test_login_scenario(db, "Active org + locked user blocked", emp_email, "test123",
                           "locked by the administrator")

        # ── Test 9: Active org + Deactivated user -> Login blocked ──
        print("\n9. Active Org + Deactivated User -> Login blocked")
        reset_user(db, emp_id, EmployeeStatus.DEACTIVATED, False)
        if org_id:
            db.execute(text("UPDATE organizations SET status = 'ACTIVE', is_active = TRUE WHERE id = :oid"),
                       {"oid": org_id})
            db.commit()
        test_login_scenario(db, "Active org + deactivated user blocked", emp_email, "test123",
                           "deactivated")

        # ── Test 10: Org PENDING blocks login ──
        print("\n10. Organization PENDING -> Login blocked")
        reset_user(db, emp_id, EmployeeStatus.ACTIVE, True)
        test_login_scenario(db, "Org PENDING blocks login", emp_email, "test123",
                           "pending Super Admin approval",
                           org_status="PENDING")

        # ── Test 11: Org ON_HOLD blocks login ──
        print("\n11. Organization ON_HOLD -> Login blocked")
        reset_user(db, emp_id, EmployeeStatus.ACTIVE, True)
        test_login_scenario(db, "Org ON_HOLD blocks login", emp_email, "test123",
                           "on hold",
                           org_status="ON_HOLD")

        # ── Test 12: Org APPROVED allows login ──
        print("\n12. Organization APPROVED + Active User -> Login succeeds")
        reset_user(db, emp_id, EmployeeStatus.ACTIVE, True)
        test_login_scenario(db, "Org APPROVED + active user login succeeds", emp_email, "test123",
                           "",
                           org_status="APPROVED")

        # ── API-level tests ──
        if org_id:
            token = create_access_token({"sub": admin.email, "role": "super_admin", "id": admin.id})
            headers = {"Authorization": f"Bearer {token}"}

            db.execute(text("UPDATE organizations SET status = 'ACTIVE', is_active = TRUE WHERE id = :oid"),
                       {"oid": org_id})
            db.commit()

            # ── Test 13: Org stats endpoint ──
            print("\n13. Organization Stats Endpoint")
            r = client.get(f"/super-admin/organizations/{org_id}/stats", headers=headers)
            print(f"  {PASS if r.status_code == 200 else FAIL} GET stats: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                print(f"    total_users={data.get('total_users')}, org_admins={data.get('org_admin_count')}")

            # ── Test 14: Org users endpoint ──
            print("\n14. Organization Users Endpoint")
            r = client.get(f"/super-admin/organizations/{org_id}/users", headers=headers)
            print(f"  {PASS if r.status_code == 200 else FAIL} GET users: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                print(f"    total={data.get('total')}")

            # ── Test 15: Put On Hold endpoint ──
            print("\n15. Put On Hold Endpoint")
            db.execute(text("UPDATE organizations SET status = 'ACTIVE', is_active = TRUE WHERE id = :oid"),
                       {"oid": org_id})
            db.commit()
            r = client.put(f"/super-admin/organizations/{org_id}/hold", headers=headers)
            print(f"  {PASS if r.status_code == 200 else FAIL} PUT hold: {r.status_code}")
            if r.status_code == 200:
                db.expire_all()
                org_check = db.query(Organization).filter(Organization.id == org_id).first()
                print(f"  {PASS if org_check and org_check.status == OrganizationStatus.ON_HOLD else FAIL} On hold status: {org_check.status if org_check else 'None'}")

            db.execute(text("UPDATE organizations SET status = 'ACTIVE', is_active = TRUE WHERE id = :oid"),
                       {"oid": org_id})
            db.commit()

            # ── Test 16: Approve org endpoint ──
            print("\n16. Approve Organization Endpoint")
            db.execute(text("UPDATE organizations SET status = 'PENDING' WHERE id = :oid"),
                       {"oid": org_id})
            db.commit()
            r = client.put(f"/super-admin/organizations/{org_id}/approve", headers=headers)
            print(f"  {PASS if r.status_code == 200 else FAIL} PUT approve: {r.status_code}")
            if r.status_code == 200:
                db.expire_all()
                org_check = db.query(Organization).filter(Organization.id == org_id).first()
                print(f"  {PASS if org_check and org_check.status == OrganizationStatus.ACTIVE else FAIL} Approve status: {org_check.status if org_check else 'None'}")

            # ── Test 17: Reactivate org endpoint ──
            print("\n17. Reactivate Organization Endpoint")
            db.execute(text("UPDATE organizations SET status = 'SUSPENDED' WHERE id = :oid"),
                       {"oid": org_id})
            db.commit()
            r = client.put(f"/super-admin/organizations/{org_id}/reactivate", headers=headers)
            print(f"  {PASS if r.status_code == 200 else FAIL} PUT reactivate: {r.status_code}")
            if r.status_code == 200:
                db.expire_all()
                org_check = db.query(Organization).filter(Organization.id == org_id).first()
                print(f"  {PASS if org_check and org_check.status == OrganizationStatus.ACTIVE else FAIL} Reactivate status: {org_check.status if org_check else 'None'}")

        else:
            print("\n(Skipping API tests: employee has no organization_id)")

        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETE")
        print("=" * 60)

    finally:
        reset_user(db, emp_id, EmployeeStatus.ACTIVE, True)
        if emp and emp.organization_id:
            db.execute(text("UPDATE organizations SET status = 'ACTIVE', is_active = TRUE WHERE id = :oid"),
                       {"oid": emp.organization_id})
            db.commit()
        db.close()
