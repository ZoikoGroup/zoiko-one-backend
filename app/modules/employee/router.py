import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user, get_current_admin, get_current_org_admin

from app.modules.super_admin.models import AuditLog, AuditAction, LoginActivity

from app.modules.employee import service
from app.modules.employee.models import EmployeeStatus, UserRole
from app.modules.employee.schema import (
    EmployeeCreate, EmployeeUpdate, EmployeeResponse, EmployeeListResponse,
    LoginRequest, RegisterRequest, TokenResponse, SuccessResponse,
    UserCreateRequest, UserUpdateRequest, UserResponse, UserListResponse,
    PasswordResetResponse, ChangePasswordRequest,
)
from app.modules.hr.schemas import (
    LeaveRequestCreate, LeaveRequestResponse,
    TravelRequestCreate, TravelRequestResponse,
    TravelExpenseCreateSimple, TravelExpenseResponse,
    HrDocumentResponse, HrDocumentUpdate, HrDocumentStatusUpdate,
)
from app.modules.hr import service as hr_service

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
employee_router = APIRouter(prefix="/hr", tags=["Employees"])


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@auth_router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get access token",
)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    result = service.login_employee(db, data)
    employee = result.get("employee")
    if employee:
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")
        login_activity = LoginActivity(
            user_id=employee.id,
            email=employee.email,
            organization_id=employee.organization_id,
            ip_address=ip,
            user_agent=ua,
            status="success",
        )
        db.add(login_activity)
        audit = AuditLog(
            action=AuditAction.LOGIN,
            entity_type="User",
            entity_id=employee.id,
            performed_by=employee.id,
            performed_by_email=employee.email,
            details={"ip": ip, "user_agent": ua},
        )
        db.add(audit)
        db.commit()
    return result


@auth_router.post(
    "/register",
    response_model=dict,
    summary="Register a new organization",
)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    return service.register_enterprise(db, data)


@auth_router.get(
    "/me",
    response_model=EmployeeResponse,
    summary="Get current logged-in user",
)
def get_me(current_user=Depends(get_current_user)):
    return current_user


@auth_router.post(
    "/logout",
    response_model=SuccessResponse,
    summary="Logout",
)
def logout(current_user=Depends(get_current_user), request: Request = None, db: Session = Depends(get_db)):
    ip = request.client.host if request and request.client else None
    audit = AuditLog(
        action=AuditAction.LOGOUT,
        entity_type="User",
        entity_id=current_user.id,
        performed_by=current_user.id,
        performed_by_email=current_user.email,
        details={"ip": ip},
    )
    db.add(audit)
    db.commit()
    return {"message": "Logged out successfully."}


