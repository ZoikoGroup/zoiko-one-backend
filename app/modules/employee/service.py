import secrets
import string
from datetime import date, datetime, timedelta
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.modules.employee.models import (
    Employee, EmploymentType, EmployeeStatus, UserRole, Gender,
)
from app.modules.employee.schema import (
    EmployeeCreate, EmployeeUpdate,
    UserCreateRequest, UserUpdateRequest,
    LoginRequest, RegisterRequest,
    ChangeManagerRequest, ConfirmProbationRequest,
    PromoteEmployeeRequest, TransferEmployeeRequest,
    ResignationRequest, ExitEmployeeRequest, EmployeeExportRequest,
    EmployeeCompensationCreate, EmployeeCompensationUpdate,
    EmployeeBenefitCreate,
)
from app.modules.hr.models import (
    Organization, OrganizationStatus, Department,
    EmployeeProfile, EmployeeReporting, EmployeeLifecycle, EmployeeHistory,
    EmployeeCompensation, EmployeeBenefit,
)
from app.core.security import hash_password, verify_password, create_access_token
from app.core.exceptions import (
    NotFoundException, AlreadyExistsException,
    UnauthorizedException, BadRequestException,
)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_employee_code(db: Session) -> str:
    max_id = db.query(func.max(Employee.id)).scalar()
    next_number = (max_id + 1) if max_id else 1
    return f"ZK-{next_number:05d}"


def _generate_temp_password(length: int = 12) -> str:
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


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


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH SERVICE
# ═══════════════════════════════════════════════════════════════════════════════

def login_employee(db: Session, data: LoginRequest) -> dict:
    employee = db.query(Employee).filter(Employee.email == data.email).first()
    if not employee:
        raise UnauthorizedException("Invalid email or password.")

    if not verify_password(data.password, employee.hashed_password):
        raise UnauthorizedException("Invalid email or password.")

    if employee.organization_id:
        org = db.query(Organization).filter(Organization.id == employee.organization_id).first()
        if org:
            if org.status == OrganizationStatus.PENDING:
                raise UnauthorizedException(
                    "Your organization registration is awaiting Super Admin approval. "
                    "You will be able to sign in after approval."
                )
            elif org.status == OrganizationStatus.REJECTED:
                reason = f" Reason: {org.rejection_reason}" if org.rejection_reason else ""
                raise UnauthorizedException(
                    f"Your organization registration has been rejected.{reason}"
                )
            elif org.status == OrganizationStatus.SUSPENDED:
                raise UnauthorizedException(
                    "Your organization has been suspended. Please contact support."
                )

    if not employee.is_active:
        raise UnauthorizedException("Your account has been deactivated.")

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


def register_enterprise(db: Session, data: RegisterRequest) -> dict:
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
        is_active=False,
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


def change_password(
    db: Session,
    employee_id: int,
    current_password: str,
    new_password: str,
) -> dict:
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise NotFoundException("Employee", employee_id)

    if not verify_password(current_password, employee.hashed_password):
        raise UnauthorizedException("Current password is incorrect.")

    employee.hashed_password = hash_password(new_password)
    db.commit()
    db.refresh(employee)

    return {"message": "Password changed successfully."}


# ═══════════════════════════════════════════════════════════════════════════════
# USER MANAGEMENT SERVICE (Organization Admin)
# ═══════════════════════════════════════════════════════════════════════════════

def create_organization_user(
    db: Session,
    data: "UserCreateRequest",
    organization_id: int,
    created_by_id: int,
) -> Employee:
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


def get_organization_users(
    db: Session,
    organization_id: int,
    search: Optional[str] = None,
    role: Optional[UserRole] = None,
    status: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
) -> dict:
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
    user = get_organization_user(db, user_id, organization_id)
    user.is_active = False
    user.status = EmployeeStatus.INACTIVE
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
    user = get_organization_user(db, user_id, organization_id)
    temp_password = _generate_temp_password()
    user.hashed_password = hash_password(temp_password)
    user.updated_by = updated_by_id
    db.commit()
    db.refresh(user)
    return user, temp_password


# ═══════════════════════════════════════════════════════════════════════════════
# EMPLOYEE CRUD
# ═══════════════════════════════════════════════════════════════════════════════

