"""
modules/hr/service.py
---------------------
Business logic layer. This is WHERE the actual work happens.
"""

import logging
import os
from datetime import date, datetime
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

logger = logging.getLogger("zoiko")


from app.modules.hr.models import (
    Employee, Department, Organization, OrganizationStatus, EmployeeStatus, EmploymentType, UserRole,
    AttendanceRecord, LeaveRequest, LeaveTypeConfig, LeaveSetting, LeaveBalance,
    CompensationItem,
    PayGrade, CompensationBand, SalaryComponent, SalaryStructure,
    StructureComponent, EmployeeCompensation, SalaryRevision,
    Allowance, Benefit, EmployeeBenefit,
    ComplianceRecord, EngagementSurvey, EssRequest,
    OnboardingNewHire, OnboardingPreboardingTask, OnboardingDocument,
    OnboardingChecklist, OnboardingChecklistItem,
    OnboardingOrientation, OnboardingOrientationAttendee, OnboardingActivity,
    PerformanceReview,
    PerformanceGoal, PerformanceKpi, PerformanceFeedback, Appraisal,
    RecruitmentCandidate, TravelRequest, WorkforcePlan,
    RequestStatus, LeaveType,
    EmployeeProfile, EmployeeReporting, EmployeeLifecycle, EmployeeHistory,
    EmployeeProfile, EmployeeReporting, EmployeeLifecycle, EmployeeHistory,
    TravelApproval, TravelExpense, TravelReceipt, TravelPolicy, TravelSetting,
    HrDocument,
)
from app.modules.hr.schemas import (
    DepartmentCreate, DepartmentUpdate,
    LoginRequest, RegisterRequest,
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
    OnboardingNewHireCreate, OnboardingNewHireUpdate,
    OnboardingPreboardingTaskCreate, OnboardingPreboardingTaskUpdate,
    OnboardingDocumentCreate, OnboardingDocumentUpdate,
    OnboardingChecklistCreate, OnboardingChecklistUpdate, OnboardingChecklistAssignmentCreate,
    OnboardingOrientationCreate, OnboardingOrientationUpdate,
    OnboardingOrientationAttendeeCreate, OnboardingOrientationAttendeeUpdate,
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
    TravelRequestCreate, TravelRequestUpdate, TravelRequestResponse,
    TravelApprovalCreate, TravelApprovalUpdate, TravelApprovalResponse,
    TravelExpenseCreate, TravelExpenseUpdate, TravelExpenseResponse,
    TravelReceiptCreate, TravelReceiptResponse,
    TravelPolicyCreate, TravelPolicyUpdate, TravelPolicyResponse,
    TravelSettingUpdate, TravelSettingResponse,
    TravelDashboardStats,
    WorkforcePlanCreate,
    EmployeeProfileCreate, EmployeeProfileUpdate,
    EmployeeReportingCreate, EmployeeReportingUpdate,
    EmployeeLifecycleCreate, EmployeeLifecycleUpdate,
    ChangeManagerRequest, ConfirmProbationRequest,
    PromoteEmployeeRequest, TransferEmployeeRequest,
    ResignationRequest, ExitEmployeeRequest, EmployeeExportRequest,
    EmployeeProfileCreate, EmployeeProfileUpdate,
    EmployeeReportingCreate, EmployeeReportingUpdate,
    EmployeeLifecycleCreate, EmployeeLifecycleUpdate,
    ChangeManagerRequest, ConfirmProbationRequest,
    PromoteEmployeeRequest, TransferEmployeeRequest,
    ResignationRequest, ExitEmployeeRequest, EmployeeExportRequest,DesignationCreate, DesignationUpdate
)
from app.core.exceptions import (
    NotFoundException, AlreadyExistsException,
    UnauthorizedException, BadRequestException
)
from app.modules.employee.service import (
    login_employee, register_enterprise,
    _generate_employee_code, _generate_temp_password, _role_to_default_title,
    create_organization_user, get_organization_users, get_organization_user,
    update_organization_user, deactivate_organization_user, activate_organization_user,
    reset_user_password,
    create_employee, get_all_employees, get_employees,
    get_employee_by_id, update_employee, deactivate_employee,
    get_employee_dashboard,
    get_employee_profile, create_employee_profile, update_employee_profile,
    get_employee_reporting, create_employee_reporting, update_employee_reporting,
    get_employee_lifecycle, create_employee_lifecycle_event, update_employee_lifecycle_event,
    get_employee_history, create_employee_history_entry,
    get_org_chart,
    change_manager, confirm_probation, promote_employee, transfer_employee,
    resign_employee, exit_employee,
    get_employee_reports, export_employee_reports,
)


# ════════════════════════════════════════════════════════════════════════════
# HELPER — Auto-generate employee code
# ════════════════════════════════════════════════════════════════════════════

def _generate_employee_code(db: Session) -> str:
    from sqlalchemy import func
    max_id = db.query(func.max(Employee.id)).scalar()
    next_number = (max_id + 1) if max_id else 1
    return f"ZK-{next_number:05d}"


# Predefined role-based permissions
ROLE_PERMISSIONS = {
    "super_admin": ["all", "manage_platforms", "manage_organizations", "view_reports", "manage_users"],
    "admin": ["manage_organization", "manage_users", "view_payroll", "manage_hr", "manage_departments", "manage_employees", "manage_attendance", "manage_leave", "manage_assets", "manage_learning", "manage_performance", "manage_recruitment", "manage_ess", "manage_travel", "manage_compliance"],
    "hr_admin": ["manage_hr", "manage_departments", "manage_employees", "manage_attendance", "manage_leave", "manage_assets", "manage_learning", "manage_performance", "manage_recruitment", "manage_ess", "manage_travel", "manage_compliance"],
    "hr_manager": ["manage_hr", "manage_departments", "manage_employees", "manage_attendance", "manage_leave", "manage_assets", "manage_learning", "manage_performance", "manage_recruitment", "manage_ess", "manage_travel", "manage_compliance"],
    "manager": ["view_subordinates", "approve_attendance", "approve_leave", "manage_performance"],
    "employee": ["view_profile", "request_leave", "clock_in_out", "view_assets", "ess"],
}

