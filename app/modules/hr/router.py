from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user, get_current_admin

from app.modules.hr import service
from app.modules.hr.models import EmployeeStatus
from app.modules.hr.schemas import (
    DepartmentCreate, DepartmentUpdate, DepartmentResponse,
    EmployeeCreate, EmployeeUpdate, EmployeeResponse, EmployeeListResponse,
    LoginRequest, TokenResponse, SuccessResponse,
    AttendanceCreate, AttendanceResponse,
    LeaveRequestCreate, LeaveRequestUpdate, LeaveRequestResponse,
    AssetCreate, AssetResponse,
    CompensationCreate, CompensationResponse,
    ComplianceRecordCreate, ComplianceRecordResponse,
    EngagementSurveyCreate, EngagementSurveyResponse,
    EssRequestCreate, EssRequestResponse,
    LearningCourseCreate, LearningCourseResponse,
    OnboardingRecordCreate, OnboardingRecordUpdate, OnboardingRecordResponse,
    OnboardingTaskCreate, OnboardingTaskUpdate, OnboardingTaskResponse,
    OnboardingActivityResponse, OnboardingDashboardResponse,
    PerformanceReviewCreate, PerformanceReviewResponse,
    RecruitmentCandidateCreate, RecruitmentCandidateUpdate,
    RecruitmentCandidateResponse,
    TravelRequestCreate, TravelRequestResponse,
    WorkforcePlanCreate, WorkforcePlanResponse,
    WorkforceSummaryResponse,
)

auth_router = APIRouter(prefix="/auth", tags=["🔐 Authentication"])
hr_router   = APIRouter(prefix="/hr",   tags=["👥 HR Module"])

# ════════════════════════════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@auth_router.post("/login", response_model=TokenResponse, summary="Login and get access token")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    return service.login_employee(db, data)


@auth_router.get("/me", summary="Get current logged-in user")
def get_me(current_user = Depends(get_current_user)):
    return current_user


# ════════════════════════════════════════════════════════════════════════════
# DEPARTMENT ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@hr_router.post("/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED, summary="Create a new department", dependencies=[Depends(get_current_admin)])
def create_department(data: DepartmentCreate, db: Session = Depends(get_db)):
    return service.create_department(db, data)


