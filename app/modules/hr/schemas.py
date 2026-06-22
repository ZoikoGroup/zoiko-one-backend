"""
modules/hr/schemas.py
---------------------
Pydantic schemas = data validation for API requests and responses.
"""

from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.modules.hr.models import (
    EmploymentType, EmployeeStatus, UserRole, Gender,
    AttendanceStatus, LeaveType, RequestStatus, AssetStatus,
    AssetCondition, MaintenancePriority, MaintenanceStatus,
    RequestPriority, AssetRequestStatus,
    OnboardingStatus,
    ShiftType,
    RecruitmentCandidateStatus, RequisitionStatus, InterviewStatus, OfferStatus,
)


# ════════════════════════════════════════════════════════════════════════════
# DEPARTMENT SCHEMAS
# ════════════════════════════════════════════════════════════════════════════

class DepartmentCreate(BaseModel):
    """Data required to CREATE a new department."""
    name:        str = Field(..., min_length=2, max_length=100, example="Engineering")
    code:        str = Field(..., min_length=2, max_length=20,  example="ENG")
    description: Optional[str] = Field(None, example="Software development team")

    @field_validator("name")
    @classmethod
    def clean_name(cls, v):
        return v.strip()

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
    job_title:       str              = Field(..., example="Software Engineer")
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
    """Wraps a list of employees with pagination info."""
    total:    int
    page:     int
    per_page: int
    items:    List[EmployeeResponse]


class TokenResponse(BaseModel):
    """Response returned after successful login."""
    access_token:  str
    token_type:    str = "bearer"
    refresh_token: Optional[str] = None
    employee:      EmployeeResponse


class SuccessResponse(BaseModel):
    """Generic success message response."""
    message: str


# ════════════════════════════════════════════════════════════════════════════
# HR SUBMODULE SCHEMAS
# ════════════════════════════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    """Authentication structure for login requests."""
    email: EmailStr = Field(..., example="admin@zoiko.com")
    password: str = Field(..., example="SecurePassword123")


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


class AttendanceUpdate(BaseModel):
    status: Optional[AttendanceStatus] = None
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    notes: Optional[str] = None


# ════════════════════════════════════════════════════════════════════════════
# SHIFT SCHEMAS
# ════════════════════════════════════════════════════════════════════════════

class ShiftCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    shift_type: ShiftType = ShiftType.GENERAL
    start_time: str = Field(..., min_length=4, max_length=5, pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(..., min_length=4, max_length=5, pattern=r"^\d{2}:\d{2}$")
    grace_time_minutes: int = Field(default=0, ge=0)
    break_duration_minutes: int = Field(default=60, ge=0)
    is_overtime_eligible: bool = True
    requires_attendance: bool = True
    description: Optional[str] = None


class ShiftUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    shift_type: Optional[ShiftType] = None
    start_time: Optional[str] = Field(None, min_length=4, max_length=5, pattern=r"^\d{2}:\d{2}$")
    end_time: Optional[str] = Field(None, min_length=4, max_length=5, pattern=r"^\d{2}:\d{2}$")
    grace_time_minutes: Optional[int] = Field(None, ge=0)
    break_duration_minutes: Optional[int] = Field(None, ge=0)
    is_overtime_eligible: Optional[bool] = None
    requires_attendance: Optional[bool] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ShiftResponse(BaseModel):
    id: int
    name: str
    shift_type: ShiftType
    start_time: str
    end_time: str
    grace_time_minutes: int
    break_duration_minutes: int
    is_overtime_eligible: bool
    requires_attendance: bool
    description: Optional[str]
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ════════════════════════════════════════════════════════════════════════════
# SHIFT ROSTER SCHEMAS
# ════════════════════════════════════════════════════════════════════════════

class ShiftRosterCreate(BaseModel):
    employee_id: int
    shift_id: int
    date: date


class ShiftRosterBulkCreate(BaseModel):
    assignments: list[ShiftRosterCreate]


class ShiftRosterResponse(BaseModel):
    id: int
    employee_id: int
    shift_id: int
    date: date
    is_active: bool
    assigned_by: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ════════════════════════════════════════════════════════════════════════════
# HOLIDAY SCHEMAS
# ════════════════════════════════════════════════════════════════════════════

class HolidayCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    date: date
    type: str = "public"
    is_recurring: bool = False
    description: Optional[str] = None


class HolidayUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    date: Optional[date] = None
    type: Optional[str] = None
    is_recurring: Optional[bool] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class HolidayResponse(BaseModel):
    id: int
    name: str
    date: date
    type: Optional[str]
    is_recurring: bool
    description: Optional[str]
    is_active: bool
    created_by: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ════════════════════════════════════════════════════════════════════════════
# DASHBOARD / REPORT SCHEMAS
# ════════════════════════════════════════════════════════════════════════════

class AttendanceDashboardResponse(BaseModel):
    present_today: int = 0
    absent_today: int = 0
    late_arrivals: int = 0
    early_departures: int = 0
    on_leave: int = 0
    on_leave_count: int = 0
    remote: int = 0
    remote_count: int = 0
    overtime: int = 0
    overtime_count: int = 0
    attendance_percentage: float = 0.0
    attendance_rate: float = 0.0
    avg_working_hours: float = 0.0
    total_employees: int = 0
    department_attendance: list[dict] = []
    department_breakdown: list[dict] = []
    shift_distribution: list[dict] = []
    shift_utilization: list[dict] = []
    attendance_trend: list[dict] = []


class AttendanceReportResponse(BaseModel):
    employee_id: int
    employee_name: Optional[str] = None
    department: Optional[str] = None
    period_start: date
    period_end: date
    total_working_days: int = 0
    days_present: int = 0
    days_absent: int = 0
    days_on_leave: int = 0
    days_remote: int = 0
    late_arrivals: int = 0
    early_departures: int = 0
    overtime_hours: float = 0.0
    attendance_percentage: float = 0.0


class LeaveRequestCreate(BaseModel):
    employee_id: Optional[int] = None
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: Optional[str] = None


class LeaveRequestUpdate(BaseModel):
    status: Optional[RequestStatus] = None
    reason: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class LeaveRequestResponse(BaseModel):
    id: int
    employee_id: int
    organization_id: int
    leave_type: LeaveType
    start_date: date
    end_date: date
    days: int
    reason: Optional[str]
    status: RequestStatus
    reviewed_by: Optional[int]
    reviewed_at: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class LeaveTypeConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=100, description="Unique code for the leave type (e.g. emergency, comp_off)")
    default_days_per_year: int = 0
    carry_forward_allowed: bool = False
    carry_forward_max_days: Optional[int] = None
    min_notice_days: Optional[int] = None
    max_consecutive_days: Optional[int] = None
    requires_approval: bool = True
    is_active: bool = True
    color: Optional[str] = None
    icon: Optional[str] = None


