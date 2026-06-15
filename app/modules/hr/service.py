"""
modules/hr/service.py
---------------------
Business logic layer. This is WHERE the actual work happens.

Rule of thumb:
  - Router  = "what URL does what"     (thin layer, just calls service)
  - Service = "how does it actually work" (all the real logic lives here)
  - Model   = "what does the data look like in the database"

Keeping logic in the service layer means:
  - You can test it without HTTP
  - You can reuse it from multiple routers
  - Your router file stays clean and readable
"""

from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.hr.models import (
    Employee, Department, EmployeeStatus, UserRole,
    AttendanceRecord, LeaveRequest, Asset, CompensationItem,
    ComplianceRecord, EngagementSurvey, EssRequest,
    LearningCourse, OnboardingTask, PerformanceReview,
    RecruitmentCandidate, TravelRequest, WorkforcePlan,
    RequestStatus,
)
from app.modules.hr.schemas import (
    EmployeeCreate, EmployeeUpdate,
    DepartmentCreate, DepartmentUpdate,
    LoginRequest,
    AttendanceCreate, LeaveRequestCreate, LeaveRequestUpdate,
    AssetCreate, CompensationCreate,
    ComplianceRecordCreate, EngagementSurveyCreate,
    EssRequestCreate, LearningCourseCreate,
    OnboardingTaskCreate, PerformanceReviewCreate,
    RecruitmentCandidateCreate, RecruitmentCandidateUpdate,
    TravelRequestCreate, WorkforcePlanCreate,
)
from app.core.security import hash_password, verify_password, create_access_token
from app.core.exceptions import (
    NotFoundException, AlreadyExistsException,
    UnauthorizedException, BadRequestException
)


# ════════════════════════════════════════════════════════════════════════════
# HELPER — Auto-generate employee code
# ════════════════════════════════════════════════════════════════════════════

def _generate_employee_code(db: Session) -> str:
    """
    Auto-generates the next employee code like ZK-0001, ZK-0002, etc.
    Finds the highest existing ID and increments by 1.
    """
    last_employee = db.query(Employee).order_by(Employee.id.desc()).first()
    next_number = (last_employee.id + 1) if last_employee else 1
    return f"ZK-{next_number:04d}"   # ZK-0001, ZK-0042, ZK-1000


# ════════════════════════════════════════════════════════════════════════════
# AUTH SERVICE
# ════════════════════════════════════════════════════════════════════════════

def login_employee(db: Session, data: LoginRequest) -> dict:
    """
    Verifies login credentials and returns a JWT token.

    Steps:
      1. Find employee by email
      2. Check password matches
      3. Check account is active
      4. Create and return JWT token
    """
    # Step 1: Find by email
    employee = db.query(Employee).filter(Employee.email == data.email).first()
    if not employee:
        # Don't say "email not found" — that leaks info. Say credentials invalid.
        raise UnauthorizedException("Invalid email or password.")

    # Step 2: Verify password
    if not verify_password(data.password, employee.hashed_password):
        raise UnauthorizedException("Invalid email or password.")

    # Step 3: Check account is active
    if not employee.is_active:
        raise UnauthorizedException("Your account has been deactivated. Contact your HR admin.")

    # Step 4: Create token with user info embedded
    token = create_access_token(data={
        "sub":  employee.email,
        "role": employee.role.value,
        "id":   employee.id,
    })

    return {"access_token": token, "token_type": "bearer", "employee": employee}


# ════════════════════════════════════════════════════════════════════════════
# DEPARTMENT SERVICE
# ════════════════════════════════════════════════════════════════════════════

def create_department(db: Session, data: DepartmentCreate) -> Department:
    """Creates a new department after checking for duplicates."""
    # Check if name already exists
    existing = db.query(Department).filter(Department.name == data.name).first()
    if existing:
        raise AlreadyExistsException("Department", "name")

    # Check if code already exists
    existing_code = db.query(Department).filter(Department.code == data.code).first()
    if existing_code:
        raise AlreadyExistsException("Department", "code")

    dept = Department(**data.model_dump())
    db.add(dept)
    db.commit()
    db.refresh(dept)   # refresh loads the auto-generated id and timestamps
    return dept


def get_all_departments(db: Session) -> List[Department]:
    """Returns all active departments."""
    return db.query(Department).filter(Department.is_active == True).all()


