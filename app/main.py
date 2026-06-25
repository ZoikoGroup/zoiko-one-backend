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
    Base.metadata.create_all(bind=engine)

    from app.modules.hr.models import Department, Employee, EmploymentType, EmployeeStatus, UserRole, Gender, Organization

    db = SessionLocal()
    try:
        existing = db.query(Employee).filter(Employee.email == "admin@zoiko.com").first()
        if existing:
            if existing.organization_id is None:
                org = db.query(Organization).first()
                if not org:
                    org = Organization(name="Zoiko Inc", code="ZOIKO")
                    db.add(org)
                    db.commit()
                    db.refresh(org)
                existing.organization_id = org.id
                db.commit()
        else:
            org = db.query(Organization).first()
            if not org:
                org = Organization(name="Zoiko Inc", code="ZOIKO")
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
                org = Organization(name="Zoiko Inc", code="ZOIKO")
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
    except Exception as e:
        db.rollback()
        print(f"[seed] Error: {e}")
        raise
    finally:
        db.close()


# -- Router imports (each imported independently so one failure never silences the rest) ---
import traceback
from fastapi import APIRouter as _APIRouter

def _safe_import(import_fn, name):
    """Import a router safely. Returns a blank router on failure but logs the real error."""
    try:
        return import_fn()
    except Exception as e:
        print(f"[main] ❌ Failed to import {name}: {e}")
        traceback.print_exc()
        return _APIRouter()

auth_router       = _safe_import(lambda: __import__("app.modules.hr.router",          fromlist=["auth_router"]).auth_router,       "hr.auth_router")
hr_router         = _safe_import(lambda: __import__("app.modules.hr.router",          fromlist=["hr_router"]).hr_router,           "hr.hr_router")
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate limiting ────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)





# ── Audit Logging Middleware ────────────────────────────────────────────────
@app.middleware("http")
async def audit_logging_middleware(request: Request, call_next):
    start = datetime.utcnow()
    response = await call_next(request)
    elapsed = (datetime.utcnow() - start).total_seconds()
    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} ({elapsed:.3f}s) "
        f"from {request.client.host if request.client else 'unknown'}"
    )
    return response


app.add_exception_handler(ZoikoException, zoiko_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# -- Register Routers ---------------------------------------------------------
app.include_router(auth_router)
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
    print(f"[startup] Connecting to MySQL: {settings.DATABASE_URL}")
    _seed_admin_if_empty()
    _seed_asset_settings()
    _seed_workforce()
    tables = get_table_names()
    print(f"[startup] Tables ready: {tables}")


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
        "database": "mysql",
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