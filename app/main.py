"""
main.py
-------
The entry point of the entire Zoiko One Backend application.
"""

import logging
from datetime import date, datetime

import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from passlib.context import CryptContext
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import func

from app.core.rate_limiter import limiter

from app.config import settings
from app.database import engine, SessionLocal, Base, get_table_names
from app.core.exceptions import (
    ZoikoException,
    zoiko_exception_handler,
    generic_exception_handler,
)

# ── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("zoiko")

# ── Rate limiter ─────────────────────────────────────────────────────────────
# Moved to app.core.rate_limiter to avoid circular imports

# -- Seed helper --------------------------------------------------------------
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _seed_admin_if_empty():
    """Create tables and seed the default admin user if the database is empty."""
    import time
    for attempt in range(5):
        try:
            Base.metadata.create_all(bind=engine)
            break
        except Exception as e:
            logger.warning(f"Database connection failed on startup, retrying ({attempt+1}/5): {e}")
            time.sleep(3)
    else:
        logger.error("Failed to connect to the database after 5 attempts. Raising exception.")
        raise

    from app.modules.hr.models import Department, Employee, EmploymentType, EmployeeStatus, UserRole, Gender, Organization, OrganizationStatus

    db = SessionLocal()
    try:
        existing = db.query(Employee).filter(Employee.email == "admin@zoiko.com").first()
        if existing:
            if existing.organization_id is None:
                org = db.query(Organization).first()
                if not org:
                    org = Organization(name="Zoiko Inc", code="ZOIKO", status=OrganizationStatus.ACTIVE, is_active=True)
                    db.add(org)
                    db.commit()
                    db.refresh(org)
                existing.organization_id = org.id
                db.commit()
        else:
            org = db.query(Organization).first()
            if not org:
                org = Organization(name="Zoiko Inc", code="ZOIKO", status=OrganizationStatus.ACTIVE, is_active=True)
                db.add(org)
                db.commit()
                db.refresh(org)

            dept = db.query(Department).filter(Department.code == "MGMT").first()
            if not dept:
                dept = Department(name="Management", code="MGMT", description="Company management")
                db.add(dept)
                db.commit()
                db.refresh(dept)

            max_code = db.query(func.max(Employee.employee_code)).scalar()
            next_num = 1
            if max_code:
                next_num = int(max_code.split("-")[1]) + 1
            emp_code = f"ZK-{next_num:04d}"

            admin = Employee(
                email="admin@zoiko.com",
                hashed_password=bcrypt_context.hash("admin123"),
                role=UserRole.ADMIN,
                is_active=True,
                first_name="System",
                last_name="Admin",
                phone="0000000000",
                date_of_birth=date(1990, 1, 1),
                gender=Gender.MALE,
                address="Head Office",
                employee_code=emp_code,
                job_title="System Administrator",
                employment_type=EmploymentType.FULL_TIME,
                status=EmployeeStatus.ACTIVE,
                date_of_joining=date(2024, 1, 1),
                department_id=dept.id,
                organization_id=org.id,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"[seed] Admin created: admin@zoiko.com / admin123")

        # ── Seed Super Admin (runs regardless of whether admin existed) ──
        sa_existing = db.query(Employee).filter(Employee.email == "superadmin@zoiko.com").first()
        if not sa_existing:
            org = db.query(Organization).first()
            if not org:
                org = Organization(name="Zoiko Inc", code="ZOIKO", status=OrganizationStatus.ACTIVE, is_active=True)
                db.add(org)
                db.commit()
                db.refresh(org)
            dept = db.query(Department).filter(Department.code == "MGMT").first()
            if not dept:
                dept = Department(name="Management", code="MGMT", description="Company management")
                db.add(dept)
                db.commit()
                db.refresh(dept)

            max_code = db.query(func.max(Employee.employee_code)).scalar()
            next_num = 1
            if max_code:
                next_num = int(max_code.split("-")[1]) + 1
            sa_emp_code = f"ZK-{next_num:04d}"

            super_admin = Employee(
                email="superadmin@zoiko.com",
                hashed_password=bcrypt_context.hash("admin123"),
                role=UserRole.SUPER_ADMIN,
                is_active=True,
                first_name="Super",
                last_name="Admin",
                phone="0000000000",
                date_of_birth=date(1990, 1, 1),
                gender=Gender.MALE,
                address="Head Office",
                employee_code=sa_emp_code,
                job_title="Super Administrator",
                employment_type=EmploymentType.FULL_TIME,
                status=EmployeeStatus.ACTIVE,
                date_of_joining=date(2024, 1, 1),
                department_id=dept.id,
                organization_id=org.id,
            )
            db.add(super_admin)
            db.commit()
            db.refresh(super_admin)
            print(f"[seed] Super Admin created: superadmin@zoiko.com / admin123")

        # ── Seed default platform settings ──
        from app.modules.super_admin.models import PlatformSetting
        defaults = [
            ("site_name", "Zoiko One", "Platform display name", "branding"),
            ("logo_url", "", "Logo URL for the platform", "branding"),
            ("favicon_url", "", "Favicon URL", "branding"),
            ("primary_color", "#FF7A00", "Primary brand color", "branding"),
            ("smtp_host", "smtp.mailtrap.io", "SMTP server host", "email"),
            ("smtp_port", "587", "SMTP server port", "email"),
            ("smtp_username", "", "SMTP authentication username", "email"),
            ("smtp_password", "", "SMTP authentication password", "email"),
            ("smtp_from_email", "noreply@zoiko.com", "Default from email address", "email"),
            ("smtp_use_tls", "true", "Enable TLS for SMTP", "email"),
            ("session_timeout_minutes", "60", "Admin session timeout in minutes", "security"),
            ("password_min_length", "8", "Minimum password length requirement", "security"),
            ("password_require_special", "true", "Require special characters in passwords", "security"),
            ("password_require_numbers", "true", "Require numbers in passwords", "security"),
            ("jwt_expiry_minutes", "60", "JWT token expiry in minutes", "security"),
            ("jwt_refresh_expiry_days", "7", "JWT refresh token expiry in days", "security"),
            ("max_login_attempts", "5", "Max failed login attempts before lockout", "security"),
            ("max_file_size_mb", "10", "Maximum file upload size in MB", "file_upload"),
            ("allowed_file_types", "jpg,png,pdf,doc,docx,xls,xlsx,csv", "Comma-separated allowed file extensions", "file_upload"),
            ("notify_email_enabled", "true", "Enable email notifications", "notifications"),
            ("notify_in_app_enabled", "true", "Enable in-app notifications", "notifications"),
            ("notify_slack_enabled", "false", "Enable Slack notifications", "notifications"),
            ("backup_enabled", "true", "Enable automatic backups", "backup"),
            ("backup_interval_hours", "24", "Backup interval in hours", "backup"),
            ("backup_retention_days", "30", "Backup retention period in days", "backup"),
            ("maintenance_mode", "false", "Enable maintenance mode", "system"),
            ("api_rate_limit_per_minute", "60", "API rate limit per minute", "system"),
        ]
        existing_setting = db.query(PlatformSetting).first()
        if not existing_setting:
            for key, value, desc, cat in defaults:
                db.add(PlatformSetting(key=key, value=value, description=desc, category=cat))
            db.commit()
            print(f"[seed] {len(defaults)} platform settings created")
    except Exception as e:
        db.rollback()
        print(f"[seed] Error: {e}")
        raise
    finally:
        db.close()