def create_employee(db: Session, data: EmployeeCreate, organization_id: Optional[int] = None) -> Employee:
    existing = db.query(Employee).filter(Employee.email == data.email).first()
    if existing:
        raise AlreadyExistsException("Employee", "email")

    if data.department_id:
        dept = db.query(Department).filter(Department.id == data.department_id).first()
        if not dept:
            raise NotFoundException("Department", data.department_id)

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
) -> dict:
    per_page = min(per_page, 100)
    query = db.query(Employee)

    if organization_id:
        query = query.filter(Employee.organization_id == organization_id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Employee.first_name.ilike(search_term)) |
            (Employee.last_name.ilike(search_term)) |
            (Employee.email.ilike(search_term)) |
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
            (Employee.last_name.ilike(search_term)) |
            (Employee.email.ilike(search_term)) |
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


def get_employee_by_id(db: Session, employee_id: int, organization_id: Optional[int] = None) -> Employee:
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise NotFoundException("Employee", employee_id)
    return employee


def update_employee(db: Session, employee_id: int, data: EmployeeUpdate, organization_id: Optional[int] = None) -> Employee:
    employee = get_employee_by_id(db, employee_id)

    if data.department_id:
        dept = db.query(Department).filter(Department.id == data.department_id).first()
        if not dept:
            raise NotFoundException("Department", data.department_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)

    db.commit()
    db.refresh(employee)
    return employee


def deactivate_employee(db: Session, employee_id: int, organization_id: Optional[int] = None) -> Employee:
    employee = get_employee_by_id(db, employee_id)
    employee.is_active = False
    employee.status = EmployeeStatus.TERMINATED

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


