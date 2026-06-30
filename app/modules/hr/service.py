"""
modules/hr/service.py
---------------------
Business logic layer. This is WHERE the actual work happens.
"""

import logging
import os
from datetime import date, datetime, timedelta
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
    EmployeeCreate, EmployeeUpdate,
    UserCreateRequest, UserUpdateRequest,
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
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.core.exceptions import (
    NotFoundException, AlreadyExistsException,
    UnauthorizedException, BadRequestException
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


def refresh_access_token(db: Session, refresh_token_str: str) -> dict:
    from app.modules.hr.schemas import TokenResponse
    payload = decode_access_token(refresh_token_str)
    if not payload or "id" not in payload:
        raise UnauthorizedException("Invalid or expired refresh token.")
    employee = db.query(Employee).filter(Employee.id == payload["id"]).first()
    if not employee or not employee.is_active:
        raise UnauthorizedException("Employee not found or inactive.")
    new_token = create_access_token(data={
        "sub": employee.email,
        "role": employee.role.value if hasattr(employee.role, "value") else employee.role,
        "id": employee.id,
        "organization_id": employee.organization_id,
    })
    return {
        "access_token": new_token,
        "token_type": "bearer",
        "refresh_token": refresh_token_str,
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
    visible_roles: Optional[list] = None,
) -> dict:
    """List users within an organization with optional filtering/pagination.

    Args:
        visible_roles: If provided, only return users whose role is in this list.
                       Used to restrict visibility (e.g. HR Admin cannot see Organization Admin).
    """
    per_page = min(per_page, 100)
    query = db.query(Employee).filter(Employee.organization_id == organization_id)

    # Role-based visibility filter: restrict which roles the caller can see
    if visible_roles:
        query = query.filter(Employee.role.in_(visible_roles))

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


def suspend_organization_user(
    db: Session,
    user_id: int,
    organization_id: int,
    updated_by_id: int,
) -> Employee:
    """Suspend a user account."""
    user = get_organization_user(db, user_id, organization_id)
    user.is_active = False
    user.status = EmployeeStatus.SUSPENDED
    user.updated_by = updated_by_id
    db.flush()
    db.refresh(user)
    return user


def archive_organization_user(
    db: Session,
    user_id: int,
    organization_id: int,
    updated_by_id: int,
) -> Employee:
    """Archive a user account (soft archive)."""
    user = get_organization_user(db, user_id, organization_id)
    user.is_active = False
    user.status = EmployeeStatus.ARCHIVED
    user.updated_by = updated_by_id
    db.flush()
    db.refresh(user)
    return user


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


# ════════════════════════════════════════════════════════════════════════════
# EMPLOYEE SERVICE
# ════════════════════════════════════════════════════════════════════════════

def create_employee(db: Session, data: EmployeeCreate, organization_id: Optional[int] = None) -> Employee:
    existing = db.query(Employee).filter(Employee.email == data.email).first()
    if existing:
        raise AlreadyExistsException("Employee", "email")

    if data.department_id:
        get_department_by_id(db, data.department_id, organization_id)

    employee_data = data.model_dump(exclude={"password"})
    employee = Employee(
        **employee_data,
        hashed_password=hash_password(data.password),
        employee_code=_generate_employee_code(db),
        organization_id=organization_id or employee_data.get("organization_id"),
    )

    db.add(employee)
    db.flush()
    employee.employee_code = f"ZK-{employee.id:05d}"
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
    organization_id: Optional[int] = None,
    visible_roles: Optional[list] = None,
) -> dict:
    per_page = min(per_page, 100)
    query = db.query(Employee)

    if organization_id:
        query = query.filter(Employee.organization_id == organization_id)

    if visible_roles:
        query = query.filter(Employee.role.in_(visible_roles))

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


def get_employee_by_id(db: Session, employee_id: int, organization_id: int) -> Employee:
    employee = db.query(Employee).filter(
        Employee.id == employee_id,
        Employee.organization_id == organization_id,
    ).first()
    if not employee:
        raise NotFoundException("Employee", employee_id)
    return employee


def update_employee(db: Session, employee_id: int, data: EmployeeUpdate, organization_id: Optional[int] = None) -> Employee:
    employee = get_employee_by_id(db, employee_id, organization_id)

    if data.department_id:
        get_department_by_id(db, data.department_id, organization_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)

    db.commit()
    db.refresh(employee)
    return employee


def deactivate_employee(db: Session, employee_id: int, organization_id: Optional[int] = None) -> Employee:
    employee = get_employee_by_id(db, employee_id, organization_id)
    employee.is_active = False
    employee.status    = EmployeeStatus.TERMINATED

    event = EmployeeLifecycle(
        employee_id=employee_id,
        organization_id=employee.organization_id,
        event_type="exit",
        event_date=datetime.now().date(),
        status="completed",
        reason="Employee deactivated via admin action",
    )
    db.add(event)
    db.commit()
    db.refresh(employee)
    return employee


def get_hr_dashboard_stats(db: Session, organization_id: Optional[int] = None) -> dict:
    """
    Returns summary statistics for the HR dashboard.
    """
    query = db.query(Employee)
    if organization_id:
        query = query.filter(Employee.organization_id == organization_id)
    
    total = query.count()
    active = query.filter(Employee.status == EmployeeStatus.ACTIVE).count()
    
    dept_query = db.query(Department.name, func.count(Employee.id)).join(
        Employee, Employee.department_id == Department.id
    ).filter(Employee.status == EmployeeStatus.ACTIVE)
    if organization_id:
        dept_query = dept_query.filter(Department.organization_id == organization_id)
    dept_breakdown = dept_query.group_by(Department.name).all()

    return {
        "total_employees": total,
        "active_employees": active,
        "department_distribution": {name: count for name, count in dept_breakdown}
    }


def get_organization_details(db: Session, organization_id: int) -> dict:
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("Organization", organization_id)

    admin = db.query(Employee).filter(
        Employee.organization_id == organization_id,
        Employee.role == UserRole.ADMIN,
        Employee.is_active == True
    ).first()

    from app.modules.super_admin.models import Subscription
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == organization_id
    ).first()

    total_employees = db.query(Employee).filter(
        Employee.organization_id == organization_id
    ).count()

    active_employees = db.query(Employee).filter(
        Employee.organization_id == organization_id,
        Employee.status == EmployeeStatus.ACTIVE
    ).count()

    managers = db.query(Employee).filter(
        Employee.organization_id == organization_id,
        Employee.role == UserRole.MANAGER,
        Employee.is_active == True
    ).count()

    hr_admins = db.query(Employee).filter(
        Employee.organization_id == organization_id,
        Employee.role == UserRole.HR_ADMIN,
        Employee.is_active == True
    ).count()

    return {
        "id": org.id,
        "name": org.name,
        "code": org.code,
        "status": org.status,
        "is_active": org.is_active,
        "domain": org.domain,
        "address": org.address,
        "country": org.country,
        "state": org.state,
        "city": org.city,
        "timezone": org.timezone,
        "currency": org.currency,
        "industry": org.industry,
        "created_at": org.created_at,
        "admin_name": admin.full_name if admin else None,
        "admin_email": admin.email if admin else None,
        "subscription_plan": subscription.plan_type.value if subscription else None,
        "subscription_status": subscription.status.value if subscription else None,
        "subscription_end_date": subscription.end_date if subscription else None,
        "max_users": subscription.max_users if subscription else None,
        "total_employees": total_employees,
        "active_employees": active_employees,
        "managers": managers,
        "hr_admins": hr_admins,
    }


def get_org_admin_dashboard_stats(db: Session, organization_id: int) -> dict:
    active_employees = db.query(Employee).filter(
        Employee.organization_id == organization_id,
        Employee.status == EmployeeStatus.ACTIVE
    ).count()

    managers = db.query(Employee).filter(
        Employee.organization_id == organization_id,
        Employee.role == UserRole.MANAGER,
        Employee.is_active == True
    ).count()

    hr_admins = db.query(Employee).filter(
        Employee.organization_id == organization_id,
        Employee.role == UserRole.HR_ADMIN,
        Employee.is_active == True
    ).count()

    departments = db.query(Department).filter(
        Department.organization_id == organization_id,
        Department.is_active == True
    ).count()

    from app.modules.hr.models import Designation
    designations = db.query(Designation).filter(
        Designation.organization_id == organization_id
    ).count()

    pending_leave_requests = db.query(LeaveRequest).filter(
        LeaveRequest.organization_id == organization_id,
        LeaveRequest.status == RequestStatus.PENDING
    ).count()

    pending_approvals = db.query(LeaveRequest).filter(
        LeaveRequest.organization_id == organization_id,
        LeaveRequest.status == RequestStatus.PENDING,
        LeaveRequest.employee_id != None
    ).count()

    monthly_payroll = db.query(func.coalesce(func.sum(Employee.basic_salary), 0)).filter(
        Employee.organization_id == organization_id,
        Employee.status == EmployeeStatus.ACTIVE
    ).scalar()

    from app.modules.hr.models import Asset
    assets = db.query(Asset).filter(
        Asset.organization_id == organization_id,
        Asset.deleted_at == None
    ).count()

    from datetime import date
    today = date.today()
    attendance_today = db.query(func.count(AttendanceRecord.id)).filter(
        AttendanceRecord.organization_id == organization_id,
        AttendanceRecord.date == today
    ).scalar()

    return {
        "active_employees": active_employees,
        "managers": managers,
        "hr_admins": hr_admins,
        "departments": departments,
        "designations": designations,
        "pending_leave_requests": pending_leave_requests,
        "pending_approvals": pending_approvals,
        "monthly_payroll": float(monthly_payroll),
        "assets": assets,
        "attendance_today": attendance_today,
        "total_employees": db.query(Employee).filter(Employee.organization_id == organization_id).count(),
    }


def get_engagement_dashboard(db: Session, organization_id: Optional[int] = None) -> dict:
    from app.modules.hr.models import EngagementSurvey
    query = db.query(EngagementSurvey)
    if organization_id:
        query = query.filter(EngagementSurvey.organization_id == organization_id)
    total = query.count()
    avg_score = query.with_entities(func.avg(EngagementSurvey.score)).scalar() or 0
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