# -- Router imports (each imported independently so one failure never silences the rest) ---
from fastapi import APIRouter as _APIRouter

def _safe_import(import_fn, name):
    """Import a router safely. Returns a blank router on failure but logs the real error."""
    try:
        return import_fn()
    except Exception as e:
        import logging
        logging.getLogger("zoiko").error(f"Failed to import {name}: {e}", exc_info=True)
        if name in ["hr.auth_router", "hr.hr_router"]:
            raise RuntimeError(f"CRITICAL startup failure: failed to import {name} router: {e}") from e
        return _APIRouter()

auth_router       = _safe_import(lambda: __import__("app.modules.employee.router",    fromlist=["auth_router"]).auth_router,       "employee.auth_router")
hr_router         = _safe_import(lambda: __import__("app.modules.hr.router",          fromlist=["hr_router"]).hr_router,           "hr.hr_router")
employee_router   = _safe_import(lambda: __import__("app.modules.employee.router",    fromlist=["employee_router"]).employee_router, "employee.employee_router")
attendance_router = _safe_import(lambda: __import__("app.modules.hr.attendance_router", fromlist=["attendance_router"]).attendance_router, "hr.attendance_router")
asset_router      = _safe_import(lambda: __import__("app.modules.hr.asset_router",    fromlist=["asset_router"]).asset_router,     "hr.asset_router")
learning_router   = _safe_import(lambda: __import__("app.modules.hr.learning_router", fromlist=["learning_router"]).learning_router, "hr.learning_router")
recruitment_router= _safe_import(lambda: __import__("app.modules.hr.recruitment_router", fromlist=["recruitment_router"]).recruitment_router, "hr.recruitment_router")
workforce_router  = _safe_import(lambda: __import__("app.modules.hr.workforce_router", fromlist=["workforce_router"]).workforce_router, "hr.workforce_router")
time_router       = _safe_import(lambda: __import__("app.modules.time.router",        fromlist=["time_router"]).time_router,       "time.time_router")
payroll_router    = _safe_import(lambda: __import__("app.modules.payroll.router",     fromlist=["payroll_router"]).payroll_router, "payroll.payroll_router")
billing_router    = _safe_import(lambda: __import__("app.modules.billing.router",     fromlist=["billing_router"]).billing_router, "billing.billing_router")
comply_router     = _safe_import(lambda: __import__("app.modules.comply.router",      fromlist=["comply_router"]).comply_router,   "comply.comply_router")
insights_router   = _safe_import(lambda: __import__("app.modules.insights.router",   fromlist=["insights_router"]).insights_router, "insights.insights_router")
super_admin_router = _safe_import(lambda: __import__("app.modules.super_admin.router", fromlist=["router"]).router, "super_admin.router")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── Request Logging Middleware (inner) ──────────────────────────────────────
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)
    start = datetime.utcnow()
    response = await call_next(request)
    elapsed = (datetime.utcnow() - start).total_seconds()
    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} ({elapsed:.3f}s) "
        f"from {request.client.host if request.client else 'unknown'}"
    )
    return response

