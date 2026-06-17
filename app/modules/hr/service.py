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

from datetime import datetime
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.hr.models import (
    Employee, Department, EmployeeStatus, UserRole,
    AttendanceRecord, LeaveRequest, Asset, CompensationItem,
    ComplianceRecord, EngagementSurvey, EssRequest,
    LearningCourse, OnboardingRecord, OnboardingTask, OnboardingActivity,
    OnboardingStatus, PerformanceReview,
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
    OnboardingRecordCreate, OnboardingRecordUpdate,
    OnboardingTaskCreate, OnboardingTaskUpdate, PerformanceReviewCreate,
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
    """Creates a new department after checking case-insensitive duplicates."""
    # Case-insensitive validation check using .ilike()
    existing = db.query(Department).filter(Department.name.ilike(data.name)).first()
    if existing:
        raise AlreadyExistsException("Department", "name")

    existing_code = db.query(Department).filter(Department.code.ilike(data.code)).first()
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
    
    # If the name is getting updated, verify it doesn't match an existing name
    if "name" in update_data:
        existing = db.query(Department).filter(
            Department.name.ilike(update_data["name"]), 
            Department.id != dept_id
        ).first()
        if existing:
            raise AlreadyExistsException("Department", "name")

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
    from sqlalchemy import extract

    total       = db.query(Employee).count()
    active      = db.query(Employee).filter(Employee.