class LeaveTypeConfigUpdate(BaseModel):
    name: Optional[str] = None
    default_days_per_year: Optional[int] = None
    carry_forward_allowed: Optional[bool] = None
    carry_forward_max_days: Optional[int] = None
    min_notice_days: Optional[int] = None
    max_consecutive_days: Optional[int] = None
    requires_approval: Optional[bool] = None
    is_active: Optional[bool] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class LeaveTypeConfigResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    code: str
    default_days_per_year: int
    carry_forward_allowed: bool
    carry_forward_max_days: Optional[int]
    min_notice_days: Optional[int]
    max_consecutive_days: Optional[int]
    requires_approval: bool
    is_active: bool
    color: Optional[str]
    icon: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class LeaveSettingCreate(BaseModel):
    working_days: list[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    leave_year_start: Optional[date] = None
    max_consecutive_days: Optional[int] = None
    carry_forward_limit: int = 0
    approval_workflow: str = "manager"
    escalation_days: int = 3
    auto_approve_days: int = 1
    notification_on_submit: bool = True
    notification_on_approve: bool = True
    notification_on_reject: bool = True


class LeaveSettingUpdate(BaseModel):
    working_days: Optional[list[str]] = None
    leave_year_start: Optional[date] = None
    max_consecutive_days: Optional[int] = None
    carry_forward_limit: Optional[int] = None
    approval_workflow: Optional[str] = None
    escalation_days: Optional[int] = None
    auto_approve_days: Optional[int] = None
    notification_on_submit: Optional[bool] = None
    notification_on_approve: Optional[bool] = None
    notification_on_reject: Optional[bool] = None


class LeaveSettingResponse(BaseModel):
    id: int
    organization_id: int
    working_days: list[str]
    leave_year_start: Optional[date]
    max_consecutive_days: Optional[int]
    carry_forward_limit: int
    approval_workflow: str
    escalation_days: int
    auto_approve_days: int
    notification_on_submit: bool
    notification_on_approve: bool
    notification_on_reject: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class LeaveBalanceResponse(BaseModel):
    id: int
    employee_id: int
    organization_id: int
    leave_type: LeaveType
    total_days: int
    used_days: int
    pending_days: int
    year: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class LeaveBalanceUpdate(BaseModel):
    total_days: Optional[int] = None
    used_days: Optional[int] = None
    pending_days: Optional[int] = None


class LeaveDashboardStats(BaseModel):
    total_requests: int = 0
    pending_requests: int = 0
    approved_requests: int = 0
    rejected_requests: int = 0
    total_days_taken: int = 0
    pending_days_taken: int = 0
    approved_days_taken: int = 0
    employee_count: int = 0
    on_leave_today: int = 0


class LeaveCalendarEvent(BaseModel):
    id: int
    employee_id: int
    employee_name: str = ""
    leave_type: LeaveType
    start_date: date
    end_date: date
    days: int
    status: RequestStatus


class LeaveStatisticsResponse(BaseModel):
    total_employees: int = 0
    total_requests: int = 0
    approval_rate: float = 0.0
    average_days_per_request: float = 0.0
    leave_type_breakdown: Optional[list[dict]] = None
    monthly_trend: Optional[list[dict]] = None


class AssetCreate(BaseModel):
    employee_id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=150)
    asset_tag: str = Field(..., min_length=1, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    serial_number: Optional[str] = Field(None, max_length=200)
    department: Optional[str] = Field(None, max_length=100)
    assigned_date: Optional[date] = None
    purchase_date: Optional[date] = None
    purchase_cost: Optional[Decimal] = Field(None, ge=0)
    condition: Optional[AssetCondition] = None
    status: AssetStatus = AssetStatus.AVAILABLE
    notes: Optional[str] = None


class AssetUpdate(BaseModel):
    employee_id: Optional[int] = None
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    asset_tag: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    serial_number: Optional[str] = Field(None, max_length=200)
    department: Optional[str] = Field(None, max_length=100)
    assigned_date: Optional[date] = None
    purchase_date: Optional[date] = None
    purchase_cost: Optional[Decimal] = Field(None, ge=0)
    condition: Optional[AssetCondition] = None
    status: Optional[AssetStatus] = None
    notes: Optional[str] = None


class AssetResponse(BaseModel):
    id: int
    employee_id: Optional[int]
    name: str
    asset_tag: str
    category: Optional[str]
    serial_number: Optional[str]
    department: Optional[str]
    assigned_date: Optional[date]
    purchase_date: Optional[date]
    purchase_cost: Optional[Decimal]
    condition: Optional[AssetCondition]
    status: AssetStatus
    notes: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    employee_name: Optional[str] = None

    model_config = {"from_attributes": True}


class AssetListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: list[AssetResponse]


class MaintenanceCreate(BaseModel):
    asset_id: int
    asset_name: Optional[str] = None
    asset_tag: Optional[str] = None
    issue: str
    priority: MaintenancePriority = MaintenancePriority.MEDIUM
    reported_by: Optional[str] = None
    reported_by_id: Optional[int] = None
    reported_on: date


class MaintenanceUpdate(BaseModel):
    issue: Optional[str] = None
    priority: Optional[MaintenancePriority] = None
    status: Optional[MaintenanceStatus] = None


class MaintenanceResolve(BaseModel):
    resolution: str
    resolved_by: Optional[int] = None


class MaintenanceResponse(BaseModel):
    id: int
    asset_id: int
    asset_name: Optional[str]
    asset_tag: Optional[str]
    issue: str
    priority: MaintenancePriority
    reported_by: Optional[str]
    reported_by_id: Optional[int]
    reported_on: date
    status: MaintenanceStatus
    resolution: Optional[str]
    resolved_by: Optional[int]
    resolved_on: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AssetRequestCreate(BaseModel):
    employee_id: Optional[int] = None
    employee_name: Optional[str] = None
    asset_type: str
    quantity: int = Field(default=1, ge=1)
    priority: RequestPriority = RequestPriority.MEDIUM
    reason: Optional[str] = None
    notes: Optional[str] = None
    requested_on: date


class AssetRequestResponse(BaseModel):
    id: int
    employee_id: Optional[int]
    employee_name: Optional[str]
    asset_type: str
    quantity: int
    priority: RequestPriority
    reason: Optional[str]
    notes: Optional[str]
    status: AssetRequestStatus
    requested_on: date
    approved_by: Optional[int]
    approved_on: Optional[datetime]
    fulfilled_on: Optional[datetime]
    cancelled_on: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AssetCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class AssetCategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_active: bool
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AssetReportGenerate(BaseModel):
    report_type: str
    title: str
    description: Optional[str] = None
    parameters: Optional[str] = None


class AssetReportResponse(BaseModel):
    id: int
    report_type: str
    title: str
    description: Optional[str]
    generated_by: Optional[int]
    parameters: Optional[str]
    file_url: Optional[str]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AssetSettingUpdate(BaseModel):
    settings: dict[str, Optional[str]]


class AssetSettingResponse(BaseModel):
    id: int
    setting_key: str
    setting_value: Optional[str]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AssetDashboardResponse(BaseModel):
    total_assets: int = 0
    assigned_count: int = 0
    available_count: int = 0
    maintenance_count: int = 0
    retired_count: int = 0
    lost_count: int = 0
    recently_added: int = 0
    category_breakdown: list[dict] = []
    status_breakdown: list[dict] = []
    pending_requests: int = 0
    open_maintenance: int = 0


# ── Compensation Schemas ──────────────────────────────────────────────────────

# Legacy compensation item (used by old dashboard stats)
class CompensationCreate(BaseModel):
    employee_id: int
    amount: Decimal
    item_type: str
    description: Optional[str] = None

class CompensationResponse(CompensationCreate):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}


class PayGradeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    min_salary: Decimal
    max_salary: Decimal
    description: Optional[str] = None

class PayGradeUpdate(BaseModel):
    name: Optional[str] = None
    min_salary: Optional[Decimal] = None
    max_salary: Optional[Decimal] = None
    description: Optional[str] = None

class PayGradeResponse(PayGradeCreate):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    model_config = {"from_attributes": True}

class CompensationBandCreate(BaseModel):
    band_name: str = Field(..., min_length=1, max_length=100)
    level: int
    min_salary: Decimal
    max_salary: Decimal

class CompensationBandUpdate(BaseModel):
    band_name: Optional[str] = None
    level: Optional[int] = None
    min_salary: Optional[Decimal] = None
    max_salary: Optional[Decimal] = None

class CompensationBandResponse(CompensationBandCreate):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    model_config = {"from_attributes": True}


class SalaryComponentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    component_type: str = Field(..., pattern="^(earning|deduction)$")
    is_taxable: bool = True
    default_amount: Optional[Decimal] = None
    description: Optional[str] = None


class SalaryComponentUpdate(BaseModel):
    name: Optional[str] = None
    component_type: Optional[str] = None
    is_taxable: Optional[bool] = None
    default_amount: Optional[Decimal] = None
    description: Optional[str] = None