# ── CORS Middleware (outermost — handles preflight before anything else) ────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",")],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ── Rate limiting ────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


app.add_exception_handler(ZoikoException, zoiko_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# -- Register Routers ---------------------------------------------------------
app.include_router(auth_router)
app.include_router(employee_router)
app.include_router(hr_router)
app.include_router(attendance_router)
app.include_router(asset_router)
app.include_router(learning_router)
app.include_router(recruitment_router)
app.include_router(workforce_router)
app.include_router(time_router)
app.include_router(payroll_router)
app.include_router(billing_router)
app.include_router(comply_router)
app.include_router(insights_router)
app.include_router(super_admin_router)

# -- Serve uploaded files for download -----------------------------------------
_upload_dirs = [
    ("uploads/hr_documents", "/uploads/hr_documents"),
    ("uploads/onboarding_documents", "/uploads/onboarding_documents"),
]
for dir_path, url_path in _upload_dirs:
    os.makedirs(dir_path, exist_ok=True)
    app.mount(url_path, StaticFiles(directory=dir_path), name=f"uploads_{os.path.basename(dir_path)}")


# -- Seed default asset settings -----------------------------------------------
def _seed_asset_settings():
    from app.modules.hr.models import AssetSetting
    db = SessionLocal()
    try:
        existing = db.query(AssetSetting).first()
        if existing:
            return
        defaults = {
            "default_asset_prefix": "AST",
            "auto_asset_tag_format": "AST-{NNNN}",
            "auto_approve_threshold": "500",
            "warrantyPeriod": "12",
            "maintenanceInterval": "90",
            "repairBudget": "25000",
            "vendorWarranty": "Yes",
            "depreciation_method": "straight_line",
            "default_useful_life": "5",
            "salvage_value": "10",
            "warranty_expiry": "true",
            "maintenance_due": "true",
            "asset_assigned": "true",
            "asset_returned": "true",
            "request_approved": "true",
            "maintenance_overdue": "true",
        }
        for key, value in defaults.items():
            db.add(AssetSetting(setting_key=key, setting_value=value))
        db.commit()
        print(f"[seed] {len(defaults)} default asset settings created.")
    except Exception as e:
        db.rollback()
        print(f"[seed] Asset settings error: {e}")
    finally:
        db.close()


# -- Seed workforce planning data -----------------------------------------------
def _seed_workforce():
    from app.modules.hr.models import (
        Organization, Department, Employee, EmploymentType, EmployeeStatus, UserRole, Gender,
        WfPlan, WfHeadcount, WfSuccession,
    )
    db = SessionLocal()
    try:
        existing = db.query(WfPlan).first()
        if existing:
            return
        org = db.query(Organization).first()
        if not org:
            return

        mgmt = db.query(Department).filter(Department.code == "MGMT").first()

        def _ensure_dept(name, code, desc):
            dept = db.query(Department).filter(Department.code == code).first()
            if not dept:
                dept = Department(name=name, code=code, description=desc)
                db.add(dept)
                db.flush()
            return dept

        eng_dept = _ensure_dept("Engineering", "ENG", "Engineering and product development")
        sales_dept = _ensure_dept("Sales", "SALES", "Sales and business development")
        hr_dept = _ensure_dept("Human Resources", "HR", "Human resources and people operations")

        def _ensure_emp(email, first, last, role, dept, title):
            emp = db.query(Employee).filter(Employee.email == email).first()
            if not emp:
                max_code = db.query(func.max(Employee.employee_code)).scalar()
                next_num = 1
                if max_code:
                    next_num = int(max_code.split("-")[1]) + 1
                emp_code = f"ZK-{next_num:04d}"
                emp = Employee(
                    email=email,
                    hashed_password=bcrypt_context.hash("employee123"),
                    role=role,
                    is_active=True,
                    first_name=first,
                    last_name=last,
                    phone="0000000000",
                    date_of_birth=date(1990, 1, 1),
                    gender=Gender.MALE,
                    address="Office",
                    employee_code=emp_code,
                    job_title=title,
                    employment_type=EmploymentType.FULL_TIME,
                    status=EmployeeStatus.ACTIVE,
                    date_of_joining=date(2024, 1, 1),
                    department_id=dept.id,
                    organization_id=org.id,
                )
                db.add(emp)
                db.flush()
            return emp

        eng_mgr = _ensure_emp("eng.mgr@zoiko.com", "Alice", "Chen", UserRole.HR_MANAGER, eng_dept, "Engineering Manager")
        eng_succ = _ensure_emp("eng.lead@zoiko.com", "Bob", "Kumar", UserRole.EMPLOYEE, eng_dept, "Senior Engineering Lead")
        sales_dir = _ensure_emp("sales.dir@zoiko.com", "Carol", "Smith", UserRole.HR_MANAGER, sales_dept, "Sales Director")
        sales_succ = _ensure_emp("sales.mgr@zoiko.com", "David", "Lee", UserRole.EMPLOYEE, sales_dept, "Regional Sales Manager")
        hr_mgr = _ensure_emp("hr.mgr@zoiko.com", "Eve", "Davis", UserRole.HR_MANAGER, hr_dept, "HR Manager")
        hr_succ = _ensure_emp("hr.spec@zoiko.com", "Frank", "Wilson", UserRole.EMPLOYEE, hr_dept, "Senior HR Specialist")

        db.flush()

        plans = [
            WfPlan(
                organization_id=org.id, department_id=eng_dept.id,
                title="FY2027 Engineering Expansion", plan_year=2027, status="active",
                owner_id=eng_mgr.id, budget=2500000, target_headcount=45, current_headcount=32,
                description="Scaling engineering team for next-gen product platform development including AI/ML capabilities and cloud infrastructure expansion.",
                created_by=eng_mgr.id,
            ),
            WfPlan(
                organization_id=org.id, department_id=sales_dept.id,
                title="Sales Growth Initiative", plan_year=2027, status="approved",
                owner_id=sales_dir.id, budget=1200000, target_headcount=25, current_headcount=18,
                description="Expanding sales team across new geographic regions with specialized enterprise account executives and customer success managers.",
                created_by=sales_dir.id,
            ),
            WfPlan(
                organization_id=org.id, department_id=hr_dept.id,
                title="HR Transformation Program", plan_year=2027, status="active",
                owner_id=hr_mgr.id, budget=450000, target_headcount=12, current_headcount=8,
                description="Modernizing HR operations with digital tools, automated workflows, and expanded talent acquisition capabilities.",
                created_by=hr_mgr.id,
            ),
        ]
        for p in plans:
            db.add(p)
        db.flush()

        headcounts = [
            WfHeadcount(
                organization_id=org.id, department_id=eng_dept.id,
                fiscal_year=2027, approved_positions=45, filled_positions=32,
                vacant_positions=13, planned_hires=15, projected_cost=2800000,
                created_by=eng_mgr.id,
            ),
            WfHeadcount(
                organization_id=org.id, department_id=sales_dept.id,
                fiscal_year=2027, approved_positions=25, filled_positions=18,
                vacant_positions=7, planned_hires=8, projected_cost=1350000,
                created_by=sales_dir.id,
            ),
            WfHeadcount(
                organization_id=org.id, department_id=hr_dept.id,
                fiscal_year=2027, approved_positions=12, filled_positions=8,
                vacant_positions=4, planned_hires=5, projected_cost=525000,
                created_by=hr_mgr.id,
            ),
        ]
        for h in headcounts:
            db.add(h)
        db.flush()

        now = date.today()
        def add_months(d, m):
            month = d.month - 1 + m
            return date(d.year + month // 12, month % 12 + 1, 1)

        successions = [
            WfSuccession(
                organization_id=org.id, employee_id=eng_mgr.id,
                successor_employee_id=eng_succ.id,
                readiness_level="ready", risk_level="low",
                target_position="Engineering Manager",
                review_date=now,
                notes="Successor is fully prepared. Has been leading key projects for 18 months. Recommended for immediate transition.",
                created_by=eng_mgr.id,
            ),
            WfSuccession(
                organization_id=org.id, employee_id=sales_dir.id,
                successor_employee_id=sales_succ.id,
                readiness_level="moderately_ready", risk_level="medium",
                target_position="Sales Director",
                review_date=add_months(now, 6),
                notes="Successor needs additional exposure to strategic account management and executive presentations. Estimated readiness in 6 months.",
                created_by=sales_dir.id,
            ),
            WfSuccession(
                organization_id=org.id, employee_id=hr_mgr.id,
                successor_employee_id=hr_succ.id,
                readiness_level="not_ready", risk_level="high",
                target_position="HR Manager",
                review_date=add_months(now, 12),
                notes="Successor requires completion of HR certification and leadership training. Estimated readiness in 12 months. High risk due to potential departure.",
                created_by=hr_mgr.id,
            ),
        ]
        for s in successions:
            db.add(s)

        db.commit()
        print(f"[seed] Workforce Planning: 3 plans, 3 headcounts, 3 successions created.")
    except Exception as e:
        db.rollback()
        print(f"[seed] Workforce planning error: {e}")
    finally:
        db.close()


# -- Startup: create tables + seed admin --------------------------------------
@app.on_event("startup")
def on_startup():
    import socket
    import time
    from urllib.parse import urlparse

    parsed = urlparse(settings.DATABASE_URL)
    hostname = parsed.hostname or ""
    logger.info(f"[startup] Resolving DB hostname: {hostname}")
    for attempt in range(10):
        try:
            socket.getaddrinfo(hostname, parsed.port or 5432)
            logger.info(f"[startup] DNS resolved: {hostname}")
            break
        except OSError as e:
            logger.warning(f"[startup] DNS resolution failed ({attempt+1}/10): {e}")
            time.sleep(2)
    else:
        logger.error(f"[startup] Could not resolve DB hostname after 10 attempts: {hostname}")

    print(f"[startup] Connecting to DB: {settings.DATABASE_URL}")
    _seed_admin_if_empty()
    _seed_asset_settings()
    _seed_workforce()

    try:
        tables = get_table_names()
        print(f"[startup] Tables ready: {tables}")
    except Exception as e:
        logger.warning(f"[startup] Could not fetch table list: {e}")
        tables = []

    # Ensure the userrole ENUM has all expected values
    try:
        _ensure_user_role_enum()
    except Exception as e:
        logger.warning(f"[startup] User role enum migration error: {e}")

    # Migrate existing orgs: set status column for rows created before the column existed
    try:
        _migrate_org_statuses()
    except Exception as e:
        logger.warning(f"[startup] Org status migration error: {e}")

    # Normalize existing subscription plan values to uppercase
    try:
        _normalize_subscription_plans()
    except Exception as e:
        logger.warning(f"[startup] Subscription plan normalization error: {e}")

    # Ensure every approved/suspended org has a subscription record
    try:
        _ensure_subscriptions_for_approved_orgs()
    except Exception as e:
        logger.warning(f"[startup] Subscription backfill error: {e}")


def _ensure_user_role_enum():
    """Ensure the PostgreSQL userrole ENUM type has all expected values."""
    try:
        from app.database import engine
        from sqlalchemy import text
        from app.modules.hr.models import UserRole
        expected = [m.name for m in UserRole]
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT unnest(enum_range(NULL::userrole))::text"
            )).fetchall()
            existing = [r[0] for r in result]
        for val in expected:
            if val not in existing:
                try:
                    with engine.connect() as conn:
                        conn.execute(text(f"ALTER TYPE userrole ADD VALUE IF NOT EXISTS '{val}'"))
                        conn.commit()
                    print(f"[migrate] Added value '{val}' to userrole ENUM")
                except Exception as e:
                    print(f"[migrate] Could not add '{val}' to userrole ENUM: {e}")
            else:
                print(f"[migrate] Value '{val}' already exists in userrole ENUM")
        print(f"[migrate] Current userrole ENUM values: {existing}")
    except Exception as e:
        import logging
        logging.getLogger("zoiko").warning(f"User role enum migration error: {e}")


