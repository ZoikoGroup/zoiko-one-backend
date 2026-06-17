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
    ASSIGNED     = "assigned"
    RETURNED     = "returned"
    MAINTENANCE  = "maintenance"


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
    attendance_records = relationship("AttendanceRecord", back_populates="employee")
    leave_requests  = relationship("LeaveRequest", back_populates="employee")
    assets          = relationship("Asset", back_populates="employee")
    compensation_items = relationship("CompensationItem", back_populates="employee")
    compliance_records  = relationship("ComplianceRecord", back_populates="employee")
    engagement_surveys  = relationship("EngagementSurvey", back_populates="employee")
    ess_requests    = relationship("EssRequest", back_populates="employee")
    learning_courses = relationship("LearningCourse", back_populates="employee")
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

    id          = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date        = Column(Date, nullable=False)
    status      = Column(SQLEnum(AttendanceStatus), default=AttendanceStatus.PRESENT, nullable=False)
    check_in    = Column(DateTime(timezone=True), nullable=True)
    check_out   = Column(DateTime(timezone=True), nullable=True)
    notes       = Column(Text, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    employee    = relationship("Employee", back_populates="attendance_records")


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
    assigned_date  = Column(Date, nullable=True)
    status         = Column(SQLEnum(AssetStatus), default=AssetStatus.ASSIGNED, nullable=False)
    notes          = Column(Text, nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    employee       = relationship("Employee", back_populates="assets")


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
    employee_id    = Column(Integer, ForeignKey("employees.id"), nullable=False)
    title          = Column(String(200), nullable=False)
    provider       = Column(String(150), nullable=True)
    status         = Column(String(80), nullable=False, default="enrolled")
    enrolled_at    = Column(DateTime(timezone=True), server_default=func.now())
    completed_at   = Column(DateTime(timezone=True), nullable=True)
    notes          = Column(Text, nullable=True)

    employee       = relationship("Employee", back_populates="learning_courses")


# ── Onboarding Tasks ──────────────────────────────────────────────────────────
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

    id               = Column(Integer, primary_key=True, index=True)
    department_id    = Column(Integer, ForeignKey("departments.id"), nullable=True)
    year             = Column(Integer, nullable=False)
    headcount_target = Column(Integer, nullable=False)
    notes            = Column(Text, nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    department       = relationship("Department")