def create_attendance_record(db: Session, data: AttendanceCreate, organization_id: Optional[int] = None) -> AttendanceRecord:
    record = AttendanceRecord(**data.model_dump())
    if organization_id:
        record.organization_id = organization_id
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_attendance_records(db: Session, employee_id: Optional[int] = None, organization_id: Optional[int] = None) -> list[AttendanceRecord]:
    query = db.query(AttendanceRecord)
    if organization_id:
        query = query.filter(AttendanceRecord.organization_id == organization_id)
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
    department_id: Optional[int] = None,
) -> list[dict]:
    query = (
        db.query(
            LeaveRequest,
            Employee.employee_code,
            Employee.first_name,
            Employee.last_name,
            Department.name.label("department_name"),
            Employee.id.label("emp_id"),
        )
        .join(Employee, LeaveRequest.employee_id == Employee.id)
        .outerjoin(Department, Employee.department_id == Department.id)
        .filter(LeaveRequest.organization_id == org_id)
    )

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
    if department_id:
        query = query.filter(Employee.department_id == department_id)

    results = query.order_by(LeaveRequest.created_at.desc()).all()

    leave_requests = []
    for row in results:
        lr = row[0]
        employee_code = row[1]
        first_name = row[2]
        last_name = row[3]
        department_name = row[4]

        reviewer_name = None
        if lr.reviewed_by:
            reviewer = db.query(Employee).filter(Employee.id == lr.reviewed_by).first()
            if reviewer:
                reviewer_name = reviewer.full_name

        leave_requests.append({
            "id": lr.id,
            "employee_id": lr.employee_id,
            "employee_code": employee_code,
            "employee_name": f"{first_name} {last_name}",
            "department": department_name or "-",
            "organization_id": lr.organization_id,
            "leave_type": lr.leave_type,
            "start_date": lr.start_date,
            "end_date": lr.end_date,
            "days": lr.days,
            "reason": lr.reason,
            "status": lr.status,
            "reviewed_by": lr.reviewed_by,
            "reviewed_at": lr.reviewed_at,
            "approved_by": reviewer_name or "-",
            "approval_date": lr.reviewed_at,
            "approval_comments": lr.reason if lr.status != RequestStatus.PENDING else "-",
            "created_at": lr.created_at,
            "updated_at": lr.updated_at,
        })

    return leave_requests


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


def update_salary_revision(db: Session, revision_id: int, data, org_id: int) -> SalaryRevision:
    revision = db.query(SalaryRevision).filter(
        SalaryRevision.id == revision_id,
        SalaryRevision.organization_id == org_id,
    ).first()
    if not revision:
        raise NotFoundException("SalaryRevision", revision_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(revision, key, value)
    db.commit()
    db.refresh(revision)
    return revision


def delete_salary_revision(db: Session, revision_id: int, org_id: int) -> None:
    revision = db.query(SalaryRevision).filter(
        SalaryRevision.id == revision_id,
        SalaryRevision.organization_id == org_id,
    ).first()
    if not revision:
        raise NotFoundException("SalaryRevision", revision_id)
    db.delete(revision)
    db.commit()


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

def create_compliance_record(db: Session, data: ComplianceRecordCreate, organization_id: int) -> ComplianceRecord:
    record = ComplianceRecord(**data.model_dump())
    record.organization_id = organization_id
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_compliance_records(db: Session, organization_id: Optional[int] = None, employee_id: Optional[int] = None) -> list[ComplianceRecord]:
    query = db.query(ComplianceRecord)
    if organization_id:
        query = query.filter(ComplianceRecord.organization_id == organization_id)
    if employee_id:
        query = query.filter(ComplianceRecord.employee_id == employee_id)
    return query.order_by(ComplianceRecord.created_at.desc()).all()


def get_compliance_reports(db: Session = None) -> list[dict]:
    return []


def get_compliance_dashboard(db: Session, organization_id: Optional[int] = None) -> dict:
    from app.modules.hr.models import ComplianceViolation, Audit, RequestStatus
    base_records = db.query(ComplianceRecord)
    base_violations = db.query(ComplianceViolation)
    base_audits = db.query(Audit)
    if organization_id:
        base_records = base_records.filter(ComplianceRecord.organization_id == organization_id)
    total_policies = base_records.with_entities(ComplianceRecord.policy_name).distinct().count()
    pending = base_records.filter(ComplianceRecord.status == RequestStatus.PENDING).count()
    open_violations = base_violations.filter(ComplianceViolation.status.in_(["investigating", "open"])).count()
    completed_audits = base_audits.filter(Audit.status == "completed").count()
    return {
        "stats": {
            "totalPolicies": total_policies,
            "pendingAcknowledgment": pending,
            "openViolations": open_violations,
            "completedAudits": completed_audits,
        }
    }


# ── Compliance Policies ─────────────────────────────────────────────

def get_policies(
    db: Session,
    category: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    organization_id: Optional[int] = None,
) -> list[dict]:
    from app.modules.comply.models import CompliancePolicy
    q = db.query(CompliancePolicy)
    if organization_id:
        q = q.filter(CompliancePolicy.organization_id == organization_id)
    if category:
        q = q.filter(CompliancePolicy.category == category)
    if status:
        q = q.filter(CompliancePolicy.status == status)
    if search:
        term = f"%{search}%"
        q = q.filter(CompliancePolicy.title.ilike(term))
    rows = q.order_by(CompliancePolicy.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "category": r.category.value if hasattr(r.category, "value") else r.category,
            "status": r.status.value if hasattr(r.status, "value") else r.status,
            "owner": None,
            "created_at": r.created_at,
        }
        for r in rows
    ]


