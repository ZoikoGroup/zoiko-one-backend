"""
modules/hr/service.py
---------------------
Business logic layer. This is WHERE the actual work happens.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.hr.models import (
    Employee, Department, EmployeeStatus, UserRole,
    AttendanceRecord, LeaveRequest, CompensationItem,
    ComplianceRecord, EngagementSurvey, EssRequest,
    OnboardingRecord, OnboardingTask, OnboardingActivity,
    OnboardingStatus, PerformanceReview,
    RecruitmentCandidate, TravelRequest, WorkforcePlan,
    RequestStatus,
)
from app.modules.hr.schemas import (
    EmployeeCreate, EmployeeUpdate,
    DepartmentCreate, DepartmentUpdate,
    LoginRequest,
    AttendanceCreate, LeaveRequestCreate, LeaveRequestUpdate,
    CompensationCreate,
    ComplianceRecordCreate, EngagementSurveyCreate,
    EssRequestCreate,
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
    last_employee = db.query(Employee).order_by(Employee.id.desc()).first()
    next_number = (last_employee.id + 1) if last_employee else 1
    return f"ZK-{next_number:04d}"


# ════════════════════════════════════════════════════════════════════════════
# AUTH SERVICE
# ════════════════════════════════════════════════════════════════════════════

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

    refresh_token = create_access_token(
        data={"sub": employee.email, "id": employee.id},
        expires_delta=timedelta(days=7),
    )

    return {
        "access_token": token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "employee": employee,
    }


# ════════════════════════════════════════════════════════════════════════════
# DEPARTMENT SERVICE
# ════════════════════════════════════════════════════════════════════════════

def create_department(db: Session, data: DepartmentCreate) -> Department:
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
            f"Cannot delete department '{dept.name}'. It still has {active_count} active employee(s)."
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


# ── FIX APPLIED HERE ──
def get_hr_dashboard_stats(db: Session) -> dict:
    """
    Returns summary statistics for the HR dashboard.
    """
    total = db.query(Employee).count()
    active = db.query(Employee).filter(Employee.status == EmployeeStatus.ACTIVE).count()
    
    dept_breakdown = (
        db.query(Department.name, func.count(Employee.id))
        .join(Employee, Employee.department_id == Department.id)
        .filter(Employee.status == EmployeeStatus.ACTIVE)
        .group_by(Department.name)
        .all()
    )

    return {
        "total_employees": total,
        "active_employees": active,
        "department_distribution": {name: count for name, count in dept_breakdown}
    }


def get_performance_dashboard(db: Session) -> dict:
    from app.modules.hr.models import PerformanceReview, RequestStatus
    total = db.query(PerformanceReview).count()
    pending = db.query(PerformanceReview).filter(PerformanceReview.status == RequestStatus.PENDING).count()
    completed = db.query(PerformanceReview).filter(PerformanceReview.status.in_([RequestStatus.APPROVED, RequestStatus.COMPLETED])).count()
    return {
        "total_reviews": total,
        "pending_reviews": pending,
        "completed_reviews": completed,
    }


def get_engagement_dashboard(db: Session) -> dict:
    from app.modules.hr.models import EngagementSurvey
    total = db.query(EngagementSurvey).count()
    avg_score = db.query(func.avg(EngagementSurvey.score)).scalar() or 0
    return {
        "engagement_score": round(float(avg_score), 1),
        "active_surveys": total,
        "participation_rate": 0,
    }


def get_compensation_dashboard(db: Session) -> dict:
    from app.modules.hr.models import CompensationItem
    total = db.query(CompensationItem).count()
    return {
        "payroll_processed": total,
        "employees_paid": 0,
        "pending_payments": 0,
    }


# ════════════════════════════════════════════════════════════════════════════
# ATTENDANCE SERVICE
# ════════════════════════════════════════════════════════════════════════════

def create_attendance_record(db: Session, data: AttendanceCreate) -> AttendanceRecord:
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


# ════════════════════════════════════════════════════════════════════════════
# LEAVE REQUEST SERVICE
# ════════════════════════════════════════════════════════════════════════════

def create_leave_request(db: Session, data: LeaveRequestCreate) -> LeaveRequest:
    record = LeaveRequest(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_leave_requests(db: Session, employee_id: Optional[int] = None) -> list[LeaveRequest]:
    query = db.query(LeaveRequest)
    if employee_id:
        query = query.filter(LeaveRequest.employee_id == employee_id)
    return query.order_by(LeaveRequest.created_at.desc()).all()


def review_leave_request(db: Session, leave_id: int, data: LeaveRequestUpdate) -> LeaveRequest:
    record = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not record:
        raise NotFoundException("LeaveRequest", leave_id)
    update_data = data.model_dump(exclude_unset=True)
    if "status" in update_data:
        record.status = update_data["status"]
        record.reviewed_at = datetime.utcnow()
    if "reason" in update_data:
        record.reason = update_data["reason"]
    db.commit()
    db.refresh(record)
    return record


# ════════════════════════════════════════════════════════════════════════════
# COMPENSATION ITEM SERVICE
# ════════════════════════════════════════════════════════════════════════════

def create_compensation_item(db: Session, data: CompensationCreate) -> CompensationItem:
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


# ════════════════════════════════════════════════════════════════════════════
# COMPLIANCE RECORD SERVICE
# ════════════════════════════════════════════════════════════════════════════

def create_compliance_record(db: Session, data: ComplianceRecordCreate) -> ComplianceRecord:
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


# ════════════════════════════════════════════════════════════════════════════
# ENGAGEMENT SURVEY SERVICE
# ════════════════════════════════════════════════════════════════════════════

def create_engagement_survey(db: Session, data: EngagementSurveyCreate) -> EngagementSurvey:
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


# ════════════════════════════════════════════════════════════════════════════
# ESS REQUEST SERVICE
# ════════════════════════════════════════════════════════════════════════════

def create_ess_request(db: Session, data: EssRequestCreate) -> EssRequest:
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


# ════════════════════════════════════════════════════════════════════════════
# ONBOARDING RECORD SERVICE
# ════════════════════════════════════════════════════════════════════════════

def create_onboarding_record(db: Session, data: OnboardingRecordCreate) -> OnboardingRecord:
    record = OnboardingRecord(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_onboarding_records(db: Session) -> list[OnboardingRecord]:
    return db.query(OnboardingRecord).order_by(OnboardingRecord.created_at.desc()).all()


def get_onboarding_record_by_id(db: Session, record_id: int) -> OnboardingRecord:
    record = db.query(OnboardingRecord).filter(OnboardingRecord.id == record_id).first()
    if not record:
        raise NotFoundException("OnboardingRecord", record_id)
    return record


def update_onboarding_record(db: Session, record_id: int, data: OnboardingRecordUpdate) -> OnboardingRecord:
    record = get_onboarding_record_by_id(db, record_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return record


def delete_onboarding_record(db: Session, record_id: int) -> None:
    record = get_onboarding_record_by_id(db, record_id)
    db.delete(record)
    db.commit()


def get_onboarding_dashboard(db: Session) -> dict:
    total = db.query(OnboardingRecord).count()
    pending = db.query(OnboardingRecord).filter(OnboardingRecord.status.in_([OnboardingStatus.OFFER_SENT, OnboardingStatus.OFFER_ACCEPTED, OnboardingStatus.PRE_JOINING])).count()
    completed = db.query(OnboardingRecord).filter(OnboardingRecord.status == OnboardingStatus.COMPLETED).count()
    in_progress = db.query(OnboardingRecord).filter(OnboardingRecord.status == OnboardingStatus.IN_PROGRESS).count()

    monthly = (
        db.query(func.date_format(OnboardingRecord.created_at, "%Y-%m").label("month"), func.count(OnboardingRecord.id))
        .group_by("month")
        .order_by("month")
        .all()
    )

    deptwise = (
        db.query(Department.name, func.count(OnboardingRecord.id))
        .join(OnboardingRecord, OnboardingRecord.department_id == Department.id, isouter=True)
        .group_by(Department.name)
        .all()
    )

    upcoming = (
        db.query(OnboardingRecord)
        .filter(OnboardingRecord.joining_date >= func.current_date())
        .order_by(OnboardingRecord.joining_date)
        .limit(10)
        .all()
    )

    recent = (
        db.query(OnboardingActivity)
        .order_by(OnboardingActivity.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "totalNewHires": total,
        "pendingOnboarding": pending,
        "completedOnboarding": completed,
        "documentsPending": pending,
        "assetsPending": in_progress,
        "orientationPending": in_progress,
        "trainingPending": in_progress,
        "monthlyJoiningTrend": [{"month": m, "count": c} for m, c in monthly],
        "departmentWise": [{"department": d, "count": c} for d, c in deptwise],
        "completionStatus": {"total": total, "completed": completed, "in_progress": in_progress, "pending": pending},
        "upcomingJoiners": [{"id": r.id, "name": r.candidate_name, "position": r.position, "joining_date": str(r.joining_date) if r.joining_date else None} for r in upcoming],
        "recentActivities": [{"id": a.id, "action": a.action, "description": a.description, "timestamp": str(a.created_at) if a.created_at else None} for a in recent],
    }


def get_onboarding_activities(db: Session, limit: int = 50) -> list[OnboardingActivity]:
    return db.query(OnboardingActivity).order_by(OnboardingActivity.created_at.desc()).limit(limit).all()


# ════════════════════════════════════════════════════════════════════════════
# ONBOARDING TASK SERVICE
# ════════════════════════════════════════════════════════════════════════════

def create_onboarding_task(db: Session, data: OnboardingTaskCreate) -> OnboardingTask:
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


def update_onboarding_task(db: Session, task_id: int, data: OnboardingTaskUpdate) -> OnboardingTask:
    task = db.query(OnboardingTask).filter(OnboardingTask.id == task_id).first()
    if not task:
        raise NotFoundException("OnboardingTask", task_id)
    update_data = data.model_dump(exclude_unset=True)
    if "completed" in update_data and update_data["completed"] and not task.completed:
        task.completed_at = datetime.utcnow()
    for field, value in update_data.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


def delete_onboarding_task(db: Session, task_id: int) -> None:
    task = db.query(OnboardingTask).filter(OnboardingTask.id == task_id).first()
    if not task:
        raise NotFoundException("OnboardingTask", task_id)
    db.delete(task)
    db.commit()


# ════════════════════════════════════════════════════════════════════════════
# PERFORMANCE REVIEW SERVICE
# ════════════════════════════════════════════════════════════════════════════

def create_performance_review(db: Session, data: PerformanceReviewCreate) -> PerformanceReview:
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


# ════════════════════════════════════════════════════════════════════════════
# RECRUITMENT CANDIDATE SERVICE
# ════════════════════════════════════════════════════════════════════════════

def create_recruitment_candidate(db: Session, data: RecruitmentCandidateCreate) -> RecruitmentCandidate:
    existing = db.query(RecruitmentCandidate).filter(RecruitmentCandidate.email == data.email).first()
    if existing:
        raise AlreadyExistsException("RecruitmentCandidate", "email")
    candidate = RecruitmentCandidate(**data.model_dump())
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def get_recruitment_candidates(db: Session) -> list[RecruitmentCandidate]:
    return db.query(RecruitmentCandidate).order_by(RecruitmentCandidate.applied_at.desc()).all()


def update_recruitment_candidate(db: Session, candidate_id: int, data: RecruitmentCandidateUpdate) -> RecruitmentCandidate:
    candidate = db.query(RecruitmentCandidate).filter(RecruitmentCandidate.id == candidate_id).first()
    if not candidate:
        raise NotFoundException("RecruitmentCandidate", candidate_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(candidate, field, value)
    db.commit()
    db.refresh(candidate)
    return candidate


# ════════════════════════════════════════════════════════════════════════════
# TRAVEL REQUEST SERVICE
# ════════════════════════════════════════════════════════════════════════════

def create_travel_request(db: Session, data: TravelRequestCreate) -> TravelRequest:
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


# ════════════════════════════════════════════════════════════════════════════
# WORKFORCE PLANNING SERVICE
# ════════════════════════════════════════════════════════════════════════════

def create_workforce_plan(db: Session, data: WorkforcePlanCreate) -> WorkforcePlan:
    plan = WorkforcePlan(**data.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def get_workforce_plans(db: Session) -> list[WorkforcePlan]:
    return db.query(WorkforcePlan).order_by(WorkforcePlan.year.desc()).all()


def get_workforce_summary(db: Session) -> dict:
    total = db.query(Employee).count()
    active = db.query(Employee).filter(Employee.status == EmployeeStatus.ACTIVE).count()

    dept_breakdown = (
        db.query(Department.name, func.count(Employee.id))
        .join(Employee, Employee.department_id == Department.id, isouter=True)
        .group_by(Department.name)
        .all()
    )

    return {
        "total_headcount": total,
        "active_employees": active,
        "department_breakdown": [{"department": d, "count": c} for d, c in dept_breakdown],
        "yearly_trend": [],
        "turnover_rate": None,
    }