def _migrate_org_statuses():
    """Add status/approval columns to organizations table and migrate existing data."""
    try:
        from app.database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        try:
            # Add new columns if they don't exist
            columns_to_add = [
                ("status", "VARCHAR(20) DEFAULT 'PENDING'"),
                ("approved_by", "INTEGER REFERENCES employees(id)"),
                ("approved_at", "TIMESTAMP"),
                ("rejection_reason", "TEXT"),
                ("suspended_at", "TIMESTAMP"),
                ("reactivated_at", "TIMESTAMP"),
            ]
            existing = [row[0] for row in db.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'organizations'"
            )).fetchall()]

            for col_name, col_type in columns_to_add:
                if col_name not in existing:
                    db.execute(text(f"ALTER TABLE organizations ADD COLUMN {col_name} {col_type}"))
                    print(f"[migrate] Added column '{col_name}' to organizations table")

            # Set status for existing rows based on is_active
            result = db.execute(text(
                "UPDATE organizations SET status = 'ACTIVE' WHERE is_active = TRUE AND (status IS NULL OR status != 'ACTIVE')"
            ))
            updated_active = result.rowcount

            result = db.execute(text(
                "UPDATE organizations SET status = 'SUSPENDED' WHERE is_active = FALSE AND (status IS NULL OR status != 'SUSPENDED')"
            ))
            updated_suspended = result.rowcount
            db.commit()
            if updated_active or updated_suspended:
                print(f"[migrate] Set status for {updated_active} ACTIVE and {updated_suspended} SUSPENDED organizations")

            # Add/update approval_history table
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS super_admin_approval_history (
                    id SERIAL PRIMARY KEY,
                    organization_id INTEGER NOT NULL REFERENCES organizations(id),
                    action VARCHAR(50) NOT NULL,
                    previous_status VARCHAR(50),
                    new_status VARCHAR(50),
                    performed_by INTEGER NOT NULL REFERENCES employees(id),
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            # Add columns if missing (for existing tables)
            for col_name, col_type in [("previous_status", "VARCHAR(50)"), ("new_status", "VARCHAR(50)")]:
                existing_cols = [row[0] for row in db.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = 'super_admin_approval_history'"
                )).fetchall()]
                if col_name not in existing_cols:
                    db.execute(text(f"ALTER TABLE super_admin_approval_history ADD COLUMN {col_name} {col_type}"))
                    print(f"[migrate] Added column '{col_name}' to super_admin_approval_history")
            db.commit()

            # Add new auditaction enum values
            for val in ['APPROVED', 'REJECTED', 'REACTIVATED']:
                try:
                    db.execute(text(f"ALTER TYPE auditaction ADD VALUE IF NOT EXISTS '{val}'"))
                except Exception:
                    pass
            db.commit()
        finally:
            db.close()
    except Exception as e:
        import logging
        logging.getLogger("zoiko").warning(f"Migration error: {e}")


