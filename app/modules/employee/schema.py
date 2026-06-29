from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.modules.employee.models import (
    EmploymentType, EmployeeStatus, UserRole, Gender,
)


class DepartmentResponse(BaseModel):
    id: int
    name: str
    code: str
    description: Optional[str]
    is_active: bool
    created_at: Optional[datetime]
    organization_id: Optional[int]
    head: Optional[str]
    budget: Optional[Decimal]
    spent_budget: Optional[Decimal]
    establishment_year: Optional[int]
    parent_id: Optional[int]
    employee_count: Optional[int] = 0

    model_config = {"from_attributes": True}


class EmployeeCreate(BaseModel):
    email:               EmailStr          = Field(..., example="john.doe@zoiko.com")
    password:            str               = Field(..., min_length=8, example="SecurePass123!")
    first_name:          str               = Field(..., min_length=1, max_length=100, example="John")
    last_name:           str               = Field(..., min_length=1, max_length=100, example="Doe")
    phone:               Optional[str]     = Field(None, example="+91-9876543210")
    date_of_birth:       Optional[date]    = Field(None, example="1995-06-15")
    gender:              Optional[Gender]  = None
    job_title:           str               = Field(..., example="Software Engineer")
    employment_type:     EmploymentType    = Field(EmploymentType.FULL_TIME)
    date_of_joining:     date              = Field(..., example="2024-01-15")
    department_id:       Optional[int]     = Field(None, example=1)
    designation_id:      Optional[int]     = Field(None, example=1)
    reporting_manager_id: Optional[int]    = Field(None, example=1)
    basic_salary:        Optional[Decimal] = Field(None, example=75000.00)
    ctc:                 Optional[Decimal] = Field(None, example=1200000.00)
    role:                UserRole          = Field(UserRole.EMPLOYEE)
    work_email:          Optional[str]     = Field(None, example="john@zoikone.com")
    personal_email:      Optional[str]     = Field(None, example="john@gmail.com")
    confirmation_date:   Optional[date]    = Field(None, example="2024-07-15")
    company:             Optional[str]     = Field(None, example="ZoikoOne")
    business_unit:       Optional[str]     = Field(None, example="Enterprise")
    division:            Optional[str]     = Field(None, example="Engineering")
    team:                Optional[str]     = Field(None, example="Frontend")
    current_address:     Optional[str]     = Field(None, example="123 Main St")
    permanent_address:   Optional[str]     = Field(None, example="456 Oak Ave")
    city:                Optional[str]     = Field(None, example="Mumbai")
    state:               Optional[str]     = Field(None, example="Maharashtra")
    country:             Optional[str]     = Field(None, example="India")
    pincode:             Optional[str]     = Field(None, example="400001")


class EmployeeUpdate(BaseModel):
    first_name:           Optional[str]            = None
    last_name:            Optional[str]            = None
    phone:                Optional[str]            = None
    date_of_birth:        Optional[date]           = None
    gender:               Optional[Gender]         = None
    job_title:            Optional[str]            = None
    employment_type:      Optional[EmploymentType] = None
    status:               Optional[EmployeeStatus] = None
    department_id:        Optional[int]            = None
    designation_id:       Optional[int]            = None
    reporting_manager_id: Optional[int]            = None
    basic_salary:         Optional[Decimal]        = None
    ctc:                  Optional[Decimal]        = None
    address:              Optional[str]            = None
    profile_picture:      Optional[str]            = None
    work_email:           Optional[str]            = None
    personal_email:       Optional[str]            = None
    confirmation_date:    Optional[date]           = None
    company:              Optional[str]            = None
    business_unit:        Optional[str]            = None
    division:             Optional[str]            = None
    team:                 Optional[str]            = None
    current_address:      Optional[str]            = None
    permanent_address:    Optional[str]            = None
    city:                 Optional[str]            = None
    state:                Optional[str]            = None
    country:              Optional[str]            = None
    pincode:              Optional[str]            = None


def _to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


