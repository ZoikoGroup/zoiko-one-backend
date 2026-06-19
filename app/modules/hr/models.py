"""
modules/hr/models.py
--------------------
SQLAlchemy ORM models = your database TABLES defined in Python.

Each class = one table in PostgreSQL.
Each class attribute = one column in that table.

When Alembic runs, it reads these classes and creates the actual
tables in your PostgreSQL database automatically.

Tables defined here:
  - Department  → stores company departments
  - Employee    → stores all employee records
"""

import enum
from datetime import datetime, date

from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime,
    Enum as SQLEnum, ForeignKey, Text, Numeric
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


# ── Enums (fixed choice lists) ────────────────────────────────────────────────
# Enums ensure only valid values go into the database.

class EmploymentType(str, enum.Enum):
    FULL_TIME  = "full_time"
    PART_TIME  = "part_time"
    CONTRACT   = "contract"
    INTERN     = "intern"


class EmployeeStatus(str, enum.Enum):
    ACTIVE     = "active"
    INACTIVE   = "inactive"
    ON_LEAVE   = "on_leave"
    TERMINATED = "terminated"


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN       = "admin"
    HR_MANAGER  = "hr_manager"
    EMPLOYEE    = "employee"


class Gender(str, enum.Enum):
    MALE        = "male"
    FEMALE      = "female"
    OTHER       = "other"
    PREFER_NOT  = "prefer_not_to_say"


class AttendanceStatus(str, enum.Enum):
    PRESENT   = "present"
    ABSENT    = "absent"
    ON_LEAVE  = "on_leave"
    REMOTE    = "remote"


class CorrectionType(str, enum.Enum):
    MISSED_CLOCK_IN = "missed_clock_in"
    MISSED_CLOCK_OUT = "missed_clock_out"
    INCORRECT_TIME = "incorrect_time"
    WRONG_STATUS = "wrong_status"
    WORK_FROM_HOME = "work_from_home"
    FORGOT_CHECKOUT = "forgot_checkout"
    OTHER = "other"


class RegularizationStatus(str, enum.Enum):
    PENDING = "pending"
    MANAGER_APPROVED = "manager_approved"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ShiftType(str, enum.Enum):
    GENERAL = "general"
    MORNING = "morning"
    EVENING = "evening"
    NIGHT = "night"
    ROTATIONAL = "rotational"


class OvertimeStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ExceptionStatus(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    IGNORED = "ignored"


class ExceptionType(str, enum.Enum):
    MISSING_PUNCH = "missing_punch"
    DUPLICATE_ENTRY = "duplicate_entry"
    INVALID_SHIFT = "invalid_shift"
    EARLY_DEPARTURE = "early_departure"
    LATE_ARRIVAL = "late_arrival"
    ATTENDANCE_VIOLATION = "attendance_violation"


class LeaveType(str, enum.Enum):
    SICK      = "sick"
    CASUAL    = "casual"
    EARNED    = "earned"
    UNPAID    = "unpaid"


class RequestStatus(str, enum.Enum):
    PENDING   = "pending"
    APPROVED  = "approved"
    REJECTED  = "rejected"
    COMPLETED = "completed"


class OnboardingStatus(str, enum.Enum):
    OFFER_SENT     = "offer_sent"
    OFFER_ACCEPTED = "offer_accepted"
    PRE_JOINING    = "pre_joining"
    IN_PROGRESS    = "in_progress"
    COMPLETED      = "completed"
    CANCELLED      = "cancelled"


class AssetStatus(str, enum.Enum):
    AVAILABLE    = "available"
    ASSIGNED     = "assigned"
    MAINTENANCE  = "maintenance"
    RETIRED      = "retired"
    LOST         = "lost"


class AssetCondition(str, enum.Enum):
    NEW     = "new"
    GOOD    = "good"
    FAIR    = "fair"
    POOR    = "poor"
    DAMAGED = "damaged"


class MaintenancePriority(str, enum.Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"
    URGENT = "urgent"


class MaintenanceStatus(str, enum.Enum):
    REPORTED    = "reported"
    IN_PROGRESS = "in_progress"
    RESOLVED    = "resolved"
    CANCELLED   = "cancelled"


class RequestPriority(str, enum.Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"
    URGENT = "urgent"


class AssetRequestStatus(str, enum.Enum):
    PENDING    = "pending"
    APPROVED   = "approved"
    REJECTED   = "rejected"
    FULFILLED  = "fulfilled"
    CANCELLED  = "cancelled"


class EnrollmentStatus(str, enum.Enum):
    ENROLLED    = "enrolled"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    DROPPED     = "dropped"


class QuizAttemptStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    GRADED      = "graded"


class QuestionType(str, enum.Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE      = "true_false"
    SHORT_ANSWER    = "short_answer"


class ProgramStatus(str, enum.Enum):
    PLANNED    = "planned"
    ACTIVE     = "active"
    COMPLETED  = "completed"
    CANCELLED  = "cancelled"


class ProgramAssignmentStatus(str, enum.Enum):
    REGISTERED = "registered"
    ATTENDED   = "attended"
    COMPLETED  = "completed"
    NO_SHOW    = "no_show"


class EventType(str, enum.Enum):
    SESSION  = "session"
    WEBINAR  = "webinar"
    WORKSHOP = "workshop"
    DEADLINE = "deadline"


# ── Department Table ──────────────────────────────────────────────────────────
class Department(Base):
    """
    Stores all company departments.
    Example rows: Engineering, Marketing, HR, Finance, Operations
    """
    __tablename__ = "departments"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), unique=True, nullable=False)
    code        = Column(String(20), unique=True, nullable=False)   # e.g. "ENG", "MKT"
    description = Column(Text, nullable=True)
    is_active   = Column(Boolean, default=True)

    # Timestamps — set automatically
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship: one department has many employees
    # "employees" becomes a Python list you can access: dept.employees
    employees   = relationship("Employee", back_populates="department")

    def __repr__(self):
        return f"<Department id={self.id} name={self.name}>"


# ── Employee Table ────────────────────────────────────────────────────────────
class Employee(Base):
    """
    Core employee record. This is the most important table in the HR module.
    Stores personal info, job info, and login credentials.
    """
    __tablename__ = "employees"

    # ── Primary Key ──────────────────────────────────────────────────────
    id              = Column(Integer, primary_key=True, index=True)

    # ── Login / Auth fields ───────────────────────────────────────────────
    email           = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role            = Column(SQLEnum(UserRole), default=UserRole.EMPLOYEE, nullable=False)
    is_active       = Column(Boolean, default=True)

    # ── Personal Information ──────────────────────────────────────────────
    first_name      = Column(String(100), nullable=False)
    last_name       = Column(String(100), nullable=False)
    phone           = Column(String(20), nullable=True)
    date_of_birth   = Column(Date, nullable=True)
    gender          = Column(SQLEnum(Gender), nullable=True)
    address         = Column(Text, nullable=True)
    profile_picture = Column(String(500), nullable=True)   # URL to image

    # ── Job Information ───────────────────────────────────────────────────
    employee_code   = Column(String(50), unique=True, nullable=False)  # e.g. "ZK-0001"
    job_title       = Column(String(150), nullable=False)
    employment_type = Column(SQLEnum(EmploymentType), default=EmploymentType.FULL_TIME)
    status          = Column(SQLEnum(EmployeeStatus), default=EmployeeStatus.ACTIVE)
    date_of_joining = Column(Date, nullable=False)
    date_of_leaving = Column(Date, nullable=True)   # filled when employee leaves

    # ── Salary ───────────────────────────────────────────────────────────
    # Numeric(10, 2) = up to 10 digits, 2 decimal places  e.g. 75000.00
    basic_salary    = Column(Numeric(10, 2), nullable=True)

    # ── Foreign Key: links to Department table ────────────────────────────
    # nullable=True means an employee CAN exist without a department (edge case)
    department_id   = Column(Integer, ForeignKey("departments.id"), nullable=True)

    # Relationship: access the department object via employee.department
    department      = relationship("Department", back_populates="employees")
    attendance_records = relationship("AttendanceRecord", back_populates="employee", foreign_keys="AttendanceRecord.employee_id")
    leave_requests  = relationship("LeaveRequest", back_populates="employee")
    assets          = relationship("Asset", back_populates="employee", foreign_keys="Asset.employee_id")
    compensation_items = relationship("CompensationItem", back_populates="employee")
    compliance_records  = relationship("ComplianceRecord", back_populates="employee")
    engagement_surveys  = relationship("EngagementSurvey", back_populates="employee")
    ess_requests    = relationship("EssRequest", back_populates="employee")
    learning_enrollments = relationship("LearningEnrollment", back_populates="employee", foreign_keys="LearningEnrollment.employee_id")
    onboarding_tasks = relationship("OnboardingTask", back_populates="employee")
    onboarding_records = relationship("OnboardingRecord", back_populates="employee", foreign_keys="OnboardingRecord.employee_id")
    performance_reviews = relationship("PerformanceReview", back_populates="employee", foreign_keys="PerformanceReview.employee_id")
    travel_requests = relationship("TravelRequest", back_populates="employee")

    # ── Timestamps ───────────────────────────────────────────────────────
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    # ── Helper property ───────────────────────────────────────────────────
    @property
    def full_name(self) -> str:
        """Convenience: employee.full_name instead of f"{first} {last}" """
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<Employee id={self.id} name={self.full_name} code={self.employee_code}>"


# ── Attendance Records ─────────────────────────────────────────────────────────
class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id              = Column(Integer, primary_key=True, index=True)
    employee_id     = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date            = Column(Date, nullable=False)
    status          = Column(SQLEnum(AttendanceStatus), default=AttendanceStatus.PRESENT, nullable=False)
    check_in        = Column(DateTime(timezone=True), nullable=True)
    check_out       = Column(DateTime(timezone=True), nullable=True)
    break_start     = Column(DateTime(timezone=True), nullable=True)
    break_end       = Column(DateTime(timezone=True), nullable=True)
    notes           = Column(Text, nullable=True)
    remote_location = Column(String(200), nullable=True)
    is_biometric    = Column(Boolean, default=False)
    created_by      = Column(Integer, ForeignKey("employees.id"), nullable=True)
    updated_by      = Column(Integer, ForeignKey("employees.id"), nullable=True)
    deleted_at      = Column(DateTime(timezone=True), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    employee        = relationship("Employee", back_populates="attendance_records", foreign_keys=[employee_id])
    creator         = relationship("Employee", foreign_keys=[created_by])
    updater         = relationship("Employee", foreign_keys=[updated_by])


class AttendanceRegularization(Base):
    __tablename__ = "attendance_regularizations"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    attendance_record_id = Column(Integer, ForeignKey("attendance_records.id"), nullable=True)
    correction_type = Column(SQLEnum(CorrectionType), nullable=False)
    date = Column(Date, nullable=False)
    expected_check_in = Column(DateTime(timezone=True), nullable=True)
    expected_check_out = Column(DateTime(timezone=True), nullable=True)
    actual_check_in = Column(DateTime(timezone=True), nullable=True)
    actual_check_out = Column(DateTime(timezone=True), nullable=True)
    reason = Column(Text, nullable=True)
    status = Column(SQLEnum(RegularizationStatus), default=RegularizationStatus.PENDING, nullable=False)
    manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    manager_approved_at = Column(DateTime(timezone=True), nullable=True)
    hr_approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    employee = relationship("Employee", foreign_keys=[employee_id])
    attendance_record = relationship("AttendanceRecord")
    manager = relationship("Employee", foreign_keys=[manager_id])
    rejector = relationship("Employee", foreign_keys=[rejected_by])


class AttendancePolicy(Base):
    __tablename__ = "attendance_policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    working_hours = Column(Numeric(4, 2), nullable=False, default=8.0)
    grace_time_minutes = Column(Integer, nullable=False, default=0)
    late_threshold_minutes = Column(Integer, nullable=False, default=15)
    early_exit_threshold_minutes = Column(Integer, nullable=False, default=15)
    requires_overtime_approval = Column(Boolean, default=True)
    overtime_rate = Column(Numeric(3, 2), nullable=True, default=1.5)
    max_overtime_hours = Column(Numeric(4, 1), nullable=True, default=4.0)
    break_duration_minutes = Column(Integer, nullable=False, default=60)
    min_working_days = Column(Integer, nullable=True, default=5)
    is_active = Column(Boolean, default=True)
    applicable_departments = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    creator = relationship("Employee", foreign_keys=[created_by])


class Shift(Base):
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    shift_type = Column(SQLEnum(ShiftType), default=ShiftType.GENERAL, nullable=False)
    start_time = Column(String(5), nullable=False)
    end_time = Column(String(5), nullable=False)
    grace_time_minutes = Column(Integer, nullable=False, default=0)
    break_duration_minutes = Column(Integer, nullable=False, default=60)
    is_overtime_eligible = Column(Boolean, default=True)
    requires_attendance = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    creator = relationship("Employee", foreign_keys=[created_by])


class ShiftRoster(Base):
    __tablename__ = "shift_rosters"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=False)
    date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True)
    assigned_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    employee = relationship("Employee", foreign_keys=[employee_id])
    shift = relationship("Shift")
    assigner = relationship("Employee", foreign_keys=[assigned_by])


class GeofenceLocation(Base):
    __tablename__ = "geofence_locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    latitude = Column(Numeric(10, 7), nullable=False)
    longitude = Column(Numeric(10, 7), nullable=False)
    radius_meters = Column(Integer, nullable=False, default=100)
    address = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    creator = relationship("Employee", foreign_keys=[created_by])


class OvertimeRequest(Base):
    __tablename__ = "overtime_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=False)
    hours_requested = Column(Numeric(4, 1), nullable=False)
    hours_approved = Column(Numeric(4, 1), nullable=True)
    reason = Column(Text, nullable=True)
    status = Column(SQLEnum(OvertimeStatus), default=OvertimeStatus.PENDING, nullable=False)
    approved_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    employee = relationship("Employee", foreign_keys=[employee_id])
    approver = relationship("Employee", foreign_keys=[approved_by])
    rejector = relationship("Employee", foreign_keys=[rejected_by])


class AttendanceException(Base):
    __tablename__ = "attendance_exceptions"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    attendance_record_id = Column(Integer, ForeignKey("attendance_records.id"), nullable=True)
    exception_type = Column(SQLEnum(ExceptionType), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(ExceptionStatus), default=ExceptionStatus.OPEN, nullable=False)
    resolved_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    escalated_to = Column(Integer, ForeignKey("employees.id"), nullable=True)
    escalated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee", foreign_keys=[employee_id])
    attendance_record = relationship("AttendanceRecord")
    resolver = relationship("Employee", foreign_keys=[resolved_by])
    escalated_user = relationship("Employee", foreign_keys=[escalated_to])


class Holiday(Base):
    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    date = Column(Date, nullable=False)
    type = Column(String(50), nullable=True, default="public")
    is_recurring = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    creator = relationship("Employee", foreign_keys=[created_by])


class WeekendConfig(Base):
    __tablename__ = "weekend_configs"

    id = Column(Integer, primary_key=True, index=True)
    day_of_week = Column(Integer, nullable=False)
    is_weekend = Column(Boolean, default=False)
    is_alternate = Column(Boolean, default=False)
    description = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    creator = relationship("Employee", foreign_keys=[created_by])


class AttendanceAuditLog(Base):
    __tablename__ = "attendance_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=True)
    changes = Column(Text, nullable=True)
    performed_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee", foreign_keys=[employee_id])
    performer = relationship("Employee", foreign_keys=[performed_by])


class BiometricDevice(Base):
    __tablename__ = "biometric_devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    device_id = Column(String(100), unique=True, nullable=False)
    ip_address = Column(String(50), nullable=True)
    port = Column(Integer, nullable=True)
    location = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    last_sync = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    creator = relationship("Employee", foreign_keys=[created_by])


# ── Leave Requests ───────────────────────────────────────────────────────────
class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id          = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    leave_type  = Column(SQLEnum(LeaveType), nullable=False)
    start_date  = Column(Date, nullable=False)
    end_date    = Column(Date, nullable=False)
    reason      = Column(Text, nullable=True)
    status      = Column(SQLEnum(RequestStatus), default=RequestStatus.PENDING, nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    employee    = relationship("Employee", back_populates="leave_requests")


# ── Assets ─────────────────────────────────────────────────────────────────────
class Asset(Base):
    __tablename__ = "assets"

    id             = Column(Integer, primary_key=True, index=True)
    employee_id    = Column(Integer, ForeignKey("employees.id"), nullable=True)
    name           = Column(String(150), nullable=False)
    asset_tag      = Column(String(100), unique=True, nullable=False)
    category       = Column(String(100), nullable=True)
    serial_number  = Column(String(200), nullable=True)
    department     = Column(String(100), nullable=True)
    assigned_date  = Column(Date, nullable=True)
    purchase_date  = Column(Date, nullable=True)
    purchase_cost  = Column(Numeric(10, 2), nullable=True)
    condition      = Column(SQLEnum(AssetCondition), nullable=True)
    status         = Column(SQLEnum(AssetStatus), default=AssetStatus.AVAILABLE, nullable=False)
    notes          = Column(Text, nullable=True)
    retired_at     = Column(DateTime(timezone=True), nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at     = Column(DateTime(timezone=True), nullable=True)
    created_by    = Column(Integer, ForeignKey("employees.id"), nullable=True)
    updated_by    = Column(Integer, ForeignKey("employees.id"), nullable=True)
    warranty_expiry = Column(Date, nullable=True)
    vendor        = Column(String(200), nullable=True)
    location      = Column(String(200), nullable=True)

    employee       = relationship("Employee", back_populates="assets", foreign_keys=[employee_id])
    creator       = relationship("Employee", foreign_keys=[created_by])
    updater       = relationship("Employee", foreign_keys=[updated_by])


class AssetMaintenanceRequest(Base):
    __tablename__ = "asset_maintenance_requests"

    id             = Column(Integer, primary_key=True, index=True)
    asset_id       = Column(Integer, ForeignKey("assets.id"), nullable=False)
    asset_name     = Column(String(150), nullable=True)
    asset_tag      = Column(String(100), nullable=True)
    issue          = Column(Text, nullable=False)
    priority       = Column(SQLEnum(MaintenancePriority), default=MaintenancePriority.MEDIUM, nullable=False)
    reported_by    = Column(String(150), nullable=True)
    reported_by_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    reported_on    = Column(Date, nullable=False)
    status         = Column(SQLEnum(MaintenanceStatus), default=MaintenanceStatus.REPORTED, nullable=False)
    resolution     = Column(Text, nullable=True)
    resolved_by    = Column(Integer, ForeignKey("employees.id"), nullable=True)
    resolved_on    = Column(DateTime(timezone=True), nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now())
    created_by    = Column(Integer, ForeignKey("employees.id"), nullable=True)
    updated_by    = Column(Integer, ForeignKey("employees.id"), nullable=True)

    asset          = relationship("Asset")
    reporter       = relationship("Employee", foreign_keys=[reported_by_id])
    resolver       = relationship("Employee", foreign_keys=[resolved_by])
    creator        = relationship("Employee", foreign_keys=[created_by])
    updater        = relationship("Employee", foreign_keys=[updated_by])


class AssetRequest(Base):
    __tablename__ = "asset_requests"

    id             = Column(Integer, primary_key=True, index=True)
    employee_id    = Column(Integer, ForeignKey("employees.id"), nullable=True)
    employee_name  = Column(String(150), nullable=True)
    asset_type     = Column(String(100), nullable=False)
    quantity       = Column(Integer, nullable=False, default=1)
    priority       = Column(SQLEnum(RequestPriority), default=RequestPriority.MEDIUM, nullable=False)
    reason         = Column(Text, nullable=True)
    notes          = Column(Text, nullable=True)
    status         = Column(SQLEnum(AssetRequestStatus), default=AssetRequestStatus.PENDING, nullable=False)
    requested_on   = Column(Date, nullable=False)
    approved_by    = Column(Integer, ForeignKey("employees.id"), nullable=True)
    approved_on    = Column(DateTime(timezone=True), nullable=True)
    fulfilled_on   = Column(DateTime(timezone=True), nullable=True)
    cancelled_on   = Column(DateTime(timezone=True), nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now())
    created_by    = Column(Integer, ForeignKey("employees.id"), nullable=True)
    updated_by    = Column(Integer, ForeignKey("employees.id"), nullable=True)

    employee       = relationship("Employee", foreign_keys=[employee_id])
    approver       = relationship("Employee", foreign_keys=[approved_by])
    creator        = relationship("Employee", foreign_keys=[created_by])
    updater        = relationship("Employee", foreign_keys=[updated_by])


class AssetCategory(Base):
    __tablename__ = "asset_categories"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())
    created_by    = Column(Integer, ForeignKey("employees.id"), nullable=True)

    creator       = relationship("Employee", foreign_keys=[created_by])


class AssetReport(Base):
    __tablename__ = "asset_reports"

    id            = Column(Integer, primary_key=True, index=True)
    report_type   = Column(String(50), nullable=False)
    title         = Column(String(200), nullable=False)
    description   = Column(Text, nullable=True)
    generated_by  = Column(Integer, ForeignKey("employees.id"), nullable=True)
    parameters    = Column(Text, nullable=True)
    file_url      = Column(String(500), nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    generator     = relationship("Employee", foreign_keys=[generated_by])


class AssetSetting(Base):
    __tablename__ = "asset_settings"

    id            = Column(Integer, primary_key=True, index=True)
    setting_key   = Column(String(100), unique=True, nullable=False)
    setting_value = Column(Text, nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_by    = Column(Integer, ForeignKey("employees.id"), nullable=True)
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())

    updater       = relationship("Employee", foreign_keys=[updated_by])


# ── Compensation Components ────────────────────────────────────────────────────
class CompensationItem(Base):
    __tablename__ = "compensation_items"

    id          = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    amount      = Column(Numeric(10, 2), nullable=False)
    component   = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    period      = Column(String(50), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    employee    = relationship("Employee", back_populates="compensation_items")


# ── Compliance Records ────────────────────────────────────────────────────────
class ComplianceRecord(Base):
    __tablename__ = "compliance_records"

    id             = Column(Integer, primary_key=True, index=True)
    employee_id    = Column(Integer, ForeignKey("employees.id"), nullable=False)
    policy_name    = Column(String(150), nullable=False)
    completed_at   = Column(DateTime(timezone=True), nullable=True)
    status         = Column(SQLEnum(RequestStatus), default=RequestStatus.PENDING, nullable=False)
    notes          = Column(Text, nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    employee       = relationship("Employee", back_populates="compliance_records")


# ── Engagement Surveys ─────────────────────────────────────────────────────────
class EngagementSurvey(Base):
    __tablename__ = "engagement_surveys"

    id           = Column(Integer, primary_key=True, index=True)
    employee_id  = Column(Integer, ForeignKey("employees.id"), nullable=False)
    survey_name  = Column(String(150), nullable=False)
    score        = Column(Integer, nullable=False)
    comments     = Column(Text, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    employee     = relationship("Employee", back_populates="engagement_surveys")


# ── ESS Requests ──────────────────────────────────────────────────────────────
class EssRequest(Base):
    __tablename__ = "ess_requests"

    id           = Column(Integer, primary_key=True, index=True)
    employee_id  = Column(Integer, ForeignKey("employees.id"), nullable=False)
    request_type = Column(String(120), nullable=False)
    description  = Column(Text, nullable=True)
    status       = Column(SQLEnum(RequestStatus), default=RequestStatus.PENDING, nullable=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at  = Column(DateTime(timezone=True), nullable=True)

    employee     = relationship("Employee", back_populates="ess_requests")


# ── Learning Programs ─────────────────────────────────────────────────────────
class LearningCourse(Base):
    __tablename__ = "learning_courses"

    id             = Column(Integer, primary_key=True, index=True)
    course_name    = Column(String(200), nullable=False)
    description    = Column(Text, nullable=True)
    course_type    = Column(String(50), nullable=True)
    category       = Column(String(100), nullable=True)
    provider       = Column(String(150), nullable=True)
    duration_hours = Column(Integer, nullable=True)
    cost           = Column(Numeric(10, 2), nullable=True)
    status         = Column(String(50), nullable=False, default="active")
    created_by     = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now())

    creator        = relationship("Employee", foreign_keys=[created_by])


class LearningEnrollment(Base):
    __tablename__ = "learning_enrollments"

    id            = Column(Integer, primary_key=True, index=True)
    course_id     = Column(Integer, ForeignKey("learning_courses.id"), nullable=False)
    employee_id   = Column(Integer, ForeignKey("employees.id"), nullable=False)
    status        = Column(String(50), nullable=False, default="enrolled")
    progress_pct  = Column(Integer, nullable=False, default=0)
    enrolled_at   = Column(DateTime(timezone=True), server_default=func.now())
    started_at    = Column(DateTime(timezone=True), nullable=True)
    completed_at  = Column(DateTime(timezone=True), nullable=True)
    score         = Column(Integer, nullable=True)
    notes         = Column(Text, nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())

    course        = relationship("LearningCourse")
    employee      = relationship("Employee", back_populates="learning_enrollments", foreign_keys=[employee_id])


class LearningPath(Base):
    __tablename__ = "learning_paths"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    created_by  = Column(Integer, ForeignKey("employees.id"), nullable=True)
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    creator     = relationship("Employee", foreign_keys=[created_by])
    items       = relationship("LearningPathItem", back_populates="path", cascade="all, delete-orphan")


class LearningPathItem(Base):
    __tablename__ = "learning_path_items"

    id          = Column(Integer, primary_key=True, index=True)
    path_id     = Column(Integer, ForeignKey("learning_paths.id"), nullable=False)
    course_id   = Column(Integer, ForeignKey("learning_courses.id"), nullable=False)
    sort_order  = Column(Integer, nullable=False, default=0)
    is_required = Column(Boolean, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    path        = relationship("LearningPath", back_populates="items")
    course      = relationship("LearningCourse")


class LearningCertification(Base):
    __tablename__ = "learning_certifications"

    id                     = Column(Integer, primary_key=True, index=True)
    employee_id            = Column(Integer, ForeignKey("employees.id"), nullable=False)
    certification_name     = Column(String(200), nullable=False)
    issuing_organization   = Column(String(200), nullable=True)
    issue_date             = Column(Date, nullable=False)
    expiry_date            = Column(Date, nullable=True)
    credential_url         = Column(String(500), nullable=True)
    status                 = Column(String(50), nullable=False, default="active")
    created_by             = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at             = Column(DateTime(timezone=True), server_default=func.now())
    updated_at             = Column(DateTime(timezone=True), onupdate=func.now())

    employee               = relationship("Employee", foreign_keys=[employee_id])
    creator                = relationship("Employee", foreign_keys=[created_by])


class LearningSkill(Base):
    __tablename__ = "learning_skills"

    id                = Column(Integer, primary_key=True, index=True)
    employee_id       = Column(Integer, ForeignKey("employees.id"), nullable=False)
    skill_name        = Column(String(200), nullable=False)
    category          = Column(String(100), nullable=True)
    proficiency_level = Column(Integer, nullable=False, default=3)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())
    updated_at        = Column(DateTime(timezone=True), onupdate=func.now())

    employee          = relationship("Employee", foreign_keys=[employee_id])


class LearningAssessment(Base):
    __tablename__ = "learning_assessments"

    id              = Column(Integer, primary_key=True, index=True)
    course_id       = Column(Integer, ForeignKey("learning_courses.id"), nullable=False)
    title           = Column(String(200), nullable=False)
    description     = Column(Text, nullable=True)
    passing_score   = Column(Integer, nullable=False, default=70)
    max_attempts    = Column(Integer, nullable=True, default=0)
    duration_minutes = Column(Integer, nullable=True)
    is_active       = Column(Boolean, default=True)
    created_by      = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    course          = relationship("LearningCourse")
    creator         = relationship("Employee", foreign_keys=[created_by])
    questions       = relationship("LearningAssessmentQuestion", back_populates="assessment", cascade="all, delete-orphan")
    quiz_attempts   = relationship("LearningQuizAttempt", back_populates="assessment", cascade="all, delete-orphan")


class LearningAssessmentQuestion(Base):
    __tablename__ = "learning_assessment_questions"

    id             = Column(Integer, primary_key=True, index=True)
    assessment_id  = Column(Integer, ForeignKey("learning_assessments.id"), nullable=False)
    question_text  = Column(Text, nullable=False)
    question_type  = Column(String(50), nullable=False, default="multiple_choice")
    options        = Column(Text, nullable=True)
    correct_answer = Column(Text, nullable=True)
    points         = Column(Integer, nullable=False, default=1)
    sort_order     = Column(Integer, default=0)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    assessment     = relationship("LearningAssessment", back_populates="questions")


class LearningQuizAttempt(Base):
    __tablename__ = "learning_quiz_attempts"

    id              = Column(Integer, primary_key=True, index=True)
    assessment_id   = Column(Integer, ForeignKey("learning_assessments.id"), nullable=False)
    employee_id     = Column(Integer, ForeignKey("employees.id"), nullable=False)
    enrollment_id   = Column(Integer, ForeignKey("learning_enrollments.id"), nullable=True)
    started_at      = Column(DateTime(timezone=True), nullable=False)
    completed_at    = Column(DateTime(timezone=True), nullable=True)
    score           = Column(Integer, nullable=True)
    passed          = Column(Boolean, nullable=True)
    answers         = Column(Text, nullable=True)
    attempt_number  = Column(Integer, nullable=False, default=1)
    status          = Column(String(50), nullable=False, default="in_progress")
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    assessment      = relationship("LearningAssessment", back_populates="quiz_attempts")
    employee        = relationship("Employee", foreign_keys=[employee_id])
    enrollment      = relationship("LearningEnrollment")


class LearningTrainingProgram(Base):
    __tablename__ = "learning_training_programs"

    id               = Column(Integer, primary_key=True, index=True)
    name             = Column(String(200), nullable=False)
    description      = Column(Text, nullable=True)
    instructor_id    = Column(Integer, ForeignKey("employees.id"), nullable=True)
    start_date       = Column(Date, nullable=True)
    end_date         = Column(Date, nullable=True)
    status           = Column(String(50), nullable=False, default="planned")
    max_participants = Column(Integer, nullable=True)
    created_by       = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), onupdate=func.now())

    instructor       = relationship("Employee", foreign_keys=[instructor_id])
    creator          = relationship("Employee", foreign_keys=[created_by])
    assignments      = relationship("LearningTrainingProgramAssignment", back_populates="program", cascade="all, delete-orphan")


class LearningTrainingProgramAssignment(Base):
    __tablename__ = "learning_training_program_assignments"

    id          = Column(Integer, primary_key=True, index=True)
    program_id  = Column(Integer, ForeignKey("learning_training_programs.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    status      = Column(String(50), nullable=False, default="registered")
    attended_at = Column(DateTime(timezone=True), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    program     = relationship("LearningTrainingProgram", back_populates="assignments")
    employee    = relationship("Employee", foreign_keys=[employee_id])


class LearningCalendarEvent(Base):
    __tablename__ = "learning_calendar_events"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    event_date  = Column(Date, nullable=False)
    start_time  = Column(DateTime, nullable=True)
    end_time    = Column(DateTime, nullable=True)
    event_type  = Column(String(50), nullable=False, default="session")
    course_id   = Column(Integer, ForeignKey("learning_courses.id"), nullable=True)
    program_id  = Column(Integer, ForeignKey("learning_training_programs.id"), nullable=True)
    location    = Column(String(200), nullable=True)
    created_by  = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    course      = relationship("LearningCourse")
    program     = relationship("LearningTrainingProgram")
    creator     = relationship("Employee", foreign_keys=[created_by])


# ── Onboarding Records & Tasks ────────────────────────────────────────────────
class OnboardingRecord(Base):
    __tablename__ = "onboarding_records"

    id             = Column(Integer, primary_key=True, index=True)
    employee_id    = Column(Integer, ForeignKey("employees.id"), nullable=True)
    candidate_name = Column(String(150), nullable=False)
    email          = Column(String(255), nullable=False, index=True)
    phone          = Column(String(50), nullable=True)
    position       = Column(String(150), nullable=False)
    department_id  = Column(Integer, ForeignKey("departments.id"), nullable=True)
    manager_id     = Column(Integer, ForeignKey("employees.id"), nullable=True)
    joining_date   = Column(Date, nullable=True)
    status         = Column(SQLEnum(OnboardingStatus), default=OnboardingStatus.OFFER_SENT, nullable=False)
    notes          = Column(Text, nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now())

    employee       = relationship("Employee", foreign_keys=[employee_id], back_populates="onboarding_records")
    manager        = relationship("Employee", foreign_keys=[manager_id])
    department     = relationship("Department")
    tasks          = relationship("OnboardingTask", back_populates="record", cascade="all, delete-orphan")
    activities     = relationship("OnboardingActivity", back_populates="record", cascade="all, delete-orphan")

    @property
    def department_name(self):
        return self.department.name if self.department else None

    @property
    def manager_name(self):
        return self.manager.full_name if self.manager else None


class OnboardingTask(Base):
    __tablename__ = "onboarding_tasks"

    id           = Column(Integer, primary_key=True, index=True)
    employee_id  = Column(Integer, ForeignKey("employees.id"), nullable=True)
    onboarding_record_id = Column(Integer, ForeignKey("onboarding_records.id"), nullable=True)
    title        = Column(String(200), nullable=False)
    description  = Column(Text, nullable=True)
    due_date     = Column(Date, nullable=True)
    completed    = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    employee     = relationship("Employee", back_populates="onboarding_tasks")
    record       = relationship("OnboardingRecord", back_populates="tasks")


class OnboardingActivity(Base):
    __tablename__ = "onboarding_activities"

    id          = Column(Integer, primary_key=True, index=True)
    onboarding_record_id = Column(Integer, ForeignKey("onboarding_records.id"), nullable=True)
    action      = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    record      = relationship("OnboardingRecord", back_populates="activities")


# ── Performance Reviews ───────────────────────────────────────────────────────
class PerformanceReview(Base):
    __tablename__ = "performance_reviews"

    id           = Column(Integer, primary_key=True, index=True)
    employee_id  = Column(Integer, ForeignKey("employees.id"), nullable=False)
    reviewer_id  = Column(Integer, ForeignKey("employees.id"), nullable=True)
    cycle        = Column(String(100), nullable=False)
    rating       = Column(Integer, nullable=False)
    comments     = Column(Text, nullable=True)
    status       = Column(SQLEnum(RequestStatus), default=RequestStatus.PENDING, nullable=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at  = Column(DateTime(timezone=True), nullable=True)

    employee     = relationship("Employee", foreign_keys=[employee_id], back_populates="performance_reviews")
    reviewer     = relationship("Employee", foreign_keys=[reviewer_id])


# ── Recruitment Candidates ────────────────────────────────────────────────────
class RecruitmentCandidate(Base):
    __tablename__ = "recruitment_candidates"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(150), nullable=False)
    email       = Column(String(255), nullable=False, unique=True, index=True)
    phone       = Column(String(50), nullable=True)
    position    = Column(String(150), nullable=False)
    source      = Column(String(120), nullable=True)
    status      = Column(SQLEnum(RequestStatus), default=RequestStatus.PENDING, nullable=False)
    applied_at  = Column(DateTime(timezone=True), server_default=func.now())
    notes       = Column(Text, nullable=True)


# ── Travel Requests ──────────────────────────────────────────────────────────
class TravelRequest(Base):
    __tablename__ = "travel_requests"

    id          = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    destination = Column(String(200), nullable=False)
    purpose     = Column(Text, nullable=True)
    start_date  = Column(Date, nullable=False)
    end_date    = Column(Date, nullable=False)
    status      = Column(SQLEnum(RequestStatus), default=RequestStatus.PENDING, nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    employee    = relationship("Employee", back_populates="travel_requests")


# ── Workforce Planning ───────────────────────────────────────────────────────
class WorkforcePlan(Base):
    __tablename__ = "workforce_plans"

    id                = Column(Integer, primary_key=True, index=True)
    department_id     = Column(Integer, ForeignKey("departments.id"), nullable=True)
    year              = Column(Integer, nullable=False)
    headcount_target  = Column(Integer, nullable=False)
    notes             = Column(Text, nullable=True)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())

    department        = relationship("Department")