def get_department_by_id(db: Session, dept_id: int) -> Department:
    """Returns one department or raises 404."""
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise NotFoundException("Department", dept_id)
    return dept


def update_department(db: Session, dept_id: int, data: DepartmentUpdate) -> Department:
    """Updates only the fields that were provided (partial update)."""
    dept = get_department_by_id(db, dept_id)

    # model_dump(exclude_unset=True) = only fields the user actually sent
    # This prevents accidentally overwriting fields with None
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dept, field, value)

    db.commit()
    db.refresh(dept)
    return dept


def delete_department(db: Session, dept_id: int) -> None:
    """Soft-deletes a department (sets is_active=False instead of real delete)."""
    dept = get_department_by_id(db, dept_id)

    # Check if department has active employees
    active_count = db.query(Employee).filter(
        Employee.department_id == dept_id,
        Employee.status == EmployeeStatus.ACTIVE
    ).count()

    if active_count > 0:
        raise BadRequestException(
            f"Cannot delete department '{dept.name}'. "
            f"It still has {active_count} active employee(s). "
            f"Please reassign them first."
        )

    dept.is_active = False
    db.commit()


# ════════════════════════════════════════════════════════════════════════════
# EMPLOYEE SERVICE
# ════════════════════════════════════════════════════════════════════════════

def create_employee(db: Session, data: EmployeeCreate) -> Employee:
    """
    Onboards a new employee.

    Steps:
      1. Check email not already in use
      2. Validate department exists (if provided)
      3. Hash the password
      4. Auto-generate employee code
      5. Save to database
    """
    # Step 1: Check email uniqueness
    existing = db.query(Employee).filter(Employee.email == data.email).first()
    if existing:
        raise AlreadyExistsException("Employee", "email")

    # Step 2: Validate department
    if data.department_id:
        get_department_by_id(db, data.department_id)  # raises 404 if not found

    # Step 3 & 4: Prepare employee object
    employee_data = data.model_dump(exclude={"password"})  # remove plain password
    employee = Employee(
        **employee_data,
        hashed_password=hash_password(data.password),
        employee_code=_generate_employee_code(db),
    )

    # Step 5: Save
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


def get_all_employees(
    db: Session,
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    department_id: Optional[int] = None,
    status: Optional[EmployeeStatus] = None,
) -> dict:
    """
    Returns a paginated list of employees with optional filters.

    Parameters:
        page          = which page (starts at 1)
        per_page      = how many per page (max 100)
        search        = search by name or email
        department_id = filter by department
        status        = filter by employment status
    """
    per_page = min(per_page, 100)  # cap at 100 to prevent huge queries
    query = db.query(Employee)

    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Employee.first_name.ilike(search_term)) |
            (Employee.last_name.ilike(search_term))  |
            (Employee.email.ilike(search_term))      |
            (Employee.employee_code.ilike(search_term))
        )

    if department_id:
        query = query.filter(Employee.department_id == department_id)

    if status:
        query = query.filter(Employee.status == status)

    # Get total count BEFORE pagination (for frontend to know total pages)
    total = query.count()

    # Apply pagination
    employees = query.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "items":    employees,
    }


def get_employee_by_id(db: Session, employee_id: int) -> Employee:
    """Returns one employee or raises 404."""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise NotFoundException("Employee", employee_id)
    return employee


def update_employee(db: Session, employee_id: int, data: EmployeeUpdate) -> Employee:
    """Partially updates an employee record."""
    employee = get_employee_by_id(db, employee_id)

    # Validate new department if provided
    if data.department_id:
        get_department_by_id(db, data.department_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)

    db.commit()
    db.refresh(employee)
    return employee


def deactivate_employee(db: Session, employee_id: int) -> Employee:
    """
    Deactivates an employee (soft delete / terminate).
    Sets status to TERMINATED and is_active to False.
    We NEVER hard-delete employees — we need the history.
    """
    employee = get_employee_by_id(db, employee_id)
    employee.is_active = False
    employee.status    = EmployeeStatus.TERMINATED
    db.commit()
    db.refresh(employee)
    return employee


