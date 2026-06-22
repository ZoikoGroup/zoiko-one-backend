"""
modules/hr/service.py
---------------------
Business logic layer. This is WHERE the actual work happens.
"""

from datetime import date, datetime, timedelta
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.hr.models import (
    Employee, Department, EmployeeStatus, UserRole,
    AttendanceRecord, LeaveRequest, LeaveTypeConfig, LeaveSetting, LeaveBalance,
    CompensationItem,
    PayGrade, CompensationBand, SalaryComponent, SalaryStructure, 
    StructureComponent, EmployeeCompensation, SalaryRevision, 
    Allowance, Benefit, EmployeeBenefit,
    ComplianceRecord, EngagementSurvey, EssRequest,
    OnboardingRecord, OnboardingTask, OnboardingActivity,
    OnboardingStatus, PerformanceReview,
    PerformanceGoal, PerformanceKpi, PerformanceFeedback, Appraisal,
    RecruitmentCandidate, TravelRequest, WorkforcePlan,
    RequestStatus, LeaveType,
)
from app.modules.hr.schemas import (
    EmployeeCreate, EmployeeUpdate,
    DepartmentCreate, DepartmentUpdate,
    LoginRequest,
    AttendanceCreate, LeaveRequestCreate, LeaveRequestUpdate,
    LeaveTypeConfigCreate, LeaveTypeConfigUpdate, LeaveTypeConfigResponse,
    LeaveSettingCreate, LeaveSettingUpdate, LeaveSettingResponse,
    LeaveBalanceResponse, LeaveBalanceUpdate,
    LeaveDashboardStats, LeaveCalendarEvent, LeaveStatisticsResponse,
    CompensationCreate,
    PayGradeCreate, PayGradeUpdate,
    CompensationBandCreate, CompensationBandUpdate,
    SalaryComponentCreate, SalaryComponentUpdate,
    SalaryStructureCreate, SalaryStructureUpdate,
    StructureComponentCreate, StructureComponentUpdate,
    EmployeeCompensationCreate, EmployeeCompensationUpdate,
    SalaryRevisionCreate, AllowanceCreate, AllowanceUpdate,
    BenefitCreate, BenefitUpdate, EmployeeBenefitCreate,
    ComplianceRecordCreate, EngagementSurveyCreate,
    EssRequestCreate,
    OnboardingRecordCreate, OnboardingRecordUpdate,
    OnboardingTaskCreate, OnboardingTaskUpdate,
    PerformanceReviewCreate,
    PerformanceGoalCreate, PerformanceGoalUpdate,
    PerformanceKpiCreate, PerformanceKpiUpdate,
    PerformanceFeedbackCreate,
    AppraisalCreate, AppraisalUpdate,
    RecruitmentCandidateCreate, RecruitmentCandidateUpdate,
    ApplicationCreate, ApplicationResponse,
    InterviewFeedbackCreate, InterviewFeedbackResponse,
    OfferApprovalCreate, OfferApprovalResponse,
    RecruitmentAnalyticsResponse,
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


def get_engagement_dashboard(db: Session) -> dict:
    from app.modules.hr.models import EngagementSurvey
    total = db.query(EngagementSurvey).count()
    avg_score = db.query(func.avg(EngagementSurvey.score)).scalar() or 0
    return {
        "engagement_score": round(float(avg_score), 1),
        "active_surveys": total,
        "participation_rate": 0,
    }


def get_compensation_dashboard(db: Session, org_id: int) -> dict:
    from app.modules.hr.models import (
        PayGrade, CompensationBand, SalaryComponent, SalaryStructure,
        EmployeeCompensation, Allowance, Benefit, EmployeeBenefit,
        SalaryRevision,
    )
    return {
        "total_pay_grades": db.query(PayGrade).filter(PayGrade.organization_id == org_id).count(),
        "total_bands": db.query(CompensationBand).filter(CompensationBand.organization_id == org_id).count(),
        "total_components": db.query(SalaryComponent).filter(SalaryComponent.organization_id == org_id).count(),
        "total_structures": db.query(SalaryStructure).filter(SalaryStructure.organization_id == org_id).count(),
        "total_assignments": db.query(EmployeeCompensation).filter(EmployeeCompensation.organization_id == org_id).count(),
        "total_revisions": db.query(SalaryRevision).filter(SalaryRevision.organization_id == org_id).count(),
        "total_allowances": db.query(Allowance).filter(Allowance.organization_id == org_id).count(),
        "total_benefits": db.query(Benefit).filter(Benefit.organization_id == org_id).count(),
        "total_enrollments": db.query(EmployeeBenefit).filter(EmployeeBenefit.organization_id == org_id).count(),
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
# LEAVE SERVICE
# ════════════════════════════════════════════════════════════════════════════

def _compute_leave_days(start_date: date, end_date: date) -> int:
    return (end_date - start_date).days + 1

# ── Leave Requests ─────────────────────────────────────────────────────────

def create_leave_request(db: Session, data: LeaveRequestCreate, org_id: int) -> LeaveRequest:
    days = _compute_leave_days(data.start_date, data.end_date)
    record = LeaveRequest(
        employee_id=data.employee_id,
        organization_id=org_id,
        leave_type=data.leave_type,
        start_date=data.start_date,
        end_date=data.end_date,
        days=days,
        reason=data.reason,
        status=RequestStatus.PENDING,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    balance = db.query(LeaveBalance).filter(
        LeaveBalance.employee_id == data.employee_id,
        LeaveBalance.leave_type == data.leave_type,
        LeaveBalance.year == data.start_date.year,
    ).first()
    if balance:
        balance.pending_days += days
        db.commit()

    return record


def get_leave_requests(
    db: Session,
    org_id: int,
    employee_id: Optional[int] = None,
    status: Optional[RequestStatus] = None,
    leave_type: Optional[LeaveType] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> list[LeaveRequest]:
    query = db.query(LeaveRequest).filter(LeaveRequest.organization_id == org_id)
    if employee_id:
        query = query.filter(LeaveRequest.employee_id == employee_id)
    if status:
        query = query.filter(LeaveRequest.status == status)
    if leave_type:
        query = query.filter(LeaveRequest.leave_type == leave_type)
    if start_date:
        query = query.filter(LeaveRequest.start_date >= start_date)
    if end_date:
        query = query.filter(LeaveRequest.end_date <= end_date)
    return query.order_by(LeaveRequest.created_at.desc()).all()


def get_leave_request(db: Session, leave_id: int, org_id: int) -> LeaveRequest:
    record = db.query(LeaveRequest).filter(
        LeaveRequest.id == leave_id,
        LeaveRequest.organization_id == org_id,
    ).first()
    if not record:
        raise NotFoundException("LeaveRequest", leave_id)
    return record


def update_leave_request(db: Session, leave_id: int, data: LeaveRequestUpdate, org_id: int) -> LeaveRequest:
    record = get_leave_request(db, leave_id, org_id)
    update_data = data.model_dump(exclude_unset=True)
    if "start_date" in update_data or "end_date" in update_data:
        start = update_data.get("start_date", record.start_date)
        end = update_data.get("end_date", record.end_date)
        update_data["days"] = _compute_leave_days(start, end)
    for key, value in update_data.items():
        setattr(record, key, value)
    if "status" in update_data:
        record.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


def delete_leave_request(db: Session, leave_id: int, org_id: int) -> None:
    record = get_leave_request(db, leave_id, org_id)
    db.delete(record)
    db.commit()


def review_leave_request(db: Session, leave_id: int, data: LeaveRequestUpdate, org_id: int, reviewer_id: int) -> LeaveRequest:
    record = get_leave_request(db, leave_id, org_id)
    update_data = data.model_dump(exclude_unset=True)
    if "status" in update_data:
        record.status = update_data["status"]
        record.reviewed_by = reviewer_id
        record.reviewed_at = datetime.utcnow()
    if "reason" in update_data:
        record.reason = update_data["reason"]
    db.commit()
    db.refresh(record)

    if record.status in (RequestStatus.APPROVED, RequestStatus.REJECTED):
        balance = db.query(LeaveBalance).filter(
            LeaveBalance.employee_id == record.employee_id,
            LeaveBalance.leave_type == record.leave_type,
            LeaveBalance.year == record.start_date.year,
        ).first()
        if balance and record.status == RequestStatus.APPROVED:
            balance.pending_days -= record.days
            balance.used_days += record.days
        elif balance and record.status == RequestStatus.REJECTED:
            balance.pending_days -= record.days
        db.commit()

    return record


# ── Leave Type Configs ─────────────────────────────────────────────────────

def create_leave_type_config(db: Session, data: LeaveTypeConfigCreate, org_id: int) -> LeaveTypeConfig:
    raw = data.model_dump()
    raw["code"] = raw["code"].strip().lower()
    existing = db.query(LeaveTypeConfig).filter(
        LeaveTypeConfig.organization_id == org_id,
        LeaveTypeConfig.code == raw["code"],
    ).first()
    if existing:
        raise AlreadyExistsException("LeaveTypeConfig", field=f"code '{raw['code']}'")
    record = LeaveTypeConfig(organization_id=org_id, **raw)
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AlreadyExistsException("LeaveTypeConfig", field=f"code '{raw['code']}'")
    db.refresh(record)
    return record


def get_leave_type_configs(db: Session, org_id: int) -> list[LeaveTypeConfig]:
    return db.query(LeaveTypeConfig).filter(
        LeaveTypeConfig.organization_id == org_id,
    ).order_by(LeaveTypeConfig.code).all()


def get_leave_type_config(db: Session, config_id: int, org_id: int) -> LeaveTypeConfig:
    record = db.query(LeaveTypeConfig).filter(
        LeaveTypeConfig.id == config_id,
        LeaveTypeConfig.organization_id == org_id,
    ).first()
    if not record:
        raise NotFoundException("LeaveTypeConfig", config_id)
    return record


def update_leave_type_config(db: Session, config_id: int, data: LeaveTypeConfigUpdate, org_id: int) -> LeaveTypeConfig:
    record = get_leave_type_config(db, config_id, org_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


def delete_leave_type_config(db: Session, config_id: int, org_id: int) -> None:
    record = get_leave_type_config(db, config_id, org_id)
    db.delete(record)
    db.commit()


# ── Leave Settings ─────────────────────────────────────────────────────────

def get_leave_settings(db: Session, org_id: int) -> LeaveSetting:
    record = db.query(LeaveSetting).filter(
        LeaveSetting.organization_id == org_id,
    ).first()
    if not record:
        record = LeaveSetting(organization_id=org_id)
        db.add(record)
        db.commit()
        db.refresh(record)
    return record


def update_leave_settings(db: Session, org_id: int, data: LeaveSettingUpdate) -> LeaveSetting:
    record = get_leave_settings(db, org_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


# ── Leave Balances ─────────────────────────────────────────────────────────

def get_leave_balances(db: Session, org_id: int, employee_id: Optional[int] = None) -> list[LeaveBalance]:
    query = db.query(LeaveBalance).filter(LeaveBalance.organization_id == org_id)
    if employee_id:
        query = query.filter(LeaveBalance.employee_id == employee_id)
    return query.order_by(LeaveBalance.employee_id, LeaveBalance.leave_type).all()


def init_leave_balance(db: Session, employee_id: int, org_id: int, year: int) -> None:
    configs = get_leave_type_configs(db, org_id)
    for config in configs:
        existing = db.query(LeaveBalance).filter(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_type == config.code,
            LeaveBalance.year == year,
        ).first()
        if not existing:
            balance = LeaveBalance(
                employee_id=employee_id,
                organization_id=org_id,
                leave_type=config.code,
                total_days=config.default_days_per_year,
                used_days=0,
                pending_days=0,
                year=year,
            )
            db.add(balance)
    db.commit()


def update_leave_balance(db: Session, balance_id: int, data: LeaveBalanceUpdate, org_id: int) -> LeaveBalance:
    record = db.query(LeaveBalance).filter(
        LeaveBalance.id == balance_id,
        LeaveBalance.organization_id == org_id,
    ).first()
    if not record:
        raise NotFoundException("LeaveBalance", balance_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


# ── Leave Dashboard / Calendar ─────────────────────────────────────────────

def get_leave_dashboard(db: Session, org_id: int) -> LeaveDashboardStats:
    base = db.query(LeaveRequest).filter(LeaveRequest.organization_id == org_id)
    total = base.count()
    pending = base.filter(LeaveRequest.status == RequestStatus.PENDING).count()
    approved = base.filter(LeaveRequest.status == RequestStatus.APPROVED).count()
    rejected = base.filter(LeaveRequest.status == RequestStatus.REJECTED).count()
    days_approved = db.query(func.coalesce(func.sum(LeaveRequest.days), 0)).filter(
        LeaveRequest.organization_id == org_id,
        LeaveRequest.status == RequestStatus.APPROVED,
    ).scalar()
    days_pending = db.query(func.coalesce(func.sum(LeaveRequest.days), 0)).filter(
        LeaveRequest.organization_id == org_id,
        LeaveRequest.status == RequestStatus.PENDING,
    ).scalar()
    employee_count = db.query(func.count(Employee.id)).filter(
        Employee.organization_id == org_id,
        Employee.status == EmployeeStatus.ACTIVE,
    ).scalar()
    today = date.today()
    on_leave_today = db.query(func.count(LeaveRequest.id)).filter(
        LeaveRequest.organization_id == org_id,
        LeaveRequest.status == RequestStatus.APPROVED,
        LeaveRequest.start_date <= today,
        LeaveRequest.end_date >= today,
    ).scalar()

    return LeaveDashboardStats(
        total_requests=total,
        pending_requests=pending,
        approved_requests=approved,
        rejected_requests=rejected,
        total_days_taken=days_approved,
        pending_days_taken=days_pending,
        approved_days_taken=days_approved,
        employee_count=employee_count,
        on_leave_today=on_leave_today,
    )


def get_leave_calendar(db: Session, org_id: int, year: Optional[int] = None, month: Optional[int] = None) -> list[LeaveCalendarEvent]:
    query = db.query(LeaveRequest).filter(
        LeaveRequest.organization_id == org_id,
        LeaveRequest.status.in_([RequestStatus.APPROVED, RequestStatus.PENDING]),
    )
    if year:
        query = query.filter(
            func.extract("year", LeaveRequest.start_date) == year,
        )
    if month:
        query = query.filter(
            func.extract("month", LeaveRequest.start_date) == month,
        )
    records = query.order_by(LeaveRequest.start_date).all()

    events = []
    for r in records:
        emp = db.query(Employee).filter(Employee.id == r.employee_id).first()
        events.append(LeaveCalendarEvent(
            id=r.id,
            employee_id=r.employee_id,
            employee_name=emp.full_name if emp else "",
            leave_type=r.leave_type,
            start_date=r.start_date,
            end_date=r.end_date,
            days=r.days,
            status=r.status,
        ))
    return events


def get_leave_statistics(db: Session, org_id: int) -> LeaveStatisticsResponse:
    total_employees = db.query(func.count(Employee.id)).filter(
        Employee.organization_id == org_id,
        Employee.status == EmployeeStatus.ACTIVE,
    ).scalar()
    total_requests = db.query(func.count(LeaveRequest.id)).filter(
        LeaveRequest.organization_id == org_id,
    ).scalar()
    approved_count = db.query(func.count(LeaveRequest.id)).filter(
        LeaveRequest.organization_id == org_id,
        LeaveRequest.status == RequestStatus.APPROVED,
    ).scalar()
    approval_rate = (approved_count / total_requests * 100) if total_requests else 0.0
    total_days = db.query(func.coalesce(func.sum(LeaveRequest.days), 0)).filter(
        LeaveRequest.organization_id == org_id,
        LeaveRequest.status == RequestStatus.APPROVED,
    ).scalar()
    avg_days = (total_days / approved_count) if approved_count else 0.0

    type_breakdown = db.query(
        LeaveRequest.leave_type,
        func.count(LeaveRequest.id).label("count"),
        func.coalesce(func.sum(LeaveRequest.days), 0).label("days"),
    ).filter(
        LeaveRequest.organization_id == org_id,
    ).group_by(LeaveRequest.leave_type).all()

    monthly = db.query(
        func.extract("year", LeaveRequest.created_at).label("yr"),
        func.extract("month", LeaveRequest.created_at).label("mo"),
        func.count(LeaveRequest.id).label("count"),
    ).filter(
        LeaveRequest.organization_id == org_id,
    ).group_by("yr", "mo").order_by("yr", "mo").all()

    return LeaveStatisticsResponse(
        total_employees=total_employees,
        total_requests=total_requests,
        approval_rate=round(approval_rate, 2),
        average_days_per_request=round(avg_days, 2),
        leave_type_breakdown=[{"type": t.leave_type.value, "count": t.count, "days": t.days} for t in type_breakdown],
        monthly_trend=[{"year": int(m.yr), "month": int(m.mo), "count": m.count} for m in monthly],
    )


# ════════════════════════════════════════════════════════════════════════════
# COMPENSATION SERVICE
# ════════════════════════════════════════════════════════════════════════════

# ── Pay Grades ──────────────────────────────────────────────────────────────

def create_pay_grade(db: Session, data: PayGradeCreate, org_id: int) -> PayGrade:
    grade = PayGrade(**data.model_dump(), organization_id=org_id)
    db.add(grade)
    db.commit()
    db.refresh(grade)
    return grade

def get_pay_grades(db: Session, org_id: int) -> list[PayGrade]:
    return db.query(PayGrade).filter(PayGrade.organization_id == org_id).all()

def update_pay_grade(db: Session, grade_id: int, data: PayGradeUpdate, org_id: int) -> PayGrade:
    grade = db.query(PayGrade).filter(PayGrade.id == grade_id, PayGrade.organization_id == org_id).first()
    if not grade:
        raise NotFoundException("PayGrade", grade_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(grade, key, value)
    db.commit()
    db.refresh(grade)
    return grade

def delete_pay_grade(db: Session, grade_id: int, org_id: int) -> None:
    grade = db.query(PayGrade).filter(PayGrade.id == grade_id, PayGrade.organization_id == org_id).first()
    if not grade:
        raise NotFoundException("PayGrade", grade_id)
    db.delete(grade)
    db.commit()

# ── Compensation Bands ──────────────────────────────────────────────────────

def create_compensation_band(db: Session, data: CompensationBandCreate, org_id: int) -> CompensationBand:
    band = CompensationBand(**data.model_dump(), organization_id=org_id)
    db.add(band)
    db.commit()
    db.refresh(band)
    return band

def get_compensation_bands(db: Session, org_id: int) -> list[CompensationBand]:
    return db.query(CompensationBand).filter(CompensationBand.organization_id == org_id).all()

def update_compensation_band(db: Session, band_id: int, data: CompensationBandUpdate, org_id: int) -> CompensationBand:
    band = db.query(CompensationBand).filter(CompensationBand.id == band_id, CompensationBand.organization_id == org_id).first()
    if not band:
        raise NotFoundException("CompensationBand", band_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(band, key, value)
    db.commit()
    db.refresh(band)
    return band

def delete_compensation_band(db: Session, band_id: int, org_id: int) -> None:
    band = db.query(CompensationBand).filter(CompensationBand.id == band_id, CompensationBand.organization_id == org_id).first()
    if not band:
        raise NotFoundException("CompensationBand", band_id)
    db.delete(band)
    db.commit()

# ── Salary Components ──────────────────────────────────────────────────────

def create_salary_component(db: Session, data: SalaryComponentCreate, org_id: int) -> SalaryComponent:
    comp = SalaryComponent(**data.model_dump(), organization_id=org_id)
    db.add(comp)
    db.commit()
    db.refresh(comp)
    return comp

def get_salary_components(db: Session, org_id: int) -> list[SalaryComponent]:
    return db.query(SalaryComponent).filter(SalaryComponent.organization_id == org_id).all()

def update_salary_component(db: Session, comp_id: int, data: SalaryComponentUpdate, org_id: int) -> SalaryComponent:
    comp = db.query(SalaryComponent).filter(SalaryComponent.id == comp_id, SalaryComponent.organization_id == org_id).first()
    if not comp:
        raise NotFoundException("SalaryComponent", comp_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(comp, key, value)
    db.commit()
    db.refresh(comp)
    return comp

def delete_salary_component(db: Session, comp_id: int, org_id: int) -> None:
    comp = db.query(SalaryComponent).filter(SalaryComponent.id == comp_id, SalaryComponent.organization_id == org_id).first()
    if not comp:
        raise NotFoundException("SalaryComponent", comp_id)
    db.delete(comp)
    db.commit()

# ── Salary Structures ──────────────────────────────────────────────────────

def create_salary_structure(db: Session, data: SalaryStructureCreate, org_id: int) -> SalaryStructure:
    struct = SalaryStructure(**data.model_dump(), organization_id=org_id)
    db.add(struct)
    db.commit()
    db.refresh(struct)
    return struct

def get_salary_structures(db: Session, org_id: int) -> list[SalaryStructure]:
    return db.query(SalaryStructure).filter(SalaryStructure.organization_id == org_id).all()

def update_salary_structure(db: Session, struct_id: int, data: SalaryStructureUpdate, org_id: int) -> SalaryStructure:
    struct = db.query(SalaryStructure).filter(SalaryStructure.id == struct_id, SalaryStructure.organization_id == org_id).first()
    if not struct:
        raise NotFoundException("SalaryStructure", struct_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(struct, key, value)
    db.commit()
    db.refresh(struct)
    return struct

def delete_salary_structure(db: Session, struct_id: int, org_id: int) -> None:
    struct = db.query(SalaryStructure).filter(SalaryStructure.id == struct_id, SalaryStructure.organization_id == org_id).first()
    if not struct:
        raise NotFoundException("SalaryStructure", struct_id)
    db.delete(struct)
    db.commit()

# ── Structure Components ───────────────────────────────────────────────────

def create_structure_component(db: Session, data: StructureComponentCreate, org_id: int) -> StructureComponent:
    struct = db.query(SalaryStructure).filter(SalaryStructure.id == data.structure_id, SalaryStructure.organization_id == org_id).first()
    if not struct:
        raise NotFoundException("SalaryStructure", data.structure_id)
    struct_comp = StructureComponent(**data.model_dump())
    db.add(struct_comp)
    db.commit()
    db.refresh(struct_comp)
    return struct_comp

def get_structure_components(db: Session, structure_id: int, org_id: int) -> list[StructureComponent]:
    struct = db.query(SalaryStructure).filter(SalaryStructure.id == structure_id, SalaryStructure.organization_id == org_id).first()
    if not struct:
        raise NotFoundException("SalaryStructure", structure_id)
    return db.query(StructureComponent).filter(StructureComponent.structure_id == structure_id).all()

def delete_structure_component(db: Session, struct_comp_id: int, org_id: int) -> None:
    struct_comp = db.query(StructureComponent).filter(StructureComponent.id == struct_comp_id).first()
    if not struct_comp:
        raise NotFoundException("StructureComponent", struct_comp_id)
    struct = db.query(SalaryStructure).filter(SalaryStructure.id == struct_comp.structure_id, SalaryStructure.organization_id == org_id).first()
    if not struct:
        raise NotFoundException("SalaryStructure", struct_comp.structure_id)
    db.delete(struct_comp)
    db.commit()


# ── Employee Compensation ───────────────────────────────────────────────────

def create_employee_compensation(db: Session, data: EmployeeCompensationCreate, org_id: int) -> EmployeeCompensation:
    comp = EmployeeCompensation(**data.model_dump(), organization_id=org_id)
    db.add(comp)
    db.commit()
    db.refresh(comp)
    return comp

def get_employee_compensations(db: Session, org_id: int, employee_id: Optional[int] = None) -> list[EmployeeCompensation]:
    query = db.query(EmployeeCompensation).filter(EmployeeCompensation.organization_id == org_id)
    if employee_id:
        query = query.filter(EmployeeCompensation.employee_id == employee_id)
    return query.all()

def get_employee_compensation(db: Session, comp_id: int, org_id: int) -> EmployeeCompensation:
    comp = db.query(EmployeeCompensation).filter(EmployeeCompensation.id == comp_id, EmployeeCompensation.organization_id == org_id).first()
    if not comp:
        raise NotFoundException("EmployeeCompensation", comp_id)
    return comp

def update_employee_compensation(db: Session, comp_id: int, data: EmployeeCompensationUpdate, org_id: int) -> EmployeeCompensation:
    comp = db.query(EmployeeCompensation).filter(EmployeeCompensation.id == comp_id, EmployeeCompensation.organization_id == org_id).first()
    if not comp:
        raise NotFoundException("EmployeeCompensation", comp_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(comp, key, value)
    db.commit()
    db.refresh(comp)
    return comp

def delete_employee_compensation(db: Session, comp_id: int, org_id: int) -> None:
    comp = db.query(EmployeeCompensation).filter(EmployeeCompensation.id == comp_id, EmployeeCompensation.organization_id == org_id).first()
    if not comp:
        raise NotFoundException("EmployeeCompensation", comp_id)
    db.query(SalaryRevision).filter(SalaryRevision.employee_compensation_id == comp_id).delete()
    db.delete(comp)
    db.commit()

# ── Salary Revisions ────────────────────────────────────────────────────────

def create_salary_revision(db: Session, data: SalaryRevisionCreate, org_id: int) -> SalaryRevision:
    emp_comp = db.query(EmployeeCompensation).filter(EmployeeCompensation.id == data.employee_compensation_id, EmployeeCompensation.organization_id == org_id).first()
    if not emp_comp:
        raise NotFoundException("EmployeeCompensation", data.employee_compensation_id)
    revision = SalaryRevision(**data.model_dump(), organization_id=org_id)
    db.add(revision)
    db.commit()
    db.refresh(revision)
    return revision

def get_salary_revisions(db: Session, org_id: int) -> list[SalaryRevision]:
    return db.query(SalaryRevision).filter(SalaryRevision.organization_id == org_id).all()

# ── Allowances ─────────────────────────────────────────────────────────────

def create_allowance(db: Session, data: AllowanceCreate, org_id: int) -> Allowance:
    allowance = Allowance(**data.model_dump(), organization_id=org_id)
    db.add(allowance)
    db.commit()
    db.refresh(allowance)
    return allowance

def get_allowances(db: Session, org_id: int) -> list[Allowance]:
    return db.query(Allowance).filter(Allowance.organization_id == org_id).all()

def update_allowance(db: Session, allowance_id: int, data: AllowanceUpdate, org_id: int) -> Allowance:
    allowance = db.query(Allowance).filter(Allowance.id == allowance_id, Allowance.organization_id == org_id).first()
    if not allowance:
        raise NotFoundException("Allowance", allowance_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(allowance, key, value)
    db.commit()
    db.refresh(allowance)
    return allowance

def delete_allowance(db: Session, allowance_id: int, org_id: int) -> None:
    allowance = db.query(Allowance).filter(Allowance.id == allowance_id, Allowance.organization_id == org_id).first()
    if not allowance:
        raise NotFoundException("Allowance", allowance_id)
    db.delete(allowance)
    db.commit()

# ── Benefits ───────────────────────────────────────────────────────────────

def create_benefit(db: Session, data: BenefitCreate, org_id: int) -> Benefit:
    benefit = Benefit(**data.model_dump(), organization_id=org_id)
    db.add(benefit)
    db.commit()
    db.refresh(benefit)
    return benefit

def get_benefits(db: Session, org_id: int) -> list[Benefit]:
    return db.query(Benefit).filter(Benefit.organization_id == org_id).all()

def update_benefit(db: Session, benefit_id: int, data: BenefitUpdate, org_id: int) -> Benefit:
    benefit = db.query(Benefit).filter(Benefit.id == benefit_id, Benefit.organization_id == org_id).first()
    if not benefit:
        raise NotFoundException("Benefit", benefit_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(benefit, key, value)
    db.commit()
    db.refresh(benefit)
    return benefit

def delete_benefit(db: Session, benefit_id: int, org_id: int) -> None:
    benefit = db.query(Benefit).filter(Benefit.id == benefit_id, Benefit.organization_id == org_id).first()
    if not benefit:
        raise NotFoundException("Benefit", benefit_id)
    db.delete(benefit)
    db.commit()

# ── Employee Benefits ───────────────────────────────────────────────────────

def create_employee_benefit(db: Session, data: EmployeeBenefitCreate, org_id: int) -> EmployeeBenefit:
    emp_benefit = EmployeeBenefit(**data.model_dump(), organization_id=org_id)
    db.add(emp_benefit)
    db.commit()
    db.refresh(emp_benefit)
    return emp_benefit

def get_employee_benefits(db: Session, org_id: int) -> list[EmployeeBenefit]:
    return db.query(EmployeeBenefit).filter(EmployeeBenefit.organization_id == org_id).all()

def delete_employee_benefit(db: Session, emp_benefit_id: int, org_id: int) -> None:
    emp_benefit = db.query(EmployeeBenefit).filter(EmployeeBenefit.id == emp_benefit_id, EmployeeBenefit.organization_id == org_id).first()
    if not emp_benefit:
        raise NotFoundException("EmployeeBenefit", emp_benefit_id)
    db.delete(emp_benefit)
    db.commit()


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

def check_and_seed_performance(db: Session):
    try:
        from app.modules.hr.models import (
            PerformanceGoal, PerformanceKpi, PerformanceReview, Appraisal,
            GoalStatus, RequestStatus, AppraisalStatus, Employee
        )
        from datetime import date
        
        goal_count = db.query(PerformanceGoal).count()
        review_count = db.query(PerformanceReview).count()
        appraisal_count = db.query(Appraisal).count()
        
        if goal_count > 0 or review_count > 0 or appraisal_count > 0:
            return
            
        employees = db.query(Employee).all()
        emp_ids = [e.id for e in employees] if employees else []
        if not emp_ids:
            fallback = Employee(
                email="demo.employee@zoiko.com",
                hashed_password="hashed_password",
                employee_code="ZK-9999",
                first_name="Demo",
                last_name="Employee",
                job_title="Software Engineer",
                date_of_joining=date(2026, 1, 1),
                is_active=True
            )
            db.add(fallback)
            db.commit()
            db.refresh(fallback)
            emp_ids = [fallback.id]
            
        num_emps = len(emp_ids)
        def get_emp_id(idx):
            return emp_ids[idx % num_emps]

        # Seed 10 Goals
        goals_data = [
            {"title": "Redesign corporate website for mobile first", "description": "Ensure responsive design and sub-second load times.", "goal_type": "okr", "quarter": "Q1 2026", "year": 2026, "progress": 85, "status": GoalStatus.ON_TRACK, "due_date": date(2026, 3, 31)},
            {"title": "Decrease API response latency by 30%", "description": "Optimize SQL queries and implement redis caching.", "goal_type": "kpi", "quarter": "Q1 2026", "year": 2026, "progress": 50, "status": GoalStatus.ON_TRACK, "due_date": date(2026, 3, 31)},
            {"title": "Obtain ISO 27001 Security Certification", "description": "Document all standard operating procedures and train employees.", "goal_type": "individual", "quarter": "Q2 2026", "year": 2026, "progress": 15, "status": GoalStatus.AT_RISK, "due_date": date(2026, 6, 30)},
            {"title": "Hire and onboard 5 senior engineers", "description": "Scale up engineering team for new features backlog.", "goal_type": "okr", "quarter": "Q1 2026", "year": 2026, "progress": 100, "status": GoalStatus.COMPLETED, "due_date": date(2026, 3, 15)},
            {"title": "Improve Customer Support CSAT to 95%", "description": "Decrease ticket response time and provide advanced training.", "goal_type": "kpi", "quarter": "Q1 2026", "year": 2026, "progress": 90, "status": GoalStatus.ON_TRACK, "due_date": date(2026, 3, 31)},
            {"title": "Reduce cloud infrastructure costs by 15%", "description": "Clean up unused resources and right-size ec2 instances.", "goal_type": "okr", "quarter": "Q1 2026", "year": 2026, "progress": 10, "status": GoalStatus.NOT_STARTED, "due_date": date(2026, 3, 31)},
            {"title": "Publish 4 tech blog posts", "description": "Enhance technical brand and share solutions with community.", "goal_type": "individual", "quarter": "Q2 2026", "year": 2026, "progress": 25, "status": GoalStatus.ON_TRACK, "due_date": date(2026, 6, 30)},
            {"title": "Migrate core microservices to Kubernetes", "description": "Achieve zero-downtime rolling updates and better resource use.", "goal_type": "okr", "quarter": "Q2 2026", "year": 2026, "progress": 65, "status": GoalStatus.ON_TRACK, "due_date": date(2026, 6, 30)},
            {"title": "Achieve 99.99% uptime for payment gateway", "description": "Setup multi-region replication and circuit breakers.", "goal_type": "kpi", "quarter": "Q1 2026", "year": 2026, "progress": 95, "status": GoalStatus.ON_TRACK, "due_date": date(2026, 3, 31)},
            {"title": "Conduct security audit on internal systems", "description": "Identify vulnerability vectors and patch outdated dependencies.", "goal_type": "individual", "quarter": "Q1 2026", "year": 2026, "progress": 100, "status": GoalStatus.COMPLETED, "due_date": date(2026, 2, 28)},
        ]
        
        seeded_goals = []
        for idx, gd in enumerate(goals_data):
            goal = PerformanceGoal(
                employee_id=get_emp_id(idx),
                **gd
            )
            db.add(goal)
            db.flush()
            seeded_goals.append(goal)
            
        for g in seeded_goals:
            kpi1 = PerformanceKpi(
                employee_id=g.employee_id,
                goal_id=g.id,
                name=f"Key Result 1 for {g.title[:20]}...",
                target_value=100.0,
                actual_value=float(g.progress),
                unit="%",
                weight=0.5,
                period=g.quarter
            )
            kpi2 = PerformanceKpi(
                employee_id=g.employee_id,
                goal_id=g.id,
                name=f"Milestone Check for {g.title[:20]}...",
                target_value=5.0,
                actual_value=round(g.progress / 20.0, 1),
                unit="milestones",
                weight=0.5,
                period=g.quarter
            )
            db.add(kpi1)
            db.add(kpi2)

        reviews_data = [
            {"cycle": "FY 2025 Annual", "rating": 5, "comments": "Outstanding performance this year, went above and beyond.", "status": RequestStatus.APPROVED},
            {"cycle": "FY 2025 Annual", "rating": 4, "comments": "Strong analytical skills, very dependable teammate.", "status": RequestStatus.APPROVED},
            {"cycle": "FY 2025 Annual", "rating": 3, "comments": "Meets expectations. Solid execution of core duties.", "status": RequestStatus.COMPLETED},
            {"cycle": "Q1 2026 Quarterly", "rating": 4, "comments": "Excellent start to the year. Exceeded Q1 delivery milestones.", "status": RequestStatus.PENDING},
            {"cycle": "Q1 2026 Quarterly", "rating": 3, "comments": "Good progress on objectives, needs to focus on communication.", "status": RequestStatus.PENDING},
            {"cycle": "FY 2025 Annual", "rating": 2, "comments": "Needs improvement in timeliness of delivery and technical depth.", "status": RequestStatus.COMPLETED},
            {"cycle": "FY 2025 Annual", "rating": 5, "comments": "Consistently demonstrates high technical leadership and mentors juniors.", "status": RequestStatus.APPROVED},
            {"cycle": "Q1 2026 Quarterly", "rating": 3, "comments": "On track. Needs to maintain momentum on goals.", "status": RequestStatus.PENDING},
            {"cycle": "FY 2025 Annual", "rating": 4, "comments": "Great contribution to the design system project.", "status": RequestStatus.APPROVED},
            {"cycle": "FY 2025 Annual", "rating": 1, "comments": "Significantly missed performance targets. Performance Improvement Plan initiated.", "status": RequestStatus.COMPLETED},
        ]
        
        for idx, rd in enumerate(reviews_data):
            emp_id = get_emp_id(idx)
            rev_id = get_emp_id(idx + 1)
            if emp_id == rev_id and num_emps > 1:
                rev_id = get_emp_id(idx + 2)
            review = PerformanceReview(
                employee_id=emp_id,
                reviewer_id=rev_id,
                **rd
            )
            db.add(review)

        appraisals_data = [
            {"cycle": "FY 2025 Cycle", "self_score": 4.5, "manager_score": 4.8, "final_score": 4.7, "recommendation": "promotion_bonus", "salary_hike": 15.0, "comments": "Excellent execution of roadmap projects, highly recommended for promotion.", "status": AppraisalStatus.APPROVED},
            {"cycle": "FY 2025 Cycle", "self_score": 4.0, "manager_score": 4.2, "final_score": 4.1, "recommendation": "bonus", "salary_hike": 10.0, "comments": "Consistently delivered robust solutions and showed great teamwork.", "status": AppraisalStatus.APPROVED},
            {"cycle": "FY 2025 Cycle", "self_score": 3.5, "manager_score": 3.5, "final_score": 3.5, "recommendation": "bonus", "salary_hike": 5.0, "comments": "Solid year of contributions. Keep up the steady work.", "status": AppraisalStatus.APPROVED},
            {"cycle": "FY 2025 Cycle", "self_score": 4.2, "manager_score": 4.5, "final_score": 4.4, "recommendation": "promotion", "salary_hike": 12.0, "comments": "Demonstrated strong leadership qualities, ready for the next level.", "status": AppraisalStatus.SUBMITTED},
            {"cycle": "FY 2025 Cycle", "self_score": 3.0, "manager_score": 3.0, "final_score": 3.0, "recommendation": None, "salary_hike": 3.0, "comments": "Meets expectations in all categories.", "status": AppraisalStatus.DRAFT},
            {"cycle": "FY 2025 Cycle", "self_score": 2.5, "manager_score": 2.8, "final_score": 2.7, "recommendation": "improvement_plan", "salary_hike": 0.0, "comments": "Performance fell short in multiple quarters. Focus on skill development.", "status": AppraisalStatus.APPROVED},
            {"cycle": "FY 2025 Cycle", "self_score": 4.8, "manager_score": 4.9, "final_score": 4.9, "recommendation": "promotion_bonus", "salary_hike": 18.0, "comments": "Exceptional year. Truly outstanding contributor and mentor.", "status": AppraisalStatus.APPROVED},
            {"cycle": "FY 2025 Cycle", "self_score": 3.8, "manager_score": 3.9, "final_score": 3.9, "recommendation": "bonus", "salary_hike": 8.0, "comments": "Great work on expanding domain expertise and delivering key tasks.", "status": AppraisalStatus.SUBMITTED},
            {"cycle": "FY 2025 Cycle", "self_score": 4.0, "manager_score": 4.0, "final_score": 4.0, "recommendation": "bonus", "salary_hike": 7.5, "comments": "Dependable developer who consistently meets targets.", "status": AppraisalStatus.APPROVED},
            {"cycle": "FY 2025 Cycle", "self_score": 2.0, "manager_score": 2.0, "final_score": 2.0, "recommendation": "improvement_plan", "salary_hike": 0.0, "comments": "Significant performance gaps identified. Performance Improvement Plan ongoing.", "status": AppraisalStatus.REJECTED},
        ]
        
        for idx, ad in enumerate(appraisals_data):
            emp_id = get_emp_id(idx)
            rev_id = get_emp_id(idx + 1)
            if emp_id == rev_id and num_emps > 1:
                rev_id = get_emp_id(idx + 2)
            appraisal = Appraisal(
                employee_id=emp_id,
                reviewer_id=rev_id,
                **ad
            )
            db.add(appraisal)

        db.commit()
    except Exception as e:
        print(f"Error during performance seeding: {e}")
        db.rollback()


def get_performance_dashboard(db: Session) -> dict:
    check_and_seed_performance(db)
    from app.modules.hr.models import (
        PerformanceReview, PerformanceGoal, PerformanceFeedback,
        Appraisal, RequestStatus, GoalStatus
    )
    total_reviews = db.query(PerformanceReview).count()
    pending_reviews = db.query(PerformanceReview).filter(PerformanceReview.status == RequestStatus.PENDING).count()
    completed_reviews = db.query(PerformanceReview).filter(PerformanceReview.status.in_([RequestStatus.APPROVED, RequestStatus.COMPLETED])).count()
    total_goals = db.query(PerformanceGoal).count()
    completed_goals = db.query(PerformanceGoal).filter(PerformanceGoal.status == GoalStatus.COMPLETED).count()
    total_feedback = db.query(PerformanceFeedback).count()
    total_appraisals = db.query(Appraisal).count()
    pending_appraisals = db.query(Appraisal).filter(Appraisal.status == "draft").count()
    return {
        "total_reviews": total_reviews,
        "pending_reviews": pending_reviews,
        "completed_reviews": completed_reviews,
        "total_goals": total_goals,
        "completed_goals": completed_goals,
        "total_feedback": total_feedback,
        "total_appraisals": total_appraisals,
        "pending_appraisals": pending_appraisals,
    }


def create_performance_goal(db: Session, data: PerformanceGoalCreate) -> PerformanceGoal:
    goal = PerformanceGoal(**data.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def get_performance_goals(db: Session, employee_id: Optional[int] = None) -> list[PerformanceGoal]:
    q = db.query(PerformanceGoal)
    if employee_id:
        q = q.filter(PerformanceGoal.employee_id == employee_id)
    return q.order_by(PerformanceGoal.created_at.desc()).all()


def get_performance_goal(db: Session, goal_id: int) -> PerformanceGoal:
    goal = db.query(PerformanceGoal).filter(PerformanceGoal.id == goal_id).first()
    if not goal:
        raise NotFoundException("PerformanceGoal", goal_id)
    return goal


def update_performance_goal(db: Session, goal_id: int, data: PerformanceGoalUpdate) -> PerformanceGoal:
    goal = get_performance_goal(db, goal_id)
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(goal, key, val)
    db.commit()
    db.refresh(goal)
    return goal


def delete_performance_goal(db: Session, goal_id: int) -> None:
    goal = get_performance_goal(db, goal_id)
    db.delete(goal)
    db.commit()


def create_performance_kpi(db: Session, data: PerformanceKpiCreate) -> PerformanceKpi:
    kpi = PerformanceKpi(**data.model_dump())
    db.add(kpi)
    db.commit()
    db.refresh(kpi)
    return kpi


def get_performance_kpis(db: Session, goal_id: Optional[int] = None, employee_id: Optional[int] = None) -> list[PerformanceKpi]:
    q = db.query(PerformanceKpi)
    if goal_id:
        q = q.filter(PerformanceKpi.goal_id == goal_id)
    if employee_id:
        q = q.filter(PerformanceKpi.employee_id == employee_id)
    return q.order_by(PerformanceKpi.created_at.desc()).all()


def get_performance_kpi(db: Session, kpi_id: int) -> PerformanceKpi:
    kpi = db.query(PerformanceKpi).filter(PerformanceKpi.id == kpi_id).first()
    if not kpi:
        raise NotFoundException("PerformanceKpi", kpi_id)
    return kpi


def update_performance_kpi(db: Session, kpi_id: int, data: PerformanceKpiUpdate) -> PerformanceKpi:
    kpi = get_performance_kpi(db, kpi_id)
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(kpi, key, val)
    db.commit()
    db.refresh(kpi)
    return kpi


def delete_performance_kpi(db: Session, kpi_id: int) -> None:
    kpi = get_performance_kpi(db, kpi_id)
    db.delete(kpi)
    db.commit()


def create_performance_feedback(db: Session, data: PerformanceFeedbackCreate) -> PerformanceFeedback:
    fb = PerformanceFeedback(**data.model_dump())
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


def get_performance_feedback(
    db: Session,
    employee_id: Optional[int] = None,
    reviewer_id: Optional[int] = None,
    review_id: Optional[int] = None,
) -> list[PerformanceFeedback]:
    q = db.query(PerformanceFeedback)
    if employee_id:
        q = q.filter(PerformanceFeedback.employee_id == employee_id)
    if reviewer_id:
        q = q.filter(PerformanceFeedback.reviewer_id == reviewer_id)
    if review_id:
        q = q.filter(PerformanceFeedback.review_id == review_id)
    return q.order_by(PerformanceFeedback.submitted_at.desc()).all()


def delete_performance_feedback(db: Session, fb_id: int) -> None:
    fb = db.query(PerformanceFeedback).filter(PerformanceFeedback.id == fb_id).first()
    if not fb:
        raise NotFoundException("PerformanceFeedback", fb_id)
    db.delete(fb)
    db.commit()


def create_appraisal(db: Session, data: AppraisalCreate) -> Appraisal:
    appraisal = Appraisal(**data.model_dump())
    db.add(appraisal)
    db.commit()
    db.refresh(appraisal)
    return appraisal


def get_appraisals(db: Session, employee_id: Optional[int] = None) -> list[Appraisal]:
    q = db.query(Appraisal)
    if employee_id:
        q = q.filter(Appraisal.employee_id == employee_id)
    return q.order_by(Appraisal.created_at.desc()).all()


def get_appraisal(db: Session, appraisal_id: int) -> Appraisal:
    a = db.query(Appraisal).filter(Appraisal.id == appraisal_id).first()
    if not a:
        raise NotFoundException("Appraisal", appraisal_id)
    return a


def update_appraisal(db: Session, appraisal_id: int, data: AppraisalUpdate) -> Appraisal:
    a = get_appraisal(db, appraisal_id)
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(a, key, val)
    db.commit()
    db.refresh(a)
    return a


def delete_appraisal(db: Session, appraisal_id: int) -> None:
    a = get_appraisal(db, appraisal_id)
    db.delete(a)
    db.commit()


def get_performance_analytics(db: Session) -> dict:
    check_and_seed_performance(db)
    from app.modules.hr.models import (
        PerformanceReview, PerformanceGoal, PerformanceFeedback,
        Appraisal, RequestStatus, GoalStatus
    )
    total_reviews = db.query(PerformanceReview).count()
    completed_reviews = db.query(PerformanceReview).filter(PerformanceReview.status == RequestStatus.COMPLETED).count()
    avg_rating = db.query(func.avg(PerformanceReview.rating)).scalar() or 0
    total_goals = db.query(PerformanceGoal).count()
    completed_goals = db.query(PerformanceGoal).filter(PerformanceGoal.status == GoalStatus.COMPLETED).count()
    total_feedback = db.query(PerformanceFeedback).count()
    total_appraisals = db.query(Appraisal).count()
    avg_final_score = db.query(func.avg(Appraisal.final_score)).scalar() or 0
    return {
        "avg_performance_score": round(float(avg_rating) * 20, 1),
        "goal_completion_rate": round((completed_goals / total_goals * 100) if total_goals else 0, 1),
        "review_completion_rate": round((completed_reviews / total_reviews * 100) if total_reviews else 0, 1),
        "avg_rating": round(float(avg_rating), 2),
        "feedback_count": total_feedback,
        "avg_appraisal_score": round(float(avg_final_score), 2),
        "total_reviews": total_reviews,
        "completed_reviews": completed_reviews,
        "pending_reviews": total_reviews - completed_reviews,
        "total_goals": total_goals,
        "completed_goals": completed_goals,
        "total_appraisals": total_appraisals,
    }


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


def get_performance_review(db: Session, review_id: int) -> PerformanceReview:
    review = db.query(PerformanceReview).filter(PerformanceReview.id == review_id).first()
    if not review:
        raise NotFoundException("PerformanceReview", review_id)
    return review


def update_performance_review(db: Session, review_id: int, data: PerformanceReviewCreate) -> PerformanceReview:
    review = get_performance_review(db, review_id)
    for key, val in data.model_dump().items():
        setattr(review, key, val)
    db.commit()
    db.refresh(review)
    return review


def delete_performance_review(db: Session, review_id: int) -> None:
    review = get_performance_review(db, review_id)
    db.delete(review)
    db.commit()


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