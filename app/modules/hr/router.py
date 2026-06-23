"""
modules/hr/router.py
--------------------
Defines all HTTP endpoints for the HR module.

Endpoints created here:
  AUTH
    POST   /auth/login                  → Login, get token

  DEPARTMENTS
    POST   /hr/departments              → Create department
    GET    /hr/departments              → List all departments
    GET    /hr/departments/{id}         → Get one department
    PUT    /hr/departments/{id}         → Update department
    DELETE /hr/departments/{id}         → Delete department

  EMPLOYEES
    POST   /hr/employees                → Onboard new employee
    GET    /hr/employees                → List employees (with filters)
    GET    /hr/employees/{id}           → Get one employee
    PUT    /hr/employees/{id}           → Update employee
    DELETE /hr/employees/{id}           → Deactivate employee
    GET    /hr/employees/me             → Get my own profile

  DASHBOARD
    GET    /hr/dashboard/stats          → HR summary stats
"""

import os
import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user, get_current_admin

from app.modules.hr import service
from app.modules.hr.models import EmployeeStatus, LeaveType, RequestStatus
from app.modules.hr.schemas import (
    DepartmentCreate, DepartmentUpdate, DepartmentResponse,
    EmployeeCreate, EmployeeUpdate, EmployeeResponse, EmployeeListResponse,
    LoginRequest, TokenResponse, SuccessResponse,
    AttendanceCreate, AttendanceResponse,
    LeaveRequestCreate, LeaveRequestUpdate, LeaveRequestResponse,
    LeaveTypeConfigCreate, LeaveTypeConfigUpdate, LeaveTypeConfigResponse,
    LeaveSettingCreate, LeaveSettingUpdate, LeaveSettingResponse,
    LeaveBalanceResponse, LeaveBalanceUpdate,
    LeaveDashboardStats, LeaveCalendarEvent, LeaveStatisticsResponse,
    PayGradeCreate, PayGradeUpdate, PayGradeResponse,
    CompensationBandCreate, CompensationBandUpdate, CompensationBandResponse,
    SalaryComponentCreate, SalaryComponentUpdate, SalaryComponentResponse,
    SalaryStructureCreate, SalaryStructureUpdate, SalaryStructureResponse,
    StructureComponentCreate, StructureComponentUpdate, StructureComponentResponse,
    EmployeeCompensationCreate, EmployeeCompensationUpdate, EmployeeCompensationResponse,
    SalaryRevisionCreate, SalaryRevisionResponse,
    AllowanceCreate, AllowanceUpdate, AllowanceResponse,
    BenefitCreate, BenefitUpdate, BenefitResponse,
    EmployeeBenefitCreate, EmployeeBenefitResponse,
    ComplianceRecordCreate, ComplianceRecordResponse,
    EngagementSurveyCreate, EngagementSurveyResponse,
    EssRequestCreate, EssRequestResponse,
    OnboardingRecordCreate, OnboardingRecordUpdate, OnboardingRecordResponse,
    OnboardingTaskCreate, OnboardingTaskUpdate, OnboardingTaskResponse,
    OnboardingNewHireCreate, OnboardingNewHireUpdate, OnboardingNewHireResponse,
    OnboardingPreboardingTaskCreate, OnboardingPreboardingTaskUpdate, OnboardingPreboardingTaskResponse,
    OnboardingDocumentCreate, OnboardingDocumentUpdate, OnboardingDocumentResponse,
    OnboardingChecklistCreate, OnboardingChecklistUpdate, OnboardingChecklistResponse,
    OnboardingChecklistAssignmentCreate,
    OnboardingOrientationCreate, OnboardingOrientationUpdate, OnboardingOrientationResponse,
    OnboardingOrientationAttendeeCreate, OnboardingOrientationAttendeeUpdate, OnboardingOrientationAttendeeResponse,
    OnboardingActivityResponse, OnboardingDashboardResponse, OnboardingAnalyticsResponse,
    PerformanceReviewCreate, PerformanceReviewResponse,
    PerformanceGoalCreate, PerformanceGoalUpdate, PerformanceGoalResponse,
    PerformanceKpiCreate, PerformanceKpiUpdate, PerformanceKpiResponse,
    PerformanceFeedbackCreate, PerformanceFeedbackResponse,
    AppraisalCreate, AppraisalUpdate, AppraisalResponse,
    RecruitmentCandidateCreate, RecruitmentCandidateUpdate,
    RecruitmentCandidateResponse,
    TravelRequestCreate, TravelRequestResponse,
    WorkforcePlanCreate, WorkforcePlanResponse,
    WorkforceSummaryResponse,
    EmployeeProfileCreate, EmployeeProfileUpdate, EmployeeProfileResponse,
    EmployeeReportingCreate, EmployeeReportingUpdate, EmployeeReportingResponse,
    EmployeeLifecycleCreate, EmployeeLifecycleUpdate, EmployeeLifecycleResponse,
    EmployeeHistoryResponse,
    EmployeeDashboardResponse,
    ChangeManagerRequest,
    ConfirmProbationRequest,
    PromoteEmployeeRequest,
    TransferEmployeeRequest,
    ResignationRequest,
    ExitEmployeeRequest,
    EmployeeReportRequest,
    EmployeeExportRequest,
    EmployeeAnalyticsResponse,
    DesignationCreate,
    DesignationUpdate,
    DesignationResponse,
    HrDocumentUpdate,
    HrDocumentStatusUpdate,
    HrDocumentResponse,
)

# ── Create two routers ────────────────────────────────────────────────────────
# auth_router  = no login required  (you can't be logged in to log in!)
# hr_router    = login required by default via dependencies
auth_router = APIRouter(prefix="/auth", tags=["🔐 Authentication"])
hr_router   = APIRouter(prefix="/hr",   tags=["👥 HR Module"])


# ════════════════════════════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@auth_router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get access token",
    description="Send email + password, get back a JWT token to use in future requests."
)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    result = service.login_employee(db, data)
    return result


@auth_router.get(
    "/me",
    response_model=EmployeeResponse,
    summary="Get current logged-in user",
    description="Returns the authenticated employee's profile."
)
def get_me(current_user = Depends(get_current_user)):
    return current_user


@auth_router.post(
    "/logout",
    response_model=SuccessResponse,
    summary="Logout",
    description="Logs out the current user. Client should discard the token."
)
def logout(current_user = Depends(get_current_user)):
    return {"message": "Logged out successfully."}


# ════════════════════════════════════════════════════════════════════════════
# DEPARTMENT ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@hr_router.post(
    "/departments",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new department",
    dependencies=[Depends(get_current_admin)],   # only admins can create
)
def create_department(data: DepartmentCreate, db: Session = Depends(get_db)):
    return service.create_department(db, data)


@hr_router.get(
    "/departments",
    response_model=list[DepartmentResponse],
    summary="List all departments",
)
def list_departments(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),   # any logged-in user can view
):
    return service.get_all_departments(db)


@hr_router.get(
    "/departments/{dept_id}",
    response_model=DepartmentResponse,
    summary="Get a single department by ID",
)
def get_department(
    dept_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.get_department_by_id(db, dept_id)


@hr_router.put(
    "/departments/{dept_id}",
    response_model=DepartmentResponse,
    summary="Update a department",
    dependencies=[Depends(get_current_admin)],
)
def update_department(
    dept_id: int,
    data: DepartmentUpdate,
    db: Session = Depends(get_db),
):
    return service.update_department(db, dept_id, data)


@hr_router.delete(
    "/departments/{dept_id}",
    response_model=SuccessResponse,
    summary="Deactivate a department",
    dependencies=[Depends(get_current_admin)],
)
def delete_department(dept_id: int, db: Session = Depends(get_db)):
    service.delete_department(db, dept_id)
    return {"message": f"Department {dept_id} has been deactivated successfully."}


# ════════════════════════════════════════════════════════════════════════════
# EMPLOYEE ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@hr_router.get(
    "/employees/me",
    response_model=EmployeeResponse,
    summary="Get my own profile",
    description="Returns the profile of the currently logged-in employee."
)
def get_my_profile(current_user=Depends(get_current_user)):
    return current_user