# ═══════════════════════════════════════════════════════════════════════════════
# EMPLOYEE DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

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

    from datetime import date as dt_date
    new_hires_this_month = db.query(Employee).filter(
        *base_filter,
        extract("month", Employee.date_of_joining) == extract("month", dt_date.today()),
        extract("year", Employee.date_of_joining) == extract("year", dt_date.today())
    ).count()

    exits_this_month = db.query(Employee).filter(
        *base_filter,
        extract("month", Employee.updated_at) == extract("month", dt_date.today()),
        extract("year", Employee.updated_at) == extract("year", dt_date.today()),
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
            "status": status,
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
            "probation_end_date": event_date,
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
            "confirmation_date": event_date,
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
        today = dt_date.today()
        next_birthday = dt_date(today.year, joining_date.month, joining_date.day)
        if next_birthday < today:
            next_birthday = dt_date(today.year + 1, joining_date.month, joining_date.day)

        upcoming_anniversaries.append({
            "employee_id": emp_id,
            "employee_name": f"{first_name} {last_name}",
            "next_birthday": next_birthday,
            "join_date": joining_date,
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


# ═══════════════════════════════════════════════════════════════════════════════
# EMPLOYEE PROFILE
# ═══════════════════════════════════════════════════════════════════════════════

def get_employee_profile(db: Session, employee_id: int) -> EmployeeProfile:
    profile = db.query(EmployeeProfile).filter(EmployeeProfile.employee_id == employee_id).first()
    if not profile:
        raise NotFoundException("EmployeeProfile", employee_id)
    return profile


def create_employee_profile(db: Session, data) -> EmployeeProfile:
    profile = EmployeeProfile(**data.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_employee_profile(db: Session, employee_id: int, data) -> EmployeeProfile:
    profile = db.query(EmployeeProfile).filter(EmployeeProfile.employee_id == employee_id).first()
    if not profile:
        raise NotFoundException("EmployeeProfile", employee_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile


# ═══════════════════════════════════════════════════════════════════════════════
# EMPLOYEE REPORTING
# ═══════════════════════════════════════════════════════════════════════════════

def get_employee_reporting(db: Session, employee_id: int) -> EmployeeReporting:
    reporting = db.query(EmployeeReporting).filter(EmployeeReporting.employee_id == employee_id).first()
    if not reporting:
        raise NotFoundException("EmployeeReporting", employee_id)
    return reporting


def create_employee_reporting(db: Session, data) -> EmployeeReporting:
    reporting = EmployeeReporting(**data.model_dump())
    db.add(reporting)
    db.commit()
    db.refresh(reporting)
    return reporting


def update_employee_reporting(db: Session, employee_id: int, data) -> EmployeeReporting:
    reporting = get_employee_reporting(db, employee_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(reporting, field, value)
    db.commit()
    db.refresh(reporting)
    return reporting


# ═══════════════════════════════════════════════════════════════════════════════
# EMPLOYEE LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════════════

def get_employee_lifecycle(db: Session, employee_id: Optional[int] = None, organization_id: Optional[int] = None) -> list[EmployeeLifecycle]:
    query = db.query(EmployeeLifecycle)
    if organization_id:
        query = query.filter(EmployeeLifecycle.organization_id == organization_id)
    if employee_id:
        query = query.filter(EmployeeLifecycle.employee_id == employee_id)
    return query.order_by(EmployeeLifecycle.event_date.desc()).all()


def create_employee_lifecycle_event(db: Session, data) -> EmployeeLifecycle:
    event = EmployeeLifecycle(**data.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def update_employee_lifecycle_event(db: Session, event_id: int, data) -> EmployeeLifecycle:
    event = db.query(EmployeeLifecycle).filter(EmployeeLifecycle.id == event_id).first()
    if not event:
        raise NotFoundException("EmployeeLifecycle", event_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)

    db.commit()
    db.refresh(event)
    return event


# ═══════════════════════════════════════════════════════════════════════════════
# EMPLOYEE HISTORY
# ═══════════════════════════════════════════════════════════════════════════════

def get_employee_history(db: Session, employee_id: int) -> list[EmployeeHistory]:
    return db.query(EmployeeHistory).filter(
        EmployeeHistory.employee_id == employee_id
    ).order_by(EmployeeHistory.created_at.desc()).all()


def create_employee_history_entry(
    db: Session,
    employee_id: int,
    field_name: str,
    old_value: str,
    new_value: str,
    changed_by: Optional[int] = None,
    change_reason: Optional[str] = None,
) -> EmployeeHistory:
    history = EmployeeHistory(
        employee_id=employee_id,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        changed_by=changed_by,
        change_reason=change_reason,
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    return history


# ═══════════════════════════════════════════════════════════════════════════════
# ORG CHART
# ═══════════════════════════════════════════════════════════════════════════════

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
            "children": [],
        }

    reporting_structure = []
    for emp in employees:
        manager_id = report_map.get(emp.id)
        if manager_id and manager_id in employee_map:
            employee_map[emp.id]["manager_name"] = employee_map[manager_id]["name"]
            employee_map[manager_id]["children"].append(employee_map[emp.id])
        else:
            reporting_structure.append(employee_map[emp.id])

    return {
        "employees": list(employee_map.values()),
        "reporting_structure": reporting_structure,
        "departments": dept_map,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# EMPLOYEE LIFECYCLE OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

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
            effective_from=date.today(),
        )
        db.add(reporting)
    else:
        reporting.manager_id = data.new_manager_id

    db.commit()

    create_employee_history_entry(
        db, data.employee_id, "manager_id",
        str(old_manager_id), str(data.new_manager_id),
        change_reason=data.reason,
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
        reason=data.notes,
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
        reason=data.reason,
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
            "location": data.new_location,
        },
        reason=data.reason,
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
            "last_working_date": str(data.last_working_date),
        },
        reason=data.reason,
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
            "final_settlement_date": str(data.final_settlement_date),
        },
        reason=data.reason,
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
                (Employee.last_name.ilike(search_term)) |
                (Employee.email.ilike(search_term)) |
                (Employee.employee_code.ilike(search_term))
            )

    return query.order_by(Employee.created_at.desc()).all()


def export_employee_reports(db: Session, data: EmployeeExportRequest, organization_id: Optional[int] = None) -> list:
    return get_employee_reports(db, data.filters, organization_id)


# ═══════════════════════════════════════════════════════════════════════════════
# EMPLOYEE COMPENSATION & BENEFITS
# ═══════════════════════════════════════════════════════════════════════════════

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
    from app.modules.hr.models import SalaryRevision
    db.query(SalaryRevision).filter(SalaryRevision.employee_compensation_id == comp_id).delete()
    db.delete(comp)
    db.commit()

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
