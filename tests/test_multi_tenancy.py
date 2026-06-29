"""Tests for organization-level multi-tenancy isolation.

Every test verifies that one organization's users cannot read, create, update,
or delete another organization's data. Super Admin is the only role that can
bypass organization boundaries (with explicit org_id).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.hr.models import (
    Employee, Organization, OrganizationStatus, Department, UserRole, EmployeeStatus,
    EmploymentType, Gender
)
from app.core.security import hash_password
from datetime import date


# ── Helpers ─────────────────────────────────────────────────────────────────

def create_org(db: Session, name: str, code: str) -> Organization:
    org = Organization(name=name, code=code, status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    db.refresh(org)
    return org


def create_dept(db: Session, name: str, code: str, org_id: int) -> Department:
    dept = Department(name=name, code=code, organization_id=org_id)
    db.add(dept)
    db.flush()
    db.refresh(dept)
    return dept


def create_employee(
    db: Session, email: str, org_id: int, dept_id: int,
    role: UserRole = UserRole.ADMIN, password: str = "pass123"
) -> Employee:
    emp = Employee(
        email=email,
        hashed_password=hash_password(password),
        role=role,
        is_active=True,
        first_name="Test",
        last_name="User",
        phone="0000000000",
        date_of_birth=date(1990, 1, 1),
        gender=Gender.MALE,
        employee_code=f"ZK-{org_id}-{email[:3]}",
        job_title="Tester",
        employment_type=EmploymentType.FULL_TIME,
        status=EmployeeStatus.ACTIVE,
        date_of_joining=date(2024, 1, 1),
        department_id=dept_id,
        organization_id=org_id,
    )
    db.add(emp)
    db.flush()
    db.refresh(emp)
    return emp


def login_as(client: TestClient, email: str, password: str = "pass123") -> dict:
    resp = client.post("/auth/login", json={
        "email": email,
        "password": password,
    })
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def two_orgs(db: Session):
    """Creates two organizations with one admin each."""
    org_a = create_org(db, "Org A", "ORGA")
    org_b = create_org(db, "Org B", "ORGB")

    dept_a = create_dept(db, "Engineering A", "ENGA", org_a.id)
    dept_b = create_dept(db, "Engineering B", "ENGB", org_b.id)

    admin_a = create_employee(db, "admin_a@test.com", org_a.id, dept_a.id, UserRole.ADMIN)
    admin_b = create_employee(db, "admin_b@test.com", org_b.id, dept_b.id, UserRole.ADMIN)

    db.flush()
    return {
        "org_a": org_a,
        "org_b": org_b,
        "dept_a": dept_a,
        "dept_b": dept_b,
        "admin_a": admin_a,
        "admin_b": admin_b,
    }


# ── Dependency Tests ────────────────────────────────────────────────────────

class TestOrganizationDependencies:
    """Test the organization isolation dependencies directly."""

    def test_get_organization_id_blocks_super_admin(self, db):
        """Super Admin cannot use get_organization_id; must use get_super_admin_organization_id."""
        from app.core.dependencies import get_organization_id

        org = db.query(Organization).first()

        class FakeUser:
            role = UserRole.SUPER_ADMIN
            organization_id = org.id

        with pytest.raises(Exception) as exc:
            get_organization_id(current_user=FakeUser())
        assert "Super Admin must use get_super_admin_organization_id" in str(exc.value)

    def test_get_organization_id_returns_org_id(self, db):
        """Regular users get their organization_id from get_organization_id."""
        from app.core.dependencies import get_organization_id

        org = db.query(Organization).first()

        class FakeUser:
            role = UserRole.ADMIN
            organization_id = org.id

        result = get_organization_id(current_user=FakeUser())
        assert result == org.id

    def test_get_organization_id_raises_for_none_org(self):
        """Users without organization_id get a ForbiddenException."""
        from app.core.dependencies import get_organization_id

        class FakeUser:
            role = UserRole.ADMIN
            organization_id = None

        with pytest.raises(Exception) as exc:
            get_organization_id(current_user=FakeUser())
        assert "not associated with any organization" in str(exc.value)

    def test_super_admin_dependency_blocks_non_super_admin(self):
        """Non-Super Admin users cannot use get_super_admin_organization_id."""
        from app.core.dependencies import get_super_admin_organization_id

        class FakeUser:
            role = UserRole.ADMIN

        with pytest.raises(Exception) as exc:
            get_super_admin_organization_id(organization_id=1, current_user=FakeUser())
        assert "Only Super Admin" in str(exc.value)

    def test_super_admin_dependency_requires_org_id(self):
        """Super Admin must provide organization_id."""
        from app.core.dependencies import get_super_admin_organization_id

        class FakeUser:
            role = UserRole.SUPER_ADMIN

        with pytest.raises(Exception) as exc:
            get_super_admin_organization_id(organization_id=None, current_user=FakeUser())
        assert "must provide organization_id" in str(exc.value)

    def test_super_admin_dependency_returns_org_id(self):
        """Super Admin gets back the provided organization_id."""
        from app.core.dependencies import get_super_admin_organization_id

        class FakeUser:
            role = UserRole.SUPER_ADMIN

        result = get_super_admin_organization_id(organization_id=42, current_user=FakeUser())
        assert result == 42


# ── Cross-Organization Isolation Tests ─────────────────────────────────────

class TestCrossOrgIsolation:
    """Users from one organization cannot access another organization's data."""

    def test_cross_org_employee_list(self, client, db, two_orgs):
        """User from Org A only sees Org A's employees in list."""
        headers_a = login_as(client, "admin_a@test.com")
        headers_b = login_as(client, "admin_b@test.com")

        resp_a = client.get("/hr/employees", headers=headers_a)
        assert resp_a.status_code == 200
        data_a = resp_a.json()
        for emp in data_a["items"]:
            assert emp["id"] not in [two_orgs["admin_b"].id]

        resp_b = client.get("/hr/employees", headers=headers_b)
        assert resp_b.status_code == 200
        data_b = resp_b.json()
        for emp in data_b["items"]:
            assert emp["id"] not in [two_orgs["admin_a"].id]

    def test_cross_org_employee_by_id(self, client, db, two_orgs):
        """Org A user cannot fetch Org B's employee by ID."""
        headers_a = login_as(client, "admin_a@test.com")
        headers_b = login_as(client, "admin_b@test.com")

        emp_b_id = two_orgs["admin_b"].id
        resp = client.get(f"/hr/employees/{emp_b_id}", headers=headers_a)
        assert resp.status_code == 404

        emp_a_id = two_orgs["admin_a"].id
        resp = client.get(f"/hr/employees/{emp_a_id}", headers=headers_b)
        assert resp.status_code == 404

    def test_cross_org_create_employee(self, client, db, two_orgs):
        """Creating an employee with a department from another org fails."""
        headers_a = login_as(client, "admin_a@test.com")

        resp = client.post("/hr/employees", headers=headers_a, json={
            "email": "cross_org_emp@test.com",
            "password": "pass123",
            "first_name": "Cross",
            "last_name": "Org",
            "phone": "1111111111",
            "date_of_birth": "1990-01-01",
            "gender": "male",
            "job_title": "Engineer",
            "employment_type": "full_time",
            "date_of_joining": "2024-01-01",
            "department_id": two_orgs["dept_b"].id,
        })
        assert resp.status_code in (400, 403, 404, 422)

    def test_cross_org_update(self, client, db, two_orgs):
        """Org A user cannot update Org B's employee."""
        headers_a = login_as(client, "admin_a@test.com")

        emp_b_id = two_orgs["admin_b"].id
        resp = client.put(f"/hr/employees/{emp_b_id}", headers=headers_a, json={
            "first_name": "Hacked",
        })
        assert resp.status_code == 404

    def test_cross_org_deactivate(self, client, db, two_orgs):
        """Org A user cannot deactivate Org B's employee."""
        headers_a = login_as(client, "admin_a@test.com")

        emp_b_id = two_orgs["admin_b"].id
        resp = client.delete(f"/hr/employees/{emp_b_id}", headers=headers_a)
        assert resp.status_code == 404

    def test_cross_org_department_list(self, client, db, two_orgs):
        """User from Org A only sees Org A's departments."""
        headers_a = login_as(client, "admin_a@test.com")

        resp_a = client.get("/hr/departments", headers=headers_a)
        assert resp_a.status_code == 200
        depts_a = resp_a.json()
        assert isinstance(depts_a, list)
        for dept in depts_a:
            assert dept["id"] == two_orgs["dept_a"].id

    def test_cross_org_department_access(self, client, db, two_orgs):
        """Org A user cannot access Org B's department by ID."""
        headers_a = login_as(client, "admin_a@test.com")

        resp = client.get(f"/hr/departments/{two_orgs['dept_b'].id}", headers=headers_a)
        assert resp.status_code == 404

    def test_cross_org_department_update(self, client, db, two_orgs):
        """Org A user cannot update Org B's department."""
        headers_a = login_as(client, "admin_a@test.com")

        resp = client.put(f"/hr/departments/{two_orgs['dept_b'].id}", headers=headers_a, json={
            "name": "Hacked Dept",
        })
        assert resp.status_code == 404

    def test_cross_org_department_delete(self, client, db, two_orgs):
        """Org A user cannot delete Org B's department."""
        headers_a = login_as(client, "admin_a@test.com")

        resp = client.delete(f"/hr/departments/{two_orgs['dept_b'].id}", headers=headers_a)
        assert resp.status_code == 404

    def test_cross_org_dashboard_stats(self, client, db, two_orgs):
        """Dashboard stats are scoped to the user's organization."""
        headers_a = login_as(client, "admin_a@test.com")
        headers_b = login_as(client, "admin_b@test.com")

        resp_a = client.get("/hr/dashboard/stats", headers=headers_a)
        assert resp_a.status_code == 200
        data_a = resp_a.json()

        resp_b = client.get("/hr/dashboard/stats", headers=headers_b)
        assert resp_b.status_code == 200
        data_b = resp_b.json()

        if "total_employees" in data_a:
            assert data_a["total_employees"] == 1
        if "total_employees" in data_b:
            assert data_b["total_employees"] == 1