@auth_router.post(
    "/change-password",
    response_model=SuccessResponse,
    summary="Change current user password",
)
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return service.change_password(
        db,
        employee_id=current_user.id,
        current_password=data.current_password,
        new_password=data.new_password,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# USER MANAGEMENT ENDPOINTS (Organization Admin)
# ═══════════════════════════════════════════════════════════════════════════════

@employee_router.get(
    "/admin/users",
    response_model=UserListResponse,
    summary="List users in the organization",
    dependencies=[Depends(get_current_org_admin)],
)
def list_users(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    search: Optional[str] = Query(None, description="Search by name, email, or code"),
    role: Optional[str] = Query(None, description="Filter by role"),
    status: Optional[str] = Query(None, description="Filter by status: active, inactive"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
):
    role_filter = None
    if role:
        try:
            role_filter = UserRole(role)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid role: {role}")

    return service.get_organization_users(
        db,
        organization_id=current_user.organization_id,
        search=search,
        role=role_filter,
        status=status,
        page=page,
        per_page=per_page,
    )


@employee_router.post(
    "/admin/users",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    dependencies=[Depends(get_current_org_admin)],
)
def create_user(
    data: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if data.role not in (UserRole.ADMIN, UserRole.HR_ADMIN, UserRole.EMPLOYEE):
        raise HTTPException(
            status_code=422,
            detail=f"Cannot create user with role '{data.role.value}'. Allowed: admin, hr_admin, employee."
        )

    employee, temp_password = service.create_organization_user(
        db, data,
        organization_id=current_user.organization_id,
        created_by_id=current_user.id,
    )

    return {
        "message": f"User {employee.full_name} created successfully.",
        "user": UserResponse.model_validate(employee),
        "temporary_password": temp_password,
    }


@employee_router.get(
    "/admin/users/{user_id}",
    response_model=UserResponse,
    summary="Get user details",
    dependencies=[Depends(get_current_org_admin)],
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return service.get_organization_user(db, user_id, current_user.organization_id)


@employee_router.put(
    "/admin/users/{user_id}",
    response_model=UserResponse,
    summary="Update a user",
    dependencies=[Depends(get_current_org_admin)],
)
def update_user(
    user_id: int,
    data: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return service.update_organization_user(
        db, user_id, data,
        organization_id=current_user.organization_id,
        updated_by_id=current_user.id,
    )


@employee_router.delete(
    "/admin/users/{user_id}",
    response_model=UserResponse,
    summary="Deactivate (soft-delete) a user",
    dependencies=[Depends(get_current_org_admin)],
)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return service.deactivate_organization_user(
        db, user_id,
        organization_id=current_user.organization_id,
        updated_by_id=current_user.id,
    )


@employee_router.post(
    "/admin/users/{user_id}/activate",
    response_model=UserResponse,
    summary="Activate a user",
    dependencies=[Depends(get_current_org_admin)],
)
def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return service.activate_organization_user(
        db, user_id,
        organization_id=current_user.organization_id,
        updated_by_id=current_user.id,
    )


@employee_router.post(
    "/admin/users/{user_id}/reset-password",
    response_model=PasswordResetResponse,
    summary="Reset user password",
    dependencies=[Depends(get_current_org_admin)],
)
def reset_user_password(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user, temp_password = service.reset_user_password(
        db, user_id,
        organization_id=current_user.organization_id,
        updated_by_id=current_user.id,
    )

    return PasswordResetResponse(
        message=f"Password reset for {user.full_name}.",
        temporary_password=temp_password,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# EMPLOYEE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@employee_router.get(
    "/employees/me",
    response_model=EmployeeResponse,
    summary="Get my own profile",
)
def get_my_profile(current_user=Depends(get_current_user)):
    return current_user


@employee_router.put(
    "/employees/me",
    response_model=EmployeeResponse,
    summary="Update my own profile",
)
def update_my_profile(
    data: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return service.update_employee(db, current_user.id, data, current_user.organization_id)


@employee_router.post(
    "/employees",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Onboard a new employee",
    dependencies=[Depends(get_current_admin)],
)
def create_employee(data: EmployeeCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return service.create_employee(db, data, current_user.organization_id)


@employee_router.get(
    "/employees",
    response_model=EmployeeListResponse,
    summary="List employees with search and filters",
)
def list_employees(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=10000, description="Results per page"),
    search: Optional[str] = Query(None, description="Search name/email/code"),
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    status: Optional[EmployeeStatus] = Query(None, description="Filter by status"),
):
    return service.get_all_employees(db, page, per_page, search, department_id, status, current_user.organization_id)


@employee_router.get(
    "/employees/{employee_id}",
    response_model=EmployeeResponse,
    summary="Get a single employee by ID",
)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return service.get_employee_by_id(db, employee_id, current_user.organization_id)


@employee_router.put(
    "/employees/{employee_id}",
    response_model=EmployeeResponse,
    summary="Update employee details",
    dependencies=[Depends(get_current_admin)],
)
def update_employee(
    employee_id: int,
    data: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return service.update_employee(db, employee_id, data, current_user.organization_id)


@employee_router.delete(
    "/employees/{employee_id}",
    response_model=SuccessResponse,
    summary="Deactivate / terminate an employee",
    dependencies=[Depends(get_current_admin)],
)
def deactivate_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service.deactivate_employee(db, employee_id, current_user.organization_id)
    return {"message": f"Employee {employee_id} has been deactivated successfully."}


# ═══════════════════════════════════════════════════════════════════════════════
# EMPLOYEE SELF-SERVICE — LEAVE
# ═══════════════════════════════════════════════════════════════════════════════

@employee_router.post(
    "/leaves",
    response_model=LeaveRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Apply for leave",
)
def create_leave(
    data: LeaveRequestCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if data.employee_id is None:
        data.employee_id = current_user.id
    return hr_service.create_leave_request(db, data, org_id=current_user.organization_id)


# ═══════════════════════════════════════════════════════════════════════════════
# EMPLOYEE SELF-SERVICE — TRAVEL
# ═══════════════════════════════════════════════════════════════════════════════

@employee_router.post(
    "/travel",
    response_model=TravelRequestResponse,
    summary="Create a travel request",
)
def create_travel(
    data: TravelRequestCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if data.employee_id is None:
        data.employee_id = current_user.id
    return hr_service.create_travel_request(db, data, organization_id=current_user.organization_id)


@employee_router.post(
    "/travel/expenses",
    response_model=TravelExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a travel expense",
)
def create_travel_expense(
    data: TravelExpenseCreateSimple,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if data.employee_id is None:
        data.employee_id = current_user.id
    return hr_service.create_travel_expense(db, data, organization_id=current_user.organization_id)


# ═══════════════════════════════════════════════════════════════════════════════
# EMPLOYEE SELF-SERVICE — DOCUMENTS
# ═══════════════════════════════════════════════════════════════════════════════

_DOCUMENT_UPLOAD_DIR = os.environ.get("HR_DOCUMENT_UPLOAD_DIR", "uploads/hr_documents")


@employee_router.post(
    "/documents/upload",
    response_model=HrDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new document",
)
async def upload_document(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    file: UploadFile = File(..., description="The document file to upload"),
    title: str = Form("Untitled"),
    category: str = Form("other"),
    description: Optional[str] = Form(None),
    note: Optional[str] = Form(None),
    document_type: Optional[str] = Form(None),
):
    description = description or note
    os.makedirs(_DOCUMENT_UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(_DOCUMENT_UPLOAD_DIR, unique_name)

    contents = await file.read()
    with open(file_path, "wb") as fh:
        fh.write(contents)

    return hr_service.upload_hr_document(
        db=db,
        title=title,
        category=category,
        file_path=file_path,
        file_name=file.filename or unique_name,
        file_size=len(contents),
        mime_type=file.content_type,
        description=description,
        document_type=document_type,
        uploaded_by=current_user.id,
    )