class SalaryComponentResponse(SalaryComponentCreate):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    model_config = {"from_attributes": True}


class SalaryStructureCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    is_active: bool = True

class SalaryStructureUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None

class SalaryStructureResponse(SalaryStructureCreate):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    model_config = {"from_attributes": True}

class StructureComponentCreate(BaseModel):
    structure_id: int
    component_id: int
    amount_or_formula: str

class StructureComponentUpdate(BaseModel):
    structure_id: Optional[int] = None
    component_id: Optional[int] = None
    amount_or_formula: Optional[str] = None

class StructureComponentResponse(StructureComponentCreate):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    model_config = {"from_attributes": True}

class EmployeeCompensationCreate(BaseModel):
    employee_id: int
    structure_id: int
    pay_grade_id: Optional[int] = None
    band_id: Optional[int] = None
    effective_date: date

class EmployeeCompensationUpdate(BaseModel):
    structure_id: Optional[int] = None
    pay_grade_id: Optional[int] = None
    band_id: Optional[int] = None
    effective_date: Optional[date] = None

class EmployeeCompensationResponse(EmployeeCompensationCreate):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    model_config = {"from_attributes": True}

class SalaryRevisionCreate(BaseModel):
    employee_compensation_id: int
    old_salary: Optional[Decimal] = None
    new_salary: Decimal
    effective_date: date
    reason: Optional[str] = None

class SalaryRevisionResponse(SalaryRevisionCreate):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    model_config = {"from_attributes": True}

class AllowanceCreate(BaseModel):
    employee_id: int
    allowance_type: str
    amount: Decimal
    effective_date: date

class AllowanceUpdate(BaseModel):
    allowance_type: Optional[str] = None
    amount: Optional[Decimal] = None
    effective_date: Optional[date] = None

class AllowanceResponse(AllowanceCreate):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    model_config = {"from_attributes": True}

class BenefitCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True

class BenefitUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class BenefitResponse(BenefitCreate):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    model_config = {"from_attributes": True}

class EmployeeBenefitCreate(BaseModel):
    employee_id: int
    benefit_id: int
    coverage_start_date: Optional[date] = None
    coverage_end_date: Optional[date] = None

class EmployeeBenefitResponse(EmployeeBenefitCreate):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
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


class CourseCreate(BaseModel):
    course_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    course_type: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=100)
    provider: Optional[str] = Field(None, max_length=150)
    duration_hours: Optional[int] = Field(None, ge=0)
    cost: Optional[Decimal] = Field(None, ge=0)
    status: str = "active"


class CourseUpdate(BaseModel):
    course_name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    course_type: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=100)
    provider: Optional[str] = Field(None, max_length=150)
    duration_hours: Optional[int] = Field(None, ge=0)
    cost: Optional[Decimal] = Field(None, ge=0)
    status: Optional[str] = None


class CourseResponse(BaseModel):
    id: int
    course_name: str
    description: Optional[str]
    course_type: Optional[str]
    category: Optional[str]
    provider: Optional[str]
    duration_hours: Optional[int]
    cost: Optional[Decimal]
    status: str
    created_by: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class CourseListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: list[CourseResponse]


class EnrollmentCreate(BaseModel):
    course_id: int
    employee_id: int
    notes: Optional[str] = None


class EnrollmentUpdate(BaseModel):
    status: Optional[str] = None
    progress_pct: Optional[int] = Field(None, ge=0, le=100)
    score: Optional[int] = Field(None, ge=0, le=100)
    notes: Optional[str] = None


class EnrollmentResponse(BaseModel):
    id: int
    course_id: int
    employee_id: int
    status: str
    progress_pct: int
    enrolled_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    score: Optional[int]
    notes: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    course_name: Optional[str] = None
    employee_name: Optional[str] = None

    model_config = {"from_attributes": True}


class LearningPathCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class LearningPathUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class LearningPathItemCreate(BaseModel):
    course_id: int
    sort_order: int = 0
    is_required: bool = False


class LearningPathItemResponse(BaseModel):
    id: int
    path_id: int
    course_id: int
    sort_order: int
    is_required: bool
    course_name: Optional[str] = None

    model_config = {"from_attributes": True}


class LearningPathResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_by: Optional[int]
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    items: list[LearningPathItemResponse] = []

    model_config = {"from_attributes": True}


class CertificationCreate(BaseModel):
    employee_id: int
    certification_name: str = Field(..., min_length=1, max_length=200)
    issuing_organization: Optional[str] = Field(None, max_length=200)
    issue_date: date
    expiry_date: Optional[date] = None
    credential_url: Optional[str] = Field(None, max_length=500)
    status: str = "active"
    created_by: Optional[int] = None


