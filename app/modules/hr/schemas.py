from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.modules.hr.models import (
    EmploymentType, EmployeeStatus, UserRole, Gender,
    AttendanceStatus, LeaveType, RequestStatus, AssetStatus,
    OnboardingStatus,
)


# ════════════════════════════════════════════════════════════════════════════
# DEPARTMENT SCHEMAS
# ════════════════════════════════════════════════════════════════════════════

class DepartmentCreate(BaseModel):
    """Data required to CREATE a new department."""
    name:        str = Field(..., min_length=2, max_length=100, example="Engineering")
    code:        str = Field(..., min_length=2, max_length=20,  example="ENG")
    description: Optional[str] = Field(None, example="Software development team")

    # Validator: Clean whitespace and protect case duplication
    @field_validator("name")
    @classmethod
    def clean_name(cls, v):
        return v.strip()

    # Validator: auto-uppercase the code
    @field_validator("code")
    @classmethod
    def uppercase_code(cls, v):
        return v.upper().strip()


class DepartmentUpdate(BaseModel):
    """All fields optional — only send what you want to change."""
    name:        Optional[str] = Field(None, min_length=2, max_length=100)
    code:        Optional[str] = Field(None, min_length=2, max_length=20)
    description: Optional[str] = None
    is_active:   Optional[bool] = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, v):
        return v.strip() if v else v

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, v):
        return v.upper().strip() if v else v


class DepartmentResponse(BaseModel):
    """What the API returns when you request department data."""
    id:           int
    name:         str
    code:         str
    description:  Optional[str]
    is_active:    bool
    created_at:   Optional[datetime]

    # This tells Pydantic to read from SQLAlchemy model attributes directly
    model_config = {"from_attributes": True}


# ════════════════════════════════════════════════════════════════════════════
# EMPLOYEE SCHEMAS
# ════════════════════════════════════════════════════════════════════════════

class EmployeeCreate(BaseModel):
    """Data required to CREATE (onboard) a new employee."""
    email:           EmailStr = Field(..., example="john.doe@zoiko.com")
    password:        str      = Field(..., min_length=8, example="SecurePass123!")
    first_name:      str      = Field(..., min_length=1, max_length=100, example="John")
    last_name:       str      = Field(..., min_length=1, max_length=100, example="Doe")
    phone:           Optional[str]  = Field(None, example="+91-9876543210")
    date_of_birth:   Optional[date] = Field(None, example="1995-06-15")
    gender:          Optional[Gender] = None
    job_title:       str             = Field(..., example="Software Engineer")
    employment_type: EmploymentType  = Field(EmploymentType.FULL_TIME)
    date_of_joining: date            = Field(..., example="2024-01-15")
    department_id:   Optional[int]   = Field(None, example=1)
    basic_salary:    Optional[Decimal] = Field(None, example=75000.00)
    role:            UserRole        = Field(UserRole.EMPLOYEE)


class EmployeeUpdate(BaseModel):
    """Update an existing employee. ALL fields are optional."""
    first_name:      Optional[str]            = None
    last_name:       Optional[str]            = None
    phone:           Optional[str]            = None
    date_of_birth:   Optional[date]           = None
    gender:          Optional[Gender]         = None
    job_title:       Optional[str]            = None
    employment_type: Optional[EmploymentType] = None
    status:          Optional[EmployeeStatus] = None
    department_id:   Optional[int]            = None
    basic_salary:    Optional[Decimal]        = None
    address:         Optional[str]            = None
    profile_picture: Optional[str]            = None


class EmployeeResponse(BaseModel):
    """What the API returns for employee data."""
    id:              int
    email:           str
    role:            UserRole
    is_active:       bool
    first_name:      str
    last_name:       str
    full_name:       str          
    phone:           Optional[str]
    date_of_birth:   Optional[date]
    gender:          Optional[Gender]
    profile_picture: Optional[str]
    employee_code:   str
    job_title:       str
    employment_type: EmploymentType
    status:          EmployeeStatus
    date_of_joining: date
    basic_salary:    Optional[Decimal]
    department_id:   Optional[int]
    department:      Optional[DepartmentResponse] = None
    created_at:      Optional[datetime]

    model_config = {"from_attributes": True}


