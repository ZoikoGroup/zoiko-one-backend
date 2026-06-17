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

def _generate_employee_code(db: Session) -> str:
    last_employee = db.query(Employee).order_by(Employee.id.desc()).first()
    next_number = (last_employee.id + 1) if last_employee else 1
    return f"ZK-{next_number:04d}"   


def login_employee(db: Session, data: LoginRequest) -> dict:
    employee = db.query(Employee).filter(Employee.email == data.email).first()
    if not employee:
        raise UnauthorizedException("Invalid email or password.")

    if not verify_password(data.password, employee.hashed_password):
        raise UnauthorizedException("Invalid email or password.")

    if not employee.is_active:
        raise UnauthorizedException("Your account has been deactivated. Contact your HR admin.")

    token = create_access_token(data={
        "sub":  employee.email,
        "role": employee.role.value,
        "id":   employee.id,
    })
    return {"access_token": token, "token_type": "bearer", "employee": employee}


# ════════════════════════════════════════════════════════════════════════════
# DEPARTMENT SERVICE (UPDATED DUPLICATE CHECKS)
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
    db.refresh(dept)   
    return dept


def get_all_departments(db: Session) -> List[Department]:
    return db.query(Department).filter(Department.is_active == True).all()


def get_department_by_id(db: Session, dept_id: int) -> Department:
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise NotFoundException("Department", dept_id)
    return dept


def update_department(db: Session, dept_id: int, data: DepartmentUpdate) -> Department:
    dept = get_department_by_id(db, dept_id)

    # If the name is getting updated, verify it doesn't match an existing name
    update_data = data.model_dump(exclude_unset=True)
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
    dept = get_department_by_id(db, dept_id)

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
    existing = db.query(Employee).filter(Employee.email == data.email).first()
    if existing:
        raise AlreadyExistsException("Employee", "email")

    if data.department_id:
        get_department_by_id(db, data.department_id)  

    employee_data = data.model_dump(exclude={"password"})  
    employee = Employee(
        **employee_data,
        hashed_password=hash_password(data.password),
        employee_code=_generate_employee_code(db),
    )

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
    per_page = min(per_page, 100)  
    query = db.query(Employee)

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

    total = query.count()
    employees = query.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "items":    employees,
    }


def get_employee_by_id(db: Session, employee_id: int) -> Employee:
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise NotFoundException("Employee", employee_id)
    return employee


def update_employee(db: Session, employee_id: int, data: EmployeeUpdate) -> Employee:
    employee = get_employee_by_id(db, employee_id)

    if data.department_id:
        get_department_by_id(db, data.department_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)

    db.commit()
    db.refresh(employee)
    return employee


def deactivate_employee(db: Session, employee_id: int) -> Employee:
    employee = get_employee_by_id(db, employee_id)
    employee.is_active = False
    employee.status    = EmployeeStatus.TERMINATED
    db.commit()
    db.refresh(employee)
    return employee


def get_hr_dashboard_stats(db: Session) -> dict:
    from datetime import date
    from sqlalchemy import extract

    total       = db.query(Employee).count()
    active      = db.query(Employee).filter(Employee.status == EmployeeStatus.ACTIVE).count()
    on_leave    = db.query(Employee).filter(Employee.status == EmployeeStatus.ON_LEAVE).count()
    terminated  = db.query(Employee).filter(Employee.status == EmployeeStatus.TERMINATED).count()

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


def _add_onboarding_activity(
    db: Session,
    record_id: Optional[int],
    action: str,
    description: str,
    commit: bool = False,
) -> OnboardingActivity:
    activity = OnboardingActivity(
        onboarding_record_id=record_id,
        action=action,
        description=description,
    )
    db.add(activity)
    if commit:
        db.commit()
        db.refresh(activity)
    return activity


def get_onboarding_records(db: Session) -> list[OnboardingRecord]:
    return db.query(OnboardingRecord).order_by(OnboardingRecord.created_at.desc()).all()


def get_onboarding_record_by_id(db: Session, record_id: int) -> OnboardingRecord:
    record = db.query(OnboardingRecord).filter(OnboardingRecord.id == record_id).first()
    if not record:
        raise NotFoundException("Onboarding record", record_id)
    return record


def create_onboarding_record(db: Session, data: OnboardingRecordCreate) -> OnboardingRecord:
    if data.department_id:
        get_department_by_id(db, data.department_id)
    if data.manager_id:
        get_employee_by_id(db, data.manager_id)

    record = OnboardingRecord(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)

    _add_onboarding_activity(
        db,
        record.id,
        "record_created",
        f"Onboarding started for {record.candidate_name}.",
        commit=True,
    )
    return record


def update_onboarding_record(db: Session, record_id: int, data: OnboardingRecordUpdate) -> OnboardingRecord:
    record = get_onboarding_record_by_id(db, record_id)
    update_data = data.model_dump(exclude_unset=True)

    if update_data.get("department_id"):
        get_department_by_id(db, update_data["department_id"])
    if update_data.get("manager_id"):
        get_employee_by_id(db, update_data["manager_id"])
    if update_data.get("employee_id"):
        get_employee_by_id(db, update_data["employee_id"])

    old_status = record.status
    for field, value in update_data.items():
        setattr(record, field, value)

    action = "record_updated"
    description = f"Onboarding record updated for {record.candidate_name}."
    if "status" in update_data and update_data["status"] != old_status:
        action = "status_changed"
        description = f"{record.candidate_name} moved to {record.status.value}."

    _add_onboarding_activity(db, record.id, action, description)
    db.commit()
    db.refresh(record)
    return record