class CertificationUpdate(BaseModel):
    certification_name: Optional[str] = Field(None, min_length=1, max_length=200)
    issuing_organization: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    credential_url: Optional[str] = None
    status: Optional[str] = None


class CertificationResponse(BaseModel):
    id: int
    employee_id: int
    certification_name: str
    issuing_organization: Optional[str]
    issue_date: date
    expiry_date: Optional[date]
    credential_url: Optional[str]
    status: str
    created_by: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class SkillCreate(BaseModel):
    employee_id: int
    skill_name: str = Field(..., min_length=1, max_length=200)
    category: Optional[str] = Field(None, max_length=100)
    proficiency_level: int = Field(default=3, ge=1, le=5)


class SkillUpdate(BaseModel):
    skill_name: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[str] = None
    proficiency_level: Optional[int] = Field(None, ge=1, le=5)


class SkillResponse(BaseModel):
    id: int
    employee_id: int
    skill_name: str
    category: Optional[str]
    proficiency_level: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AssessmentCreate(BaseModel):
    course_id: int
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    passing_score: int = 70
    max_attempts: Optional[int] = None
    duration_minutes: Optional[int] = None


class AssessmentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    passing_score: Optional[int] = None
    max_attempts: Optional[int] = None
    duration_minutes: Optional[int] = None
    is_active: Optional[bool] = None


class AssessmentResponse(BaseModel):
    id: int
    course_id: int
    title: str
    description: Optional[str]
    passing_score: int
    max_attempts: Optional[int]
    duration_minutes: Optional[int]
    is_active: bool
    created_by: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class QuestionCreate(BaseModel):
    question_text: str
    question_type: str = "multiple_choice"
    options: Optional[str] = None
    correct_answer: Optional[str] = None
    points: int = 1
    sort_order: int = 0


class QuestionUpdate(BaseModel):
    question_text: Optional[str] = None
    question_type: Optional[str] = None
    options: Optional[str] = None
    correct_answer: Optional[str] = None
    points: Optional[int] = None
    sort_order: Optional[int] = None


class QuestionResponse(BaseModel):
    id: int
    assessment_id: int
    question_text: str
    question_type: str
    options: Optional[str]
    correct_answer: Optional[str]
    points: int
    sort_order: int
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class QuizAttemptStart(BaseModel):
    assessment_id: int
    employee_id: int
    enrollment_id: Optional[int] = None


class QuizAttemptSubmit(BaseModel):
    answers: str


class QuizAttemptResponse(BaseModel):
    id: int
    assessment_id: int
    employee_id: int
    enrollment_id: Optional[int]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    score: Optional[int]
    passed: Optional[bool]
    answers: Optional[str]
    attempt_number: int
    status: str
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class TrainingProgramCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    instructor_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: str = "planned"
    max_participants: Optional[int] = Field(None, ge=1)


class TrainingProgramUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    instructor_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    max_participants: Optional[int] = Field(None, ge=1)


class TrainingProgramResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    instructor_id: Optional[int]
    start_date: Optional[date]
    end_date: Optional[date]
    status: str
    max_participants: Optional[int]
    participants_count: int = 0
    created_by: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ProgramAssignmentCreate(BaseModel):
    program_id: int
    employee_id: int


class ProgramAssignmentUpdate(BaseModel):
    status: Optional[str] = None
    attended_at: Optional[datetime] = None


class ProgramAssignmentResponse(BaseModel):
    id: int
    program_id: int
    employee_id: int
    status: str
    attended_at: Optional[datetime]
    created_at: Optional[datetime]
    employee_name: Optional[str] = None

    model_config = {"from_attributes": True}


class CalendarEventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    event_date: date
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    event_type: str = "session"
    course_id: Optional[int] = None
    program_id: Optional[int] = None
    location: Optional[str] = Field(None, max_length=200)


class CalendarEventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    event_date: Optional[date] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    event_type: Optional[str] = None
    course_id: Optional[int] = None
    program_id: Optional[int] = None
    location: Optional[str] = None


class CalendarEventResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    event_date: date
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    event_type: str
    course_id: Optional[int]
    program_id: Optional[int]
    location: Optional[str]
    created_by: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class LearningDashboardResponse(BaseModel):
    total_courses: int = 0
    active_courses: int = 0
    total_enrollments: int = 0
    completed_enrollments: int = 0
    completion_rate: float = 0.0
    total_certifications: int = 0
    total_skills: int = 0
    avg_skill_level: float = 0.0
    pending_assessments: int = 0
    upcoming_events: int = 0
    enrollment_trend: list[dict] = []
    category_distribution: list[dict] = []
    recent_enrollments: list[dict] = []


class OnboardingNewHireCreate(BaseModel):
    candidate_name: str = Field(..., min_length=1, max_length=150)
    email: EmailStr
    phone: Optional[str] = None
    position: str = Field(..., min_length=1, max_length=150)
    department_id: Optional[int] = None
    manager_id: Optional[int] = None
    joining_date: Optional[date] = None
    notes: Optional[str] = None
    status: Optional[str] = "offer_sent"
    joining_status: Optional[str] = "not_joined"
    tenant_id: Optional[str] = None