def login_employee(db: Session, data: LoginRequest) -> dict:
    # STEP 1: Find user by email (User exists check)
    employee = db.query(Employee).filter(Employee.email == data.email).first()
    if not employee:
        logger.warning(f"[AUTH] User not found: email={data.email}")
        raise UnauthorizedException("Invalid email or password.")

    logger.info(f"[AUTH] User found: id={employee.id}, email={employee.email}, "
                f"is_active={employee.is_active}, status={employee.status}, "
                f"organization_id={employee.organization_id}, role={employee.role}")

    # STEP 2: Verify Organization and Organization Status
    org = None
    if employee.organization_id:
        org = db.query(Organization).filter(Organization.id == employee.organization_id).first()
        if not org:
            logger.warning(f"[AUTH] Organization not found: id={employee.organization_id} for user {employee.email}")
            raise UnauthorizedException("Your organization account does not exist.")
        
        logger.info(f"[AUTH] Organization found: id={org.id}, name={org.name}, status={org.status}, is_active={org.is_active}")
        
        if not org.is_active or org.status not in [OrganizationStatus.ACTIVE, OrganizationStatus.APPROVED]:
            logger.warning(f"[AUTH] Login blocked: org inactive or status={org.status} for user {employee.email}")
            if org.status == OrganizationStatus.PENDING:
                raise UnauthorizedException("Your organization is awaiting Super Admin approval. Please try again after approval.")
            elif org.status == OrganizationStatus.REJECTED:
                reason = getattr(org, "rejection_reason", None)
                msg = "Your organization registration has been rejected."
                if reason:
                    msg += f" Reason: {reason}"
                raise UnauthorizedException(msg)
            elif org.status == OrganizationStatus.ON_HOLD:
                raise UnauthorizedException("Your organization account is currently on hold. Please contact support.")
            elif org.status == OrganizationStatus.SUSPENDED:
                raise UnauthorizedException("Your organization has been suspended. Please contact support.")
            else:
                raise UnauthorizedException("Your organization account has been deactivated.")
            
        logger.info(f"[AUTH] Organization status OK: {org.status} for user {employee.email}")
    else:
        # Orphan user check
        if employee.role != UserRole.SUPER_ADMIN:
            logger.warning(f"[AUTH] Login blocked: Non-superadmin user has no organization_id (orphan user).")
            raise UnauthorizedException("Your account is not associated with any organization.")

    # STEP 3: Verify User Status (User active check)
    if not employee.is_active:
        logger.warning(f"[AUTH] Login blocked: user is_active={employee.is_active} for email={employee.email}")
        raise UnauthorizedException("Your account has been deactivated.")
    if employee.status == EmployeeStatus.DEACTIVATED:
        logger.warning(f"[AUTH] Login blocked: user status={employee.status} for email={employee.email}")
        raise UnauthorizedException("Your account has been deactivated.")
    if employee.status == EmployeeStatus.LOCKED:
        logger.warning(f"[AUTH] Login blocked: user LOCKED for email={employee.email}")
        raise UnauthorizedException("Your account has been locked by the administrator.")

    # STEP 4: Verify Password hash (Password hash valid check)
    password_valid = verify_password(data.password, employee.hashed_password)
    if not password_valid:
        logger.warning(f"[AUTH] Invalid password for user: email={data.email}, id={employee.id}")
        raise UnauthorizedException("Invalid email or password.")

    logger.info(f"[AUTH] Password valid for user: email={data.email}, id={employee.id}")

    # STEP 5: Verify Role
    role_val = employee.role.value if hasattr(employee.role, "value") else str(employee.role)
    if not role_val:
        logger.warning(f"[AUTH] Login blocked: user has invalid/empty role.")
        raise UnauthorizedException("User role is invalid.")

    # STEP 6: Generate JWT (with organization_id, role, permissions, tenant_id, organization_code)
    org_code = org.code if org else None
    
    token = create_access_token(data={
        "sub": employee.email,
        "role": role_val,
        "id": employee.id,
        "organization_id": employee.organization_id,
        "permissions": ROLE_PERMISSIONS.get(role_val, []),
        "tenant_id": str(employee.organization_id) if employee.organization_id else None,
        "organization_code": org_code,
    })

    refresh_token = create_access_token(
        data={"sub": employee.email, "id": employee.id},
        expires_delta=timedelta(days=7),
    )

    logger.info(f"[AUTH] Login successful: email={employee.email}, id={employee.id}, role={employee.role}")

    return {
        "access_token": token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "employee": employee,
    }