def delete_onboarding_record(db: Session, record_id: int) -> None:
    record = get_onboarding_record_by_id(db, record_id)
    db.delete(record)
    db.commit()


def _resolve_onboarding_task_parent(
    db: Session,
    employee_id: Optional[int],
    onboarding_record_id: Optional[int],
) -> tuple[Optional[int], Optional[int]]:
    if onboarding_record_id:
        record = get_onboarding_record_by_id(db, onboarding_record_id)
        return record.employee_id, record.id

    if employee_id:
        record = db.query(OnboardingRecord).filter(OnboardingRecord.id == employee_id).first()
        if record:
            return record.employee_id, record.id
        get_employee_by_id(db, employee_id)
        return employee_id, None

    raise BadRequestException("Either employee_id or onboarding_record_id is required.")


def create_onboarding_task(db: Session, data: OnboardingTaskCreate) -> OnboardingTask:
    employee_id, record_id = _resolve_onboarding_task_parent(
        db,
        data.employee_id,
        data.onboarding_record_id,
    )
    task = OnboardingTask(
        employee_id=employee_id,
        onboarding_record_id=record_id,
        title=data.title,
        description=data.description,
        due_date=data.due_date,
    )
    db.add(task)
    if record_id:
        _add_onboarding_activity(db, record_id, "task_created", f"Checklist item added: {task.title}.")
    db.commit()
    db.refresh(task)
    return task


def get_onboarding_tasks(db: Session, employee_id: Optional[int] = None) -> list[OnboardingTask]:
    query = db.query(OnboardingTask)
    if employee_id:
        record = db.query(OnboardingRecord).filter(OnboardingRecord.id == employee_id).first()
        if record:
            query = query.filter(OnboardingTask.onboarding_record_id == record.id)
        else:
            query = query.filter(OnboardingTask.employee_id == employee_id)
    return query.order_by(OnboardingTask.created_at.desc()).all()


def update_onboarding_task(db: Session, task_id: int, data: OnboardingTaskUpdate) -> OnboardingTask:
    task = db.query(OnboardingTask).filter(OnboardingTask.id == task_id).first()
    if not task:
        raise NotFoundException("Onboarding task", task_id)

    update_data = data.model_dump(exclude_unset=True)
    if "completed" in update_data:
        task.completed_at = datetime.utcnow() if update_data["completed"] else None

    for field, value in update_data.items():
        setattr(task, field, value)

    if task.onboarding_record_id:
        action = "task_completed" if task.completed else "task_updated"
        _add_onboarding_activity(db, task.onboarding_record_id, action, f"Checklist item updated: {task.title}.")

    db.commit()
    db.refresh(task)
    return task


def delete_onboarding_task(db: Session, task_id: int) -> None:
    task = db.query(OnboardingTask).filter(OnboardingTask.id == task_id).first()
    if not task:
        raise NotFoundException("Onboarding task", task_id)

    record_id = task.onboarding_record_id
    title = task.title
    db.delete(task)
    if record_id:
        _add_onboarding_activity(db, record_id, "task_deleted", f"Checklist item removed: {title}.")
    db.commit()


def get_onboarding_activities(db: Session, limit: int = 50) -> list[OnboardingActivity]:
    return (
        db.query(OnboardingActivity)
        .order_by(OnboardingActivity.created_at.desc())
        .limit(limit)
        .all()
    )


def get_onboarding_dashboard(db: Session) -> dict:
    records = db.query(OnboardingRecord).order_by(OnboardingRecord.created_at.desc()).all()
    total = len(records)

    completed = sum(1 for r in records if r.status == OnboardingStatus.COMPLETED)
    in_progress = sum(1 for r in records if r.status == OnboardingStatus.IN_PROGRESS)
    pending = sum(1 for r in records if r.status in {OnboardingStatus.OFFER_ACCEPTED, OnboardingStatus.PRE_JOINING})
    not_started = sum(1 for r in records if r.status == OnboardingStatus.OFFER_SENT)

    monthly_counts: dict[str, int] = {}
    for record in records:
        if record.joining_date:
            key = record.joining_date.strftime("%b %Y")
            monthly_counts[key] = monthly_counts.get(key, 0) + 1

    department_counts: dict[str, int] = {}
    for record in records:
        name = record.department_name or "Unassigned"
        department_counts[name] = department_counts.get(name, 0) + 1

    upcoming = [
        {
            "id": record.id,
            "name": record.candidate_name,
            "position": record.position,
            "department": record.department_name or "Unassigned",
            "joiningDate": record.joining_date.isoformat() if record.joining_date else None,
            "status": record.status.value,
        }
        for record in records
        if record.status not in {OnboardingStatus.COMPLETED, OnboardingStatus.CANCELLED}
    ][:10]

    activities = [
        {
            "id": activity.id,
            "description": activity.description,
            "message": activity.description,
            "timestamp": activity.created_at.isoformat() if activity.created_at else None,
            "date": activity.created_at.isoformat() if activity.created_at else None,
        }
        for activity in get_onboarding_activities(db, 10)
    ]

    return {
        "totalNewHires": total,
        "pendingOnboarding": total - completed,
        "completedOnboarding": completed,
        "documentsPending": 0,
        "assetsPending": 0,
        "orientationPending": 0,
        "trainingPending": 0,
        "monthlyJoiningTrend": [{"month": month, "count": count} for month, count in monthly_counts.items()],
        "departmentWise": [{"name": name, "count": count} for name, count in department_counts.items()],
        "completionStatus": {
            "completed": completed,
            "inProgress": in_progress,
            "pending": pending,
            "notStarted": not_started,
        },
        "upcomingJoiners": upcoming,
        "recentActivities": activities,
    }


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