@hr_router.post(
    "/employees",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Onboard a new employee",
    dependencies=[Depends(get_current_admin)],
)
def create_employee(data: EmployeeCreate, db: Session = Depends(get_db)):
    return service.create_employee(db, data)


@hr_router.get(
    "/employees",
    response_model=EmployeeListResponse,
    summary="List employees with search and filters",
    description="""
    Returns a paginated list of employees.

    **Query parameters:**
    - `page`          → page number (default: 1)
    - `per_page`      → results per page (default: 20, max: 100)
    - `search`        → search by name, email, or employee code
    - `department_id` → filter by department
    - `status`        → filter by status (active, inactive, on_leave, terminated)
    """
)
def list_employees(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    page:          int                         = Query(1,    ge=1,   description="Page number"),
    per_page:      int                         = Query(20,   ge=1,   le=100, description="Results per page"),
    search:        Optional[str]               = Query(None, description="Search name/email/code"),
    department_id: Optional[int]               = Query(None, description="Filter by department ID"),
    status:        Optional[EmployeeStatus]    = Query(None, description="Filter by status"),
):
    return service.get_all_employees(db, page, per_page, search, department_id, status)


@hr_router.get(
    "/employees/{employee_id}",
    response_model=EmployeeResponse,
    summary="Get a single employee by ID",
)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.get_employee_by_id(db, employee_id)


@hr_router.put(
    "/employees/{employee_id}",
    response_model=EmployeeResponse,
    summary="Update employee details",
    dependencies=[Depends(get_current_admin)],
)
def update_employee(
    employee_id: int,
    data: EmployeeUpdate,
    db: Session = Depends(get_db),
):
    return service.update_employee(db, employee_id, data)


@hr_router.delete(
    "/employees/{employee_id}",
    response_model=SuccessResponse,
    summary="Deactivate / terminate an employee",
    dependencies=[Depends(get_current_admin)],
)
def deactivate_employee(employee_id: int, db: Session = Depends(get_db)):
    service.deactivate_employee(db, employee_id)
    return {"message": f"Employee {employee_id} has been deactivated successfully."}


# ════════════════════════════════════════════════════════════════════════════
# DASHBOARD STATS
# ════════════════════════════════════════════════════════════════════════════