def register_enterprise(db: Session, data: RegisterRequest) -> dict:
    """Register a new organization with an admin employee (PENDING approval)."""
    existing = db.query(Employee).filter(Employee.email == data.email).first()
    if existing:
        raise AlreadyExistsException("Employee", "email")

    org_code = data.organization[:50].upper().replace(" ", "_")
    suffix = 1
    while db.query(Organization).filter(Organization.code == org_code).first():
        org_code = f"{data.organization[:45].upper().replace(' ', '_')}_{suffix}"
        suffix += 1

    org = Organization(name=data.organization, code=org_code, status=OrganizationStatus.PENDING)
    db.add(org)
    db.commit()
    db.refresh(org)

    dept_code = f"MGMT_{org.id}"
    dept = Department(name="Management", code=dept_code, description="Company management", organization_id=org.id)
    db.add(dept)
    db.commit()
    db.refresh(dept)

    name_parts = data.name.strip().split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else "Admin"

    employee = Employee(
        email=data.email,
        hashed_password=hash_password(data.password),
        role=UserRole.ADMIN,
        is_active=True,
        first_name=first_name,
        last_name=last_name,
        phone="",
        employee_code=_generate_employee_code(db),
        job_title="System Administrator",
        employment_type=EmploymentType.FULL_TIME,
        status=EmployeeStatus.ACTIVE,
        date_of_joining=date.today(),
        department_id=dept.id,
        organization_id=org.id,
    )
    db.add(employee)
    db.flush()
    employee.employee_code = f"ZK-{employee.id:05d}"
    db.commit()
    db.refresh(employee)

    # Generate audit log
    from app.modules.super_admin.models import AuditLog, AuditAction, Notification
    audit = AuditLog(
        action=AuditAction.CREATE,
        entity_type="Organization",
        entity_id=org.id,
        performed_by=employee.id,
        performed_by_email=employee.email,
        details={"organization": org.name, "code": org.code, "status": "PENDING"},
    )
    db.add(audit)

    # Generate notification for super admins
    notification = Notification(
        title="New Organization Registration",
        message=f"Organization '{org.name}' has registered and is awaiting approval.",
        notification_type="org_registration",
        priority="high",
        target_org_id=org.id,
        target_user_id=employee.id,
    )
    db.add(notification)
    db.commit()

    return {
        "message": "Organization registered successfully. Awaiting Super Admin approval.",
        "organization_id": org.id,
        "organization_name": org.name,
    }


# ════════════════════════════════════════════════════════════════════════════
# USER MANAGEMENT SERVICE (Organization Admin)
# ════════════════════════════════════════════════════════════════════════════

def _generate_temp_password(length: int = 12) -> str:
    """Generate a cryptographically reasonable temporary password."""
    import secrets
    import string
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


def create_organization_user(
    db: Session,
    data: "UserCreateRequest",
    organization_id: int,
    created_by_id: int,
) -> Employee:
    """Create a user within the caller's organization.
    
    Only Organization Admin and Super Admin can call this.
    organization_id is injected server-side from the JWT token.
    """
    existing = db.query(Employee).filter(Employee.email == data.email).first()
    if existing:
        raise AlreadyExistsException("User", "email")

    temp_password = _generate_temp_password()
    role = data.role

    employee = Employee(
        email=data.email,
        hashed_password=hash_password(temp_password),
        employee_code=_generate_employee_code(db),
        role=role,
        is_active=True,
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone or "",
        job_title=_role_to_default_title(role),
        employment_type=EmploymentType.FULL_TIME,
        status=EmployeeStatus.ACTIVE,
        date_of_joining=date.today(),
        organization_id=organization_id,
        created_by=created_by_id,
    )
    db.add(employee)
    db.flush()
    employee.employee_code = f"ZK-{employee.id:05d}"
    db.commit()
    db.refresh(employee)

    return employee, temp_password


def _role_to_default_title(role: UserRole) -> str:
    titles = {
        UserRole.ADMIN: "Organization Administrator",
        UserRole.HR_ADMIN: "HR Administrator",
        UserRole.EMPLOYEE: "Employee",
        UserRole.HR_MANAGER: "HR Manager",
        UserRole.MANAGER: "Manager",
        UserRole.SUPER_ADMIN: "Super Administrator",
    }
    return titles.get(role, "Employee")
def _normalize_role(role_input) -> UserRole:
    """Convert any role input (string or enum) to a proper UserRole enum value."""
    if isinstance(role_input, UserRole):
        return role_input
    
    if isinstance(role_input, str):
        normalized = UserRole(role_input.lower() if role_input.lower() in [v.lower() for v in UserRole] else role_input)
        return normalized
    
    raise ValueError(f"Invalid role: {role_input}")


def get_organization_users(
    db: Session,
    organization_id: int,
    search: Optional[str] = None,
    role: Optional[UserRole] = None,
    status: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
) -> dict:
    """List users within an organization with optional filtering/pagination."""
    per_page = min(per_page, 100)
    query = db.query(Employee).filter(Employee.organization_id == organization_id)

    if search:
        term = f"%{search}%"
        query = query.filter(
            (Employee.first_name.ilike(term)) |
            (Employee.last_name.ilike(term)) |
            (Employee.email.ilike(term)) |
            (Employee.employee_code.ilike(term))
        )

    if role:
        query = query.filter(Employee.role == role)

    if status:
        if status == "active":
            query = query.filter(Employee.is_active == True)
        elif status == "inactive":
            query = query.filter(Employee.is_active == False)

    total = query.count()
    users = query.order_by(Employee.created_at.desc()).offset(
        (page - 1) * per_page
    ).limit(per_page).all()

    return {"total": total, "page": page, "per_page": per_page, "items": users}


def get_organization_user(
    db: Session,
    user_id: int,
    organization_id: int,
) -> Employee:
    """Get a single user by ID within the given organization."""
    user = db.query(Employee).filter(
        Employee.id == user_id,
        Employee.organization_id == organization_id,
    ).first()
    if not user:
        raise NotFoundException("User", user_id)
    return user


