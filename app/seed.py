"""app.seed

One-stop database seeding for the Zoiko One backend.

This file centralizes default platform seeding, including:
- Platform owner (Super Admin)
- Admin creation rules
- Employee creation rules (created by Admin)

Run (example):
    python -c "from app.seed import seed_database; seed_database()"

NOTE:
- Passwords below are intentionally plaintext before hashing, and will be
  stored as bcrypt hashes in the DB.
- For production, remove/disable default seeds and use environment-driven
  bootstrap flows.
"""

from __future__ import annotations

from datetime import date

from passlib.context import CryptContext

from app.database import SessionLocal, Base, engine

# Models
from app.modules.hr.models import (
    Employee,
    Department,
    Organization,
    OrganizationStatus,
)
from app.modules.employee.models import (
    EmploymentType,
    EmployeeStatus,
    Gender,
    UserRole,
)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def seed_database() -> None:
    """Create tables and seed default platform owner / admin / employees."""

    # Ensure tables exist (same behavior as main.py)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # --- Organization / Department scaffolding ---
        org = db.query(Organization).filter(Organization.code == "ZOIKO").first()
        if not org:
            org = Organization(name="Zoiko Inc", code="ZOIKO", status=OrganizationStatus.ACTIVE, is_active=True)
            db.add(org)
            db.commit()
            db.refresh(org)

        mgmt_dept = db.query(Department).filter(Department.code == "MGMT").first()
        if not mgmt_dept:
            mgmt_dept = Department(
                name="Management",
                code="MGMT",
                description="Company management",
            )
            db.add(mgmt_dept)
            db.commit()
            db.refresh(mgmt_dept)

        # --- Super Admin (Platform Owner) ---
        platform_owner_email = "admin@zoiko.com"
        platform_owner_password = "admin123"

        super_admin = db.query(Employee).filter(Employee.email == platform_owner_email).first()
        if not super_admin:
            # Generate a simple employee_code
            max_code = db.query(Employee.employee_code).filter(Employee.employee_code.isnot(None)).all()
            # Fallback if employee_code format differs
            emp_code_num = 1
            try:
                # best-effort parse for ZK-0001 style
                employee_codes = [row[0] for row in max_code if row[0]]
                parsed = [int(code.split("-")[1]) for code in employee_codes if "-" in code and code.split("-")[1].isdigit()]
                if parsed:
                    emp_code_num = max(parsed) + 1
            except Exception:
                emp_code_num = 1
            emp_code = f"ZK-{emp_code_num:04d}"

            super_admin = Employee(
                email=platform_owner_email,
                hashed_password=_hash_password(platform_owner_password),
                role=UserRole.SUPER_ADMIN,
                is_active=True,
                first_name="System",
                last_name="Admin",
                phone="0000000000",
                date_of_birth=date(1990, 1, 1),
                gender=Gender.MALE,
                address="Head Office",
                employee_code=emp_code,
                job_title="Platform Owner",
                employment_type=EmploymentType.FULL_TIME,
                status=EmployeeStatus.ACTIVE,
                date_of_joining=date(2024, 1, 1),
                department_id=mgmt_dept.id,
                organization_id=org.id,
            )
            db.add(super_admin)
            db.commit()
            db.refresh(super_admin)

        # --- Admins should be created during registration ---
        # This seed keeps behavior minimal: it provides only the platform owner.
        # Admin/HR/Employees should be created by the admin registration flow
        # at runtime.

        # --- Default employees template (created by Admin) ---
        # If these employees do not exist, create them with default password.
        # NOTE: in real system, these should be created through the registration
        # workflow protected by admin privileges.
        default_employee_password = "employee123"

        default_employees = [
            ("eng.mgr@zoiko.com", "Alice", "Chen", UserRole.HR_MANAGER, "Engineering Manager"),
            ("eng.lead@zoiko.com", "Bob", "Kumar", UserRole.EMPLOYEE, "Senior Engineering Lead"),
            ("sales.dir@zoiko.com", "Carol", "Smith", UserRole.HR_MANAGER, "Sales Director"),
            ("sales.mgr@zoiko.com", "David", "Lee", UserRole.EMPLOYEE, "Regional Sales Manager"),
            ("hr.mgr@zoiko.com", "Eve", "Davis", UserRole.HR_MANAGER, "HR Manager"),
            ("hr.spec@zoiko.com", "Frank", "Wilson", UserRole.EMPLOYEE, "Senior HR Specialist"),
        ]

        # Create department placeholders for better organization
        depts = {
            "ENG": ("Engineering", "ENG", "Engineering and product development"),
            "SALES": ("Sales", "SALES", "Sales and business development"),
            "HR": ("Human Resources", "HR", "Human resources and people operations"),
        }

        for code, (name, dept_code, desc) in depts.items():
            d = db.query(Department).filter(Department.code == dept_code).first()
            if not d:
                d = Department(name=name, code=dept_code, description=desc)
                db.add(d)
                db.commit()
                db.refresh(d)

        eng_dept = db.query(Department).filter(Department.code == "ENG").first()
        sales_dept = db.query(Department).filter(Department.code == "SALES").first()
        hr_dept = db.query(Department).filter(Department.code == "HR").first()

        def pick_dept(email: str):
            if email.startswith("eng."):
                return eng_dept
            if email.startswith("sales."):
                return sales_dept
            if email.startswith("hr."):
                return hr_dept
            return mgmt_dept

        for email, first, last, role, job_title in default_employees:
            existing = db.query(Employee).filter(Employee.email == email).first()
            if existing:
                continue

            max_code = db.query(Employee.employee_code).filter(Employee.employee_code.isnot(None)).all()
            emp_code_num = 1
            try:
                employee_codes = [row[0] for row in max_code if row[0]]
                parsed = [int(code.split("-")[1]) for code in employee_codes if "-" in code and code.split("-")[1].isdigit()]
                if parsed:
                    emp_code_num = max(parsed) + 1
            except Exception:
                emp_code_num = 1
            emp_code = f"ZK-{emp_code_num:04d}"

            dept = pick_dept(email)
            emp = Employee(
                email=email,
                hashed_password=_hash_password(default_employee_password),
                role=role,
                is_active=True,
                first_name=first,
                last_name=last,
                phone="0000000000",
                date_of_birth=date(1990, 1, 1),
                gender=Gender.MALE,
                address="Office",
                employee_code=emp_code,
                job_title=job_title,
                employment_type=EmploymentType.FULL_TIME,
                status=EmployeeStatus.ACTIVE,
                date_of_joining=date(2024, 1, 1),
                department_id=dept.id if dept else mgmt_dept.id,
                organization_id=org.id,
            )
            db.add(emp)

        db.commit()

    finally:
        db.close()