@hr_router.get(
    "/dashboard/stats",
    summary="HR Dashboard statistics",
    description="Returns total employees, active count, departments, new joiners this month, etc."
)
def dashboard_stats(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.get_hr_dashboard_stats(db)


@hr_router.get(
    "/performance/dashboard",
    summary="Performance dashboard stats",
    description="Returns performance review summary statistics."
)
def performance_dashboard(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.get_performance_dashboard(db)


@hr_router.get(
    "/engagement/dashboard",
    summary="Engagement dashboard stats",
    description="Returns engagement survey summary statistics."
)
def engagement_dashboard(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.get_engagement_dashboard(db)


@hr_router.get(
    "/compensation/dashboard",
    summary="Compensation dashboard stats",
    description="Returns compensation summary statistics."
)
def compensation_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return service.get_compensation_dashboard(db, current_user.organization_id)


# ── Legacy compatibility endpoints ──────────────────────────────────────────
@hr_router.get("/overview", summary="HR overview stats")
def overview(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_hr_dashboard_stats(db)


@hr_router.get("/workforce", summary="Workforce overview")
def workforce(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_workforce_summary(db)


@hr_router.get("/compensation", summary="Compensation overview")
def compensation_overview(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return service.get_compensation_dashboard(db, current_user.organization_id)


@hr_router.get("/learning", summary="Learning overview")
def learning_overview(db: Session = Depends(get_db), _=Depends(get_current_user)):
    from app.modules.hr import learning_service
    return learning_service.get_learning_dashboard(db)


@hr_router.get("/payrollSummary", summary="Payroll summary")
def payroll_summary(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return {"message": "Payroll summary not yet implemented", "data": []}


# ════════════════════════════════════════════════════════════════════════════
# HR SUBMODULE ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@hr_router.post(
    "/attendance",
    response_model=AttendanceResponse,
    summary="Record attendance",
    description="Create a new attendance record for an employee."
)
def create_attendance(data: AttendanceCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.create_attendance_record(db, data)





# ── Leave Dashboard ────────────────────────────────────────────────────────

@hr_router.get(
    "/leaves/dashboard",
    response_model=LeaveDashboardStats,
    summary="Leave dashboard statistics",
)
def leave_dashboard(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    return service.get_leave_dashboard(db, current_user.organization_id)


@hr_router.get(
    "/leaves/calendar",
    response_model=list[LeaveCalendarEvent],
    summary="Leave calendar events",
)
def leave_calendar(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
):
    return service.get_leave_calendar(db, current_user.organization_id, year, month)


@hr_router.get(
    "/leaves/statistics",
    response_model=LeaveStatisticsResponse,
    summary="Leave statistics & reports",
)
def leave_statistics(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    return service.get_leave_statistics(db, current_user.organization_id)


# ── Leave Requests ─────────────────────────────────────────────────────────

@hr_router.post(
    "/leaves",
    response_model=LeaveRequestResponse,
    summary="Submit a leave request",
)
def create_leave_request(
    data: LeaveRequestCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    if data.employee_id is None:
        data.employee_id = current_user.id
    return service.create_leave_request(db, data, current_user.organization_id)


@hr_router.get(
    "/leaves",
    response_model=list[LeaveRequestResponse],
    summary="List leave requests",
)
def list_leave_requests(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
    status: Optional[RequestStatus] = Query(None, description="Filter by status"),
    leave_type: Optional[LeaveType] = Query(None, description="Filter by leave type"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
):
    return service.get_leave_requests(db, current_user.organization_id, employee_id, status, leave_type, start_date, end_date, department_id)


# ── Leave Type Configs ─────────────────────────────────────────────────────

@hr_router.get(
    "/leaves/type-configs",
    response_model=list[LeaveTypeConfigResponse],
    summary="List leave type configurations",
)
def list_leave_type_configs(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    return service.get_leave_type_configs(db, current_user.organization_id)


@hr_router.post(
    "/leaves/type-configs",
    response_model=LeaveTypeConfigResponse,
    summary="Create leave type configuration",
)
def create_leave_type_config(
    data: LeaveTypeConfigCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    return service.create_leave_type_config(db, data, current_user.organization_id)


@hr_router.put(
    "/leaves/type-configs/{config_id}",
    response_model=LeaveTypeConfigResponse,
    summary="Update leave type configuration",
)
def update_leave_type_config(
    config_id: int,
    data: LeaveTypeConfigUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    return service.update_leave_type_config(db, config_id, data, current_user.organization_id)


@hr_router.delete(
    "/leaves/type-configs/{config_id}",
    response_model=SuccessResponse,
    summary="Delete leave type configuration",
)
def delete_leave_type_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    service.delete_leave_type_config(db, config_id, current_user.organization_id)
    return SuccessResponse(message="Leave type config deleted")


# ── Leave Balances ─────────────────────────────────────────────────────────

@hr_router.get(
    "/leaves/balance",
    response_model=list[LeaveBalanceResponse],
    summary="Get leave balances",
)
def list_leave_balances(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
):
    return service.get_leave_balances(db, current_user.organization_id, employee_id)


@hr_router.put(
    "/leaves/balance/{balance_id}",
    response_model=LeaveBalanceResponse,
    summary="Update leave balance",
)
def update_leave_balance(
    balance_id: int,
    data: LeaveBalanceUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    return service.update_leave_balance(db, balance_id, data, current_user.organization_id)


@hr_router.post(
    "/leaves/balance/init",
    response_model=SuccessResponse,
    summary="Initialize leave balances for an employee",
)
def init_leave_balance(
    employee_id: int = Query(...),
    year: int = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    service.init_leave_balance(db, employee_id, current_user.organization_id, year)
    return SuccessResponse(message=f"Leave balances initialized for employee {employee_id}")


# ── Leave Settings ─────────────────────────────────────────────────────────

@hr_router.get(
    "/leaves/settings",
    response_model=LeaveSettingResponse,
    summary="Get leave settings",
)
def get_leave_settings(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    return service.get_leave_settings(db, current_user.organization_id)


@hr_router.put(
    "/leaves/settings",
    response_model=LeaveSettingResponse,
    summary="Update leave settings",
)
def update_leave_settings(
    data: LeaveSettingUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    return service.update_leave_settings(db, current_user.organization_id, data)


# ── Leave Request Dynamic Routes ───────────────────────────────────────────

@hr_router.get(
    "/leaves/{leave_id}",
    response_model=LeaveRequestResponse,
    summary="Get a single leave request",
)
def get_leave_request(
    leave_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    return service.get_leave_request(db, leave_id, current_user.organization_id)


@hr_router.put(
    "/leaves/{leave_id}",
    response_model=LeaveRequestResponse,
    summary="Update a leave request",
)
def update_leave_request(
    leave_id: int,
    data: LeaveRequestUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    return service.update_leave_request(db, leave_id, data, current_user.organization_id)


@hr_router.delete(
    "/leaves/{leave_id}",
    response_model=SuccessResponse,
    summary="Delete a leave request",
)
def delete_leave_request(
    leave_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    service.delete_leave_request(db, leave_id, current_user.organization_id)
    return SuccessResponse(message="Leave request deleted")


@hr_router.put(
    "/leaves/{leave_id}/review",
    response_model=LeaveRequestResponse,
    summary="Review (approve/reject) a leave request",
    dependencies=[Depends(get_current_admin)],
)
def review_leave(
    leave_id: int,
    data: LeaveRequestUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    return service.review_leave_request(db, leave_id, data, current_user.organization_id, current_user.id)


# ── Compensation Endpoints (Expanded) ─────────────────────────────────────────

@hr_router.get("/compensation/pay-grades", response_model=list[PayGradeResponse], summary="List pay grades")
def get_pay_grades(db: Session = Depends(get_db), org_id: int = Depends(get_current_user)):
    return service.get_pay_grades(db, org_id.organization_id)

@hr_router.post("/compensation/pay-grades", response_model=PayGradeResponse, summary="Create pay grade", dependencies=[Depends(get_current_admin)])
def create_pay_grade(data: PayGradeCreate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return service.create_pay_grade(db, data, current_user.organization_id)

@hr_router.put("/compensation/pay-grades/{id}", response_model=PayGradeResponse, summary="Update pay grade", dependencies=[Depends(get_current_admin)])
def update_pay_grade(id: int, data: PayGradeUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return service.update_pay_grade(db, id, data, current_user.organization_id)

@hr_router.delete("/compensation/pay-grades/{id}", summary="Delete pay grade", dependencies=[Depends(get_current_admin)])
def delete_pay_grade(id: int, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    service.delete_pay_grade(db, id, current_user.organization_id)
    return {"message": "Pay grade deleted successfully."}

@hr_router.get("/compensation/bands", response_model=list[CompensationBandResponse], summary="List bands")
def get_compensation_bands(db: Session = Depends(get_db), org_id: int = Depends(get_current_user)):
    return service.get_compensation_bands(db, org_id.organization_id)

@hr_router.post("/compensation/bands", response_model=CompensationBandResponse, summary="Create band", dependencies=[Depends(get_current_admin)])
def create_compensation_band(data: CompensationBandCreate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return service.create_compensation_band(db, data, current_user.organization_id)

@hr_router.put("/compensation/bands/{id}", response_model=CompensationBandResponse, summary="Update band", dependencies=[Depends(get_current_admin)])
def update_compensation_band(id: int, data: CompensationBandUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return service.update_compensation_band(db, id, data, current_user.organization_id)

@hr_router.delete("/compensation/bands/{id}", summary="Delete band", dependencies=[Depends(get_current_admin)])
def delete_compensation_band(id: int, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    service.delete_compensation_band(db, id, current_user.organization_id)
    return {"message": "Compensation band deleted successfully."}

@hr_router.get("/compensation/salary-components", response_model=list[SalaryComponentResponse], summary="List components")
def get_salary_components(db: Session = Depends(get_db), org_id: int = Depends(get_current_user)):
    return service.get_salary_components(db, org_id.organization_id)

@hr_router.post("/compensation/salary-components", response_model=SalaryComponentResponse, summary="Create component", dependencies=[Depends(get_current_admin)])
def create_salary_component(data: SalaryComponentCreate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return service.create_salary_component(db, data, current_user.organization_id)

@hr_router.put("/compensation/salary-components/{id}", response_model=SalaryComponentResponse, summary="Update component", dependencies=[Depends(get_current_admin)])
def update_salary_component(id: int, data: SalaryComponentUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return service.update_salary_component(db, id, data, current_user.organization_id)

@hr_router.delete("/compensation/salary-components/{id}", summary="Delete component", dependencies=[Depends(get_current_admin)])
def delete_salary_component(id: int, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    service.delete_salary_component(db, id, current_user.organization_id)
    return {"message": "Salary component deleted successfully."}

@hr_router.get("/compensation/salary-structures", response_model=list[SalaryStructureResponse], summary="List structures")
def get_salary_structures(db: Session = Depends(get_db), org_id: int = Depends(get_current_user)):
    return service.get_salary_structures(db, org_id.organization_id)

@hr_router.post("/compensation/salary-structures", response_model=SalaryStructureResponse, summary="Create structure", dependencies=[Depends(get_current_admin)])
def create_salary_structure(data: SalaryStructureCreate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return service.create_salary_structure(db, data, current_user.organization_id)

@hr_router.put("/compensation/salary-structures/{id}", response_model=SalaryStructureResponse, summary="Update structure", dependencies=[Depends(get_current_admin)])
def update_salary_structure(id: int, data: SalaryStructureUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return service.update_salary_structure(db, id, data, current_user.organization_id)

@hr_router.delete("/compensation/salary-structures/{id}", summary="Delete structure", dependencies=[Depends(get_current_admin)])
def delete_salary_structure(id: int, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    service.delete_salary_structure(db, id, current_user.organization_id)
    return {"message": "Salary structure deleted successfully."}

@hr_router.post("/compensation/salary-structures/{id}/components", response_model=StructureComponentResponse, summary="Add component to structure", dependencies=[Depends(get_current_admin)])
def add_structure_component(id: int, data: StructureComponentCreate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return service.create_structure_component(db, data, current_user.organization_id)

@hr_router.get("/compensation/salary-structures/{id}/components", response_model=list[StructureComponentResponse], summary="Get structure components")
def get_structure_components(id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return service.get_structure_components(db, id, current_user.organization_id)

@hr_router.delete("/compensation/salary-structures/{id}/components/{comp_id}", summary="Remove component from structure", dependencies=[Depends(get_current_admin)])
def delete_structure_component(id: int, comp_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    service.delete_structure_component(db, comp_id, current_user.organization_id)
    return {"message": "Structure component removed successfully."}

@hr_router.get("/compensation/employee-compensation", response_model=list[EmployeeCompensationResponse], summary="List employee compensation")
def get_employee_compensations(db: Session = Depends(get_db), org_id: int = Depends(get_current_user), employee_id: Optional[int] = Query(None)):
    return service.get_employee_compensations(db, org_id.organization_id, employee_id)

@hr_router.post("/compensation/employee-compensation", response_model=EmployeeCompensationResponse, summary="Assign compensation", dependencies=[Depends(get_current_admin)])
def create_employee_compensation(data: EmployeeCompensationCreate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return service.create_employee_compensation(db, data, current_user.organization_id)

@hr_router.put("/compensation/employee-compensation/{id}", response_model=EmployeeCompensationResponse, summary="Update employee compensation", dependencies=[Depends(get_current_admin)])
def update_employee_compensation(id: int, data: EmployeeCompensationUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return service.update_employee_compensation(db, id, data, current_user.organization_id)

@hr_router.delete("/compensation/employee-compensation/{id}", summary="Delete employee compensation", dependencies=[Depends(get_current_admin)])
def delete_employee_compensation(id: int, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    service.delete_employee_compensation(db, id, current_user.organization_id)
    return {"message": "Employee compensation deleted successfully."}

@hr_router.get("/compensation/revisions", response_model=list[SalaryRevisionResponse], summary="List salary revisions")
def get_salary_revisions(db: Session = Depends(get_db), org_id: int = Depends(get_current_user)):
    return service.get_salary_revisions(db, org_id.organization_id)

@hr_router.post("/compensation/revisions", response_model=SalaryRevisionResponse, summary="Create salary revision", dependencies=[Depends(get_current_admin)])
def create_salary_revision(data: SalaryRevisionCreate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return service.create_salary_revision(db, data, current_user.organization_id)

@hr_router.get("/compensation/allowances", response_model=list[AllowanceResponse], summary="List allowances")
def get_allowances(db: Session = Depends(get_db), org_id: int = Depends(get_current_user)):
    return service.get_allowances(db, org_id.organization_id)

@hr_router.post("/compensation/allowances", response_model=AllowanceResponse, summary="Add allowance", dependencies=[Depends(get_current_admin)])
def create_allowance(data: AllowanceCreate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return service.create_allowance(db, data, current_user.organization_id)

@hr_router.put("/compensation/allowances/{id}", response_model=AllowanceResponse, summary="Update allowance", dependencies=[Depends(get_current_admin)])
def update_allowance(id: int, data: AllowanceUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return service.update_allowance(db, id, data, current_user.organization_id)

@hr_router.delete("/compensation/allowances/{id}", summary="Delete allowance", dependencies=[Depends(get_current_admin)])
def delete_allowance(id: int, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    service.delete_allowance(db, id, current_user.organization_id)
    return {"message": "Allowance deleted successfully."}

@hr_router.get("/compensation/benefits", response_model=list[BenefitResponse], summary="List benefits")
def get_benefits(db: Session = Depends(get_db), org_id: int = Depends(get_current_user)):
    return service.get_benefits(db, org_id.organization_id)

@hr_router.post("/compensation/benefits", response_model=BenefitResponse, summary="Add benefit", dependencies=[Depends(get_current_admin)])
def create_benefit(data: BenefitCreate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return service.create_benefit(db, data, current_user.organization_id)

@hr_router.put("/compensation/benefits/{id}", response_model=BenefitResponse, summary="Update benefit", dependencies=[Depends(get_current_admin)])
def update_benefit(id: int, data: BenefitUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return service.update_benefit(db, id, data, current_user.organization_id)

@hr_router.delete("/compensation/benefits/{id}", summary="Delete benefit", dependencies=[Depends(get_current_admin)])
def delete_benefit(id: int, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    service.delete_benefit(db, id, current_user.organization_id)
    return {"message": "Benefit deleted successfully."}

@hr_router.post("/compensation/employee-benefits", response_model=EmployeeBenefitResponse, summary="Enroll in benefit", dependencies=[Depends(get_current_admin)])
def create_employee_benefit(data: EmployeeBenefitCreate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return service.create_employee_benefit(db, data, current_user.organization_id)

@hr_router.get("/compensation/employee-benefits", response_model=list[EmployeeBenefitResponse], summary="List employee benefits")
def get_employee_benefits(db: Session = Depends(get_db), org_id: int = Depends(get_current_user)):
    return service.get_employee_benefits(db, org_id.organization_id)

@hr_router.delete("/compensation/employee-benefits/{id}", summary="Remove benefit", dependencies=[Depends(get_current_admin)])
def delete_employee_benefit(id: int, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    service.delete_employee_benefit(db, id, current_user.organization_id)
    return {"message": "Employee benefit removed successfully."}


@hr_router.post(
    "/compliance",
    response_model=ComplianceRecordResponse,
    summary="Create a compliance record",
    dependencies=[Depends(get_current_admin)],
)
def create_compliance_record(data: ComplianceRecordCreate, db: Session = Depends(get_db)):
    return service.create_compliance_record(db, data)


@hr_router.get(
    "/compliance",
    response_model=list[ComplianceRecordResponse],
    summary="List compliance records",
)
def list_compliance_records(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
):
    return service.get_compliance_records(db, employee_id)


@hr_router.post(
    "/engagement",
    response_model=EngagementSurveyResponse,
    summary="Submit an engagement survey",
)
def create_engagement_survey(data: EngagementSurveyCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.create_engagement_survey(db, data)


@hr_router.get(
    "/engagement",
    response_model=list[EngagementSurveyResponse],
    summary="List engagement surveys",
)
def list_engagement_surveys(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
):
    return service.get_engagement_surveys(db, employee_id)


@hr_router.post(
    "/ess",
    response_model=EssRequestResponse,
    summary="Create an ESS request",
)
def create_ess_request(data: EssRequestCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.create_ess_request(db, data)


@hr_router.get(
    "/ess",
    response_model=list[EssRequestResponse],
    summary="List ESS requests",
)
def list_ess_requests(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
):
    return service.get_ess_requests(db, employee_id)


# ════════════════════════════════════════════════════════════════════════════
# ONBOARDING MODULE — Production-Ready Endpoints
# ════════════════════════════════════════════════════════════════════════════

# ── New Hires ──────────────────────────────────────────────────────────────

@hr_router.get(
    "/onboarding/new-hires",
    response_model=list[OnboardingNewHireResponse],
    summary="List all new hires",
)
def list_new_hires(
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    return service.get_new_hires(db, search=search, status=status)


@hr_router.post(
    "/onboarding/new-hires",
    response_model=OnboardingNewHireResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new hire record",
)
def create_new_hire(data: OnboardingNewHireCreate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    return service.create_new_hire(db, data)


@hr_router.get(
    "/onboarding/new-hires/{new_hire_id}",
    response_model=OnboardingNewHireResponse,
    summary="Get a single new hire by ID",
)
def get_new_hire(new_hire_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    return service.get_new_hire_by_id(db, new_hire_id)


@hr_router.put(
    "/onboarding/new-hires/{new_hire_id}",
    response_model=OnboardingNewHireResponse,
    summary="Update a new hire record",
)
def update_new_hire(new_hire_id: int, data: OnboardingNewHireUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    return service.update_new_hire(db, new_hire_id, data)


@hr_router.delete(
    "/onboarding/new-hires/{new_hire_id}",
    response_model=SuccessResponse,
    summary="Soft-delete a new hire record",
)
def delete_new_hire(new_hire_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    service.delete_new_hire(db, new_hire_id)
    return {"message": f"New hire {new_hire_id} deleted successfully."}


# ── Legacy alias endpoints (kept for backward compatibility) ────────────────

@hr_router.post(
    "/onboarding/records",
    response_model=OnboardingNewHireResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an onboarding record (alias)",
)
def create_onboarding_record(data: OnboardingNewHireCreate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    return service.create_new_hire(db, data)


@hr_router.get(
    "/onboarding/records",
    response_model=list[OnboardingNewHireResponse],
    summary="List onboarding records (alias)",
)
def list_onboarding_records(
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    return service.get_new_hires(db, search=search, status=status)


@hr_router.get(
    "/onboarding/records/{record_id}",
    response_model=OnboardingNewHireResponse,
    summary="Get onboarding record by ID (alias)",
)
def get_onboarding_record(record_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    return service.get_new_hire_by_id(db, record_id)


@hr_router.put(
    "/onboarding/records/{record_id}",
    response_model=OnboardingNewHireResponse,
    summary="Update onboarding record (alias)",
)
def update_onboarding_record(record_id: int, data: OnboardingNewHireUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    return service.update_new_hire(db, record_id, data)


@hr_router.delete(
    "/onboarding/records/{record_id}",
    response_model=SuccessResponse,
    summary="Delete onboarding record (alias)",
)
def delete_onboarding_record(record_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    service.delete_new_hire(db, record_id)
    return {"message": f"Onboarding record {record_id} deleted successfully."}


# ── Pre-boarding / Tasks ───────────────────────────────────────────────────

@hr_router.get(
    "/onboarding/preboarding-tasks",
    response_model=list[OnboardingPreboardingTaskResponse],
    summary="List pre-boarding tasks",
)
def list_preboarding_tasks(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    new_hire_id: Optional[int] = Query(None),
    employee_id: Optional[int] = Query(None),
):
    return service.get_preboarding_tasks(db, new_hire_id=new_hire_id, employee_id=employee_id)


@hr_router.post(
    "/onboarding/preboarding-tasks",
    response_model=OnboardingPreboardingTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a pre-boarding task",
)
def create_preboarding_task(data: OnboardingPreboardingTaskCreate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    return service.create_preboarding_task(db, data)


@hr_router.put(
    "/onboarding/preboarding-tasks/{task_id}",
    response_model=OnboardingPreboardingTaskResponse,
    summary="Update a pre-boarding task",
)
def update_preboarding_task(task_id: int, data: OnboardingPreboardingTaskUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    # Self-service: employees can update their own tasks (e.g., mark complete)
    return service.update_preboarding_task(db, task_id, data)


@hr_router.delete(
    "/onboarding/preboarding-tasks/{task_id}",
    response_model=SuccessResponse,
    summary="Delete a pre-boarding task",
)
def delete_preboarding_task(task_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    service.delete_preboarding_task(db, task_id)
    return {"message": f"Task {task_id} deleted successfully."}

# ── Checklist Templates ────────────────────────────────────────────────────

@hr_router.get(
    "/onboarding/checklist-templates",
    response_model=list[OnboardingChecklistResponse],
    summary="List checklist templates",
)
def list_checklist_templates(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    category: Optional[str] = Query(None),
):
    return service.get_checklists(db, is_template=True, category=category)


@hr_router.post(
    "/onboarding/checklist-templates",
    response_model=OnboardingChecklistResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a checklist template",
)
def create_checklist_template(data: OnboardingChecklistCreate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    return service.create_checklist(db, data)


@hr_router.get(
    "/onboarding/checklist-templates/{checklist_id}",
    response_model=OnboardingChecklistResponse,
    summary="Get a checklist template by ID",
)
def get_checklist_template(checklist_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    checklists = service.get_checklists(db, is_template=True)
    checklist = next((c for c in checklists if c.id == checklist_id), None)
    if not checklist:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("OnboardingChecklist", checklist_id)
    return checklist


@hr_router.put(
    "/onboarding/checklist-templates/{checklist_id}",
    response_model=OnboardingChecklistResponse,
    summary="Update a checklist template",
)
def update_checklist_template(checklist_id: int, data: OnboardingChecklistUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    return service.update_checklist(db, checklist_id, data)


@hr_router.delete(
    "/onboarding/checklist-templates/{checklist_id}",
    response_model=SuccessResponse,
    summary="Delete a checklist template",
)
def delete_checklist_template(checklist_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    service.delete_checklist(db, checklist_id)
    return {"message": f"Checklist template {checklist_id} deleted successfully."}


# ── Checklist Assignments ──────────────────────────────────────────────────

@hr_router.get(
    "/onboarding/checklist-assignments",
    response_model=list[OnboardingChecklistResponse],
    summary="List checklist assignments for a new hire",
)
def list_checklist_assignments(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    onboarding_record_id: Optional[int] = Query(None),
):
    return service.get_checklists(db, is_template=False, new_hire_id=onboarding_record_id)


@hr_router.post(
    "/onboarding/checklist-assignments",
    response_model=OnboardingChecklistResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a checklist template to a new hire",
)
def assign_checklist(data: OnboardingChecklistAssignmentCreate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    return service.assign_checklist_template(db, data.onboarding_record_id, data.template_id)


@hr_router.put(
    "/onboarding/checklist-assignments/{checklist_id}",
    response_model=OnboardingChecklistResponse,
    summary="Update a checklist assignment (mark items complete etc.)",
)
def update_checklist_assignment(checklist_id: int, data: OnboardingChecklistUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    # Self-service: employees can mark checklist items complete
    return service.update_checklist(db, checklist_id, data)


@hr_router.delete(
    "/onboarding/checklist-assignments/{checklist_id}",
    response_model=SuccessResponse,
    summary="Remove a checklist assignment",
)
def delete_checklist_assignment(checklist_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    service.delete_checklist(db, checklist_id)
    return {"message": f"Checklist assignment {checklist_id} removed."}


# ── Orientation Sessions ───────────────────────────────────────────────────

@hr_router.get(
    "/onboarding/orientation-sessions",
    response_model=list[OnboardingOrientationResponse],
    summary="List orientation sessions",
)
def list_orientation_sessions(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_orientations(db)


@hr_router.post(
    "/onboarding/orientation-sessions",
    response_model=OnboardingOrientationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an orientation session",
)
def create_orientation_session(data: OnboardingOrientationCreate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    return service.create_orientation(db, data)


@hr_router.get(
    "/onboarding/orientation-sessions/{session_id}",
    response_model=OnboardingOrientationResponse,
    summary="Get an orientation session by ID",
)
def get_orientation_session(session_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    sessions = service.get_orientations(db)
    session = next((s for s in sessions if s.id == session_id), None)
    if not session:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("OnboardingOrientation", session_id)
    return session


@hr_router.put(
    "/onboarding/orientation-sessions/{session_id}",
    response_model=OnboardingOrientationResponse,
    summary="Update an orientation session",
)
def update_orientation_session(session_id: int, data: OnboardingOrientationUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    return service.update_orientation(db, session_id, data)


@hr_router.delete(
    "/onboarding/orientation-sessions/{session_id}",
    response_model=SuccessResponse,
    summary="Delete an orientation session",
)
def delete_orientation_session(session_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    service.delete_orientation(db, session_id)
    return {"message": f"Orientation session {session_id} deleted."}


# ── Orientation Attendees ──────────────────────────────────────────────────

@hr_router.get(
    "/onboarding/orientation-attendees",
    response_model=list[OnboardingOrientationAttendeeResponse],
    summary="List orientation attendees",
)
def list_orientation_attendees(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    session_id: Optional[int] = Query(None),
    onboarding_record_id: Optional[int] = Query(None),
):
    return service.get_orientation_attendees(db, session_id=session_id, new_hire_id=onboarding_record_id)


@hr_router.post(
    "/onboarding/orientation-attendees",
    response_model=OnboardingOrientationAttendeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an attendee to an orientation session",
)
def add_orientation_attendee(data: OnboardingOrientationAttendeeCreate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    return service.add_orientation_attendee(db, data)


@hr_router.put(
    "/onboarding/orientation-attendees/{attendee_id}",
    response_model=OnboardingOrientationAttendeeResponse,
    summary="Update orientation attendee status",
)
def update_orientation_attendee(attendee_id: int, data: OnboardingOrientationAttendeeUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.update_orientation_attendee(db, attendee_id, data)


@hr_router.delete(
    "/onboarding/orientation-attendees/{attendee_id}",
    response_model=SuccessResponse,
    summary="Remove an orientation attendee",
)
def remove_orientation_attendee(attendee_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    service.remove_orientation_attendee(db, attendee_id)
    return {"message": f"Attendee {attendee_id} removed."}


# ── Activities, Dashboard & Analytics ─────────────────────────────────────

@hr_router.get(
    "/onboarding/activities",
    response_model=list[OnboardingActivityResponse],
    summary="List onboarding activity log",
)
def list_onboarding_activities(
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
    limit: int = Query(50, ge=1, le=200),
):
    return service.get_onboarding_activities(db, limit)


@hr_router.get(
    "/onboarding/dashboard",
    response_model=OnboardingDashboardResponse,
    summary="Get onboarding dashboard overview",
)
def onboarding_dashboard(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    return service.get_onboarding_dashboard(db)


@hr_router.get(
    "/onboarding/analytics",
    response_model=OnboardingAnalyticsResponse,
    summary="Get onboarding analytics summary",
)
def onboarding_analytics(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    return service.get_onboarding_analytics(db)


# ── Reports ───────────────────────────────────────────────────────────────

@hr_router.get("/onboarding/reports/joining", summary="Joining report")
def onboarding_joining_report(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    new_hires = service.get_new_hires(db)
    from datetime import date as ddate
    today = ddate.today()
    this_month = [r for r in new_hires if r.joining_date and r.joining_date.month == today.month and r.joining_date.year == today.year]
    this_quarter_months = {1,2,3} if today.month <= 3 else ({4,5,6} if today.month <= 6 else ({7,8,9} if today.month <= 9 else {10,11,12}))
    this_quarter = [r for r in new_hires if r.joining_date and r.joining_date.month in this_quarter_months and r.joining_date.year == today.year]
    # Monthly trend grouping
    from collections import defaultdict
    monthly_counts: dict = defaultdict(int)
    for r in new_hires:
        if r.joining_date:
            key = r.joining_date.strftime("%b %Y")
            monthly_counts[key] += 1
    monthly_trend = [{"month": k, "count": v} for k, v in sorted(monthly_counts.items())]
    return {
        "totalJoiners": len(new_hires),
        "thisMonth": len(this_month),
        "thisQuarter": len(this_quarter),
        "avgDaysToOnboard": 14,
        "monthlyTrend": monthly_trend,
    }





@hr_router.post(
    "/performance",
    response_model=PerformanceReviewResponse,
    summary="Create a performance review",
)
def create_performance_review(data: PerformanceReviewCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.create_performance_review(db, data)


@hr_router.get(
    "/performance",
    response_model=list[PerformanceReviewResponse],
    summary="List performance reviews",
)
def list_performance_reviews(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
):
    return service.get_performance_reviews(db, employee_id)


# ── Performance Goals ──────────────────────────────────────────────

@hr_router.get(
    "/performance/goals",
    response_model=list[PerformanceGoalResponse],
    summary="List performance goals",
)
def list_performance_goals(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
):
    return service.get_performance_goals(db, employee_id)


@hr_router.post(
    "/performance/goals",
    response_model=PerformanceGoalResponse,
    summary="Create a performance goal",
)
def create_performance_goal(data: PerformanceGoalCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.create_performance_goal(db, data)


@hr_router.get(
    "/performance/goals/{goal_id}",
    response_model=PerformanceGoalResponse,
    summary="Get a performance goal",
)
def get_performance_goal(goal_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_performance_goal(db, goal_id)


@hr_router.put(
    "/performance/goals/{goal_id}",
    response_model=PerformanceGoalResponse,
    summary="Update a performance goal",
)
def update_performance_goal(goal_id: int, data: PerformanceGoalUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.update_performance_goal(db, goal_id, data)


@hr_router.delete(
    "/performance/goals/{goal_id}",
    response_model=SuccessResponse,
    summary="Delete a performance goal",
)
def delete_performance_goal(goal_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    service.delete_performance_goal(db, goal_id)
    return {"message": f"Performance goal {goal_id} deleted successfully."}


# ── Performance KPIs ───────────────────────────────────────────────

@hr_router.get(
    "/performance/kpis",
    response_model=list[PerformanceKpiResponse],
    summary="List performance KPIs",
)
def list_performance_kpis(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    goal_id: Optional[int] = Query(None, description="Filter by goal ID"),
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
):
    return service.get_performance_kpis(db, goal_id, employee_id)


@hr_router.post(
    "/performance/kpis",
    response_model=PerformanceKpiResponse,
    summary="Create a performance KPI",
)
def create_performance_kpi(data: PerformanceKpiCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.create_performance_kpi(db, data)


@hr_router.get(
    "/performance/kpis/{kpi_id}",
    response_model=PerformanceKpiResponse,
    summary="Get a performance KPI",
)
def get_performance_kpi(kpi_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_performance_kpi(db, kpi_id)


@hr_router.put(
    "/performance/kpis/{kpi_id}",
    response_model=PerformanceKpiResponse,
    summary="Update a performance KPI",
)
def update_performance_kpi(kpi_id: int, data: PerformanceKpiUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.update_performance_kpi(db, kpi_id, data)


@hr_router.delete(
    "/performance/kpis/{kpi_id}",
    response_model=SuccessResponse,
    summary="Delete a performance KPI",
)
def delete_performance_kpi(kpi_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    service.delete_performance_kpi(db, kpi_id)
    return {"message": f"Performance KPI {kpi_id} deleted successfully."}


# ── Performance Feedback ───────────────────────────────────────────

@hr_router.get(
    "/performance/feedback",
    response_model=list[PerformanceFeedbackResponse],
    summary="List performance feedback",
)
def list_performance_feedback(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
    reviewer_id: Optional[int] = Query(None, description="Filter by reviewer ID"),
    review_id: Optional[int] = Query(None, description="Filter by review ID"),
):
    return service.get_performance_feedback(db, employee_id, reviewer_id, review_id)


@hr_router.post(
    "/performance/feedback",
    response_model=PerformanceFeedbackResponse,
    summary="Create performance feedback",
)
def create_performance_feedback(data: PerformanceFeedbackCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.create_performance_feedback(db, data)


@hr_router.delete(
    "/performance/feedback/{fb_id}",
    response_model=SuccessResponse,
    summary="Delete performance feedback",
)
def delete_performance_feedback(fb_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    service.delete_performance_feedback(db, fb_id)
    return {"message": f"Performance feedback {fb_id} deleted successfully."}


# ── Appraisals ─────────────────────────────────────────────────────

@hr_router.get(
    "/performance/appraisals",
    response_model=list[AppraisalResponse],
    summary="List appraisals",
)
def list_appraisals(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
):
    return service.get_appraisals(db, employee_id)


@hr_router.post(
    "/performance/appraisals",
    response_model=AppraisalResponse,
    summary="Create an appraisal",
)
def create_appraisal(data: AppraisalCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.create_appraisal(db, data)


@hr_router.get(
    "/performance/appraisals/{appraisal_id}",
    response_model=AppraisalResponse,
    summary="Get an appraisal",
)
def get_appraisal(appraisal_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_appraisal(db, appraisal_id)


@hr_router.put(
    "/performance/appraisals/{appraisal_id}",
    response_model=AppraisalResponse,
    summary="Update an appraisal",
)
def update_appraisal(appraisal_id: int, data: AppraisalUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.update_appraisal(db, appraisal_id, data)


@hr_router.delete(
    "/performance/appraisals/{appraisal_id}",
    response_model=SuccessResponse,
    summary="Delete an appraisal",
)
def delete_appraisal(appraisal_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    service.delete_appraisal(db, appraisal_id)
    return {"message": f"Appraisal {appraisal_id} deleted successfully."}


# ── Performance Analytics ──────────────────────────────────────────

@hr_router.get(
    "/performance/analytics",
    summary="Performance analytics data",
)
def performance_analytics(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.get_performance_analytics(db)


@hr_router.get(
    "/performance/{review_id}",
    response_model=PerformanceReviewResponse,
    summary="Get a performance review",
)
def get_performance_review(
    review_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.get_performance_review(db, review_id)


@hr_router.put(
    "/performance/{review_id}",
    response_model=PerformanceReviewResponse,
    summary="Update a performance review",
)
def update_performance_review(
    review_id: int,
    data: PerformanceReviewCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.update_performance_review(db, review_id, data)


@hr_router.delete(
    "/performance/{review_id}",
    response_model=SuccessResponse,
    summary="Delete a performance review",
)
def delete_performance_review(
    review_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    service.delete_performance_review(db, review_id)
    return {"message": f"Performance review {review_id} deleted successfully."}


@hr_router.post(
    "/recruitment",
    response_model=RecruitmentCandidateResponse,
    summary="Create a recruitment candidate",
    dependencies=[Depends(get_current_admin)],
)
def create_recruitment_candidate(data: RecruitmentCandidateCreate, db: Session = Depends(get_db)):
    return service.create_recruitment_candidate(db, data)


@hr_router.get(
    "/recruitment",
    response_model=list[RecruitmentCandidateResponse],
    summary="List recruitment candidates",
    dependencies=[Depends(get_current_admin)],
)
def list_recruitment_candidates(db: Session = Depends(get_db)):
    return service.get_recruitment_candidates(db)


@hr_router.put(
    "/recruitment/{candidate_id}",
    response_model=RecruitmentCandidateResponse,
    summary="Update recruitment candidate status",
    dependencies=[Depends(get_current_admin)],
)
def update_recruitment_candidate(candidate_id: int, data: RecruitmentCandidateUpdate, db: Session = Depends(get_db)):
    return service.update_recruitment_candidate(db, candidate_id, data)


@hr_router.post(
    "/travel",
    response_model=TravelRequestResponse,
    summary="Create a travel request",
)
def create_travel_request(data: TravelRequestCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.create_travel_request(db, data)


@hr_router.get(
    "/travel",
    response_model=list[TravelRequestResponse],
    summary="List travel requests",
)
def list_travel_requests(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
):
    return service.get_travel_requests(db, employee_id)


@hr_router.post(
    "/workforce-planning",
    response_model=WorkforcePlanResponse,
    summary="Create workforce planning item",
    dependencies=[Depends(get_current_admin)],
)
def create_workforce_plan(data: WorkforcePlanCreate, db: Session = Depends(get_db)):
    return service.create_workforce_plan(db, data)


@hr_router.get(
    "/workforce-planning",
    response_model=list[WorkforcePlanResponse],
    summary="List workforce planning items",
    dependencies=[Depends(get_current_admin)],
)
def list_workforce_plans(db: Session = Depends(get_db)):
    return service.get_workforce_plans(db)


@hr_router.get(
    "/workforce/summary",
    response_model=WorkforceSummaryResponse,
    summary="Get workforce analytics summary"
)
def workforce_summary(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_workforce_summary(db)


# ════════════════════════════════════════════════════════════════════════════════
# EMPLOYEE MANAGEMENT ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════════

# ── DASHBOARD ────────────────────────────────────────────────────────────────

@hr_router.get(
    "/employee-management/dashboard",
    summary="Employee management dashboard",
    description="Returns employee statistics and analytics."
)
def employee_dashboard(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_employee_dashboard(db)

# ── EMPLOYEES ────────────────────────────────────────────────────────────────

@hr_router.get(
    "/employee-management/employees",
    response_model=EmployeeListResponse,
    summary="List employees with search and filters",
    description="""
    Returns a paginated list of employees.

    **Query parameters:**
    - `page`          → page number (default: 1)
    - `per_page`      → results per page (default: 20, max: 100)
    - `search`        → search by name, email, or employee code
    - `department_id` → filter by department
    - `status`        → filter by status (active, inactive, on_leave, terminated)
    """
)
def list_employees(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    page:          int                         = Query(1,    ge=1,   description="Page number"),
    per_page:      int                         = Query(20,   ge=1,   le=100, description="Results per page"),
    search:        Optional[str]               = Query(None, description="Search name/email/code"),
    department_id: Optional[int]               = Query(None, description="Filter by department ID"),
    status:        Optional[EmployeeStatus]    = Query(None, description="Filter by status"),
):
    return service.get_employees(db, page, per_page, search, department_id, status)


@hr_router.get(
    "/employee-management/employees/{employee_id}",
    response_model=EmployeeResponse,
    summary="Get a single employee by ID",
)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.get_employee_by_id(db, employee_id)


@hr_router.post(
    "/employee-management/employees",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new employee",
    dependencies=[Depends(get_current_admin)],
)
def create_employee(data: EmployeeCreate, db: Session = Depends(get_db)):
    return service.create_employee(db, data)


@hr_router.put(
    "/employee-management/employees/{employee_id}",
    response_model=EmployeeResponse,
    summary="Update employee details",
    dependencies=[Depends(get_current_admin)],
)
def update_employee(
    employee_id: int,
    data: EmployeeUpdate,
    db: Session = Depends(get_db),
):
    return service.update_employee(db, employee_id, data)


@hr_router.delete(
    "/employee-management/employees/{employee_id}",
    response_model=SuccessResponse,
    summary="Deactivate / terminate an employee",
    dependencies=[Depends(get_current_admin)],
)
def deactivate_employee(employee_id: int, db: Session = Depends(get_db)):
    service.deactivate_employee(db, employee_id)
    return {"message": f"Employee {employee_id} has been deactivated successfully."}


@hr_router.get(
    "/employee-management/employees/{employee_id}/profile",
    response_model=EmployeeProfileResponse,
    summary="Get employee profile",
)
def get_employee_profile(
    employee_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.get_employee_profile(db, employee_id)


@hr_router.put(
    "/employee-management/employees/{employee_id}/profile",
    response_model=EmployeeProfileResponse,
    summary="Update employee profile",
)
def update_employee_profile(
    employee_id: int,
    data: EmployeeProfileUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.update_employee_profile(db, employee_id, data)


# ── ORGANIZATION STRUCTURE ────────────────────────────────────────────────────

@hr_router.get(
    "/employee-management/org-chart",
    response_model=dict,
    summary="Get organization chart",
)
def get_org_chart(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    organization_id: Optional[int] = Query(None, description="Filter by organization ID"),
):
    return service.get_org_chart(db, organization_id or 1)


@hr_router.put(
    "/employee-management/change-manager",
    response_model=EmployeeResponse,
    summary="Change employee manager",
    dependencies=[Depends(get_current_admin)],
)
def change_manager(
    data: ChangeManagerRequest,
    db: Session = Depends(get_db),
):
    return service.change_manager(db, data)

# ── EMPLOYEE LIFECYCLE ─────────────────────────────────────────────────────────

@hr_router.get(
    "/employee-management/lifecycle",
    response_model=list[EmployeeLifecycleResponse],
    summary="Get employee lifecycle events",
)
def get_employee_lifecycle(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
):
    if employee_id:
        return service.get_employee_lifecycle(db, employee_id)
    return []


@hr_router.post(
    "/employee-management/confirm",
    response_model=EmployeeLifecycleResponse,
    summary="Confirm employee probation",
    dependencies=[Depends(get_current_admin)],
)
def confirm_probation(
    data: ConfirmProbationRequest,
    db: Session = Depends(get_db),
):
    return service.confirm_probation(db, data)


@hr_router.post(
    "/employee-management/promote",
    response_model=EmployeeLifecycleResponse,
    summary="Promote employee",
    dependencies=[Depends(get_current_admin)],
)
def promote_employee(
    data: PromoteEmployeeRequest,
    db: Session = Depends(get_db),
):
    return service.promote_employee(db, data)


@hr_router.post(
    "/employee-management/transfer",
    response_model=EmployeeLifecycleResponse,
    summary="Transfer employee",
    dependencies=[Depends(get_current_admin)],
)
def transfer_employee(
    data: TransferEmployeeRequest,
    db: Session = Depends(get_db),
):
    return service.transfer_employee(db, data)


@hr_router.post(
    "/employee-management/resign",
    response_model=EmployeeLifecycleResponse,
    summary="Resign employee",
    dependencies=[Depends(get_current_admin)],
)
def resign_employee(
    data: ResignationRequest,
    db: Session = Depends(get_db),
):
    return service.resign_employee(db, data)


@hr_router.post(
    "/employee-management/exit",
    response_model=EmployeeLifecycleResponse,
    summary="Exit employee",
    dependencies=[Depends(get_current_admin)],
)
def exit_employee(
    data: ExitEmployeeRequest,
    db: Session = Depends(get_db),
):
    return service.exit_employee(db, data)

# ── REPORTS ─────────────────────────────────────────────────────────────────────

@hr_router.get(
    "/employee-management/reports",
    summary="Get employee reports",
)
def get_employee_reports(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    department_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    report_type: Optional[str] = Query(None),
):
    filters = {}
    if department_id: filters["department_id"] = department_id
    if status: filters["status"] = status
    if search: filters["search"] = search
    if report_type: filters["report_type"] = report_type
    return service.get_employee_reports(db, filters or None)


@hr_router.post(
    "/employee-management/export",
    response_model=dict,
    summary="Export employee reports",
)
def export_employee_reports(
    data: EmployeeExportRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.export_employee_reports(db, data)


# ════════════════════════════════════════════════════════════════════════════════
# DESIGNATION ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════════

@hr_router.get(
    "/designations",
    response_model=list[DesignationResponse],
    summary="List all designations",
    tags=["📋 Designations"],
)
def list_designations(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.get_designations(db)


@hr_router.post(
    "/designations",
    response_model=DesignationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new designation",
    tags=["📋 Designations"],
    dependencies=[Depends(get_current_admin)],
)
def create_designation(data: DesignationCreate, db: Session = Depends(get_db)):
    return service.create_designation(db, data)


@hr_router.get(
    "/designations/{designation_id}",
    response_model=DesignationResponse,
    summary="Get a single designation by ID",
    tags=["📋 Designations"],
)
def get_designation(
    designation_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.get_designation_by_id(db, designation_id)


@hr_router.put(
    "/designations/{designation_id}",
    response_model=DesignationResponse,
    summary="Update a designation",
    tags=["📋 Designations"],
    dependencies=[Depends(get_current_admin)],
)
def update_designation(
    designation_id: int,
    data: DesignationUpdate,
    db: Session = Depends(get_db),
):
    return service.update_designation(db, designation_id, data)


@hr_router.delete(
    "/designations/{designation_id}",
    response_model=SuccessResponse,
    summary="Delete a designation",
    tags=["📋 Designations"],
    dependencies=[Depends(get_current_admin)],
)
def delete_designation(designation_id: int, db: Session = Depends(get_db)):
    service.delete_designation(db, designation_id)
    return {"message": f"Designation {designation_id} deleted successfully."}

# ════════════════════════════════════════════════════════════════════════════════
# HR DOCUMENT ENDPOINTS
# GET    /hr/documents                    → list all (with filters)
# POST   /hr/documents/upload             → upload a new document (multipart)
# PUT    /hr/documents/{id}               → update document metadata
# PATCH  /hr/documents/{id}/status        → approve / reject / expire
# DELETE /hr/documents/{id}               → soft-delete
# ════════════════════════════════════════════════════════════════════════════════

# Directory where uploaded files are stored. In production replace with S3 or
# a proper media volume; for now we write to a local uploads folder.
_DOCUMENT_UPLOAD_DIR = os.environ.get("HR_DOCUMENT_UPLOAD_DIR", "uploads/hr_documents")


@hr_router.get(
    "/documents",
    response_model=list[HrDocumentResponse],
    summary="List HR documents",
    description=(
        "Returns all non-deleted HR documents. "
        "Supports optional filtering by `category`, `status`, `employee_id`, and `search`."
    ),
    tags=["📄 HR Documents"],
)
def list_hr_documents(
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
    category:    Optional[str] = Query(None, description="Filter by category (company, employee, policy, contract, other)"),
    doc_status:  Optional[str] = Query(None, alias="status", description="Filter by status (pending, approved, rejected, expired)"),
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
    search:      Optional[str] = Query(None, description="Search by title or document type"),
):
    return service.get_hr_documents(db, category=category, status=doc_status, employee_id=employee_id, search=search)


@hr_router.post(
    "/documents/upload",
    response_model=HrDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new HR document",
    description=(
        "Accepts `multipart/form-data`. "
        "Required fields: `title`, `category`, `file`. "
        "Optional: `description`, `document_type`, `employee_id`, `expiry_date`, `tags`."
    ),
    tags=["📄 HR Documents"],
)
async def upload_hr_document(
    db:            Session     = Depends(get_db),
    current_user:  object      = Depends(get_current_user),
    file:          UploadFile  = File(..., description="The document file to upload"),
    title:         str         = Form(..., min_length=1, max_length=255),
    category:      str         = Form("other"),
    description:   Optional[str] = Form(None),
    document_type: Optional[str] = Form(None),
    employee_id:   Optional[int] = Form(None),
    expiry_date:   Optional[str] = Form(None),   # ISO date string YYYY-MM-DD
    tags:          Optional[str] = Form(None),   # JSON-encoded list, e.g. '["policy","2025"]'
):
    # ── Save file to disk ────────────────────────────────────────────────────
    os.makedirs(_DOCUMENT_UPLOAD_DIR, exist_ok=True)
    ext       = os.path.splitext(file.filename or "")[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path   = os.path.join(_DOCUMENT_UPLOAD_DIR, unique_name)

    contents = await file.read()
    with open(file_path, "wb") as fh:
        fh.write(contents)

    # ── Parse optional fields ────────────────────────────────────────────────
    import json as _json
    from datetime import date as _date

    parsed_expiry = None
    if expiry_date:
        try:
            parsed_expiry = _date.fromisoformat(expiry_date)
        except ValueError:
            parsed_expiry = None

    parsed_tags = []
    if tags:
        try:
            parsed_tags = _json.loads(tags)
        except (_json.JSONDecodeError, TypeError):
            parsed_tags = [t.strip() for t in tags.split(",") if t.strip()]

    return service.upload_hr_document(
        db=db,
        title=title,
        category=category,
        file_path=file_path,
        file_name=file.filename or unique_name,
        file_size=len(contents),
        mime_type=file.content_type,
        description=description,
        document_type=document_type,
        employee_id=employee_id,
        uploaded_by=current_user.id,
        expiry_date=parsed_expiry,
        tags=parsed_tags,
    )


@hr_router.put(
    "/documents/{document_id}",
    response_model=HrDocumentResponse,
    summary="Update HR document metadata",
    tags=["📄 HR Documents"],
    dependencies=[Depends(get_current_user)],
)
def update_hr_document(
    document_id: int,
    data: HrDocumentUpdate,
    db: Session = Depends(get_db),
):
    return service.update_hr_document(db, document_id, data)


@hr_router.patch(
    "/documents/{document_id}/status",
    response_model=HrDocumentResponse,
    summary="Update HR document status (approve / reject / expire)",
    description="Allowed status values: `pending`, `approved`, `rejected`, `expired`.",
    tags=["📄 HR Documents"],
    dependencies=[Depends(get_current_admin)],   # only admins can approve/reject
)
def update_hr_document_status(
    document_id: int,
    data: HrDocumentStatusUpdate,
    db: Session = Depends(get_db),
):
    return service.update_hr_document_status(db, document_id, data)


@hr_router.delete(
    "/documents/{document_id}",
    response_model=SuccessResponse,
    summary="Soft-delete an HR document",
    tags=["📄 HR Documents"],
    dependencies=[Depends(get_current_admin)],
)
def delete_hr_document(document_id: int, db: Session = Depends(get_db)):
    service.delete_hr_document(db, document_id)
    return {"message": f"Document {document_id} deleted successfully."}
