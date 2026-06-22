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

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
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
    OnboardingActivityResponse, OnboardingDashboardResponse,
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
):
    return service.get_leave_requests(db, current_user.organization_id, employee_id, status, leave_type, start_date, end_date)


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


@hr_router.post(
    "/onboarding/records", 
    response_model=OnboardingRecordResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Create an onboarding record"
)
def create_onboarding_record(data: OnboardingRecordCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.create_onboarding_record(db, data)


@hr_router.get(
    "/onboarding/records", 
    response_model=list[OnboardingRecordResponse],
    summary="List onboarding records"
)
def list_onboarding_records(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_onboarding_records(db)


@hr_router.get(
    "/onboarding/records/{record_id}", 
    response_model=OnboardingRecordResponse,
    summary="Get an onboarding record by ID"
)
def get_onboarding_record(record_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_onboarding_record_by_id(db, record_id)


@hr_router.put(
    "/onboarding/records/{record_id}", 
    response_model=OnboardingRecordResponse,
    summary="Update an onboarding record"
)
def update_onboarding_record(record_id: int, data: OnboardingRecordUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.update_onboarding_record(db, record_id, data)


@hr_router.delete(
    "/onboarding/records/{record_id}", 
    response_model=SuccessResponse,
    summary="Delete an onboarding record"
)
def delete_onboarding_record(record_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    service.delete_onboarding_record(db, record_id)
    return {"message": f"Onboarding record {record_id} has been deleted successfully."}


@hr_router.get(
    "/onboarding/dashboard", 
    response_model=OnboardingDashboardResponse,
    summary="Get onboarding dashboard overview"
)
def onboarding_dashboard(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_onboarding_dashboard(db)


@hr_router.get(
    "/onboarding/activities", 
    response_model=list[OnboardingActivityResponse],
    summary="List onboarding activities"
)
def list_onboarding_activities(db: Session = Depends(get_db), _=Depends(get_current_user), limit: int = Query(50, ge=1, le=200)):
    return service.get_onboarding_activities(db, limit)


@hr_router.post(
    "/onboarding",
    response_model=OnboardingTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an onboarding task",
)
def create_onboarding_task(data: OnboardingTaskCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.create_onboarding_task(db, data)


@hr_router.get(
    "/onboarding",
    response_model=list[OnboardingTaskResponse],
    summary="List onboarding tasks",
)
def list_onboarding_tasks(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
):
    return service.get_onboarding_tasks(db, employee_id)


@hr_router.put(
    "/onboarding/{task_id}", 
    response_model=OnboardingTaskResponse,
    summary="Update an onboarding task"
)
def update_onboarding_task(task_id: int, data: OnboardingTaskUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.update_onboarding_task(db, task_id, data)


@hr_router.delete(
    "/onboarding/{task_id}", 
    response_model=SuccessResponse,
    summary="Delete an onboarding task"
)
def delete_onboarding_task(task_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    service.delete_onboarding_task(db, task_id)
    return {"message": f"Onboarding task {task_id} has been deleted successfully."}


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
