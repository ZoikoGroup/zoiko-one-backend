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
    CorrectionType, RegularizationStatus, ShiftType,
    OvertimeStatus, ExceptionStatus, ExceptionType,
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


# ════════════════════════════════════════════════════════════════════════════
# ATTENDANCE REGULARIZATION SCHEMAS
# ════════════════════════════════════════════════════════════════════════════

class AttendanceRegularizationCreate(BaseModel):
    employee_id: int
    attendance_record_id: Optional[int] = None
    correction_type: CorrectionType
    date: date
    expected_check_in: Optional[datetime] = None
    expected_check_out: Optional[datetime] = None
    actual_check_in: Optional[datetime] = None
    actual_check_out: Optional[datetime] = None
    reason: Optional[str] = None


class AttendanceRegularizationUpdate(BaseModel):
    status: Optional[RegularizationStatus] = None
    manager_id: Optional[int] = None
    rejection_reason: Optional[str] = None


class AttendanceRegularizationResponse(BaseModel):
    id: int
    employee_id: int
    attendance_record_id: Optional[int]
    correction_type: CorrectionType
    date: date
    expected_check_in: Optional[datetime]
    expected_check_out: Optional[datetime]
    actual_check_in: Optional[datetime]
    actual_check_out: Optional[datetime]
    reason: Optional[str]
    status: RegularizationStatus
    manager_id: Optional[int]
    manager_approved_at: Optional[datetime]
    hr_approved_at: Optional[datetime]
    rejected_by: Optional[int]
    rejected_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ════════════════════════════════════════════════════════════════════════════
# ATTENDANCE POLICY SCHEMAS
# ════════════════════════════════════════════════════════════════════════════

class AttendancePolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    working_hours: Decimal = Field(default=8.0, ge=0)
    grace_time_minutes: int = Field(default=0, ge=0)
    late_threshold_minutes: int = Field(default=15, ge=0)
    early_exit_threshold_minutes: int = Field(default=15, ge=0)
    requires_overtime_approval: bool = True
    overtime_rate: Optional[Decimal] = Field(None, ge=0)
    max_overtime_hours: Optional[Decimal] = Field(None, ge=0)
    break_duration_minutes: int = Field(default=60, ge=0)
    min_working_days: Optional[int] = Field(None, ge=0)
    applicable_departments: Optional[str] = None


class AttendancePolicyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    working_hours: Optional[Decimal] = Field(None, ge=0)
    grace_time_minutes: Optional[int] = Field(None, ge=0)
    late_threshold_minutes: Optional[int] = Field(None, ge=0)
    early_exit_threshold_minutes: Optional[int] = Field(None, ge=0)
    requires_overtime_approval: Optional[bool] = None
    overtime_rate: Optional[Decimal] = Field(None, ge=0)
    max_overtime_hours: Optional[Decimal] = Field(None, ge=0)
    break_duration_minutes: Optional[int] = Field(None, ge=0)
    min_working_days: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    applicable_departments: Optional[str] = None


class AttendancePolicyResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    working_hours: Decimal
    grace_time_minutes: int
    late_threshold_minutes: int
    early_exit_threshold_minutes: int
    requires_overtime_approval: bool
    overtime_rate: Optional[Decimal]
    max_overtime_hours: Optional[Decimal]
    break_duration_minutes: int
    min_working_days: Optional[int]
    is_active: bool
    applicable_departments: Optional[str]
    created_by: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


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
    created_by: Optional[int]
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
# GEOFENCE LOCATION SCHEMAS
# ════════════════════════════════════════════════════════════════════════════

class GeofenceLocationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    latitude: Decimal = Field(..., ge=-90, le=90)
    longitude: Decimal = Field(..., ge=-180, le=180)
    radius_meters: int = Field(default=100, ge=1)
    address: Optional[str] = None


class GeofenceLocationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    radius_meters: Optional[int] = Field(None, ge=1)
    address: Optional[str] = None
    is_active: Optional[bool] = None


class GeofenceLocationResponse(BaseModel):
    id: int
    name: str
    latitude: Decimal
    longitude: Decimal
    radius_meters: int
    address: Optional[str]
    is_active: bool
    created_by: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ════════════════════════════════════════════════════════════════════════════
# OVERTIME REQUEST SCHEMAS
# ════════════════════════════════════════════════════════════════════════════

class OvertimeRequestCreate(BaseModel):
    employee_id: int
    date: date
    hours_requested: Decimal = Field(..., ge=0)
    reason: Optional[str] = None


class OvertimeRequestUpdate(BaseModel):
    status: Optional[OvertimeStatus] = None
    hours_approved: Optional[Decimal] = None
    approved_by: Optional[int] = None
    rejection_reason: Optional[str] = None