def update_organization_user(
    db: Session,
    user_id: int,
    data: "UserUpdateRequest",
    organization_id: int,
    updated_by_id: int,
) -> Employee:
    """Update a user within the given organization."""
    user = get_organization_user(db, user_id, organization_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    user.updated_by = updated_by_id
    db.commit()
    db.refresh(user)
    return user


def deactivate_organization_user(
    db: Session,
    user_id: int,
    organization_id: int,
    updated_by_id: int,
) -> Employee:
    """Soft-delete (deactivate) a user."""
    user = get_organization_user(db, user_id, organization_id)
    user.is_active = False
    user.status = EmployeeStatus.DEACTIVATED
    user.updated_by = updated_by_id
    db.commit()
    db.refresh(user)
    return user


def activate_organization_user(
    db: Session,
    user_id: int,
    organization_id: int,
    updated_by_id: int,
) -> Employee:
    """Activate a previously deactivated user."""
    user = get_organization_user(db, user_id, organization_id)
    user.is_active = True
    user.status = EmployeeStatus.ACTIVE
    user.updated_by = updated_by_id
    db.commit()
    db.refresh(user)
    return user


def reset_user_password(
    db: Session,
    user_id: int,
    organization_id: int,
    updated_by_id: int,
) -> tuple[Employee, str]:
    """Reset a user's password to a new temporary password."""
    user = get_organization_user(db, user_id, organization_id)
    temp_password = _generate_temp_password()
    user.hashed_password = hash_password(temp_password)
    user.updated_by = updated_by_id
    db.commit()
    db.refresh(user)
    return user, temp_password



# ════════════════════════════════════════════════════════════════════════════
# DEPARTMENT SERVICE
# ════════════════════════════════════════════════════════════════════════════

def create_department(db: Session, data: DepartmentCreate, organization_id: int) -> Department:
    existing = db.query(Department).filter(
        Department.name.ilike(data.name),
        Department.organization_id == organization_id
    ).first()
    if existing:
        raise AlreadyExistsException("Department", "name")

    existing_code = db.query(Department).filter(
        Department.code.ilike(data.code),
        Department.organization_id == organization_id
    ).first()
    if existing_code:
        raise AlreadyExistsException("Department", "code")

    dept = Department(**data.model_dump(), organization_id=organization_id)
    db.add(dept)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AlreadyExistsException("Department", field="code")
    db.refresh(dept)
    return dept


def get_department_by_id(db: Session, dept_id: int, organization_id: int) -> Department:
    dept = db.query(Department).filter(
        Department.id == dept_id,
        Department.organization_id == organization_id
    ).first()
    if not dept:
        raise NotFoundException("Department", dept_id)
    return dept


def update_department(db: Session, dept_id: int, data: DepartmentUpdate, organization_id: int) -> Department:
    dept = get_department_by_id(db, dept_id, organization_id)
    update_data = data.model_dump(exclude_unset=True)
    
    if "name" in update_data:
        existing = db.query(Department).filter(
            Department.name.ilike(update_data["name"]),
            Department.id != dept_id,
            Department.organization_id == organization_id
        ).first()
        if existing:
            raise AlreadyExistsException("Department", "name")

    for field, value in update_data.items():
        setattr(dept, field, value)

    db.commit()
    db.refresh(dept)
    return dept


def delete_department(db: Session, dept_id: int, organization_id: int) -> None:
    dept = get_department_by_id(db, dept_id, organization_id)
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


    # modules/hr/service.py

def get_all_departments(db: Session, organization_id: int) -> List[dict]:
    departments = db.query(Department).filter(
        Department.is_active == True,
        Department.organization_id == organization_id
    ).all()
    
    result = []
    for dept in departments:
        # Dynamically append active structural stats contextually 
        active_emp_count = db.query(Employee).filter(
            Employee.department_id == dept.id,
            Employee.status == EmployeeStatus.ACTIVE
        ).count()
        
        dept_dict = {
            "id": dept.id,
            "name": dept.name,
            "code": dept.code,
            "description": dept.description,
            "is_active": dept.is_active,
            "created_at": dept.created_at,
            "head": dept.head,
            "budget": dept.budget,
            "spent_budget": dept.spent_budget,
            "establishment_year": dept.establishment_year,
            "parent_id": dept.parent_id,
            "organization_id": dept.organization_id,
            "employee_count": active_emp_count  # Bind employee count directly
        }
        result.append(dept_dict)
        
    return result


# ════════════════════════════════════════════════════════════════════════════════
# EMPLOYEE MANAGEMENT SERVICE
# ════════════════════════════════════════════════════════════════════════════════

def get_employee_dashboard(db: Session, organization_id: Optional[int] = None) -> dict:
    base_filter = [Employee.organization_id == organization_id] if organization_id else []

    total = db.query(Employee).filter(*base_filter).count()
    active = db.query(Employee).filter(*base_filter, Employee.status == EmployeeStatus.ACTIVE).count()
    inactive = db.query(Employee).filter(*base_filter, Employee.status != EmployeeStatus.ACTIVE).count()
    
    lc_filter = [EmployeeLifecycle.organization_id == organization_id] if organization_id else []
    probation = db.query(EmployeeLifecycle).filter(
        *lc_filter,
        EmployeeLifecycle.event_type == "probation_start",
        EmployeeLifecycle.status == "pending"
    ).count()
    
    from datetime import date
    from sqlalchemy import extract
    new_hires_this_month = db.query(Employee).filter(
        *base_filter,
        extract("month", Employee.date_of_joining) == extract("month", date.today()),
        extract("year", Employee.date_of_joining) == extract("year", date.today())
    ).count()
    
    exits_this_month = db.query(Employee).filter(
        *base_filter,
        extract("month", Employee.updated_at) == extract("month", date.today()),
        extract("year", Employee.updated_at) == extract("year", date.today()),
        Employee.status == EmployeeStatus.TERMINATED
    ).count()

    dept_breakdown = (
        db.query(Department.name, func.count(Employee.id))
        .join(Employee, Employee.department_id == Department.id, isouter=True)
        .filter(*base_filter, Employee.status == EmployeeStatus.ACTIVE)
        .group_by(Department.name)
        .all()
    )
    
    designation_breakdown = (
        db.query(Employee.job_title, func.count(Employee.id))
        .filter(*base_filter, Employee.status == EmployeeStatus.ACTIVE)
        .group_by(Employee.job_title)
        .all()
    )
    
    location_breakdown = (
        db.query(Employee.address, func.count(Employee.id))
        .filter(*base_filter, Employee.status == EmployeeStatus.ACTIVE, Employee.address != None)
        .group_by(Employee.address)
        .all()
    )
    
    recent_lifecycle_events = []
    lifecycle_query = db.query(
        Employee.id, Employee.first_name, Employee.last_name, 
        EmployeeLifecycle.event_type, EmployeeLifecycle.event_date, 
        EmployeeLifecycle.status
    ).join(
        EmployeeLifecycle, Employee.id == EmployeeLifecycle.employee_id
    ).filter(*lc_filter).order_by(
        EmployeeLifecycle.created_at.desc()
    ).limit(10)
    
    for emp_id, first_name, last_name, event_type, event_date, status in lifecycle_query.all():
        recent_lifecycle_events.append({
            "employee_id": emp_id,
            "employee_name": f"{first_name} {last_name}",
            "event_type": event_type,
            "event_date": event_date,
            "status": status
        })
    
    upcoming_probation_end = []
    for emp_id, first_name, last_name, event_date in db.query(
        Employee.id, Employee.first_name, Employee.last_name,
        EmployeeLifecycle.event_date
    ).join(
        EmployeeLifecycle, Employee.id == EmployeeLifecycle.employee_id
    ).filter(
        *lc_filter,
        EmployeeLifecycle.event_type == "probation_end",
        EmployeeLifecycle.status == "pending"
    ).order_by(EmployeeLifecycle.event_date).limit(5).all():
        upcoming_probation_end.append({
            "employee_id": emp_id,
            "employee_name": f"{first_name} {last_name}",
            "probation_end_date": event_date
        })
    
    upcoming_confirmations = []
    for emp_id, first_name, last_name, event_date in db.query(
        Employee.id, Employee.first_name, Employee.last_name,
        EmployeeLifecycle.event_date
    ).join(
        EmployeeLifecycle, Employee.id == EmployeeLifecycle.employee_id
    ).filter(
        *lc_filter,
        EmployeeLifecycle.event_type == "confirmation",
        EmployeeLifecycle.status == "pending"
    ).order_by(EmployeeLifecycle.event_date).limit(5).all():
        upcoming_confirmations.append({
            "employee_id": emp_id,
            "employee_name": f"{first_name} {last_name}",
            "confirmation_date": event_date
        })
    
    upcoming_anniversaries = []
    for emp_id, first_name, last_name, joining_date in db.query(
        Employee.id, Employee.first_name, Employee.last_name,
        Employee.date_of_joining
    ).filter(
        *base_filter,
        Employee.status == EmployeeStatus.ACTIVE,
        Employee.date_of_birth != None
    ).order_by(
        extract("month", Employee.date_of_birth),
        extract("day", Employee.date_of_birth)
    ).limit(5).all():
        from datetime import datetime
        today = datetime.now().date()
        next_birthday = datetime(today.year, joining_date.month, joining_date.day).date()
        if next_birthday < today:
            next_birthday = datetime(today.year + 1, joining_date.month, joining_date.day).date()
        
        upcoming_anniversaries.append({
            "employee_id": emp_id,
            "employee_name": f"{first_name} {last_name}",
            "next_birthday": next_birthday,
            "join_date": joining_date
        })
    
    return {
        "total_employees": total,
        "active_employees": active,
        "inactive_employees": inactive,
        "on_probation": probation,
        "new_hires_this_month": new_hires_this_month,
        "exits_this_month": exits_this_month,
        "department_distribution": [{"department": d, "count": c} for d, c in dept_breakdown],
        "designation_distribution": [{"designation": d, "count": c} for d, c in designation_breakdown],
        "location_distribution": [{"location": l, "count": c} for l, c in location_breakdown],
        "lifecycle_events": recent_lifecycle_events,
        "upcoming_probation_end": upcoming_probation_end,
        "upcoming_confirmations": upcoming_confirmations,
        "upcoming_anniversaries": upcoming_anniversaries,
    }


def get_employees(
    db: Session,
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    department_id: Optional[int] = None,
    status: Optional[EmployeeStatus] = None,
    employment_type: Optional[EmploymentType] = None,
    organization_id: Optional[int] = None,
) -> dict:
    per_page = min(per_page, 10000)
    query = db.query(Employee)

    if organization_id:
        query = query.filter(Employee.organization_id == organization_id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Employee.first_name.ilike(search_term)) |
            (Employee.last_name.ilike(search_term))  |
            (Employee.email.ilike(search_term))      |
            (Employee.employee_code.ilike(search_term)) |
            (Employee.job_title.ilike(search_term))
        )

    if department_id:
        query = query.filter(Employee.department_id == department_id)

    if status:
        query = query.filter(Employee.status == status)

    if employment_type:
        query = query.filter(Employee.employment_type == employment_type)

    total = query.count()
    employees = query.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "items":    employees,
    }