class OnboardingNewHireUpdate(BaseModel):
    candidate_name: Optional[str] = Field(None, min_length=1, max_length=150)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    position: Optional[str] = Field(None, min_length=1, max_length=150)
    department_id: Optional[int] = None
    manager_id: Optional[int] = None
    joining_date: Optional[date] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    joining_status: Optional[str] = None
    employee_id: Optional[int] = None
    tenant_id: Optional[str] = None

class OnboardingNewHireResponse(BaseModel):
    id: int
    employee_id: Optional[int] = None
    candidate_name: str
    email: str
    phone: Optional[str] = None
    position: str
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    manager_id: Optional[int] = None
    manager_name: Optional[str] = None
    joining_date: Optional[date] = None
    status: str
    joining_status: str
    notes: Optional[str] = None
    tenant_id: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

# Aliases for backwards compatibility
OnboardingRecordCreate = OnboardingNewHireCreate
OnboardingRecordUpdate = OnboardingNewHireUpdate
OnboardingRecordResponse = OnboardingNewHireResponse

class OnboardingPreboardingTaskCreate(BaseModel):
    onboarding_new_hire_id: Optional[int] = None
    employee_id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    due_date: Optional[date] = None
    tenant_id: Optional[str] = None

class OnboardingPreboardingTaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    due_date: Optional[date] = None
    completed: Optional[bool] = None
    tenant_id: Optional[str] = None

class OnboardingPreboardingTaskResponse(BaseModel):
    id: int
    onboarding_new_hire_id: Optional[int] = None
    employee_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    due_date: Optional[date] = None
    completed: bool
    completed_at: Optional[datetime] = None
    tenant_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

OnboardingTaskCreate = OnboardingPreboardingTaskCreate
OnboardingTaskUpdate = OnboardingPreboardingTaskUpdate
OnboardingTaskResponse = OnboardingPreboardingTaskResponse

class OnboardingDocumentCreate(BaseModel):
    onboarding_new_hire_id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., min_length=1, max_length=100)
    tenant_id: Optional[str] = None

class OnboardingDocumentUpdate(BaseModel):
    status: Optional[str] = None
    rejection_reason: Optional[str] = None
    title: Optional[str] = None
    category: Optional[str] = None
    tenant_id: Optional[str] = None

class OnboardingDocumentResponse(BaseModel):
    id: int
    onboarding_new_hire_id: Optional[int] = None
    title: str
    category: str
    file_path: Optional[str] = None
    status: str
    rejection_reason: Optional[str] = None
    tenant_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class OnboardingChecklistItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    due_date: Optional[date] = None

class OnboardingChecklistCreate(BaseModel):
    onboarding_new_hire_id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = "HR"
    items: Optional[list[OnboardingChecklistItemCreate]] = []
    tenant_id: Optional[str] = None

class OnboardingChecklistUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    tenant_id: Optional[str] = None

class OnboardingChecklistItemResponse(BaseModel):
    id: int
    checklist_id: int
    title: str
    description: Optional[str] = None
    completed: bool
    completed_at: Optional[datetime] = None
    due_date: Optional[date] = None

    model_config = {"from_attributes": True}