class OvertimeRequestResponse(BaseModel):
    id: int
    employee_id: int
    date: date
    hours_requested: Decimal
    hours_approved: Optional[Decimal]
    reason: Optional[str]
    status: OvertimeStatus
    approved_by: Optional[int]
    approved_at: Optional[datetime]
    rejected_by: Optional[int]
    rejected_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ════════════════════════════════════════════════════════════════════════════
# ATTENDANCE EXCEPTION SCHEMAS
# ════════════════════════════════════════════════════════════════════════════

class AttendanceExceptionCreate(BaseModel):
    employee_id: int
    attendance_record_id: Optional[int] = None
    exception_type: ExceptionType
    description: Optional[str] = None


class AttendanceExceptionUpdate(BaseModel):
    status: Optional[ExceptionStatus] = None
    resolved_by: Optional[int] = None
    resolution_notes: Optional[str] = None
    escalated_to: Optional[int] = None


class AttendanceExceptionResponse(BaseModel):
    id: int
    employee_id: int
    attendance_record_id: Optional[int]
    exception_type: ExceptionType
    description: Optional[str]
    status: ExceptionStatus
    resolved_by: Optional[int]
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
    escalated_to: Optional[int]
    escalated_at: Optional[datetime]
    created_at: Optional[datetime]

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
# WEEKEND CONFIG SCHEMAS
# ════════════════════════════════════════════════════════════════════════════

class WeekendConfigCreate(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6)
    is_weekend: bool = False
    is_alternate: bool = False
    description: Optional[str] = Field(None, max_length=100)


class WeekendConfigUpdate(BaseModel):
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    is_weekend: Optional[bool] = None
    is_alternate: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class WeekendConfigResponse(BaseModel):
    id: int
    day_of_week: int
    is_weekend: bool
    is_alternate: bool
    description: Optional[str]
    is_active: bool
    created_by: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ════════════════════════════════════════════════════════════════════════════
# ATTENDANCE AUDIT LOG SCHEMA
# ════════════════════════════════════════════════════════════════════════════

class AttendanceAuditLogResponse(BaseModel):
    id: int
    employee_id: Optional[int]
    action: str
    entity_type: str
    entity_id: Optional[int]
    changes: Optional[str]
    performed_by: Optional[int]
    ip_address: Optional[str]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ════════════════════════════════════════════════════════════════════════════
# DASHBOARD / REPORT SCHEMAS
# ════════════════════════════════════════════════════════════════════════════

class AttendanceDashboardResponse(BaseModel):
    total_employees: int = 0
    present_today: int = 0
    absent_today: int = 0
    on_leave_today: int = 0
    remote_today: int = 0
    late_arrivals_today: int = 0
    early_departures_today: int = 0
    pending_regularizations: int = 0
    pending_overtime: int = 0
    open_exceptions: int = 0
    attendance_rate: float = 0.0
    department_breakdown: list[dict] = []
    weekly_trend: list[dict] = []
    monthly_trend: list[dict] = []


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
    joining_date: Optional[date] = None
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
# ATTENDANCE SCHEMAS
# ════════════════════════════════════════════════════════════════════════════

class AttendanceUpdate(BaseModel):
    status: Optional[AttendanceStatus] = None
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    notes: Optional[str] = None


class AttendanceDashboardResponse(BaseModel):
    present_today: int = 0
    absent_today: int = 0
    late_arrivals: int = 0
    early_departures: int = 0
    on_leave_count: int = 0
    remote_count: int = 0
    overtime_count: int = 0
    attendance_percentage: float = 0.0
    avg_working_hours: float = 0.0
    department_breakdown: list[dict] = []
    shift_utilization: list[dict] = []


class RegularizationCreate(BaseModel):
    employee_id: Optional[int] = None
    attendance_record_id: Optional[int] = None
    correction_type: CorrectionType
    date: date
    expected_check_in: Optional[datetime] = None
    expected_check_out: Optional[datetime] = None
    actual_check_in: Optional[datetime] = None
    actual_check_out: Optional[datetime] = None
    reason: Optional[str] = None


class RegularizationResponse(BaseModel):
    id: int
    employee_id: int
    attendance_record_id: Optional[int]
    correction_type: CorrectionType
    date: date
    expected_check_in: Optional[datetime]
    expected_check_out: Optional[datetime]
    actual_check_in: Optional[datetime]
    actual_check_out: Optional[datetime]
    reason: Optional[str]
    status: RegularizationStatus
    manager_id: Optional[int]
    manager_approved_at: Optional[datetime]
    hr_approved_at: Optional[datetime]
    rejected_by: Optional[int]
    rejected_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    employee_name: Optional[str] = None

    model_config = {"from_attributes": True}


class AttendancePolicyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    working_hours: Decimal = Decimal("8.0")
    grace_time_minutes: int = 0
    late_threshold_minutes: int = 15
    early_exit_threshold_minutes: int = 15
    requires_overtime_approval: bool = True
    overtime_rate: Optional[Decimal] = Decimal("1.5")
    max_overtime_hours: Optional[Decimal] = Decimal("4.0")
    break_duration_minutes: int = 60
    min_working_days: Optional[int] = 5
    is_active: bool = True
    applicable_departments: Optional[str] = None


class AttendancePolicyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    working_hours: Optional[Decimal] = None
    grace_time_minutes: Optional[int] = None
    late_threshold_minutes: Optional[int] = None
    early_exit_threshold_minutes: Optional[int] = None
    requires_overtime_approval: Optional[bool] = None
    overtime_rate: Optional[Decimal] = None
    max_overtime_hours: Optional[Decimal] = None
    break_duration_minutes: Optional[int] = None
    min_working_days: Optional[int] = None
    is_active: Optional[bool] = None
    applicable_departments: Optional[str] = None


class AttendancePolicyResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    working_hours: Decimal
    grace_time_minutes: int
    late_threshold_minutes: int
    early_exit_threshold_minutes: int
    requires_overtime_approval: bool
    overtime_rate: Optional[Decimal]
    max_overtime_hours: Optional[Decimal]
    break_duration_minutes: int
    min_working_days: Optional[int]
    is_active: bool
    applicable_departments: Optional[str]
    created_by: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}



    start_time: Optional[str] = None
    end_time: Optional[str] = None
    grace_time_minutes: Optional[int] = None
    break_duration_minutes: Optional[int] = None
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
    created_by: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ShiftRosterCreate(BaseModel):
    employee_id: int
    shift_id: int
    date: date


class ShiftRosterResponse(BaseModel):
    id: int
    employee_id: int
    shift_id: int
    date: date
    is_active: bool
    assigned_by: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    employee_name: Optional[str] = None
    shift_name: Optional[str] = None

    model_config = {"from_attributes": True}


class GeofenceCreate(BaseModel):
    name: str
    latitude: Decimal
    longitude: Decimal
    radius_meters: int = 100
    address: Optional[str] = None
    is_active: bool = True


class GeofenceUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    radius_meters: Optional[int] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class GeofenceResponse(BaseModel):
    id: int
    name: str
    latitude: Decimal
    longitude: Decimal
    radius_meters: int
    address: Optional[str]
    is_active: bool
    created_by: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class OvertimeCreate(BaseModel):
    employee_id: int
    date: date
    hours_requested: Decimal
    reason: Optional[str] = None


class OvertimeResponse(BaseModel):
    id: int
    employee_id: int
    date: date
    hours_requested: Decimal
    hours_approved: Optional[Decimal]
    reason: Optional[str]
    status: OvertimeStatus
    approved_by: Optional[int]
    approved_at: Optional[datetime]
    rejected_by: Optional[int]
    rejected_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    employee_name: Optional[str] = None

    model_config = {"from_attributes": True}


class AttendanceExceptionResponse(BaseModel):
    id: int
    employee_id: int
    attendance_record_id: Optional[int]
    exception_type: ExceptionType
    description: Optional[str]
    status: ExceptionStatus
    resolved_by: Optional[int]
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
    escalated_to: Optional[int]
    escalated_at: Optional[datetime]
    created_at: Optional[datetime]
    employee_name: Optional[str] = None

    model_config = {"from_attributes": True}


class HolidayCreate(BaseModel):
    name: str
    date: date
    type: Optional[str] = "public"
    is_recurring: bool = False
    description: Optional[str] = None


class HolidayUpdate(BaseModel):
    name: Optional[str] = None
    date: Optional[date] = None
    type: Optional[str] = None
    is_recurring: Optional[bool] = None
    description: Optional[str] = None


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


class WeekendConfigCreate(BaseModel):
    day_of_week: int
    is_weekend: bool = False
    is_alternate: bool = False
    description: Optional[str] = None


class WeekendConfigResponse(BaseModel):
    id: int
    day_of_week: int
    is_weekend: bool
    is_alternate: bool
    description: Optional[str]
    is_active: bool
    created_by: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class BiometricDeviceCreate(BaseModel):
    name: str
    device_id: str
    ip_address: Optional[str] = None
    port: Optional[int] = None
    location: Optional[str] = None
    is_active: bool = True


class BiometricDeviceUpdate(BaseModel):
    name: Optional[str] = None
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None


class BiometricDeviceResponse(BaseModel):
    id: int
    name: str
    device_id: str
    ip_address: Optional[str]
    port: Optional[int]
    location: Optional[str]
    is_active: bool
    last_sync: Optional[datetime]
    created_by: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AttendanceAuditLogResponse(BaseModel):
    id: int
    employee_id: Optional[int]
    action: str
    entity_type: str
    entity_id: Optional[int]
    changes: Optional[str]
    performed_by: Optional[int]
    ip_address: Optional[str]
    created_at: Optional[datetime]
    employee_name: Optional[str] = None
    performer_name: Optional[str] = None

    model_config = {"from_attributes": True}