class EmployeeListResponse(BaseModel):
    total:    int
    page:     int
    per_page: int
    items:    List[EmployeeResponse]


# ════════════════════════════════════════════════════════════════════════════
# HR SUBMODULE SCHEMAS
# ════════════════════════════════════════════════════════════════════════════

class AttendanceCreate(BaseModel):
    employee_id: int
    date: date
    status: AttendanceStatus = AttendanceStatus.PRESENT
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    notes: Optional[str] = None


class AttendanceResponse(BaseModel):
    id: int
    employee_id: int
    date: date
    status: AttendanceStatus
    check_in: Optional[datetime]
    check_out: Optional[datetime]
    notes: Optional[str]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class LeaveRequestCreate(BaseModel):
    employee_id: int
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: Optional[str] = None


class LeaveRequestUpdate(BaseModel):
    status: Optional[RequestStatus] = None
    reason: Optional[str] = None


class LeaveRequestResponse(BaseModel):
    id: int
    employee_id: int
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: Optional[str]
    status: RequestStatus
    created_at: Optional[datetime]
    reviewed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AssetCreate(BaseModel):
    employee_id: Optional[int] = None
    name: str
    asset_tag: str
    assigned_date: Optional[date] = None
    status: AssetStatus = AssetStatus.ASSIGNED
    notes: Optional[str] = None


class AssetResponse(BaseModel):
    id: int
    employee_id: Optional[int]
    name: str
    asset_tag: str
    assigned_date: Optional[date]
    status: AssetStatus
    notes: Optional[str]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class CompensationCreate(BaseModel):
    employee_id: int
    amount: Decimal
    component: str
    description: Optional[str] = None
    period: Optional[str] = None


class CompensationResponse(BaseModel):
    id: int
    employee_id: int
    amount: Decimal
    component: str
    description: Optional[str]
    period: Optional[str]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ComplianceRecordCreate(BaseModel):
    employee_id: int
    policy_name: str
    status: RequestStatus = RequestStatus.PENDING
    notes: Optional[str] = None


class ComplianceRecordResponse(BaseModel):
    id: int
    employee_id: int
    policy_name: str
    status: RequestStatus
    completed_at: Optional[datetime]
    notes: Optional[str]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class EngagementSurveyCreate(BaseModel):
    employee_id: int
    survey_name: str
    score: int
    comments: Optional[str] = None


class EngagementSurveyResponse(BaseModel):
    id: int
    employee_id: int
    survey_name: str
    score: int
    comments: Optional[str]
    completed_at: Optional[datetime]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class EssRequestCreate(BaseModel):
    employee_id: int
    request_type: str
    description: Optional[str] = None


class EssRequestResponse(BaseModel):
    id: int
    employee_id: int
    request_type: str
    description: Optional[str]
    status: RequestStatus
    created_at: Optional[datetime]
    resolved_at: Optional[datetime]

    model_config = {"from_attributes": True}


class LearningCourseCreate(BaseModel):
    employee_id: int
    title: str
    provider: Optional[str] = None
    status: str = Field("enrolled", example="completed")
    notes: Optional[str] = None


class LearningCourseResponse(BaseModel):
    id: int
    employee_id: int
    title: str
    provider: Optional[str]
    status: str
    enrolled_at: Optional[datetime]
    completed_at: Optional[datetime]
    notes: Optional[str]

    model_config = {"from_attributes": True}


class OnboardingRecordCreate(BaseModel):
    candidate_name: str = Field(..., min_length=1, max_length=150)
    email: EmailStr
    phone: Optional[str] = None
    position: str = Field(..., min_length=1, max_length=150)
    department_id: Optional[int] = None
    manager_id: Optional[int] = None
    joining_date: Optional[date] = None
    notes: Optional[str] = None
    status: OnboardingStatus = OnboardingStatus.OFFER_SENT