@hr_router.get("/departments", response_model=list[DepartmentResponse], summary="List all departments")
def list_departments(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_all_departments(db)


@hr_router.get("/departments/{dept_id}", response_model=DepartmentResponse, summary="Get a single department by ID")
def get_department(dept_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_department_by_id(db, dept_id)


@hr_router.put("/departments/{dept_id}", response_model=DepartmentResponse, summary="Update a department", dependencies=[Depends(get_current_admin)])
def update_department(dept_id: int, data: DepartmentUpdate, db: Session = Depends(get_db)):
    return service.update_department(db, dept_id, data)


@hr_router.delete("/departments/{dept_id}", response_model=SuccessResponse, summary="Deactivate a department", dependencies=[Depends(get_current_admin)])
def delete_department(dept_id: int, db: Session = Depends(get_db)):
    service.delete_department(db, dept_id)
    return {"message": f"Department {dept_id} has been deactivated successfully."}

# ════════════════════════════════════════════════════════════════════════════
# EMPLOYEE ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@hr_router.get("/employees/me", response_model=EmployeeResponse, summary="Get my own profile")
def get_my_profile(current_user=Depends(get_current_user)):
    return current_user


@hr_router.post("/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED, summary="Onboard a new employee", dependencies=[Depends(get_current_admin)])
def create_employee(data: EmployeeCreate, db: Session = Depends(get_db)):
    return service.create_employee(db, data)


@hr_router.get("/employees", response_model=EmployeeListResponse, summary="List employees with search and filters")
def list_employees(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    page:          int                     = Query(1,    ge=1),
    per_page:      int                     = Query(20,   ge=1,   le=100),
    search:        Optional[str]           = Query(None),
    department_id: Optional[int]           = Query(None),
    status:        Optional[EmployeeStatus]= Query(None),
):
    return service.get_all_employees(db, page, per_page, search, department_id, status)


@hr_router.get("/employees/{employee_id}", response_model=EmployeeResponse, summary="Get a single employee by ID")
def get_employee(employee_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_employee_by_id(db, employee_id)


@hr_router.put("/employees/{employee_id}", response_model=EmployeeResponse, summary="Update employee details", dependencies=[Depends(get_current_admin)])
def update_employee(employee_id: int, data: EmployeeUpdate, db: Session = Depends(get_db)):
    return service.update_employee(db, employee_id, data)


@hr_router.delete("/employees/{employee_id}", response_model=SuccessResponse, summary="Deactivate / terminate an employee", dependencies=[Depends(get_current_admin)])
def deactivate_employee(employee_id: int, db: Session = Depends(get_db)):
    service.deactivate_employee(db, employee_id)
    return {"message": f"Employee {employee_id} has been deactivated successfully."}

# ════════════════════════════════════════════════════════════════════════════
# DASHBOARD STATS
# ════════════════════════════════════════════════════════════════════════════

@hr_router.get("/dashboard/stats", summary="HR Dashboard statistics")
def dashboard_stats(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_hr_dashboard_stats(db)

# ════════════════════════════════════════════════════════════════════════════
# SUBMODULES (Attendance, Leave, Assets, Onboarding, etc.)
# ════════════════════════════════════════════════════════════════════════════

@hr_router.post("/attendance", response_model=AttendanceResponse)
def create_attendance(data: AttendanceCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.create_attendance_record(db, data)

@hr_router.get("/attendance", response_model=list[AttendanceResponse])
def list_attendance(db: Session = Depends(get_db), _=Depends(get_current_user), employee_id: Optional[int] = Query(None)):
    return service.get_attendance_records(db, employee_id)

@hr_router.post("/leaves", response_model=LeaveRequestResponse)
def create_leave_request(data: LeaveRequestCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.create_leave_request(db, data)

@hr_router.get("/leaves", response_model=list[LeaveRequestResponse])
def list_leave_requests(db: Session = Depends(get_db), _=Depends(get_current_user), employee_id: Optional[int] = Query(None)):
    return service.get_leave_requests(db, employee_id)

@hr_router.put("/leaves/{leave_id}/review", response_model=LeaveRequestResponse, dependencies=[Depends(get_current_admin)])
def review_leave(leave_id: int, data: LeaveRequestUpdate, db: Session = Depends(get_db)):
    return service.review_leave_request(db, leave_id, data)

@hr_router.post("/assets", response_model=AssetResponse, dependencies=[Depends(get_current_admin)])
def create_asset(data: AssetCreate, db: Session = Depends(get_db)):
    return service.create_asset(db, data)

@hr_router.get("/assets", response_model=list[AssetResponse])
def list_assets(db: Session = Depends(get_db), _=Depends(get_current_user), employee_id: Optional[int] = Query(None)):
    return service.get_assets(db, employee_id)

@hr_router.post("/compensations", response_model=CompensationResponse, dependencies=[Depends(get_current_admin)])
def create_compensation(data: CompensationCreate, db: Session = Depends(get_db)):
    return service.create_compensation_item(db, data)

@hr_router.get("/compensations", response_model=list[CompensationResponse])
def list_compensations(db: Session = Depends(get_db), _=Depends(get_current_user), employee_id: Optional[int] = Query(None)):
    return service.get_compensation_items(db, employee_id)

@hr_router.post("/compliance", response_model=ComplianceRecordResponse, dependencies=[Depends(get_current_admin)])
def create_compliance_record(data: ComplianceRecordCreate, db: Session = Depends(get_db)):
    return service.create_compliance_record(db, data)

@hr_router.get("/compliance", response_model=list[ComplianceRecordResponse])
def list_compliance_records(db: Session = Depends(get_db), _=Depends(get_current_user), employee_id: Optional[int] = Query(None)):
    return service.get_compliance_records(db, employee_id)

@hr_router.post("/engagement", response_model=EngagementSurveyResponse)
def create_engagement_survey(data: EngagementSurveyCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.create_engagement_survey(db, data)

@hr_router.get("/engagement", response_model=list[EngagementSurveyResponse])
def list_engagement_surveys(db: Session = Depends(get_db), _=Depends(get_current_user), employee_id: Optional[int] = Query(None)):
    return service.get_engagement_surveys(db, employee_id)

@hr_router.post("/ess", response_model=EssRequestResponse)
def create_ess_request(data: EssRequestCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.create_ess_request(db, data)

@hr_router.get("/ess", response_model=list[EssRequestResponse])
def list_ess_requests(db: Session = Depends(get_db), _=Depends(get_current_user), employee_id: Optional[int] = Query(None)):
    return service.get_ess_requests(db, employee_id)

@hr_router.post("/learning", response_model=LearningCourseResponse)
def create_learning_course(data: LearningCourseCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.create_learning_course(db, data)

@hr_router.get("/learning", response_model=list[LearningCourseResponse])
def list_learning_courses(db: Session = Depends(get_db), _=Depends(get_current_user), employee_id: Optional[int] = Query(None)):
    return service.get_learning_courses(db, employee_id)

@hr_router.post("/onboarding/records", response_model=OnboardingRecordResponse, status_code=status.HTTP_201_CREATED)
def create_onboarding_record(data: OnboardingRecordCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.create_onboarding_record(db, data)

@hr_router.get("/onboarding/records", response_model=list[OnboardingRecordResponse])
def list_onboarding_records(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_onboarding_records(db)

@hr_router.get("/onboarding/records/{record_id}", response_model=OnboardingRecordResponse)
def get_onboarding_record(record_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_onboarding_record_by_id(db, record_id)

@hr_router.put("/onboarding/records/{record_id}", response_model=OnboardingRecordResponse)
def update_onboarding_record(record_id: int, data: OnboardingRecordUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.update_onboarding_record(db, record_id, data)

@hr_router.delete("/onboarding/records/{record_id}", response_model=SuccessResponse)
def delete_onboarding_record(record_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    service.delete_onboarding_record(db, record_id)
    return {"message": f"Onboarding record {record_id} has been deleted successfully."}

@hr_router.get("/onboarding/dashboard", response_model=OnboardingDashboardResponse)
def onboarding_dashboard(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_onboarding_dashboard(db)

@hr_router.get("/onboarding/activities", response_model=list[OnboardingActivityResponse])
def list_onboarding_activities(db: Session = Depends(get_db), _=Depends(get_current_user), limit: int = Query(50, ge=1, le=200)):
    return service.get_onboarding_activities(db, limit)

@hr_router.post("/onboarding", response_model=OnboardingTaskResponse, status_code=status.HTTP_201_CREATED)
def create_onboarding_task(data: OnboardingTaskCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.create_onboarding_task(db, data)

@hr_router.get("/onboarding", response_model=list[OnboardingTaskResponse])
def list_onboarding_tasks(db: Session = Depends(get_db), _=Depends(get_current_user), employee_id: Optional[int] = Query(None)):
    return service.get_onboarding_tasks(db, employee_id)

@hr_router.put("/onboarding/{task_id}", response_model=OnboardingTaskResponse)
def update_onboarding_task(task_id: int, data: OnboardingTaskUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.update_onboarding_task(db, task_id, data)

@hr_router.delete("/onboarding/{task_id}", response_model=SuccessResponse)
def delete_onboarding_task(task_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    service.delete_onboarding_task(db, task_id)
    return {"message": f"Onboarding task {task_id} has been deleted successfully."}

@hr_router.post("/performance", response_model=PerformanceReviewResponse)
def create_performance_review(data: PerformanceReviewCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.create_performance_review(db, data)

@hr_router.get("/performance", response_model=list[PerformanceReviewResponse])
def list_performance_reviews(db: Session = Depends(get_db), _=Depends(get_current_user), employee_id: Optional[int] = Query(None)):
    return service.get_performance_reviews(db, employee_id)

@hr_router.post("/recruitment", response_model=RecruitmentCandidateResponse, dependencies=[Depends(get_current_admin)])
def create_recruitment_candidate(data: RecruitmentCandidateCreate, db: Session = Depends(get_db)):
    return service.create_recruitment_candidate(db, data)

@hr_router.get("/recruitment", response_model=list[RecruitmentCandidateResponse], dependencies=[Depends(get_current_admin)])
def list_recruitment_candidates(db: Session = Depends(get_db)):
    return service.get_recruitment_candidates(db)

@hr_router.put("/recruitment/{candidate_id}", response_model=RecruitmentCandidateResponse, dependencies=[Depends(get_current_admin)])
def update_recruitment_candidate(candidate_id: int, data: RecruitmentCandidateUpdate, db: Session = Depends(get_db)):
    return service.update_recruitment_candidate(db, candidate_id, data)

@hr_router.post("/travel", response_model=TravelRequestResponse)
def create_travel_request(data: TravelRequestCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.create_travel_request(db, data)

@hr_router.get("/travel", response_model=list[TravelRequestResponse])
def list_travel_requests(db: Session = Depends(get_db), _=Depends(get_current_user), employee_id: Optional[int] = Query(None)):
    return service.get_travel_requests(db, employee_id)

@hr_router.post("/workforce-planning", response_model=WorkforcePlanResponse, dependencies=[Depends(get_current_admin)])
def create_workforce_plan(data: WorkforcePlanCreate, db: Session = Depends(get_db)):
    return service.create_workforce_plan(db, data)

@hr_router.get("/workforce-planning", response_model=list[WorkforcePlanResponse], dependencies=[Depends(get_current_admin)])
def list_workforce_plans(db: Session = Depends(get_db)):
    return service.get_workforce_plans(db)

@hr_router.get("/workforce/summary", response_model=WorkforceSummaryResponse)
def workforce_summary(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_workforce_summary(db)