# ── User Management Cross-Org Access Tests ─────────────────────────────────

class TestUserManagementScoping:
    """User Management (/hr/admin/users and /super-admin/users) scoping."""

    @pytest.fixture
    def multi_org_setup(self, db: Session):
        """Creates two orgs with multiple users of different roles."""
        org_a = create_org(db, "Alpha Corp", "ALPHA")
        org_b = create_org(db, "Beta Inc", "BETA")

        dept_a = create_dept(db, "Engineering A", "ENGA", org_a.id)
        dept_b = create_dept(db, "Engineering B", "ENGB", org_b.id)

        admin_a = create_employee(db, "admin_a@test.com", org_a.id, dept_a.id, UserRole.ADMIN)
        hr_a = create_employee(db, "hr_a@test.com", org_a.id, dept_a.id, UserRole.HR_ADMIN)
        mgr_a = create_employee(db, "mgr_a@test.com", org_a.id, dept_a.id, UserRole.MANAGER)
        emp_a = create_employee(db, "emp_a@test.com", org_a.id, dept_a.id, UserRole.EMPLOYEE)

        admin_b = create_employee(db, "admin_b@test.com", org_b.id, dept_b.id, UserRole.ADMIN)
        hr_b = create_employee(db, "hr_b@test.com", org_b.id, dept_b.id, UserRole.HR_ADMIN)
        emp_b = create_employee(db, "emp_b@test.com", org_b.id, dept_b.id, UserRole.EMPLOYEE)

        db.flush()
        return {
            "org_a": org_a, "org_b": org_b,
            "dept_a": dept_a, "dept_b": dept_b,
            "admin_a": admin_a, "hr_a": hr_a, "mgr_a": mgr_a, "emp_a": emp_a,
            "admin_b": admin_b, "hr_b": hr_b, "emp_b": emp_b,
        }

    def test_super_admin_sees_all_org_users(self, client, db, multi_org_setup):
        """Super Admin sees users from ALL organizations via /super-admin/users."""
        headers = login_as(client, "superadmin@zoiko.com", "admin123")
        resp = client.get("/super-admin/users?page_size=50", headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        user_ids = {u["id"] for u in data["users"]}
        setup = multi_org_setup
        all_ids = {
            setup["admin_a"].id, setup["hr_a"].id, setup["mgr_a"].id, setup["emp_a"].id,
            setup["admin_b"].id, setup["hr_b"].id, setup["emp_b"].id,
        }
        for uid in all_ids:
            assert uid in user_ids, f"Super Admin missing user id={uid}"

    def test_org_admin_sees_only_own_org_users(self, client, db, multi_org_setup):
        """Org Admin from Org A only sees Org A users via /hr/admin/users."""
        headers = login_as(client, "admin_a@test.com")
        resp = client.get("/hr/admin/users?per_page=50", headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        user_ids = {u["id"] for u in data["items"]}
        setup = multi_org_setup
        assert setup["admin_a"].id in user_ids
        assert setup["hr_a"].id in user_ids
        assert setup["emp_a"].id in user_ids
        assert setup["mgr_a"].id in user_ids
        assert setup["admin_b"].id not in user_ids
        assert setup["hr_b"].id not in user_ids
        assert setup["emp_b"].id not in user_ids

    def test_org_admin_cannot_see_cross_org_user_detail(self, client, db, multi_org_setup):
        """Org Admin from Org A cannot fetch Org B user details via /hr/admin/users/{id}."""
        headers = login_as(client, "admin_a@test.com")
        setup = multi_org_setup
        resp = client.get(f"/hr/admin/users/{setup['admin_b'].id}", headers=headers)
        assert resp.status_code == 404

    def test_hr_admin_sees_only_own_org_users(self, client, db, multi_org_setup):
        """HR Admin from Org B only sees Org B users via /hr/admin/users."""
        headers = login_as(client, "hr_b@test.com")
        resp = client.get("/hr/admin/users?per_page=50", headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        user_ids = {u["id"] for u in data["items"]}
        setup = multi_org_setup
        assert setup["admin_b"].id in user_ids
        assert setup["hr_b"].id in user_ids
        assert setup["emp_b"].id in user_ids
        assert setup["admin_a"].id not in user_ids
        assert setup["hr_a"].id not in user_ids
        assert setup["emp_a"].id not in user_ids

    def test_super_admin_user_list_includes_org_name(self, client, db, multi_org_setup):
        """Super Admin user list includes organization_name for each user."""
        headers = login_as(client, "superadmin@zoiko.com", "admin123")
        resp = client.get("/super-admin/users?page_size=50", headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        users_by_id = {u["id"]: u for u in data["users"]}
        setup = multi_org_setup
        assert users_by_id[setup["admin_a"].id]["organization_name"] == "Alpha Corp"
        assert users_by_id[setup["admin_b"].id]["organization_name"] == "Beta Inc"

    def test_super_admin_user_list_stats(self, client, db, multi_org_setup):
        """Super Admin user list includes correct summary stats."""
        headers = login_as(client, "superadmin@zoiko.com", "admin123")
        resp = client.get("/super-admin/users?page_size=1", headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_organizations"] >= 2
        assert data["total_org_admins"] >= 2
        assert data["total_hr_admins"] >= 2
        assert data["total_managers"] >= 1
        assert data["total_employees"] >= 2

    def test_super_admin_can_filter_by_org(self, client, db, multi_org_setup):
        """Super Admin can filter users by organization_id."""
        headers = login_as(client, "superadmin@zoiko.com", "admin123")
        setup = multi_org_setup
        resp = client.get(f"/super-admin/users?organization_id={setup['org_a'].id}&page_size=50", headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        user_ids = {u["id"] for u in data["users"]}
        all_a_ids = {setup["admin_a"].id, setup["hr_a"].id, setup["mgr_a"].id, setup["emp_a"].id}
        all_b_ids = {setup["admin_b"].id, setup["hr_b"].id, setup["emp_b"].id}
        for uid in all_a_ids:
            assert uid in user_ids
        for uid in all_b_ids:
            assert uid not in user_ids


# ── Super Admin Cross-Org Access Tests ─────────────────────────────────────

class TestSuperAdminCrossOrg:
    """Super Admin can access any organization's data with explicit org_id."""

    def test_super_admin_can_access_own_org(self, client, db, two_orgs):
        """Super Admin can access their own organization's data (org 1)."""
        sa_headers = login_as(client, "superadmin@zoiko.com", "admin123")

        resp = client.get("/hr/employees", headers=sa_headers)
        assert resp.status_code == 200

        resp = client.get("/hr/departments", headers=sa_headers)
        assert resp.status_code == 200


# ── Unauthenticated Access Tests ──────────────────────────────────────────

class TestUnauthenticatedAccess:
    """Unauthenticated users are blocked from all endpoints."""

    def test_no_token_blocked(self, client):
        resp = client.get("/hr/employees")
        assert resp.status_code == 401

        resp = client.get("/hr/departments")
        assert resp.status_code == 401

        resp = client.get("/hr/dashboard/stats")
        assert resp.status_code == 401

    def test_invalid_token_blocked(self, client):
        headers = {"Authorization": "Bearer invalid_token"}
        resp = client.get("/hr/employees", headers=headers)
        assert resp.status_code == 401

        resp = client.get("/hr/departments", headers=headers)
        assert resp.status_code == 401

        resp = client.get("/hr/dashboard/stats", headers=headers)
        assert resp.status_code == 401