def get_employee_profile(db: Session, employee_id: int) -> EmployeeProfile:
    profile = db.query(EmployeeProfile).filter(EmployeeProfile.employee_id == employee_id).first()
    if not profile:
        raise NotFoundException("EmployeeProfile", employee_id)
    return profile


def create_employee_profile(db: Session, data: EmployeeProfileCreate) -> EmployeeProfile:
    profile = EmployeeProfile(**data.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_employee_profile(db: Session, employee_id: int, data: EmployeeProfileUpdate) -> EmployeeProfile:
    profile = db.query(EmployeeProfile).filter(EmployeeProfile.employee_id == employee_id).first()
    if not profile:
        raise NotFoundException("EmployeeProfile", employee_id)
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    db.commit()
    db.refresh(profile)
    return profile


def get_employee_reporting(db: Session, employee_id: int) -> EmployeeReporting:
    reporting = db.query(EmployeeReporting).filter(EmployeeReporting.employee_id == employee_id).first()
    if not reporting:
        raise NotFoundException("EmployeeReporting", employee_id)
    return reporting


def create_employee_reporting(db: Session, data: EmployeeReportingCreate) -> EmployeeReporting:
    reporting = EmployeeReporting(**data.model_dump())
    db.add(reporting)
    db.commit()
    db.refresh(reporting)
    return reporting


def update_employee_reporting(db: Session, employee_id: int, data: EmployeeReportingUpdate) -> EmployeeReporting:
    reporting = get_employee_reporting(db, employee_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(reporting, field, value)
    db.commit()
    db.refresh(reporting)
    return reporting


def get_employee_lifecycle(db: Session, employee_id: Optional[int] = None, organization_id: Optional[int] = None) -> list[EmployeeLifecycle]:
    query = db.query(EmployeeLifecycle)
    if organization_id:
        query = query.filter(EmployeeLifecycle.organization_id == organization_id)
    if employee_id:
        query = query.filter(EmployeeLifecycle.employee_id == employee_id)
    return query.order_by(EmployeeLifecycle.event_date.desc()).all()


def create_employee_lifecycle_event(db: Session, data: EmployeeLifecycleCreate) -> EmployeeLifecycle:
    event = EmployeeLifecycle(**data.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def update_employee_lifecycle_event(db: Session, event_id: int, data: EmployeeLifecycleUpdate) -> EmployeeLifecycle:
    event = db.query(EmployeeLifecycle).filter(EmployeeLifecycle.id == event_id).first()
    if not event:
        raise NotFoundException("EmployeeLifecycle", event_id)
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)
    
    db.commit()
    db.refresh(event)
    return event


def get_employee_history(db: Session, employee_id: int) -> list[EmployeeHistory]:
    return db.query(EmployeeHistory).filter(
        EmployeeHistory.employee_id == employee_id
    ).order_by(EmployeeHistory.created_at.desc()).all()


def create_employee_history_entry(db: Session, employee_id: int, field_name: str, old_value: str, new_value: str, changed_by: Optional[int] = None, change_reason: Optional[str] = None) -> EmployeeHistory:
    history = EmployeeHistory(
        employee_id=employee_id,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        changed_by=changed_by,
        change_reason=change_reason
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    return history


def get_org_chart(db: Session, organization_id: int) -> dict:
    employees = db.query(
        Employee.id, Employee.first_name, Employee.last_name,
        Employee.job_title, Employee.department_id, Employee.status
    ).filter(
        Employee.organization_id == organization_id,
        Employee.status == EmployeeStatus.ACTIVE
    ).all()

    reporting = db.query(
        EmployeeReporting.employee_id, EmployeeReporting.manager_id
    ).filter(
        EmployeeReporting.organization_id == organization_id
    ).all()

    report_map = {r.employee_id: r.manager_id for r in reporting}

    departments = db.query(
        Department.id, Department.name
    ).filter(
        Department.id.in_([e.department_id for e in employees if e.department_id])
    ).all()

    dept_map = {d.id: d.name for d in departments}

    employee_map = {}
    for emp in employees:
        employee_map[emp.id] = {
            "id": emp.id,
            "name": f"{emp.first_name} {emp.last_name}",
            "job_title": emp.job_title,
            "department": dept_map.get(emp.department_id) if emp.department_id else None,
            "manager_id": report_map.get(emp.id),
            "status": emp.status,
            "children": []
        }

    reporting_structure = []
    for emp in employees:
        manager_id = report_map.get(emp.id)
        if manager_id:
            if manager_id in employee_map:
                employee_map[emp.id]["manager_name"] = employee_map[manager_id]["name"]
                employee_map[manager_id]["children"].append(employee_map[emp.id])
        else:
            reporting_structure.append(employee_map[emp.id])

    return {
        "employees": list(employee_map.values()),
        "reporting_structure": reporting_structure,
        "departments": dept_map
    }


def change_manager(db: Session, data: ChangeManagerRequest) -> Employee:
    employee = get_employee_by_id(db, data.employee_id)
    
    reporting = db.query(EmployeeReporting).filter(
        EmployeeReporting.employee_id == data.employee_id
    ).first()
    
    old_manager_id = reporting.manager_id if reporting else None
    
    if not reporting:
        reporting = EmployeeReporting(
            employee_id=data.employee_id,
            organization_id=employee.organization_id or 1,
            manager_id=data.new_manager_id,
            effective_from=date.today()
        )
        db.add(reporting)
    else:
        reporting.manager_id = data.new_manager_id
    
    db.commit()
    
    create_employee_history_entry(
        db, data.employee_id, "manager_id",
        str(old_manager_id), str(data.new_manager_id),
        change_reason=data.reason
    )
    
    return employee


def confirm_probation(db: Session, data: ConfirmProbationRequest, organization_id: Optional[int] = None) -> EmployeeLifecycle:
    employee = get_employee_by_id(db, data.employee_id)
    
    employee.status = EmployeeStatus.ACTIVE
    employee.confirmation_date = data.confirmation_date
    
    event = EmployeeLifecycle(
        employee_id=data.employee_id,
        organization_id=employee.organization_id,
        event_type="confirmation",
        event_date=data.confirmation_date,
        status="completed",
        reason=data.notes
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    
    return event


def promote_employee(db: Session, data: PromoteEmployeeRequest, organization_id: Optional[int] = None) -> EmployeeLifecycle:
    employee = get_employee_by_id(db, data.employee_id)
    
    if data.new_designation_id:
        employee.designation_id = data.new_designation_id
    if data.new_salary:
        employee.basic_salary = data.new_salary
    
    event = EmployeeLifecycle(
        employee_id=data.employee_id,
        organization_id=employee.organization_id,
        event_type="promotion",
        event_date=data.effective_date,
        status="completed",
        new_value={"designation_id": data.new_designation_id, "salary": str(data.new_salary)},
        reason=data.reason
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    
    return event


def transfer_employee(db: Session, data: TransferEmployeeRequest, organization_id: Optional[int] = None) -> EmployeeLifecycle:
    employee = get_employee_by_id(db, data.employee_id)
    
    if data.new_department_id:
        employee.department_id = data.new_department_id
    if data.new_manager_id:
        employee.reporting_manager_id = data.new_manager_id
    
    event = EmployeeLifecycle(
        employee_id=data.employee_id,
        organization_id=employee.organization_id,
        event_type="transfer",
        event_date=data.effective_date,
        status="completed",
        new_value={
            "department_id": data.new_department_id,
            "manager_id": data.new_manager_id,
            "location": data.new_location
        },
        reason=data.reason
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    
    return event


def resign_employee(db: Session, data: ResignationRequest, organization_id: Optional[int] = None) -> EmployeeLifecycle:
    employee = get_employee_by_id(db, data.employee_id)
    
    employee.status = EmployeeStatus.RESIGNED
    employee.is_active = False
    
    event = EmployeeLifecycle(
        employee_id=data.employee_id,
        organization_id=employee.organization_id,
        event_type="resignation",
        event_date=data.resignation_date,
        status="completed",
        new_value={
            "status": "resigned",
            "last_working_date": str(data.last_working_date)
        },
        reason=data.reason
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    
    return event


def exit_employee(db: Session, data: ExitEmployeeRequest, organization_id: Optional[int] = None) -> EmployeeLifecycle:
    employee = get_employee_by_id(db, data.employee_id)
    
    employee.status = EmployeeStatus.TERMINATED
    employee.is_active = False
    
    event = EmployeeLifecycle(
        employee_id=data.employee_id,
        organization_id=employee.organization_id,
        event_type="exit",
        event_date=data.exit_date,
        status="completed",
        new_value={
            "status": data.exit_type,
            "final_settlement_date": str(data.final_settlement_date)
        },
        reason=data.reason
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    
    return event


def get_employee_reports(db: Session, filters: Optional[dict] = None, organization_id: Optional[int] = None) -> list:
    query = db.query(Employee)
    if organization_id:
        query = query.filter(Employee.organization_id == organization_id)
    if filters:
        if "department_id" in filters:
            query = query.filter(Employee.department_id == filters["department_id"])
        if "status" in filters:
            query = query.filter(Employee.status == filters["status"])
        if "search" in filters:
            search_term = f"%{filters['search']}%"
            query = query.filter(
                (Employee.first_name.ilike(search_term)) |
                (Employee.last_name.ilike(search_term))  |
                (Employee.email.ilike(search_term))      |
                (Employee.employee_code.ilike(search_term))
            )

    return query.order_by(Employee.created_at.desc()).all()


def export_employee_reports(db: Session, data: EmployeeExportRequest, organization_id: Optional[int] = None) -> list:
    return get_employee_reports(db, data.filters, organization_id)


# ════════════════════════════════════════════════════════════════════════════════
# DESIGNATION SERVICE
# ════════════════════════════════════════════════════════════════════════════════

def get_designations(db: Session) -> list:
    from app.modules.hr.models import Designation
    return db.query(Designation).order_by(Designation.created_at.desc()).all()


def get_designation_by_id(db: Session, designation_id: int):
    from app.modules.hr.models import Designation
    from app.core.exceptions import NotFoundException
    obj = db.query(Designation).filter(Designation.id == designation_id).first()
    if not obj:
        raise NotFoundException("Designation", designation_id)
    return obj


def create_designation(db: Session, data: DesignationCreate) -> object:
    from app.modules.hr.models import Designation
    
    # Extract the schema payload into a dictionary
    payload = data.model_dump()
    
    # Explicitly guarantee employees_count is set for the return validation instance
    if "employees_count" not in payload or payload["employees_count"] is None:
        payload["employees_count"] = 0

    obj = Designation(**payload)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_designation(db: Session, designation_id: int, data: DesignationUpdate, organization_id: int) -> object:
    obj = get_designation_by_id(db, designation_id, organization_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_designation(db: Session, designation_id: int, organization_id: int) -> None:
    obj = get_designation_by_id(db, designation_id, organization_id)
    db.delete(obj)
    db.commit()

# ════════════════════════════════════════════════════════════════════════════════
# HR DOCUMENT SERVICE
# ════════════════════════════════════════════════════════════════════════════════

def get_hr_documents(
    db: Session,
    organization_id: Optional[int] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    employee_id: Optional[int] = None,
    search: Optional[str] = None,
) -> list:
    """
    Return all non-deleted HR documents, with optional filtering.
    Resolves employee_name and uploader_name for the response.
    """
    from app.modules.hr.models import HrDocument

    query = db.query(HrDocument).filter(HrDocument.is_deleted == False)
    if organization_id:
        query = query.filter(HrDocument.organization_id == organization_id)

    if category:
        query = query.filter(HrDocument.category == category)
    if status:
        query = query.filter(HrDocument.status == status)
    if employee_id:
        query = query.filter(HrDocument.employee_id == employee_id)
    if search:
        term = f"%{search}%"
        query = query.filter(
            (HrDocument.title.ilike(term)) |
            (HrDocument.document_type.ilike(term))
        )

    docs = query.order_by(HrDocument.created_at.desc()).all()

    # Attach convenience name fields without a JOIN (keeps it simple)
    result = []
    for doc in docs:
        d = doc.__dict__.copy()
        d.pop("_sa_instance_state", None)

        if doc.employee_id:
            emp = db.query(Employee).filter(Employee.id == doc.employee_id).first()
            d["employee_name"] = f"{emp.first_name} {emp.last_name}" if emp else None
        else:
            d["employee_name"] = None

        if doc.uploaded_by:
            uploader = db.query(Employee).filter(Employee.id == doc.uploaded_by).first()
            d["uploader_name"] = f"{uploader.first_name} {uploader.last_name}" if uploader else None
        else:
            d["uploader_name"] = None

        result.append(d)

    return result


def upload_hr_document(
    db: Session,
    title: str,
    category: str,
    file_path: str,
    file_name: str,
    file_size: Optional[int],
    mime_type: Optional[str],
    organization_id: Optional[int] = None,
    description: Optional[str] = None,
    document_type: Optional[str] = None,
    employee_id: Optional[int] = None,
    uploaded_by: Optional[int] = None,
    expiry_date=None,
    tags: Optional[list] = None,
) -> object:
    """
    Create a new HrDocument record after the file has been stored on disk.
    The caller (router) is responsible for writing the file and passing the path.
    """
    from app.modules.hr.models import HrDocument, HrDocumentStatus

    doc = HrDocument(
        title=title,
        description=description,
        category=category,
        document_type=document_type,
        file_path=file_path,
        file_name=file_name,
        file_size=file_size,
        mime_type=mime_type,
        status=HrDocumentStatus.PENDING,
        employee_id=employee_id,
        uploaded_by=uploaded_by,
        expiry_date=expiry_date,
        tags=tags or [],
        organization_id=organization_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def update_hr_document(db: Session, document_id: int, data, organization_id: int) -> object:
    """Update editable metadata fields on an existing document."""
    from app.modules.hr.models import HrDocument

    doc = db.query(HrDocument).filter(
        HrDocument.id == document_id,
        HrDocument.organization_id == organization_id,
        HrDocument.is_deleted == False,
    ).first()
    if not doc:
        raise NotFoundException("HrDocument", document_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(doc, field, value)

    db.commit()
    db.refresh(doc)
    return doc


def update_hr_document_status(db: Session, document_id: int, data, organization_id: int) -> object:
    """
    Change the approval status of a document (approve / reject / expire).
    Accepts HrDocumentStatusUpdate schema.
    """
    from app.modules.hr.models import HrDocument, HrDocumentStatus

    doc = db.query(HrDocument).filter(
        HrDocument.id == document_id,
        HrDocument.organization_id == organization_id,
        HrDocument.is_deleted == False,
    ).first()
    if not doc:
        raise NotFoundException("HrDocument", document_id)

    # Validate the incoming status value against the enum
    try:
        doc.status = HrDocumentStatus(data.status)
    except ValueError:
        raise BadRequestException(
            f"Invalid status '{data.status}'. "
            f"Valid values: {[e.value for e in HrDocumentStatus]}"
        )

    if data.rejection_reason is not None:
        doc.rejection_reason = data.rejection_reason

    db.commit()
    db.refresh(doc)
    return doc


def delete_hr_document(db: Session, document_id: int, organization_id: int) -> None:
    """Soft-delete a document (sets is_deleted=True)."""
    from app.modules.hr.models import HrDocument

    doc = db.query(HrDocument).filter(
        HrDocument.id == document_id,
        HrDocument.organization_id == organization_id,
        HrDocument.is_deleted == False,
    ).first()
    if not doc:
        raise NotFoundException("HrDocument", document_id)

    doc.is_deleted = True
    db.commit()


def get_hr_document_by_id(db: Session, document_id: int, organization_id: Optional[int] = None) -> dict:
    from app.modules.hr.models import HrDocument

    query = db.query(HrDocument).filter(
        HrDocument.id == document_id,
        HrDocument.is_deleted == False,
    )
    if organization_id:
        query = query.filter(HrDocument.organization_id == organization_id)
    doc = query.first()
    if not doc:
        raise NotFoundException("HrDocument", document_id)

    d = doc.__dict__.copy()
    d.pop("_sa_instance_state", None)
    if doc.employee_id:
        emp = db.query(Employee).filter(Employee.id == doc.employee_id).first()
        d["employee_name"] = f"{emp.first_name} {emp.last_name}" if emp else None
    else:
        d["employee_name"] = None
    if doc.uploaded_by:
        uploader = db.query(Employee).filter(Employee.id == doc.uploaded_by).first()
        d["uploader_name"] = f"{uploader.first_name} {uploader.last_name}" if uploader else None
    else:
        d["uploader_name"] = None
    return d