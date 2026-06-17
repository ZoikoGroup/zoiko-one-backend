"""
main.py
-------
The entry point of the entire Zoiko One Backend application.

This file:
  1. Creates the FastAPI app instance
  2. Creates all database tables if they do not exist
  3. Registers all exception handlers
  4. Registers all module routers (HR first, more to come)
  5. Adds CORS middleware (so the React frontend can talk to this backend)
  6. Defines a health check endpoint

To run the server:
    uvicorn app.main:app --reload

Then open:  http://localhost:8000/docs   ← interactive API documentation
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base  # Import both engine and Base from database.py
from app.core.exceptions import (
    ZoikoException,
    zoiko_exception_handler,
    generic_exception_handler,
)

# ── 1. Import All Module Routers ──────────────────────────────────────────────
# Importing the routers automatically registers the module models into memory
from app.modules.hr.router import auth_router, hr_router
from app.modules.time.router     import time_router
from app.modules.payroll.router  import payroll_router
from app.modules.billing.router  import billing_router
from app.modules.comply.router   import comply_router
from app.modules.insights.router import insights_router


# ── 2. Create Database Tables Automatically ──────────────────────────────────────
# Since routers are imported above, Base now knows about your tables and will 
# safely build them in MySQL if they do not already exist.
Base.metadata.create_all(bind=engine)


# ── 3. Create the FastAPI App ────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## Zoiko One — Business Application Backend

A multi-module business platform with 6 core modules:

| Module | Prefix | Status |
|--------|--------|--------|
| 👥 Zoiko HR | `/hr` | ✅ Active |
| 🕐 Zoiko Time | `/time` | ✅ Active |
| 💳 Zoiko Payroll | `/payroll` | ✅ Active |
| 🧾 Zoiko Billing | `/billing` | ✅ Active |
| 📋 Zoiko Comply | `/comply` | ✅ Active |
| 📊 Zoiko Insights | `/insights` | ✅ Active |

### Authentication
All endpoints (except `/auth/login`) require a Bearer token.
1. Call `POST /auth/login` with your credentials
2. Copy the `access_token` from the response
3. Click **Authorize** button above and paste: `Bearer <your_token>`
    """,
    docs_url="/docs",       # Swagger UI  → http://localhost:8000/docs
    redoc_url="/redoc",     # ReDoc UI    → http://localhost:8000/redoc
    openapi_url="/openapi.json",
)


# ── CORS Middleware ───────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # React (Create React App)
        "http://localhost:5173",   # React (Vite)
        "http://localhost:5174",   # React (Vite alternate port)
    ],
    allow_credentials=True,    # allows cookies and auth headers
    allow_methods=["*"],       # allows GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],       # allows Authorization, Content-Type, etc.
)


# ── Register Exception Handlers ───────────────────────────────────────────────
app.add_exception_handler(ZoikoException, zoiko_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


# ── Register Routers ──────────────────────────────────────────────────────────
app.include_router(auth_router)   # POST /auth/login
app.include_router(hr_router)     # /hr/employees, /hr/departments, etc.
app.include_router(time_router)
app.include_router(payroll_router)
app.include_router(billing_router)
app.include_router(comply_router)
app.include_router(insights_router)


# ── Health Check Endpoints ────────────────────────────────────────────────────
@app.get("/", tags=["🏥 Health Check"], summary="Check if the server is running")
def root():
    return {
        "status":  "healthy",
        "app":     settings.APP_NAME,
        "version": settings.APP_VERSION,
        "message": "Zoiko One Backend is running! Visit /docs for API documentation.",
    }


@app.get("/health", tags=["🏥 Health Check"], summary="Detailed health status")
def health():
    return {
        "status":  "ok",
        "modules": {
            "hr":       "active",
            "time":     "active",
            "payroll":  "active",
            "billing":  "active",
            "comply":   "active",
            "insights": "active",
        }
    }