class OnboardingRecordUpdate(BaseModel):
    candidate_name: Optional[str] = Field(None, min_length=1, max_length=150)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    position: Optional[str] = Field(None, min_length=1, max_length=150)
    department_id: Optional[int] = None
    manager_id: Optional[int] = None
    joining_date: Optional[date] = None
    notes: Optional[str] = None
    status: Optional[OnboardingStatus] = None
    employee_id: Optional[int] = None


class OnboardingRecordResponse(BaseModel):
    id: int
    employee_id: Optional[int]
    candidate_name: str
    email: str
    phone: Optional[str]
    position: str
    department_id: Optional[int]
    department_name: Optional[str] = None
    manager_id: Optional[int]
    manager_name: Optional[str] = None
    joining_date: Optional[date]
    status: OnboardingStatus
    notes: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class OnboardingTaskCreate(BaseModel):
    employee_id: Optional[int] = None
    onboarding_record_id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    due_date: Optional[date] = None


class OnboardingTaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    due_date: Optional[date] = None
    completed: Optional[bool] = None


class OnboardingTaskResponse(BaseModel):
    id: int
    employee_id: Optional[int]
    onboarding_record_id: Optional[int]
    title: str
    description: Optional[str]
    due_date: Optional[date]
    completed: bool
    completed_at: Optional[datetime]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class OnboardingActivityResponse(BaseModel):
    id: int
    onboarding_record_id: Optional[int]
    action: str
    description: str
    created_at: Optional[datetime]
    timestamp: Optional[datetime] = None

    model_config = {"from_attributes": True}


class OnboardingDashboardResponse(BaseModel):
    totalNewHires: int
    pendingOnboarding: int
    completedOnboarding: int
    documentsPending: int
    assetsPending: int
    orientationPending: int
    trainingPending: int
    monthlyJoiningTrend: list[dict]
    departmentWise: list[dict]
    completionStatus: dict
    upcomingJoiners: list[dict]
    recentActivities: list[dict]


class PerformanceReviewCreate(BaseModel):
    employee_id: int
    reviewer_id: Optional[int] = None
    cycle: str
    rating: int = Field(..., ge=1, le=5)
    comments: Optional[str] = None


class PerformanceReviewResponse(BaseModel):
    id: int
    employee_id: int
    reviewer_id: Optional[int]
    cycle: str
    rating: int
    comments: Optional[str]
    status: RequestStatus
    created_at: Optional[datetime]
    reviewed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class RecruitmentCandidateCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    position: str
    source: Optional[str] = None
    notes: Optional[str] = None


class RecruitmentCandidateUpdate(BaseModel):
    status: Optional[RequestStatus] = None
    notes: Optional[str] = None


class RecruitmentCandidateResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: Optional[str]
    position: str
    source: Optional[str]
    status: RequestStatus
    applied_at: Optional[datetime]
    notes: Optional[str]

    model_config = {"from_attributes": True}


class TravelRequestCreate(BaseModel):
    employee_id: int
    destination: str
    purpose: Optional[str] = None
    start_date: date
    end_date: date


class TravelRequestResponse(BaseModel):
    id: int
    employee_id: int
    destination: str
    purpose: Optional[str]
    start_date: date
    end_date: date
    status: RequestStatus
    approved_at: Optional[datetime]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class WorkforcePlanCreate(BaseModel):
    department_id: Optional[int] = None
    year: int
    headcount_target: int
    notes: Optional[str] = None


class WorkforcePlanResponse(BaseModel):
    id: int
    department_id: Optional[int]
    year: int
    headcount_target: int
    notes: Optional[str]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class WorkforceSummaryResponse(BaseModel):
    total_employees: int
    active_employees: int
    departments: int
    open_leave_requests: int
    open_travel_requests: int
    open_ess_requests: int


class LoginRequest(BaseModel):
    email:    EmailStr = Field(..., example="admin@zoiko.com")
    password: str      = Field(..., example="SecurePass123!")


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    employee:     EmployeeResponse


class SuccessResponse(BaseModel):
    success: bool = True
    message: str