class EmployeeResponse(BaseModel):
    id:                   int
    email:                str
    role:                 UserRole
    is_active:            bool
    first_name:           str
    last_name:            str
    full_name:            str
    phone:                Optional[str] = Field(None, serialization_alias="phoneNumber")
    date_of_birth:        Optional[date]
    gender:               Optional[Gender]
    profile_picture:      Optional[str]
    employee_code:        str
    job_title:            str
    employment_type:      EmploymentType
    status:               EmployeeStatus
    date_of_joining:      date
    basic_salary:         Optional[Decimal]
    ctc:                  Optional[Decimal]
    department_id:        Optional[int]
    designation_id:       Optional[int]
    reporting_manager_id: Optional[int]
    department:           Optional[DepartmentResponse] = None
    work_email:           Optional[str]
    personal_email:       Optional[str]
    confirmation_date:    Optional[date]
    company:              Optional[str]
    business_unit:        Optional[str]
    division:             Optional[str]
    team:                 Optional[str]
    current_address:      Optional[str]
    permanent_address:    Optional[str]
    city:                 Optional[str]
    state:                Optional[str]
    country:              Optional[str]
    pincode:              Optional[str]
    created_at:           Optional[datetime]
    created_by:           Optional[int] = None
    updated_by:           Optional[int] = None

    # Extra fields the frontend expects in camelCase
    designationName:   Optional[str] = None
    departmentName:    Optional[str] = None
    managerName:       Optional[str] = None
    title:             Optional[str] = None
    workLocation:      Optional[str] = None
    shiftTiming:       Optional[str] = None

    model_config = {
        "from_attributes": True,
        "alias_generator": _to_camel,
        "populate_by_name": True,
    }

    @model_validator(mode="before")
    @classmethod
    def _populate_extra(cls, data):
        if isinstance(data, dict):
            return data
        fields = list(cls.model_fields.keys())
        result = {f: getattr(data, f, None) for f in fields}
        if hasattr(data, "designation"):
            d = data.designation
            if d is not None:
                result["designationName"] = getattr(d, "title", None) or getattr(d, "name", None)
        if hasattr(data, "department") and data.department:
            result["departmentName"] = data.department.name
        if hasattr(data, "reporting_manager") and data.reporting_manager:
            result["managerName"] = data.reporting_manager.full_name
        if result.get("designationName"):
            result["title"] = result["designationName"]
        return result


class EmployeeListResponse(BaseModel):
    total:    int
    page:     int
    per_page: int
    items:    List[EmployeeResponse]


class TokenResponse(BaseModel):
    access_token:  str
    token_type:    str = "bearer"
    refresh_token: Optional[str] = None
    employee:      EmployeeResponse


class SuccessResponse(BaseModel):
    message: str


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., example="admin@zoiko.com")
    password: str = Field(..., example="SecurePassword123")


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, example="John Doe")
    email: EmailStr = Field(..., example="admin@company.com")
    password: str = Field(..., min_length=8, example="SecurePass123!")
    organization: str = Field(..., min_length=1, max_length=200, example="Acme Inc.")


class UserCreateRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100, example="Jane")
    last_name:  str = Field(..., min_length=1, max_length=100, example="Smith")
    email:      EmailStr = Field(..., example="jane.smith@company.com")
    phone:      Optional[str] = Field(None, example="+1-555-0100")
    role:       UserRole = Field(..., example="hr_admin")


class UserUpdateRequest(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name:  Optional[str] = Field(None, min_length=1, max_length=100)
    phone:      Optional[str] = None
    role:       Optional[UserRole] = None
    is_active:  Optional[bool] = None


class UserResponse(BaseModel):
    id:            int
    email:         str
    role:          UserRole
    is_active:     bool
    first_name:    str
    last_name:     str
    full_name:     str
    phone:         Optional[str]
    employee_code: str
    status:        EmployeeStatus
    job_title:     Optional[str] = None
    department:    Optional[str] = None
    created_at:    Optional[datetime]
    updated_at:    Optional[datetime]
    created_by:    Optional[int] = None
    updated_by:    Optional[int] = None

    model_config = {"from_attributes": True}

    @field_validator("department", mode="before")
    @classmethod
    def coerce_department(cls, v):
        if v is None or isinstance(v, str):
            return v
        if hasattr(v, "name"):
            return v.name
        return str(v)


class UserListResponse(BaseModel):
    total:    int
    page:     int
    per_page: int
    items:    List[UserResponse]


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, example="OldPass123!")
    new_password:     str = Field(..., min_length=8, example="NewSecurePass456!")


class PasswordResetResponse(BaseModel):
    message:           str
    temporary_password: str
