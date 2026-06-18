"""
main.py
-------
The entry point of the entire Zoiko One Backend application.
"""

import logging
from datetime import date, datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
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

    from app.modules.hr.models import Department, Employee, EmploymentType, EmployeeStatus, UserRole, Gender

    db = SessionLocal()
    try:
        existing = db.query(Employee).filter(Employee.email == "admin@zoiko.com").first()
        if existing:
            return

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
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"[seed] Admin created: admin@zoiko.com / admin123")
    except Exception as e:
        db.rollback()
        print(f"[seed] Error: {e}")
        raise
    finally:
        db.close()


# -- Router imports (graceful fallback if a module is still in development) ---
try:
    from app.modules.hr.router import auth_router, hr_router
    from app.modules.hr.asset_router import asset_router
    from app.modules.hr.learning_router import learning_router
    from app.modules.time.router import time_router
    from app.modules.payroll.router import payroll_router
    from app.modules.billing.router import billing_router
    from app.modules.comply.router import comply_router
    from app.modules.insights.router import insights_router
except ImportError as e:
    print(f"[main] Router import warning: {e}")
    from fastapi import APIRouter
    auth_router = hr_router = asset_router = learning_router = time_router = payroll_router = billing_router = comply_router = insights_router = APIRouter()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"],
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
app.include_router(asset_router)
app.include_router(learning_router)
app.include_router(time_router)
app.include_router(payroll_router)
app.include_router(billing_router)
app.include_router(comply_router)
app.include_router(insights_router)


# -- Startup: create tables + seed admin --------------------------------------
@app.on_event("startup")
def on_startup():
    print(f"[startup] Connecting to MySQL: {settings.DATABASE_URL}")
    _seed_admin_if_empty()
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