def create_policy(
    db: Session,
    data,
    owner: Optional[str] = None,
    organization_id: Optional[int] = None,
) -> dict:
    from app.modules.comply.models import CompliancePolicy, PolicyCategory, PolicyStatus
    cat = data.category if isinstance(data.category, PolicyCategory) else (PolicyCategory(data.category) if data.category else PolicyCategory.OTHER)
    st = data.status if isinstance(data.status, PolicyStatus) else (PolicyStatus(data.status) if data.status else PolicyStatus.ACTIVE)
    policy = CompliancePolicy(
        title=data.title,
        category=cat,
        status=st,
        content=data.title,
        organization_id=organization_id,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return {
        "id": policy.id,
        "title": policy.title,
        "category": policy.category.value if hasattr(policy.category, "value") else policy.category,
        "status": policy.status.value if hasattr(policy.status, "value") else policy.status,
        "owner": owner,
        "created_at": policy.created_at,
    }


def get_policy_by_id(db: Session, policy_id: int, organization_id: Optional[int] = None) -> dict:
    from app.modules.comply.models import CompliancePolicy
    from app.core.exceptions import NotFoundException
    q = db.query(CompliancePolicy).filter(CompliancePolicy.id == policy_id)
    if organization_id:
        q = q.filter(CompliancePolicy.organization_id == organization_id)
    r = q.first()
    if not r:
        raise NotFoundException("CompliancePolicy", policy_id)
    return {
        "id": r.id,
        "title": r.title,
        "category": r.category.value if hasattr(r.category, "value") else r.category,
        "status": r.status.value if hasattr(r.status, "value") else r.status,
        "owner": None,
        "created_at": r.created_at,
    }


def update_policy(db: Session, policy_id: int, data, organization_id: Optional[int] = None) -> dict:
    from app.modules.comply.models import CompliancePolicy, PolicyCategory, PolicyStatus
    from app.core.exceptions import NotFoundException
    q = db.query(CompliancePolicy).filter(CompliancePolicy.id == policy_id)
    if organization_id:
        q = q.filter(CompliancePolicy.organization_id == organization_id)
    r = q.first()
    if not r:
        raise NotFoundException("CompliancePolicy", policy_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "category" and value is not None:
            value = value if isinstance(value, PolicyCategory) else PolicyCategory(value)
        elif field == "status" and value is not None:
            value = value if isinstance(value, PolicyStatus) else PolicyStatus(value)
        setattr(r, field, value)
    db.commit()
    db.refresh(r)
    return {
        "id": r.id,
        "title": r.title,
        "category": r.category.value if hasattr(r.category, "value") else r.category,
        "status": r.status.value if hasattr(r.status, "value") else r.status,
        "owner": None,
        "created_at": r.created_at,
    }


def delete_policy(db: Session, policy_id: int, organization_id: Optional[int] = None) -> None:
    from app.modules.comply.models import CompliancePolicy
    from app.core.exceptions import NotFoundException
    q = db.query(CompliancePolicy).filter(CompliancePolicy.id == policy_id)
    if organization_id:
        q = q.filter(CompliancePolicy.organization_id == organization_id)
    r = q.first()
    if not r:
        raise NotFoundException("CompliancePolicy", policy_id)
    db.delete(r)
    db.commit()


# ── Policy Acknowledgements ─────────────────────────────────────────

def get_acknowledgements(
    db: Session,
    employee_id: Optional[int] = None,
    policy_id: Optional[int] = None,
    organization_id: Optional[int] = None,
) -> list[dict]:
    from app.modules.comply.models import PolicyAcknowledgement
    q = db.query(PolicyAcknowledgement)
    if organization_id:
        q = q.filter(PolicyAcknowledgement.organization_id == organization_id)
    if employee_id:
        q = q.filter(PolicyAcknowledgement.employee_id == employee_id)
    if policy_id:
        q = q.filter(PolicyAcknowledgement.policy_id == policy_id)
    rows = q.order_by(PolicyAcknowledgement.acknowledged_at.desc()).all()
    return [
        {
            "id": r.id,
            "policy_id": r.policy_id,
            "employee_id": r.employee_id,
            "employee": None,
            "policy": None,
            "status": "completed",
            "due_date": None,
            "acknowledged_at": r.acknowledged_at,
        }
        for r in rows
    ]


def create_acknowledgement(db: Session, data, organization_id: Optional[int] = None) -> dict:
    from app.modules.comply.models import PolicyAcknowledgement
    ack = PolicyAcknowledgement(
        policy_id=data.policy_id,
        employee_id=data.employee_id,
        organization_id=organization_id,
    )
    db.add(ack)
    db.commit()
    db.refresh(ack)
    return {
        "id": ack.id,
        "policy_id": ack.policy_id,
        "employee_id": ack.employee_id,
        "employee": None,
        "policy": None,
        "status": "completed",
        "due_date": None,
        "acknowledged_at": ack.acknowledged_at,
    }


# ── Audits ──────────────────────────────────────────────────────────

def get_audits(db: Session, status: Optional[str] = None, organization_id: Optional[int] = None) -> list[dict]:
    from app.modules.hr.models import Audit
    q = db.query(Audit)
    if status:
        q = q.filter(Audit.status == status)
    rows = q.order_by(Audit.created_at.desc()).all()
    return [{"id": r.id, "title": r.title, "auditor": r.auditor, "score": r.score, "status": r.status, "created_at": r.created_at} for r in rows]


def create_audit(db: Session, data, organization_id: Optional[int] = None) -> dict:
    from app.modules.hr.models import Audit
    payload = data.model_dump()
    payload.pop("organization_id", None)
    audit = Audit(**payload)
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return {"id": audit.id, "title": audit.title, "auditor": audit.auditor, "score": audit.score, "status": audit.status, "created_at": audit.created_at}


def get_audit_by_id(db: Session, audit_id: int, organization_id: Optional[int] = None) -> dict:
    from app.modules.hr.models import Audit
    from app.core.exceptions import NotFoundException
    r = db.query(Audit).filter(Audit.id == audit_id).first()
    if not r:
        raise NotFoundException("Audit", audit_id)
    return {"id": r.id, "title": r.title, "auditor": r.auditor, "score": r.score, "status": r.status, "created_at": r.created_at}


def update_audit(db: Session, audit_id: int, data, organization_id: Optional[int] = None) -> dict:
    from app.modules.hr.models import Audit
    from app.core.exceptions import NotFoundException
    r = db.query(Audit).filter(Audit.id == audit_id).first()
    if not r:
        raise NotFoundException("Audit", audit_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(r, field, value)
    db.commit()
    db.refresh(r)
    return {"id": r.id, "title": r.title, "auditor": r.auditor, "score": r.score, "status": r.status, "created_at": r.created_at}


def delete_audit(db: Session, audit_id: int, organization_id: Optional[int] = None) -> None:
    from app.modules.hr.models import Audit
    from app.core.exceptions import NotFoundException
    r = db.query(Audit).filter(Audit.id == audit_id).first()
    if not r:
        raise NotFoundException("Audit", audit_id)
    db.delete(r)
    db.commit()


# ── Regulatory Requirements ─────────────────────────────────────────

def get_regulatory_requirements(db: Session, organization_id: Optional[int] = None) -> list[dict]:
    from app.modules.hr.models import RegulatoryRequirement
    q = db.query(RegulatoryRequirement)
    rows = q.order_by(RegulatoryRequirement.created_at.desc()).all()
    return [{"id": r.id, "name": r.name, "jurisdiction": r.jurisdiction, "category": r.category, "status": r.status} for r in rows]


def create_regulatory_requirement(db: Session, data, organization_id: Optional[int] = None) -> dict:
    from app.modules.hr.models import RegulatoryRequirement
    payload = data.model_dump()
    payload.pop("organization_id", None)
    r = RegulatoryRequirement(**payload)
    db.add(r)
    db.commit()
    db.refresh(r)
    return {"id": r.id, "name": r.name, "jurisdiction": r.jurisdiction, "category": r.category, "status": r.status}


# ── Risk Assessments ────────────────────────────────────────────────

def get_risk_assessments(db: Session, status: Optional[str] = None, organization_id: Optional[int] = None) -> list[dict]:
    from app.modules.hr.models import RiskAssessment
    q = db.query(RiskAssessment)
    if status:
        q = q.filter(RiskAssessment.status == status)
    rows = q.order_by(RiskAssessment.created_at.desc()).all()
    return [{"id": r.id, "title": r.title, "category": r.category, "risk_score": r.risk_score, "mitigation_strategy": r.mitigation_strategy, "mitigation": r.mitigation_strategy, "status": r.status} for r in rows]


def create_risk_assessment(db: Session, data, organization_id: Optional[int] = None) -> dict:
    from app.modules.hr.models import RiskAssessment
    payload = data.model_dump()
    payload.pop("organization_id", None)
    r = RiskAssessment(**payload)
    db.add(r)
    db.commit()
    db.refresh(r)
    return {"id": r.id, "title": r.title, "category": r.category, "risk_score": r.risk_score, "mitigation_strategy": r.mitigation_strategy, "mitigation": r.mitigation_strategy, "status": r.status}


def get_risk_assessment_by_id(db: Session, risk_id: int, organization_id: Optional[int] = None) -> dict:
    from app.modules.hr.models import RiskAssessment
    from app.core.exceptions import NotFoundException
    r = db.query(RiskAssessment).filter(RiskAssessment.id == risk_id).first()
    if not r:
        raise NotFoundException("RiskAssessment", risk_id)
    return {"id": r.id, "title": r.title, "category": r.category, "risk_score": r.risk_score, "mitigation_strategy": r.mitigation_strategy, "mitigation": r.mitigation_strategy, "status": r.status}


def update_risk_assessment(db: Session, risk_id: int, data, organization_id: Optional[int] = None) -> dict:
    from app.modules.hr.models import RiskAssessment
    from app.core.exceptions import NotFoundException
    r = db.query(RiskAssessment).filter(RiskAssessment.id == risk_id).first()
    if not r:
        raise NotFoundException("RiskAssessment", risk_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(r, field, value)
    db.commit()
    db.refresh(r)
    return {"id": r.id, "title": r.title, "category": r.category, "risk_score": r.risk_score, "mitigation_strategy": r.mitigation_strategy, "mitigation": r.mitigation_strategy, "status": r.status}


def delete_risk_assessment(db: Session, risk_id: int, organization_id: Optional[int] = None) -> None:
    from app.modules.hr.models import RiskAssessment
    from app.core.exceptions import NotFoundException
    r = db.query(RiskAssessment).filter(RiskAssessment.id == risk_id).first()
    if not r:
        raise NotFoundException("RiskAssessment", risk_id)
    db.delete(r)
    db.commit()


# ── Compliance Violations ───────────────────────────────────────────

def get_compliance_violations(
    db: Session,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    organization_id: Optional[int] = None,
) -> list[dict]:
    from app.modules.hr.models import ComplianceViolation
    q = db.query(ComplianceViolation)
    if status:
        q = q.filter(ComplianceViolation.status == status)
    if severity:
        q = q.filter(ComplianceViolation.severity == severity)
    rows = q.order_by(ComplianceViolation.created_at.desc()).all()
    return [
        {
            "id": r.id, "title": r.title, "violation": r.violation, "policy": r.policy,
            "employee": r.employee, "reported_by": r.reported_by, "severity": r.severity,
            "status": r.status, "date": r.date, "created_at": r.created_at,
        }
        for r in rows
    ]


def create_compliance_violation(db: Session, data, organization_id: Optional[int] = None) -> dict:
    from app.modules.hr.models import ComplianceViolation
    payload = data.model_dump()
    payload.pop("organization_id", None)
    r = ComplianceViolation(**payload)
    db.add(r)
    db.commit()
    db.refresh(r)
    return {
        "id": r.id, "title": r.title, "violation": r.violation, "policy": r.policy,
        "employee": r.employee, "reported_by": r.reported_by, "severity": r.severity,
        "status": r.status, "date": r.date, "created_at": r.created_at,
    }


def get_compliance_violation_by_id(db: Session, violation_id: int, organization_id: Optional[int] = None) -> dict:
    from app.modules.hr.models import ComplianceViolation
    from app.core.exceptions import NotFoundException
    r = db.query(ComplianceViolation).filter(ComplianceViolation.id == violation_id).first()
    if not r:
        raise NotFoundException("ComplianceViolation", violation_id)
    return {
        "id": r.id, "title": r.title, "violation": r.violation, "policy": r.policy,
        "employee": r.employee, "reported_by": r.reported_by, "severity": r.severity,
        "status": r.status, "date": r.date, "created_at": r.created_at,
    }


def update_compliance_violation(db: Session, violation_id: int, data, organization_id: Optional[int] = None) -> dict:
    from app.modules.hr.models import ComplianceViolation
    from app.core.exceptions import NotFoundException
    r = db.query(ComplianceViolation).filter(ComplianceViolation.id == violation_id).first()
    if not r:
        raise NotFoundException("ComplianceViolation", violation_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(r, field, value)
    db.commit()
    db.refresh(r)
    return {
        "id": r.id, "title": r.title, "violation": r.violation, "policy": r.policy,
        "employee": r.employee, "reported_by": r.reported_by, "severity": r.severity,
        "status": r.status, "date": r.date, "created_at": r.created_at,
    }


def delete_compliance_violation(db: Session, violation_id: int, organization_id: Optional[int] = None) -> None:
    from app.modules.hr.models import ComplianceViolation
    from app.core.exceptions import NotFoundException
    r = db.query(ComplianceViolation).filter(ComplianceViolation.id == violation_id).first()
    if not r:
        raise NotFoundException("ComplianceViolation", violation_id)
    db.delete(r)
    db.commit()


# ── Corrective Actions ──────────────────────────────────────────────

def get_corrective_actions(
    db: Session,
    violation_id: Optional[int] = None,
    assigned_to: Optional[str] = None,
    organization_id: Optional[int] = None,
) -> list[dict]:
    from app.modules.hr.models import CorrectiveAction
    q = db.query(CorrectiveAction)
    if violation_id:
        q = q.filter(CorrectiveAction.violation_id == violation_id)
    if assigned_to:
        q = q.filter(CorrectiveAction.assigned_to == assigned_to)
    rows = q.order_by(CorrectiveAction.created_at.desc()).all()
    return [
        {"id": r.id, "title": r.title, "violation_id": r.violation_id, "assigned_to": r.assigned_to,
         "status": r.status, "deadline": r.deadline}
        for r in rows
    ]


def create_corrective_action(db: Session, data, organization_id: Optional[int] = None) -> dict:
    from app.modules.hr.models import CorrectiveAction
    payload = data.model_dump()
    payload.pop("organization_id", None)
    r = CorrectiveAction(**payload)
    db.add(r)
    db.commit()
    db.refresh(r)
    return {"id": r.id, "title": r.title, "violation_id": r.violation_id, "assigned_to": r.assigned_to,
            "status": r.status, "deadline": r.deadline}


def get_corrective_action_by_id(db: Session, action_id: int, organization_id: Optional[int] = None) -> dict:
    from app.modules.hr.models import CorrectiveAction
    from app.core.exceptions import NotFoundException
    r = db.query(CorrectiveAction).filter(CorrectiveAction.id == action_id).first()
    if not r:
        raise NotFoundException("CorrectiveAction", action_id)
    return {"id": r.id, "title": r.title, "violation_id": r.violation_id, "assigned_to": r.assigned_to,
            "status": r.status, "deadline": r.deadline}


def update_corrective_action(db: Session, action_id: int, data, organization_id: Optional[int] = None) -> dict:
    from app.modules.hr.models import CorrectiveAction
    from app.core.exceptions import NotFoundException
    r = db.query(CorrectiveAction).filter(CorrectiveAction.id == action_id).first()
    if not r:
        raise NotFoundException("CorrectiveAction", action_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(r, field, value)
    db.commit()
    db.refresh(r)
    return {"id": r.id, "title": r.title, "violation_id": r.violation_id, "assigned_to": r.assigned_to,
            "status": r.status, "deadline": r.deadline}


def delete_corrective_action(db: Session, action_id: int, organization_id: Optional[int] = None) -> None:
    from app.modules.hr.models import CorrectiveAction
    from app.core.exceptions import NotFoundException
    r = db.query(CorrectiveAction).filter(CorrectiveAction.id == action_id).first()
    if not r:
        raise NotFoundException("CorrectiveAction", action_id)
    db.delete(r)
    db.commit()


# ════════════════════════════════════════════════════════════════════════════
# ENGAGEMENT SURVEY SERVICE
# ════════════════════════════════════════════════════════════════════════════

def create_engagement_survey(db: Session, data: EngagementSurveyCreate, organization_id: int) -> EngagementSurvey:
    survey = EngagementSurvey(**data.model_dump())
    survey.organization_id = organization_id
    db.add(survey)
    db.commit()
    db.refresh(survey)
    return survey


def get_engagement_surveys(db: Session, organization_id: Optional[int] = None, employee_id: Optional[int] = None) -> list[EngagementSurvey]:
    query = db.query(EngagementSurvey)
    if organization_id:
        query = query.filter(EngagementSurvey.organization_id == organization_id)
    if employee_id:
        query = query.filter(EngagementSurvey.employee_id == employee_id)
    return query.order_by(EngagementSurvey.created_at.desc()).all()


# ════════════════════════════════════════════════════════════════════════════
# ESS REQUEST SERVICE
# ════════════════════════════════════════════════════════════════════════════

def create_ess_request(db: Session, data: EssRequestCreate, organization_id: int) -> EssRequest:
    request = EssRequest(**data.model_dump())
    request.organization_id = organization_id
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def get_ess_requests(db: Session, organization_id: Optional[int] = None, employee_id: Optional[int] = None) -> list[EssRequest]:
    query = db.query(EssRequest)
    if organization_id:
        query = query.filter(EssRequest.organization_id == organization_id)
    if employee_id:
        query = query.filter(EssRequest.employee_id == employee_id)
    return query.order_by(EssRequest.created_at.desc()).all()


def update_ess_request(db: Session, request_id: int, data, organization_id: int) -> EssRequest:
    req = db.query(EssRequest).filter(EssRequest.id == request_id, EssRequest.organization_id == organization_id).first()
    if not req:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("EssRequest", request_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(req, field, value)
    db.commit()
    db.refresh(req)
    return req


def delete_ess_request(db: Session, request_id: int, organization_id: int) -> None:
    req = db.query(EssRequest).filter(EssRequest.id == request_id, EssRequest.organization_id == organization_id).first()
    if not req:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("EssRequest", request_id)
    db.delete(req)
    db.commit()


# ════════════════════════════════════════════════════════════════════════════
# ONBOARDING RECORD SERVICE
# ════════════════════════════════════════════════════════════════════════════

def create_onboarding_record(db: Session, data: OnboardingRecordCreate, organization_id: int) -> OnboardingNewHire:
    new_hire = OnboardingNewHire(**data.model_dump())
    new_hire.organization_id = organization_id
    db.add(new_hire)
    db.commit()
    db.refresh(new_hire)
    log_onboarding_activity(db, new_hire.id, "Create New Hire", f"New hire record created for {new_hire.candidate_name}.", organization_id)
    return new_hire


def get_onboarding_records(db: Session, organization_id: Optional[int] = None) -> list[OnboardingNewHire]:
    query = db.query(OnboardingNewHire).filter(OnboardingNewHire.is_deleted == False)
    if organization_id:
        query = query.filter(OnboardingNewHire.organization_id == organization_id)
    return query.order_by(OnboardingNewHire.created_at.desc()).all()


def get_onboarding_record_by_id(db: Session, record_id: int, organization_id: Optional[int] = None) -> OnboardingNewHire:
    query = db.query(OnboardingNewHire).filter(OnboardingNewHire.id == record_id, OnboardingNewHire.is_deleted == False)
    if organization_id:
        query = query.filter(OnboardingNewHire.organization_id == organization_id)
    new_hire = query.first()
    if not new_hire:
        raise NotFoundException("OnboardingNewHire", record_id)
    return new_hire


def update_onboarding_record(db: Session, record_id: int, data: OnboardingRecordUpdate, organization_id: int) -> OnboardingNewHire:
    new_hire = get_onboarding_record_by_id(db, record_id, organization_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(new_hire, field, value)
    db.commit()
    db.refresh(new_hire)
    log_onboarding_activity(db, new_hire.id, "Update New Hire", f"Updated details for {new_hire.candidate_name}.", organization_id)
    return new_hire


def delete_onboarding_record(db: Session, record_id: int, organization_id: int) -> None:
    new_hire = get_onboarding_record_by_id(db, record_id, organization_id)
    new_hire.is_deleted = True
    db.commit()
    log_onboarding_activity(db, new_hire.id, "Delete New Hire", f"Soft deleted new hire record of {new_hire.candidate_name}.", organization_id)


# Helper to log activity
def log_onboarding_activity(db: Session, new_hire_id: Optional[int], action: str, description: str, organization_id: Optional[int] = None):
    activity = OnboardingActivity(
        onboarding_new_hire_id=new_hire_id,
        action=action,
        description=description,
        organization_id=organization_id
    )
    db.add(activity)
    db.commit()

# DASHBOARD & ANALYTICS
def get_onboarding_dashboard(db: Session, organization_id: Optional[int] = None) -> dict:
    base_query = db.query(OnboardingNewHire).filter(OnboardingNewHire.is_deleted == False)
    if organization_id:
        base_query = base_query.filter(OnboardingNewHire.organization_id == organization_id)
        
    total = base_query.count()
    pending = base_query.filter(OnboardingNewHire.status.in_(["offer_sent", "offer_accepted", "pre_joining", "in_progress"])).count()
    completed = base_query.filter(OnboardingNewHire.status == "completed").count()
    
    docs_q = db.query(OnboardingDocument).filter(OnboardingDocument.status == "pending", OnboardingDocument.is_deleted == False)
    checklists_q = db.query(OnboardingChecklistItem).filter(OnboardingChecklistItem.completed == False, OnboardingChecklistItem.is_deleted == False)
    orientations_q = db.query(OnboardingOrientation).filter(OnboardingOrientation.status == "scheduled", OnboardingOrientation.is_deleted == False)
    upcoming_q = db.query(OnboardingNewHire).filter(OnboardingNewHire.joining_date >= func.current_date(), OnboardingNewHire.is_deleted == False)
    recent_q = db.query(OnboardingActivity)
    monthly_q = db.query(func.date_format(OnboardingNewHire.created_at, "%Y-%m").label("month"), func.count(OnboardingNewHire.id)).filter(OnboardingNewHire.is_deleted == False)
    deptwise_q = db.query(Department.name, func.count(OnboardingNewHire.id)).join(OnboardingNewHire, OnboardingNewHire.department_id == Department.id, isouter=True).filter(OnboardingNewHire.is_deleted == False)

    if organization_id:
        docs_q = docs_q.filter(OnboardingDocument.organization_id == organization_id)
        checklists_q = checklists_q.join(OnboardingChecklist, OnboardingChecklistItem.checklist_id == OnboardingChecklist.id).filter(OnboardingChecklist.organization_id == organization_id)
        orientations_q = orientations_q.filter(OnboardingOrientation.organization_id == organization_id)
        upcoming_q = upcoming_q.filter(OnboardingNewHire.organization_id == organization_id)
        recent_q = recent_q.filter(OnboardingActivity.organization_id == organization_id)
        monthly_q = monthly_q.filter(OnboardingNewHire.organization_id == organization_id)
        deptwise_q = deptwise_q.filter(OnboardingNewHire.organization_id == organization_id)

    docs_pending = docs_q.count()
    checklists_pending = checklists_q.count()
    orientations_pending = orientations_q.count()
    
    monthly = monthly_q.group_by("month").order_by("month").all()
    deptwise = deptwise_q.group_by(Department.name).all()
    upcoming = upcoming_q.order_by(OnboardingNewHire.joining_date).limit(10).all()
    recent = recent_q.order_by(OnboardingActivity.created_at.desc()).limit(10).all()
    
    return {
        "totalNewHires": total,
        "pendingOnboarding": pending,
        "completedOnboarding": completed,
        "documentsPending": docs_pending,
        "assetsPending": 0, # integrated into checklists
        "orientationPending": orientations_pending,
        "trainingPending": 0, # removed
        "monthlyJoiningTrend": [{"month": m, "count": c} for m, c in monthly],
        "departmentWise": [{"department": d or "Unassigned", "count": c} for d, c in deptwise],
        "completionStatus": {
            "total": total,
            "completed": completed,
            "in_progress": base_query.filter(OnboardingNewHire.status == "in_progress").count(),
            "pending": pending
        },
        "upcomingJoiners": [{"id": r.id, "name": r.candidate_name, "position": r.position, "joining_date": str(r.joining_date) if r.joining_date else None} for r in upcoming],
        "recentActivities": [{"id": a.id, "action": a.action, "description": a.description, "timestamp": str(a.created_at) if a.created_at else None} for a in recent],
    }

def get_onboarding_analytics(db: Session, organization_id: Optional[int] = None) -> dict:
    dashboard_data = get_onboarding_dashboard(db, organization_id)
    total = dashboard_data["totalNewHires"]
    completed = dashboard_data["completedOnboarding"]
    completion_rate = (completed / total * 100) if total > 0 else 0.0
    
    return {
        "totalNewHires": total,
        "completionRate": round(completion_rate, 2),
        "avgDaysToOnboard": 14.5,
        "statusDistribution": [
            {"status": "Offer Sent", "count": dashboard_data["completionStatus"]["pending"]},
            {"status": "Completed", "count": completed}
        ],
        "departmentDistribution": dashboard_data["departmentWise"]
    }

# NEW HIRES SERVICE
def get_new_hires(db: Session, organization_id: Optional[int] = None, search: Optional[str] = None, status: Optional[str] = None) -> list[OnboardingNewHire]:
    query = db.query(OnboardingNewHire).filter(OnboardingNewHire.is_deleted == False)
    if organization_id:
        query = query.filter(OnboardingNewHire.organization_id == organization_id)
    if status:
        query = query.filter(OnboardingNewHire.status == status)
    if search:
        query = query.filter(
            (OnboardingNewHire.candidate_name.ilike(f"%{search}%")) |
            (OnboardingNewHire.email.ilike(f"%{search}%")) |
            (OnboardingNewHire.position.ilike(f"%{search}%"))
        )
    return query.order_by(OnboardingNewHire.created_at.desc()).all()

def get_new_hire_by_id(db: Session, new_hire_id: int, organization_id: Optional[int] = None) -> OnboardingNewHire:
    query = db.query(OnboardingNewHire).filter(OnboardingNewHire.id == new_hire_id, OnboardingNewHire.is_deleted == False)
    if organization_id:
        query = query.filter(OnboardingNewHire.organization_id == organization_id)
    new_hire = query.first()
    if not new_hire:
        raise NotFoundException("OnboardingNewHire", new_hire_id)
    return new_hire

def create_new_hire(db: Session, data: OnboardingNewHireCreate, organization_id: int) -> OnboardingNewHire:
    new_hire = OnboardingNewHire(**data.model_dump())
    new_hire.organization_id = organization_id
    db.add(new_hire)
    db.commit()
    db.refresh(new_hire)
    log_onboarding_activity(db, new_hire.id, "Create New Hire", f"New hire record created for {new_hire.candidate_name}.", organization_id)
    return new_hire

def update_new_hire(db: Session, new_hire_id: int, data: OnboardingNewHireUpdate, organization_id: int) -> OnboardingNewHire:
    new_hire = get_new_hire_by_id(db, new_hire_id, organization_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(new_hire, field, value)
    db.commit()
    db.refresh(new_hire)
    log_onboarding_activity(db, new_hire.id, "Update New Hire", f"Updated details for {new_hire.candidate_name}.", organization_id)
    return new_hire

def delete_new_hire(db: Session, new_hire_id: int, organization_id: int) -> None:
    new_hire = get_new_hire_by_id(db, new_hire_id, organization_id)
    new_hire.is_deleted = True
    db.commit()
    log_onboarding_activity(db, new_hire.id, "Delete New Hire", f"Soft deleted new hire record of {new_hire.candidate_name}.", organization_id)

# PRE-ONBOARDING SERVICE (TASKS)
def get_preboarding_tasks(db: Session, organization_id: Optional[int] = None, new_hire_id: Optional[int] = None, employee_id: Optional[int] = None) -> list[OnboardingPreboardingTask]:
    query = db.query(OnboardingPreboardingTask).filter(OnboardingPreboardingTask.is_deleted == False)
    if organization_id:
        query = query.filter(OnboardingPreboardingTask.organization_id == organization_id)
    if new_hire_id:
        query = query.filter(OnboardingPreboardingTask.onboarding_new_hire_id == new_hire_id)
    if employee_id:
        query = query.filter(
            (OnboardingPreboardingTask.employee_id == employee_id) |
            (OnboardingPreboardingTask.onboarding_new_hire_id == employee_id)
        )
    return query.order_by(OnboardingPreboardingTask.created_at.desc()).all()

def create_preboarding_task(db: Session, data: OnboardingPreboardingTaskCreate, organization_id: int) -> OnboardingPreboardingTask:
    task = OnboardingPreboardingTask(**data.model_dump())
    task.organization_id = organization_id
    db.add(task)
    db.commit()
    db.refresh(task)
    log_onboarding_activity(db, task.onboarding_new_hire_id, "Create Task", f"Task '{task.title}' created.", organization_id)
    return task

def update_preboarding_task(db: Session, task_id: int, data: OnboardingPreboardingTaskUpdate, organization_id: int) -> OnboardingPreboardingTask:
    task = db.query(OnboardingPreboardingTask).filter(OnboardingPreboardingTask.id == task_id, OnboardingPreboardingTask.is_deleted == False, OnboardingPreboardingTask.organization_id == organization_id).first()
    if not task:
        raise NotFoundException("OnboardingPreboardingTask", task_id)
    update_data = data.model_dump(exclude_unset=True)
    if "completed" in update_data and update_data["completed"] and not task.completed:
        task.completed_at = datetime.utcnow()
    for field, value in update_data.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task

def delete_preboarding_task(db: Session, task_id: int, organization_id: int) -> None:
    task = db.query(OnboardingPreboardingTask).filter(OnboardingPreboardingTask.id == task_id, OnboardingPreboardingTask.is_deleted == False, OnboardingPreboardingTask.organization_id == organization_id).first()
    if not task:
        raise NotFoundException("OnboardingPreboardingTask", task_id)
    task.is_deleted = True
    db.commit()



# CHECKLISTS SERVICE
def get_checklists(db: Session, organization_id: Optional[int] = None, is_template: bool = True, new_hire_id: Optional[int] = None, category: Optional[str] = None) -> list[OnboardingChecklist]:
    query = db.query(OnboardingChecklist).filter(OnboardingChecklist.is_deleted == False)
    if organization_id:
        query = query.filter(OnboardingChecklist.organization_id == organization_id)
    if is_template:
        query = query.filter(OnboardingChecklist.onboarding_new_hire_id == None)
    else:
        query = query.filter(OnboardingChecklist.onboarding_new_hire_id != None)
        if new_hire_id:
            query = query.filter(OnboardingChecklist.onboarding_new_hire_id == new_hire_id)
    if category:
        query = query.filter(OnboardingChecklist.category == category)
    return query.order_by(OnboardingChecklist.created_at.desc()).all()

def create_checklist(db: Session, data: OnboardingChecklistCreate, organization_id: int) -> OnboardingChecklist:
    checklist = OnboardingChecklist(
        onboarding_new_hire_id=data.onboarding_new_hire_id,
        name=data.name,
        description=data.description,
        category=data.category or "HR",
        organization_id=organization_id
    )
    db.add(checklist)
    db.commit()
    db.refresh(checklist)
    
    if data.items:
        for item_data in data.items:
            item = OnboardingChecklistItem(
                checklist_id=checklist.id,
                title=item_data.title,
                description=item_data.description,
                due_date=item_data.due_date,
                organization_id=organization_id
            )
            db.add(item)
        db.commit()
        db.refresh(checklist)
        
    return checklist

def update_checklist(db: Session, checklist_id: int, data: OnboardingChecklistUpdate, organization_id: int) -> OnboardingChecklist:
    checklist = db.query(OnboardingChecklist).filter(OnboardingChecklist.id == checklist_id, OnboardingChecklist.is_deleted == False, OnboardingChecklist.organization_id == organization_id).first()
    if not checklist:
        raise NotFoundException("OnboardingChecklist", checklist_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(checklist, field, value)
    db.commit()
    db.refresh(checklist)
    return checklist

def update_checklist_items(db: Session, checklist_id: int, items_data: list[dict], organization_id: int) -> OnboardingChecklist:
    checklist = db.query(OnboardingChecklist).filter(OnboardingChecklist.id == checklist_id, OnboardingChecklist.is_deleted == False, OnboardingChecklist.organization_id == organization_id).first()
    if not checklist:
        raise NotFoundException("OnboardingChecklist", checklist_id)
        
    db.query(OnboardingChecklistItem).filter(OnboardingChecklistItem.checklist_id == checklist_id).delete()
    for item in items_data:
        db_item = OnboardingChecklistItem(
            checklist_id=checklist_id,
            title=item.get("title"),
            description=item.get("description"),
            completed=item.get("completed", False),
            due_date=item.get("due_date"),
            organization_id=organization_id
        )
        if db_item.completed:
            db_item.completed_at = datetime.utcnow()
        db.add(db_item)
    db.commit()
    db.refresh(checklist)
    return checklist

def delete_checklist(db: Session, checklist_id: int, organization_id: int) -> None:
    checklist = db.query(OnboardingChecklist).filter(OnboardingChecklist.id == checklist_id, OnboardingChecklist.is_deleted == False, OnboardingChecklist.organization_id == organization_id).first()
    if not checklist:
        raise NotFoundException("OnboardingChecklist", checklist_id)
    checklist.is_deleted = True
    db.commit()

def assign_checklist_template(db: Session, new_hire_id: int, template_id: int, organization_id: int) -> OnboardingChecklist:
    template = db.query(OnboardingChecklist).filter(OnboardingChecklist.id == template_id, OnboardingChecklist.is_deleted == False, OnboardingChecklist.organization_id == organization_id).first()
    if not template:
        raise NotFoundException("OnboardingChecklistTemplate", template_id)
        
    new_hire = get_new_hire_by_id(db, new_hire_id, organization_id)
    
    checklist = OnboardingChecklist(
        onboarding_new_hire_id=new_hire_id,
        template_id=template_id,
        name=template.name,
        description=template.description,
        category=template.category,
        status="pending",
        organization_id=organization_id
    )
    db.add(checklist)
    db.commit()
    db.refresh(checklist)
    
    for item in template.items:
        db_item = OnboardingChecklistItem(
            checklist_id=checklist.id,
            title=item.title,
            description=item.description,
            completed=False,
            due_date=item.due_date,
            organization_id=organization_id
        )
        db.add(db_item)
    db.commit()
    db.refresh(checklist)
    
    log_onboarding_activity(db, new_hire_id, "Assign Checklist", f"Checklist template '{template.name}' assigned to {new_hire.candidate_name}.", organization_id)
    return checklist

# ORIENTATION SERVICE
def get_orientations(db: Session, organization_id: Optional[int] = None) -> list[OnboardingOrientation]:
    query = db.query(OnboardingOrientation).filter(OnboardingOrientation.is_deleted == False)
    if organization_id:
        query = query.filter(OnboardingOrientation.organization_id == organization_id)
    return query.order_by(OnboardingOrientation.date.desc()).all()

def create_orientation(db: Session, data: OnboardingOrientationCreate, organization_id: int) -> OnboardingOrientation:
    session = OnboardingOrientation(**data.model_dump())
    session.organization_id = organization_id
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

def update_orientation(db: Session, session_id: int, data: OnboardingOrientationUpdate, organization_id: int) -> OnboardingOrientation:
    session = db.query(OnboardingOrientation).filter(OnboardingOrientation.id == session_id, OnboardingOrientation.is_deleted == False, OnboardingOrientation.organization_id == organization_id).first()
    if not session:
        raise NotFoundException("OnboardingOrientation", session_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(session, field, value)
    db.commit()
    db.refresh(session)
    return session

def delete_orientation(db: Session, session_id: int, organization_id: int) -> None:
    session = db.query(OnboardingOrientation).filter(OnboardingOrientation.id == session_id, OnboardingOrientation.is_deleted == False, OnboardingOrientation.organization_id == organization_id).first()
    if not session:
        raise NotFoundException("OnboardingOrientation", session_id)
    session.is_deleted = True
    db.commit()

# ORIENTATION ATTENDEES SERVICE
def get_orientation_attendees(db: Session, organization_id: Optional[int] = None, session_id: Optional[int] = None, new_hire_id: Optional[int] = None) -> list[OnboardingOrientationAttendee]:
    query = db.query(OnboardingOrientationAttendee).filter(OnboardingOrientationAttendee.is_deleted == False)
    if organization_id:
        query = query.filter(OnboardingOrientationAttendee.organization_id == organization_id)
    if session_id:
        query = query.filter(OnboardingOrientationAttendee.session_id == session_id)
    if new_hire_id:
        query = query.filter(OnboardingOrientationAttendee.onboarding_new_hire_id == new_hire_id)
    return query.all()

def add_orientation_attendee(db: Session, data: OnboardingOrientationAttendeeCreate) -> OnboardingOrientationAttendee:
    session = db.query(OnboardingOrientation).filter(OnboardingOrientation.id == data.session_id, OnboardingOrientation.is_deleted == False).first()
    if not session:
        raise NotFoundException("OnboardingOrientation", data.session_id)
    new_hire = get_new_hire_by_id(db, data.onboarding_record_id)
    
    existing = db.query(OnboardingOrientationAttendee).filter(
        OnboardingOrientationAttendee.session_id == data.session_id,
        OnboardingOrientationAttendee.onboarding_new_hire_id == data.onboarding_record_id,
        OnboardingOrientationAttendee.is_deleted == False
    ).first()
    if existing:
        return existing
        
    attendee = OnboardingOrientationAttendee(
        session_id=data.session_id,
        onboarding_new_hire_id=data.onboarding_record_id,
        status=data.status or "pending",
        tenant_id=session.tenant_id
    )
    db.add(attendee)
    db.commit()
    db.refresh(attendee)
    
    log_onboarding_activity(db, data.onboarding_record_id, "Add Orientation Attendee", f"Added to orientation session '{session.title}'.", session.tenant_id)
    return attendee

def update_orientation_attendee(db: Session, attendee_id: int, data: OnboardingOrientationAttendeeUpdate) -> OnboardingOrientationAttendee:
    attendee = db.query(OnboardingOrientationAttendee).filter(OnboardingOrientationAttendee.id == attendee_id, OnboardingOrientationAttendee.is_deleted == False).first()
    if not attendee:
        raise NotFoundException("OnboardingOrientationAttendee", attendee_id)
    attendee.status = data.status
    db.commit()
    db.refresh(attendee)
    return attendee

def remove_orientation_attendee(db: Session, attendee_id: int) -> None:
    attendee = db.query(OnboardingOrientationAttendee).filter(OnboardingOrientationAttendee.id == attendee_id, OnboardingOrientationAttendee.is_deleted == False).first()
    if not attendee:
        raise NotFoundException("OnboardingOrientationAttendee", attendee_id)
    attendee.is_deleted = True
    db.commit()


def get_onboarding_activities(db: Session, organization_id: int, limit: int = 50) -> list[OnboardingActivity]:
    return db.query(OnboardingActivity).filter(
        OnboardingActivity.organization_id == organization_id
    ).order_by(OnboardingActivity.created_at.desc()).limit(limit).all()


def create_onboarding_task(db: Session, data: OnboardingTaskCreate) -> OnboardingPreboardingTask:
    task = OnboardingPreboardingTask(**data.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_onboarding_tasks(db: Session, employee_id: Optional[int] = None) -> list[OnboardingPreboardingTask]:
    query = db.query(OnboardingPreboardingTask).filter(OnboardingPreboardingTask.is_deleted == False)
    if employee_id:
        query = query.filter(OnboardingPreboardingTask.employee_id == employee_id)
    return query.order_by(OnboardingPreboardingTask.created_at.desc()).all()


def update_onboarding_task(db: Session, task_id: int, data: OnboardingTaskUpdate) -> OnboardingPreboardingTask:
    task = db.query(OnboardingPreboardingTask).filter(OnboardingPreboardingTask.id == task_id, OnboardingPreboardingTask.is_deleted == False).first()
    if not task:
        raise NotFoundException("OnboardingPreboardingTask", task_id)
    update_data = data.model_dump(exclude_unset=True)
    if "completed" in update_data and update_data["completed"] and not task.completed:
        task.completed_at = datetime.utcnow()
    for field, value in update_data.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


def delete_onboarding_task(db: Session, task_id: int) -> None:
    task = db.query(OnboardingPreboardingTask).filter(OnboardingPreboardingTask.id == task_id, OnboardingPreboardingTask.is_deleted == False).first()
    if not task:
        raise NotFoundException("OnboardingPreboardingTask", task_id)
    task.is_deleted = True
    db.commit()


# ════════════════════════════════════════════════════════════════════════════
# ONBOARDING DOCUMENTS SERVICE
# ════════════════════════════════════════════════════════════════════════════

_ONBOARDING_DOC_UPLOAD_DIR = os.environ.get("ONBOARDING_DOC_UPLOAD_DIR", "uploads/onboarding_documents")


def get_onboarding_documents(
    db: Session,
    onboarding_record_id: Optional[int] = None,
    category: Optional[str] = None,
) -> list:
    query = db.query(OnboardingDocument).filter(OnboardingDocument.is_deleted == False)
    if onboarding_record_id:
        query = query.filter(OnboardingDocument.onboarding_new_hire_id == onboarding_record_id)
    if category:
        query = query.filter(OnboardingDocument.category == category)
    docs = query.order_by(OnboardingDocument.created_at.desc()).all()
    return [_onboarding_doc_to_dict(doc) for doc in docs]


def _onboarding_doc_to_dict(doc: OnboardingDocument) -> dict:
    _base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")
    file_url = None
    if doc.file_path:
        rel_path = f"/{doc.file_path.replace(os.sep, '/')}"
        file_url = f"{_base_url}{rel_path}"
    return {
        "id": doc.id,
        "onboarding_new_hire_id": doc.onboarding_new_hire_id,
        "title": doc.title,
        "category": doc.category,
        "file_path": doc.file_path,
        "file_url": file_url,
        "status": doc.status,
        "rejection_reason": doc.rejection_reason,
        "tenant_id": doc.tenant_id,
        "created_at": doc.created_at,
        "updated_at": doc.updated_at,
    }


def create_onboarding_document(
    db: Session,
    title: str,
    category: str,
    file_path: str,
    onboarding_new_hire_id: Optional[int] = None,
    tenant_id: Optional[str] = None,
) -> dict:
    doc = OnboardingDocument(
        title=title,
        category=category,
        file_path=file_path,
        onboarding_new_hire_id=onboarding_new_hire_id,
        tenant_id=tenant_id,
        status="pending",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _onboarding_doc_to_dict(doc)


def update_onboarding_document(db: Session, document_id: int, data) -> dict:
    doc = db.query(OnboardingDocument).filter(
        OnboardingDocument.id == document_id,
        OnboardingDocument.is_deleted == False,
    ).first()
    if not doc:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("OnboardingDocument", document_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(doc, field, value)
    db.commit()
    db.refresh(doc)
    return _onboarding_doc_to_dict(doc)


def delete_onboarding_document(db: Session, document_id: int) -> None:
    doc = db.query(OnboardingDocument).filter(
        OnboardingDocument.id == document_id,
        OnboardingDocument.is_deleted == False,
    ).first()
    if not doc:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("OnboardingDocument", document_id)
    doc.is_deleted = True
    db.commit()


def get_onboarding_document_by_id(db: Session, document_id: int) -> dict:
    doc = db.query(OnboardingDocument).filter(
        OnboardingDocument.id == document_id,
        OnboardingDocument.is_deleted == False,
    ).first()
    if not doc:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("OnboardingDocument", document_id)
    return _onboarding_doc_to_dict(doc)


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


def get_performance_dashboard(db: Session, organization_id: Optional[int] = None) -> dict:
    check_and_seed_performance(db)
    from app.modules.hr.models import (
        PerformanceReview, PerformanceGoal, PerformanceFeedback,
        Appraisal, RequestStatus, GoalStatus
    )
    query_review = db.query(PerformanceReview)
    query_goal = db.query(PerformanceGoal)
    query_feedback = db.query(PerformanceFeedback)
    query_appraisal = db.query(Appraisal)
    
    if organization_id:
        query_review = query_review.filter(PerformanceReview.organization_id == organization_id)
        query_goal = query_goal.filter(PerformanceGoal.organization_id == organization_id)
        query_feedback = query_feedback.filter(PerformanceFeedback.organization_id == organization_id)
        query_appraisal = query_appraisal.filter(Appraisal.organization_id == organization_id)
    
    total_reviews = query_review.count()
    pending_reviews = query_review.filter(PerformanceReview.status == RequestStatus.PENDING).count()
    completed_reviews = query_review.filter(PerformanceReview.status.in_([RequestStatus.APPROVED, RequestStatus.COMPLETED])).count()
    total_goals = query_goal.count()
    completed_goals = query_goal.filter(PerformanceGoal.status == GoalStatus.COMPLETED).count()
    total_feedback = query_feedback.count()
    total_appraisals = query_appraisal.count()
    pending_appraisals = query_appraisal.filter(Appraisal.status == "draft").count()
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


def create_performance_goal(db: Session, data: PerformanceGoalCreate, organization_id: int) -> PerformanceGoal:
    goal = PerformanceGoal(**data.model_dump(), organization_id=organization_id)
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def get_performance_goals(db: Session, organization_id: Optional[int] = None, employee_id: Optional[int] = None) -> list[PerformanceGoal]:
    q = db.query(PerformanceGoal)
    if organization_id:
        q = q.filter(PerformanceGoal.organization_id == organization_id)
    if employee_id:
        q = q.filter(PerformanceGoal.employee_id == employee_id)
    return q.order_by(PerformanceGoal.created_at.desc()).all()


def get_performance_goal(db: Session, goal_id: int, organization_id: Optional[int] = None) -> PerformanceGoal:
    q = db.query(PerformanceGoal).filter(PerformanceGoal.id == goal_id)
    if organization_id:
        q = q.filter(PerformanceGoal.organization_id == organization_id)
    goal = q.first()
    if not goal:
        raise NotFoundException("PerformanceGoal", goal_id)
    return goal


def update_performance_goal(db: Session, goal_id: int, data: PerformanceGoalUpdate, organization_id: int) -> PerformanceGoal:
    goal = get_performance_goal(db, goal_id, organization_id)
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(goal, key, val)
    db.commit()
    db.refresh(goal)
    return goal


def delete_performance_goal(db: Session, goal_id: int, organization_id: int) -> None:
    goal = get_performance_goal(db, goal_id, organization_id)
    db.delete(goal)
    db.commit()


def create_performance_kpi(db: Session, data: PerformanceKpiCreate, organization_id: int) -> PerformanceKpi:
    kpi = PerformanceKpi(**data.model_dump(), organization_id=organization_id)
    db.add(kpi)
    db.commit()
    db.refresh(kpi)
    return kpi


def get_performance_kpis(db: Session, organization_id: Optional[int] = None, goal_id: Optional[int] = None, employee_id: Optional[int] = None) -> list[PerformanceKpi]:
    q = db.query(PerformanceKpi)
    if organization_id:
        q = q.filter(PerformanceKpi.organization_id == organization_id)
    if goal_id:
        q = q.filter(PerformanceKpi.goal_id == goal_id)
    if employee_id:
        q = q.filter(PerformanceKpi.employee_id == employee_id)
    return q.order_by(PerformanceKpi.created_at.desc()).all()


def get_performance_kpi(db: Session, kpi_id: int, organization_id: Optional[int] = None) -> PerformanceKpi:
    q = db.query(PerformanceKpi).filter(PerformanceKpi.id == kpi_id)
    if organization_id:
        q = q.filter(PerformanceKpi.organization_id == organization_id)
    kpi = q.first()
    if not kpi:
        raise NotFoundException("PerformanceKpi", kpi_id)
    return kpi


def update_performance_kpi(db: Session, kpi_id: int, data: PerformanceKpiUpdate, organization_id: int) -> PerformanceKpi:
    kpi = get_performance_kpi(db, kpi_id, organization_id)
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(kpi, key, val)
    db.commit()
    db.refresh(kpi)
    return kpi


def delete_performance_kpi(db: Session, kpi_id: int, organization_id: int) -> None:
    kpi = get_performance_kpi(db, kpi_id, organization_id)
    db.delete(kpi)
    db.commit()


def create_performance_feedback(db: Session, data: PerformanceFeedbackCreate, organization_id: Optional[int] = None) -> PerformanceFeedback:
    fb = PerformanceFeedback(**data.model_dump(), organization_id=organization_id)
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


def get_performance_feedback(
    db: Session,
    organization_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    reviewer_id: Optional[int] = None,
    review_id: Optional[int] = None,
) -> list[PerformanceFeedback]:
    q = db.query(PerformanceFeedback)
    if organization_id:
        q = q.filter(PerformanceFeedback.organization_id == organization_id)
    if employee_id:
        q = q.filter(PerformanceFeedback.employee_id == employee_id)
    if reviewer_id:
        q = q.filter(PerformanceFeedback.reviewer_id == reviewer_id)
    if review_id:
        q = q.filter(PerformanceFeedback.review_id == review_id)
    return q.order_by(PerformanceFeedback.submitted_at.desc()).all()


def delete_performance_feedback(db: Session, fb_id: int, organization_id: Optional[int] = None) -> None:
    q = db.query(PerformanceFeedback).filter(PerformanceFeedback.id == fb_id)
    if organization_id:
        q = q.filter(PerformanceFeedback.organization_id == organization_id)
    fb = q.first()
    if not fb:
        raise NotFoundException("PerformanceFeedback", fb_id)
    db.delete(fb)
    db.commit()


def create_appraisal(db: Session, data: AppraisalCreate, organization_id: Optional[int] = None) -> Appraisal:
    appraisal = Appraisal(**data.model_dump(), organization_id=organization_id)
    db.add(appraisal)
    db.commit()
    db.refresh(appraisal)
    return appraisal


def get_appraisals(db: Session, organization_id: Optional[int] = None, employee_id: Optional[int] = None) -> list[Appraisal]:
    q = db.query(Appraisal)
    if organization_id:
        q = q.filter(Appraisal.organization_id == organization_id)
    if employee_id:
        q = q.filter(Appraisal.employee_id == employee_id)
    return q.order_by(Appraisal.created_at.desc()).all()


def get_appraisal(db: Session, appraisal_id: int, organization_id: Optional[int] = None) -> Appraisal:
    q = db.query(Appraisal).filter(Appraisal.id == appraisal_id)
    if organization_id:
        q = q.filter(Appraisal.organization_id == organization_id)
    a = q.first()
    if not a:
        raise NotFoundException("Appraisal", appraisal_id)
    return a


def update_appraisal(db: Session, appraisal_id: int, data: AppraisalUpdate, organization_id: Optional[int] = None) -> Appraisal:
    a = get_appraisal(db, appraisal_id, organization_id)
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(a, key, val)
    db.commit()
    db.refresh(a)
    return a


def delete_appraisal(db: Session, appraisal_id: int, organization_id: Optional[int] = None) -> None:
    a = get_appraisal(db, appraisal_id, organization_id)
    db.delete(a)
    db.commit()


def get_performance_analytics(db: Session, organization_id: Optional[int] = None) -> dict:
    check_and_seed_performance(db)
    from app.modules.hr.models import (
        PerformanceReview, PerformanceGoal, PerformanceFeedback,
        Appraisal, RequestStatus, GoalStatus
    )
    base_reviews = db.query(PerformanceReview)
    base_goals = db.query(PerformanceGoal)
    base_feedback = db.query(PerformanceFeedback)
    base_appraisals = db.query(Appraisal)
    if organization_id:
        base_reviews = base_reviews.filter(PerformanceReview.organization_id == organization_id)
        base_goals = base_goals.filter(PerformanceGoal.organization_id == organization_id)
        base_feedback = base_feedback.filter(PerformanceFeedback.organization_id == organization_id)
        base_appraisals = base_appraisals.filter(Appraisal.organization_id == organization_id)
    total_reviews = base_reviews.count()
    completed_reviews = base_reviews.filter(PerformanceReview.status == RequestStatus.COMPLETED).count()
    avg_rating = base_reviews.with_entities(func.avg(PerformanceReview.rating)).scalar() or 0
    total_goals = base_goals.count()
    completed_goals = base_goals.filter(PerformanceGoal.status == GoalStatus.COMPLETED).count()
    total_feedback = base_feedback.count()
    total_appraisals = base_appraisals.count()
    avg_final_score = base_appraisals.with_entities(func.avg(Appraisal.final_score)).scalar() or 0
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


def create_performance_review(db: Session, data: PerformanceReviewCreate, organization_id: Optional[int] = None) -> PerformanceReview:
    review = PerformanceReview(**data.model_dump(), organization_id=organization_id)
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def get_performance_reviews(db: Session, organization_id: Optional[int] = None, employee_id: Optional[int] = None) -> list[PerformanceReview]:
    query = db.query(PerformanceReview)
    if organization_id:
        query = query.filter(PerformanceReview.organization_id == organization_id)
    if employee_id:
        query = query.filter(PerformanceReview.employee_id == employee_id)
    return query.order_by(PerformanceReview.created_at.desc()).all()


def get_performance_review(db: Session, review_id: int, organization_id: Optional[int] = None) -> PerformanceReview:
    q = db.query(PerformanceReview).filter(PerformanceReview.id == review_id)
    if organization_id:
        q = q.filter(PerformanceReview.organization_id == organization_id)
    review = q.first()
    if not review:
        raise NotFoundException("PerformanceReview", review_id)
    return review


def update_performance_review(db: Session, review_id: int, data: PerformanceReviewCreate, organization_id: Optional[int] = None) -> PerformanceReview:
    review = get_performance_review(db, review_id, organization_id)
    for key, val in data.model_dump().items():
        setattr(review, key, val)
    db.commit()
    db.refresh(review)
    return review


def delete_performance_review(db: Session, review_id: int, organization_id: Optional[int] = None) -> None:
    review = get_performance_review(db, review_id, organization_id)
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


def get_recruitment_candidates(db: Session, organization_id: int) -> list[RecruitmentCandidate]:
    return db.query(RecruitmentCandidate).filter(
        RecruitmentCandidate.organization_id == organization_id
    ).order_by(RecruitmentCandidate.applied_at.desc()).all()


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

def create_travel_request(db: Session, data: TravelRequestCreate, organization_id: int) -> TravelRequest:
    request = TravelRequest(**data.model_dump(), organization_id=organization_id)
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def get_travel_requests(
    db: Session,
    organization_id: int,
    employee_id: Optional[int] = None,
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    status: Optional[RequestStatus] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    query = db.query(TravelRequest).filter(TravelRequest.organization_id == organization_id)
    
    if employee_id:
        query = query.filter(TravelRequest.employee_id == employee_id)
    if status:
        query = query.filter(TravelRequest.status == status)
    if start_date:
        query = query.filter(TravelRequest.start_date >= start_date)
    if end_date:
        query = query.filter(TravelRequest.end_date <= end_date)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (TravelRequest.destination.ilike(search_term)) |
            (TravelRequest.purpose.ilike(search_term))
        )
    
    total = query.count()
    requests = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "items": requests,
    }


def get_travel_request(db: Session, request_id: int) -> TravelRequest:
    request = db.query(TravelRequest).filter(TravelRequest.id == request_id).first()
    if not request:
        raise NotFoundException("TravelRequest", request_id)
    return request


def update_travel_request(db: Session, request_id: int, data: TravelRequestUpdate) -> TravelRequest:
    request = get_travel_request(db, request_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(request, field, value)
    db.commit()
    db.refresh(request)
    return request


def delete_travel_request(db: Session, request_id: int) -> None:
    request = get_travel_request(db, request_id)
    db.delete(request)
    db.commit()


def cancel_travel_request(db: Session, request_id: int) -> TravelRequest:
    request = get_travel_request(db, request_id)
    if request.status == RequestStatus.COMPLETED or request.status == RequestStatus.CANCELLED:
        raise BadRequestException(f"Cannot cancel travel request with status: {request.status}")
    request.status = RequestStatus.CANCELLED
    db.commit()
    db.refresh(request)
    return request


def get_travel_request_expenses(db: Session, request_id: int) -> list[TravelExpense]:
    return db.query(TravelExpense).filter(TravelExpense.request_id == request_id).all()


# ════════════════════════════════════════════════════════════════════════════
# TRAVEL APPROVAL SERVICE
# ════════════════════════════════════════════════════════════════════════════

def create_travel_approval(db: Session, data: TravelApprovalCreate, organization_id: int) -> TravelApproval:
    approval = TravelApproval(**data.model_dump(), organization_id=organization_id)
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return approval


def get_travel_approvals(
    db: Session,
    organization_id: int,
    request_id: Optional[int] = None,
    approver_id: Optional[int] = None,
    status: Optional[RequestStatus] = None,
    page: int = 1,
    per_page: int = 20,
) -> dict:
    query = db.query(TravelApproval).filter(TravelApproval.organization_id == organization_id)
    
    if request_id:
        query = query.filter(TravelApproval.request_id == request_id)
    if approver_id:
        query = query.filter(TravelApproval.approver_id == approver_id)
    if status:
        query = query.filter(TravelApproval.status == status)
    
    total = query.count()
    approvals = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "items": approvals,
    }


def update_travel_approval(db: Session, approval_id: int, data: TravelApprovalUpdate) -> TravelApproval:
    approval = db.query(TravelApproval).filter(TravelApproval.id == approval_id).first()
    if not approval:
        raise NotFoundException("TravelApproval", approval_id)
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(approval, field, value)
    
    if "status" in update_data and update_data["status"] == RequestStatus.APPROVED:
        approval.approved_at = datetime.utcnow()
        # Update the travel request status
        request = approval.request
        request.status = RequestStatus.APPROVED
        request.approved_at = datetime.utcnow()
    
    db.commit()
    db.refresh(approval)
    return approval


def get_travel_approval_history(db: Session, request_id: int) -> list[TravelApproval]:
    return db.query(TravelApproval).filter(
        TravelApproval.request_id == request_id
    ).order_by(TravelApproval.created_at.desc()).all()


# ════════════════════════════════════════════════════════════════════════════
# TRAVEL EXPENSE SERVICE
# ════════════════════════════════════════════════════════════════════════════

def create_travel_expense(db: Session, data: TravelExpenseCreate, organization_id: int) -> TravelExpense:
    expense = TravelExpense(**data.model_dump(), organization_id=organization_id)
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def get_travel_expenses(
    db: Session,
    organization_id: int,
    request_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    status: Optional[RequestStatus] = None,
    expense_type: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
) -> dict:
    query = db.query(TravelExpense).filter(TravelExpense.organization_id == organization_id)
    
    if request_id:
        query = query.filter(TravelExpense.request_id == request_id)
    if employee_id:
        query = query.filter(TravelExpense.employee_id == employee_id)
    if status:
        query = query.filter(TravelExpense.status == status)
    if expense_type:
        query = query.filter(TravelExpense.expense_type == expense_type)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (TravelExpense.expense_type.ilike(search_term)) |
            (TravelExpense.description.ilike(search_term))
        )
    
    total = query.count()
    expenses = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "items": expenses,
    }


def get_travel_expense(db: Session, expense_id: int) -> TravelExpense:
    expense = db.query(TravelExpense).filter(TravelExpense.id == expense_id).first()
    if not expense:
        raise NotFoundException("TravelExpense", expense_id)
    return expense


def update_travel_expense(db: Session, expense_id: int, data: TravelExpenseUpdate) -> TravelExpense:
    expense = get_travel_expense(db, expense_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(expense, field, value)
    db.commit()
    db.refresh(expense)
    return expense


def delete_travel_expense(db: Session, expense_id: int) -> None:
    expense = get_travel_expense(db, expense_id)
    db.delete(expense)
    db.commit()


def approve_travel_expense(db: Session, expense_id: int, approver_id: int, comments: Optional[str] = None) -> TravelExpense:
    expense = get_travel_expense(db, expense_id)
    expense.status = RequestStatus.APPROVED
    expense.approved_at = datetime.utcnow()
    if comments:
        expense.description = f"{expense.description or ''} - Approved by {approver_id}: {comments}".strip(" - ")
    db.commit()
    db.refresh(expense)
    return expense


def reimburse_travel_expense(db: Session, expense_id: int, approver_id: int, comments: Optional[str] = None) -> TravelExpense:
    expense = get_travel_expense(db, expense_id)
    if expense.status != RequestStatus.APPROVED:
        raise BadRequestException("Only approved expenses can be reimbursed")
    expense.status = RequestStatus.COMPLETED
    expense.reimbursed_at = datetime.utcnow()
    if comments:
        expense.description = f"{expense.description or ''} - Reimbursed by {approver_id}: {comments}".strip(" - ")
    db.commit()
    db.refresh(expense)
    return expense


def get_travel_expense_summary(db: Session, org_id: int) -> dict:
    from sqlalchemy import func
    
    total_expenses = db.query(func.coalesce(func.sum(TravelExpense.amount), 0)).filter(
        TravelExpense.status.in_([RequestStatus.APPROVED, RequestStatus.COMPLETED])
    ).scalar()
    
    pending_expenses = db.query(func.coalesce(func.sum(TravelExpense.amount), 0)).filter(
        TravelExpense.status == RequestStatus.PENDING
    ).scalar()
    
    rejected_expenses = db.query(func.coalesce(func.sum(TravelExpense.amount), 0)).filter(
        TravelExpense.status == RequestStatus.REJECTED
    ).scalar()
    
    expenses_by_type = db.query(
        TravelExpense.expense_type,
        func.count(TravelExpense.id),
        func.coalesce(func.sum(TravelExpense.amount), 0)
    ).group_by(TravelExpense.expense_type).all()
    
    return {
        "total_expenses": total_expenses or 0,
        "pending_expenses": pending_expenses or 0,
        "rejected_expenses": rejected_expenses or 0,
        "expenses_by_type": [
            {
                "type": expense_type,
                "count": count,
                "total_amount": total_amount or 0
            }
            for expense_type, count, total_amount in expenses_by_type
        ]
    }


# ════════════════════════════════════════════════════════════════════════════
# TRAVEL RECEIPT SERVICE
# ════════════════════════════════════════════════════════════════════════════

def create_travel_receipt(db: Session, data: TravelReceiptCreate) -> TravelReceipt:
    receipt = TravelReceipt(**data.model_dump())
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return receipt


def get_travel_receipts(db: Session, expense_id: Optional[int] = None) -> list[TravelReceipt]:
    query = db.query(TravelReceipt)
    if expense_id:
        query = query.filter(TravelReceipt.expense_id == expense_id)
    return query.order_by(TravelReceipt.uploaded_at.desc()).all()


def verify_travel_receipt(db: Session, receipt_id: int, verified_by: int, comments: Optional[str] = None) -> TravelReceipt:
    receipt = db.query(TravelReceipt).filter(TravelReceipt.id == receipt_id).first()
    if not receipt:
        raise NotFoundException("TravelReceipt", receipt_id)
    
    receipt.verified = True
    receipt.verified_at = datetime.utcnow()
    if comments:
        receipt.notes = f"{receipt.notes or ''} - Verified by {verified_by}: {comments}".strip(" - ")
    
    db.commit()
    db.refresh(receipt)
    return receipt


# ════════════════════════════════════════════════════════════════════════════
# TRAVEL POLICY SERVICE
# ════════════════════════════════════════════════════════════════════════════

def get_travel_policies(db: Session, is_active: Optional[bool] = None) -> list[TravelPolicy]:
    query = db.query(TravelPolicy)
    if is_active is not None:
        query = query.filter(TravelPolicy.is_active == is_active)
    return query.order_by(TravelPolicy.policy_name).all()


def get_travel_policy(db: Session, policy_id: int) -> TravelPolicy:
    policy = db.query(TravelPolicy).filter(TravelPolicy.id == policy_id).first()
    if not policy:
        raise NotFoundException("TravelPolicy", policy_id)
    return policy


def create_travel_policy(db: Session, data: TravelPolicyCreate) -> TravelPolicy:
    policy = TravelPolicy(**data.model_dump())
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def update_travel_policy(db: Session, policy_id: int, data: TravelPolicyUpdate) -> TravelPolicy:
    policy = get_travel_policy(db, policy_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(policy, field, value)
    db.commit()
    db.refresh(policy)
    return policy


# ════════════════════════════════════════════════════════════════════════════
# TRAVEL SETTINGS SERVICE
# ════════════════════════════════════════════════════════════════════════════

def get_travel_settings(db: Session, organization_id: int) -> TravelSetting:
    settings = db.query(TravelSetting).filter(
        TravelSetting.organization_id == organization_id
    ).first()
    if not settings:
        settings = TravelSetting(organization_id=organization_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def update_travel_settings(db: Session, organization_id: int, data: TravelSettingUpdate) -> TravelSetting:
    settings = get_travel_settings(db, organization_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    db.commit()
    db.refresh(settings)
    return settings


def get_travel_dashboard_stats(db: Session, organization_id: int) -> dict:
    from sqlalchemy import func
    
    total_requests = db.query(func.count(TravelRequest.id)).filter(
        TravelRequest.organization_id == organization_id
    ).scalar()
    
    pending_requests = db.query(func.count(TravelRequest.id)).filter(
        TravelRequest.organization_id == organization_id,
        TravelRequest.status == RequestStatus.PENDING
    ).scalar()
    
    approved_requests = db.query(func.count(TravelRequest.id)).filter(
        TravelRequest.organization_id == organization_id,
        TravelRequest.status == RequestStatus.APPROVED
    ).scalar()
    
    total_expenses = db.query(func.coalesce(func.sum(TravelExpense.amount), 0)).join(
        TravelRequest, TravelRequest.id == TravelExpense.request_id
    ).filter(
        TravelRequest.organization_id == organization_id,
        TravelExpense.status.in_([RequestStatus.APPROVED, RequestStatus.COMPLETED])
    ).scalar()
    
    return {
        "total_requests": total_requests or 0,
        "pending_requests": pending_requests or 0,
        "approved_requests": approved_requests or 0,
        "total_expenses": total_expenses or 0,
    }


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


def get_workforce_summary(db: Session, organization_id: int) -> dict:
    base_filter = [Employee.organization_id == organization_id]
    total = db.query(Employee).filter(*base_filter).count()
    active = db.query(Employee).filter(*base_filter, Employee.status == EmployeeStatus.ACTIVE).count()

    dept_breakdown = (
        db.query(Department.name, func.count(Employee.id))
        .join(Employee, Employee.department_id == Department.id, isouter=True)
        .filter(*base_filter)
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


# ════════════════════════════════════════════════════════════════════════════════
# EMPLOYEE MANAGEMENT SERVICE
# ════════════════════════════════════════════════════════════════════════════════

def get_employee_dashboard(db: Session, organization_id: Optional[int] = None, visible_roles: Optional[list] = None) -> dict:
    base_filter = [Employee.organization_id == organization_id] if organization_id else []
    if visible_roles:
        base_filter.append(Employee.role.in_(visible_roles))

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
    visible_roles: Optional[list] = None,
) -> dict:
    per_page = min(per_page, 10000)
    query = db.query(Employee)

    if organization_id:
        query = query.filter(Employee.organization_id == organization_id)

    if visible_roles:
        query = query.filter(Employee.role.in_(visible_roles))

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


def get_employee_profile(db: Session, employee_id: int, organization_id: Optional[int] = None) -> EmployeeProfile:
    query = db.query(EmployeeProfile).filter(EmployeeProfile.employee_id == employee_id)
    if organization_id:
        query = query.filter(EmployeeProfile.organization_id == organization_id)
    profile = query.first()
    if not profile:
        raise NotFoundException("EmployeeProfile", employee_id)
    return profile


def create_employee_profile(db: Session, data: EmployeeProfileCreate) -> EmployeeProfile:
    profile = EmployeeProfile(**data.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_employee_profile(db: Session, employee_id: int, data: EmployeeProfileUpdate, organization_id: Optional[int] = None) -> EmployeeProfile:
    query = db.query(EmployeeProfile).filter(EmployeeProfile.employee_id == employee_id)
    if organization_id:
        query = query.filter(EmployeeProfile.organization_id == organization_id)
    profile = query.first()
    if not profile:
        raise NotFoundException("EmployeeProfile", employee_id)
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    db.commit()
    db.refresh(profile)
    return profile


def get_employee_reporting(db: Session, employee_id: int, organization_id: Optional[int] = None) -> EmployeeReporting:
    query = db.query(EmployeeReporting).filter(EmployeeReporting.employee_id == employee_id)
    if organization_id:
        query = query.filter(EmployeeReporting.organization_id == organization_id)
    reporting = query.first()
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


def change_manager(db: Session, data: ChangeManagerRequest, organization_id: Optional[int] = None) -> Employee:
    employee = get_employee_by_id(db, data.employee_id, organization_id)
    
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
    employee = get_employee_by_id(db, data.employee_id, organization_id)
    
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
    employee = get_employee_by_id(db, data.employee_id, organization_id)
    
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
    employee = get_employee_by_id(db, data.employee_id, organization_id)
    
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
    employee = get_employee_by_id(db, data.employee_id, organization_id)
    
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
    employee = get_employee_by_id(db, data.employee_id, organization_id)
    
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


def get_employee_reports(db: Session, filters: Optional[dict] = None, organization_id: Optional[int] = None, visible_roles: Optional[list] = None) -> list:
    query = db.query(Employee)
    if organization_id:
        query = query.filter(Employee.organization_id == organization_id)
    if visible_roles:
        query = query.filter(Employee.role.in_(visible_roles))
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


def export_employee_reports(db: Session, data: EmployeeExportRequest, organization_id: Optional[int] = None, visible_roles: Optional[list] = None) -> list:
    return get_employee_reports(db, data.filters, organization_id, visible_roles=visible_roles)

# ════════════════════════════════════════════════════════════════════════════════
# DESIGNATION SERVICE
# ════════════════════════════════════════════════════════════════════════════════

def get_designations(db: Session, organization_id: int = None) -> list:
    from app.modules.hr.models import Designation
    query = db.query(Designation)
    if organization_id is not None:
        query = query.filter(Designation.organization_id == organization_id)
    return query.order_by(Designation.created_at.desc()).all()


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