def get_hr_dashboard_stats(db: Session) -> dict:
    """
    Returns summary statistics for the HR dashboard.
    Called by the dashboard page to show quick numbers.
    """
    from datetime import date
    from sqlalchemy import func, extract

    total       = db.query(Employee).count()
    active      = db.query(Employee).filter(Employee.status == EmployeeStatus.ACTIVE).count()
    on_leave    = db.query(Employee).filter(Employee.status == EmployeeStatus.ON_LEAVE).count()
    terminated  = db.query(Employee).filter(Employee.status == EmployeeStatus.TERMINATED).count()

    # New joiners this month
    today = date.today()
    new_this_month = db.query(Employee).filter(
        extract("month", Employee.date_of_joining) == today.month,
        extract("year",  Employee.date_of_joining) == today.year,
    ).count()

    dept_count = db.query(Department).filter(Department.is_active == True).count()

    return {
        "total_employees":    total,
        "active_employees":   active,
        "on_leave":           on_leave,
        "terminated":         terminated,
        "new_joiners_month":  new_this_month,
        "total_departments":  dept_count,
    }


# ════════════════════════════════════════════════════════════════════════════
# HR SUBMODULE SERVICES
# ════════════════════════════════════════════════════════════════════════════


def create_attendance_record(db: Session, data: AttendanceCreate) -> AttendanceRecord:
    get_employee_by_id(db, data.employee_id)
    record = AttendanceRecord(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_attendance_records(db: Session, employee_id: Optional[int] = None) -> list[AttendanceRecord]:
    query = db.query(AttendanceRecord)
    if employee_id:
        query = query.filter(AttendanceRecord.employee_id == employee_id)
    return query.order_by(AttendanceRecord.date.desc()).all()


def create_leave_request(db: Session, data: LeaveRequestCreate) -> LeaveRequest:
    get_employee_by_id(db, data.employee_id)
    leave = LeaveRequest(**data.model_dump())
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return leave


def review_leave_request(db: Session, leave_id: int, data: LeaveRequestUpdate) -> LeaveRequest:
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        raise NotFoundException("Leave request", leave_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(leave, field, value)
    if data.status == RequestStatus.APPROVED:
        leave.reviewed_at = func.now()
    db.commit()
    db.refresh(leave)
    return leave


def get_leave_requests(db: Session, employee_id: Optional[int] = None) -> list[LeaveRequest]:
    query = db.query(LeaveRequest)
    if employee_id:
        query = query.filter(LeaveRequest.employee_id == employee_id)
    return query.order_by(LeaveRequest.created_at.desc()).all()


def create_asset(db: Session, data: AssetCreate) -> Asset:
    if data.employee_id is not None:
        get_employee_by_id(db, data.employee_id)
    asset = Asset(**data.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def get_assets(db: Session, employee_id: Optional[int] = None) -> list[Asset]:
    query = db.query(Asset)
    if employee_id:
        query = query.filter(Asset.employee_id == employee_id)
    return query.order_by(Asset.created_at.desc()).all()


def create_compensation_item(db: Session, data: CompensationCreate) -> CompensationItem:
    get_employee_by_id(db, data.employee_id)
    item = CompensationItem(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_compensation_items(db: Session, employee_id: Optional[int] = None) -> list[CompensationItem]:
    query = db.query(CompensationItem)
    if employee_id:
        query = query.filter(CompensationItem.employee_id == employee_id)
    return query.order_by(CompensationItem.created_at.desc()).all()


def create_compliance_record(db: Session, data: ComplianceRecordCreate) -> ComplianceRecord:
    get_employee_by_id(db, data.employee_id)
    record = ComplianceRecord(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_compliance_records(db: Session, employee_id: Optional[int] = None) -> list[ComplianceRecord]:
    query = db.query(ComplianceRecord)
    if employee_id:
        query = query.filter(ComplianceRecord.employee_id == employee_id)
    return query.order_by(ComplianceRecord.created_at.desc()).all()


def create_engagement_survey(db: Session, data: EngagementSurveyCreate) -> EngagementSurvey:
    get_employee_by_id(db, data.employee_id)
    survey = EngagementSurvey(**data.model_dump())
    db.add(survey)
    db.commit()
    db.refresh(survey)
    return survey


def get_engagement_surveys(db: Session, employee_id: Optional[int] = None) -> list[EngagementSurvey]:
    query = db.query(EngagementSurvey)
    if employee_id:
        query = query.filter(EngagementSurvey.employee_id == employee_id)
    return query.order_by(EngagementSurvey.created_at.desc()).all()


def create_ess_request(db: Session, data: EssRequestCreate) -> EssRequest:
    get_employee_by_id(db, data.employee_id)
    request = EssRequest(**data.model_dump())
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def get_ess_requests(db: Session, employee_id: Optional[int] = None) -> list[EssRequest]:
    query = db.query(EssRequest)
    if employee_id:
        query = query.filter(EssRequest.employee_id == employee_id)
    return query.order_by(EssRequest.created_at.desc()).all()


def create_learning_course(db: Session, data: LearningCourseCreate) -> LearningCourse:
    get_employee_by_id(db, data.employee_id)
    course = LearningCourse(**data.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def get_learning_courses(db: Session, employee_id: Optional[int] = None) -> list[LearningCourse]:
    query = db.query(LearningCourse)
    if employee_id:
        query = query.filter(LearningCourse.employee_id == employee_id)
    return query.order_by(LearningCourse.enrolled_at.desc()).all()


def create_onboarding_task(db: Session, data: OnboardingTaskCreate) -> OnboardingTask:
    get_employee_by_id(db, data.employee_id)
    task = OnboardingTask(**data.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_onboarding_tasks(db: Session, employee_id: Optional[int] = None) -> list[OnboardingTask]:
    query = db.query(OnboardingTask)
    if employee_id:
        query = query.filter(OnboardingTask.employee_id == employee_id)
    return query.order_by(OnboardingTask.created_at.desc()).all()


def create_performance_review(db: Session, data: PerformanceReviewCreate) -> PerformanceReview:
    get_employee_by_id(db, data.employee_id)
    if data.reviewer_id:
        get_employee_by_id(db, data.reviewer_id)
    review = PerformanceReview(**data.model_dump())
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def get_performance_reviews(db: Session, employee_id: Optional[int] = None) -> list[PerformanceReview]:
    query = db.query(PerformanceReview)
    if employee_id:
        query = query.filter(PerformanceReview.employee_id == employee_id)
    return query.order_by(PerformanceReview.created_at.desc()).all()


def create_recruitment_candidate(db: Session, data: RecruitmentCandidateCreate) -> RecruitmentCandidate:
    existing = db.query(RecruitmentCandidate).filter(RecruitmentCandidate.email == data.email).first()
    if existing:
        raise AlreadyExistsException("Candidate", "email")
    candidate = RecruitmentCandidate(**data.model_dump())
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def update_recruitment_candidate(db: Session, candidate_id: int, data: RecruitmentCandidateUpdate) -> RecruitmentCandidate:
    candidate = db.query(RecruitmentCandidate).filter(RecruitmentCandidate.id == candidate_id).first()
    if not candidate:
        raise NotFoundException("Candidate", candidate_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(candidate, field, value)
    db.commit()
    db.refresh(candidate)
    return candidate


def get_recruitment_candidates(db: Session) -> list[RecruitmentCandidate]:
    return db.query(RecruitmentCandidate).order_by(RecruitmentCandidate.applied_at.desc()).all()


def create_travel_request(db: Session, data: TravelRequestCreate) -> TravelRequest:
    get_employee_by_id(db, data.employee_id)
    request = TravelRequest(**data.model_dump())
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def get_travel_requests(db: Session, employee_id: Optional[int] = None) -> list[TravelRequest]:
    query = db.query(TravelRequest)
    if employee_id:
        query = query.filter(TravelRequest.employee_id == employee_id)
    return query.order_by(TravelRequest.created_at.desc()).all()


def create_workforce_plan(db: Session, data: WorkforcePlanCreate) -> WorkforcePlan:
    if data.department_id:
        get_department_by_id(db, data.department_id)
    plan = WorkforcePlan(**data.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def get_workforce_plans(db: Session) -> list[WorkforcePlan]:
    return db.query(WorkforcePlan).order_by(WorkforcePlan.created_at.desc()).all()


def get_workforce_summary(db: Session) -> dict:
    open_leave = db.query(LeaveRequest).filter(LeaveRequest.status == RequestStatus.PENDING).count()
    open_travel = db.query(TravelRequest).filter(TravelRequest.status == RequestStatus.PENDING).count()
    open_ess = db.query(EssRequest).filter(EssRequest.status == RequestStatus.PENDING).count()

    return {
        "total_employees": db.query(Employee).count(),
        "active_employees": db.query(Employee).filter(Employee.status == EmployeeStatus.ACTIVE).count(),
        "departments": db.query(Department).filter(Department.is_active == True).count(),
        "open_leave_requests": open_leave,
        "open_travel_requests": open_travel,
        "open_ess_requests": open_ess,
    }