def _normalize_subscription_plans():
    """Normalize existing subscription plan_type values to uppercase."""
    try:
        from app.database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        try:
            result = db.execute(text(
                "UPDATE super_admin_subscriptions SET plan_type = UPPER(plan_type::text)::plantype WHERE plan_type::text != UPPER(plan_type::text)"
            ))
            db.commit()
            if result.rowcount:
                print(f"[migrate] Normalized {result.rowcount} subscription plan values to uppercase")
        finally:
            db.close()
    except Exception as e:
        import logging
        logging.getLogger("zoiko").warning(f"Subscription plan normalization error: {e}")


def _ensure_subscriptions_for_approved_orgs():
    """Create a default FREE subscription for every approved/suspended org that lacks one."""
    try:
        from app.database import SessionLocal
        from app.modules.super_admin.models import PlanType, SubscriptionStatus, Subscription
        from app.modules.hr.models import Organization
        db = SessionLocal()
        try:
            orgs = db.query(Organization).filter(
                Organization.status.in_(["ACTIVE", "SUSPENDED", "APPROVED"])
            ).all()
            created = 0
            for org in orgs:
                existing = db.query(Subscription).filter(Subscription.organization_id == org.id).first()
                if not existing:
                    sub = Subscription(
                        organization_id=org.id,
                        plan_type=PlanType.FREE.name,
                        status=SubscriptionStatus.ACTIVE.name,
                        max_users=15,
                        max_storage_gb=5,
                    )
                    db.add(sub)
                    created += 1
            if created:
                db.commit()
                print(f"[migrate] Created {created} missing subscription(s) for approved/suspended organizations")
        finally:
            db.close()
    except Exception as e:
        import logging
        logging.getLogger("zoiko").warning(f"Subscription backfill error: {e}")


# -- Root endpoint ------------------------------------------------------------
@app.get("/", tags=["Root"])
def read_root():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "message": "Zoiko One Backend is running! Visit /docs for API documentation.",
    }


# -- Health check ------------------------------------------------------------
@app.get("/health", tags=["Health Check"], summary="Detailed health status")
def health():
    return {
        "status": "ok",
        "database": "postgres",
        "tables": get_table_names(),
        "modules": {
            "hr": "active",
            "time": "active",
            "payroll": "active",
            "billing": "active",
            "comply": "active",
            "insights": "active",
        }
    }