class OnboardingChecklistResponse(BaseModel):
    id: int
    onboarding_new_hire_id: Optional[int] = None
    template_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    category: str
    status: str
    tenant_id: Optional[str] = None
    items: list[OnboardingChecklistItemResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class OnboardingChecklistAssignmentCreate(BaseModel):
    onboarding_record_id: int
    template_id: int

class OnboardingOrientationCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    date: date
    time: Optional[str] = None
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    presenter: Optional[str] = None
    status: Optional[str] = "scheduled"
    tenant_id: Optional[str] = None

class OnboardingOrientationUpdate(BaseModel):
    title: Optional[str] = None
    date: Optional[date] = None
    time: Optional[str] = None
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    presenter: Optional[str] = None
    status: Optional[str] = None
    tenant_id: Optional[str] = None

class OnboardingOrientationAttendeeCreate(BaseModel):
    session_id: int
    onboarding_record_id: int
    status: Optional[str] = "pending"

class OnboardingOrientationAttendeeUpdate(BaseModel):
    status: str

class OnboardingOrientationAttendeeResponse(BaseModel):
    id: int
    session_id: int
    onboarding_new_hire_id: int
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class OnboardingOrientationResponse(BaseModel):
    id: int
    title: str
    date: date
    time: Optional[str] = None
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    presenter: Optional[str] = None
    status: str
    tenant_id: Optional[str] = None
    attendees: list[OnboardingOrientationAttendeeResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class OnboardingActivityResponse(BaseModel):
    id: int
    onboarding_new_hire_id: Optional[int] = None
    action: str
    description: str
    created_at: Optional[datetime] = None

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

class OnboardingAnalyticsResponse(BaseModel):
    totalNewHires: int
    completionRate: float
    avgDaysToOnboard: float
    statusDistribution: list[dict]
    departmentDistribution: list[dict]


class PerformanceGoalCreate(BaseModel):
    employee_id: int
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    goal_type: Optional[str] = "okr"
    quarter: Optional[str] = None
    year: Optional[int] = None
    progress: Optional[int] = 0
    status: Optional[str] = "not_started"
    due_date: Optional[date] = None


class PerformanceGoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    goal_type: Optional[str] = None
    quarter: Optional[str] = None
    year: Optional[int] = None
    progress: Optional[int] = None
    status: Optional[str] = None
    due_date: Optional[date] = None


class PerformanceGoalResponse(BaseModel):
    id: int
    employee_id: int
    title: str
    description: Optional[str]
    goal_type: Optional[str]
    quarter: Optional[str]
    year: Optional[int]
    progress: int
    status: str
    due_date: Optional[date]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class PerformanceKpiCreate(BaseModel):
    employee_id: int
    goal_id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=255)
    target_value: Optional[float] = None
    actual_value: Optional[float] = None
    unit: Optional[str] = None
    weight: Optional[float] = 1.0
    period: Optional[str] = None


class PerformanceKpiUpdate(BaseModel):
    name: Optional[str] = None
    target_value: Optional[float] = None
    actual_value: Optional[float] = None
    unit: Optional[str] = None
    weight: Optional[float] = None
    period: Optional[str] = None


class PerformanceKpiResponse(BaseModel):
    id: int
    employee_id: int
    goal_id: Optional[int]
    name: str
    target_value: Optional[float]
    actual_value: Optional[float]
    unit: Optional[str]
    weight: float
    period: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class PerformanceFeedbackCreate(BaseModel):
    employee_id: int
    reviewer_id: Optional[int] = None
    review_id: Optional[int] = None
    feedback_type: Optional[str] = "peer"
    rating: Optional[int] = None
    comments: Optional[str] = None
    strengths: Optional[str] = None
    improvements: Optional[str] = None


class PerformanceFeedbackResponse(BaseModel):
    id: int
    employee_id: int
    reviewer_id: Optional[int]
    review_id: Optional[int]
    feedback_type: str
    rating: Optional[int]
    comments: Optional[str]
    strengths: Optional[str]
    improvements: Optional[str]
    submitted_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AppraisalCreate(BaseModel):
    employee_id: int
    reviewer_id: Optional[int] = None
    cycle: str = Field(..., min_length=1, max_length=50)
    self_score: Optional[float] = None
    manager_score: Optional[float] = None
    final_score: Optional[float] = None
    recommendation: Optional[str] = None
    salary_hike: Optional[float] = None
    comments: Optional[str] = None
    status: Optional[str] = "draft"


class AppraisalUpdate(BaseModel):
    self_score: Optional[float] = None
    manager_score: Optional[float] = None
    final_score: Optional[float] = None
    recommendation: Optional[str] = None
    salary_hike: Optional[float] = None
    comments: Optional[str] = None
    status: Optional[str] = None


class AppraisalResponse(BaseModel):
    id: int
    employee_id: int
    reviewer_id: Optional[int]
    cycle: str
    self_score: Optional[float]
    manager_score: Optional[float]
    final_score: Optional[float]
    recommendation: Optional[str]
    salary_hike: Optional[float]
    comments: Optional[str]
    status: str
    created_at: Optional[datetime]
    reviewed_at: Optional[datetime]

    model_config = {"from_attributes": True}


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
    name: Optional[str] = None
    status: Optional[str] = None


class RecruitmentCandidateResponse(BaseModel):
    id: int
    name: str
    email: str
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
    """Workforce analytics summary."""
    total_headcount: int = 0
    active_employees: int = 0
    department_breakdown: list[dict] = []
    yearly_trend: list[dict] = []
    turnover_rate: Optional[float] = None


# ════════════════════════════════════════════════════════════════════════════
# RECRUITMENT SCHEMAS
# ════════════════════════════════════════════════════════════════════════════

class RecruitmentDashboardResponse(BaseModel):
    total_open_positions: int = 0
    active_candidates: int = 0
    scheduled_interviews: int = 0
    offers_extended: int = 0
    offers_accepted: int = 0
    time_to_hire: float = 0.0
    hiring_funnel: list[dict] = []
    recent_activity: list[dict] = []


class RequisitionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    department: str = Field(..., min_length=1, max_length=100)
    location: Optional[str] = Field(None, max_length=150)
    openings: int = Field(default=1, ge=1)
    priority: str = "medium"
    description: Optional[str] = None


class RequisitionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    department: Optional[str] = Field(None, min_length=1, max_length=100)
    location: Optional[str] = Field(None, max_length=150)
    openings: Optional[int] = Field(None, ge=1)
    filled: Optional[int] = Field(None, ge=0)
    priority: Optional[str] = None
    status: Optional[RequisitionStatus] = None
    description: Optional[str] = None


class RequisitionResponse(BaseModel):
    id: int
    title: str
    department: str
    location: Optional[str]
    openings: int
    filled: int
    priority: str
    status: RequisitionStatus
    description: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class CandidateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    position: str = Field(..., min_length=1, max_length=150)
    source: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=150)
    experience: Optional[int] = Field(None, ge=0)
    resume_link: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None


class CandidateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    position: Optional[str] = Field(None, min_length=1, max_length=150)
    source: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=150)
    experience: Optional[int] = Field(None, ge=0)
    resume_link: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None


class CandidateStatusUpdate(BaseModel):
    status: RecruitmentCandidateStatus


class CandidateResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str]
    position: str
    source: Optional[str]
    status: RecruitmentCandidateStatus
    location: Optional[str]
    experience: Optional[int]
    resume_link: Optional[str]
    applied_at: Optional[datetime]
    notes: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class InterviewCreate(BaseModel):
    candidate_id: Optional[int] = None
    candidate_name: str = Field(..., min_length=1, max_length=150)
    position: str = Field(..., min_length=1, max_length=150)
    interview_type: str = "in_person"
    interview_date: date
    start_time: Optional[str] = Field(None, max_length=10)
    end_time: Optional[str] = Field(None, max_length=10)
    interviewer: Optional[str] = Field(None, max_length=150)
    interviewer_id: Optional[int] = None
    notes: Optional[str] = None


class InterviewUpdate(BaseModel):
    candidate_id: Optional[int] = None
    candidate_name: Optional[str] = Field(None, min_length=1, max_length=150)
    position: Optional[str] = Field(None, min_length=1, max_length=150)
    interview_type: Optional[str] = None
    interview_date: Optional[date] = None
    start_time: Optional[str] = Field(None, max_length=10)
    end_time: Optional[str] = Field(None, max_length=10)
    interviewer: Optional[str] = Field(None, max_length=150)
    interviewer_id: Optional[int] = None
    status: Optional[InterviewStatus] = None
    notes: Optional[str] = None


class InterviewFeedback(BaseModel):
    feedback: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    status: Optional[InterviewStatus] = None


class InterviewResponse(BaseModel):
    id: int
    candidate_id: int
    candidate_name: str
    position: str
    interview_type: str
    interview_date: date
    start_time: Optional[str]
    end_time: Optional[str]
    interviewer: Optional[str]
    interviewer_id: Optional[int]
    status: InterviewStatus
    feedback: Optional[str]
    rating: Optional[int]
    notes: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class OfferCreate(BaseModel):
    candidate_id: Optional[int] = None
    candidate_name: str = Field(..., min_length=1, max_length=150)
    position: str = Field(..., min_length=1, max_length=150)
    salary: Optional[Decimal] = Field(None, ge=0)
    equity: Optional[str] = Field(None, max_length=50)
    joining_date: Optional[date] = None
    notes: Optional[str] = None


class OfferUpdate(BaseModel):
    candidate_name: Optional[str] = Field(None, min_length=1, max_length=150)
    position: Optional[str] = Field(None, min_length=1, max_length=150)
    salary: Optional[Decimal] = Field(None, ge=0)
    equity: Optional[str] = Field(None, max_length=50)
    joining_date: Optional[date] = None
    status: Optional[OfferStatus] = None
    notes: Optional[str] = None


class OfferStatusUpdate(BaseModel):
    status: OfferStatus


class OfferResponse(BaseModel):
    id: int
    candidate_id: int
    candidate_name: str
    position: str
    salary: Optional[Decimal]
    equity: Optional[str]
    joining_date: Optional[date]
    status: OfferStatus
    notes: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class DocumentCreate(BaseModel):
    candidate_id: int
    document_type: str = Field(..., min_length=2, max_length=50)
    file_name: str = Field(..., min_length=1, max_length=255)
    file_size: Optional[int] = Field(None, ge=0)


class DocumentResponse(BaseModel):
    id: int
    candidate_id: int
    document_type: str
    file_path: str
    file_name: str
    file_size: Optional[int]
    upload_date: Optional[datetime]

    model_config = {"from_attributes": True}


class ApplicationCreate(BaseModel):
    candidate_id: int
    requisition_id: int
    status: str = "new"
    notes: Optional[str] = None


class ApplicationResponse(BaseModel):
    id: int
    candidate_id: int
    requisition_id: int
    application_date: Optional[datetime]
    status: str
    notes: Optional[str]

    model_config = {"from_attributes": True}


class InterviewFeedbackCreate(BaseModel):
    interview_id: int
    interviewer_id: int
    rating: int = Field(..., ge=1, le=10)
    feedback: Optional[str] = None
    strengths: Optional[str] = None
    improvements: Optional[str] = None


class InterviewFeedbackResponse(BaseModel):
    id: int
    interview_id: int
    interviewer_id: int
    rating: int
    feedback: Optional[str]
    strengths: Optional[str]
    improvements: Optional[str]
    created_date: Optional[datetime]

    model_config = {"from_attributes": True}


class OfferApprovalCreate(BaseModel):
    offer_id: int
    approver_id: int
    approval_status: str = "pending"
    comments: Optional[str] = None


class OfferApprovalResponse(BaseModel):
    id: int
    offer_id: int
    approver_id: int
    approval_status: str
    comments: Optional[str]
    approved_date: Optional[datetime]

    model_config = {"from_attributes": True}


class RecruitmentAnalyticsResponse(BaseModel):
    id: int
    requisition_id: Optional[int]
    total_applicants: int = 0
    interviews_scheduled: int = 0
    interviews_completed: int = 0
    offers_extended: int = 0
    offers_accepted: int = 0
    offers_rejected: int = 0
    time_to_hire: Optional[int]
    cost_per_hire: Optional[float]

    model_config = {"from_attributes": True}