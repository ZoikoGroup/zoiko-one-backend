"""
modules/insights/models.py
--------------------------
SQLAlchemy ORM models for the Zoiko Insights module.

Tables:
  - Report        → saved report definitions
  - ReportRun     → log of each time a report was executed
"""

import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from app.database import Base


class ReportType(str, enum.Enum):
    HR          = "hr"
    PAYROLL     = "payroll"
    BILLING     = "billing"
    TIME        = "time"
    COMPLY      = "comply"
    CUSTOM      = "custom"


class ReportFormat(str, enum.Enum):
    JSON    = "json"
    CSV     = "csv"
    PDF     = "pdf"


class Report(Base):
    __tablename__ = "reports"

    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String(200), nullable=False)
    description     = Column(Text, nullable=True)
    report_type     = Column(SQLEnum(ReportType), nullable=False)
    filters         = Column(JSON, nullable=True)       # stores filter config as JSON
    is_active       = Column(Boolean, default=True)
    created_by      = Column(Integer, ForeignKey("employees.id"), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Report id={self.id} name={self.name}>"


class ReportRun(Base):
    __tablename__ = "report_runs"

    id              = Column(Integer, primary_key=True, index=True)
    report_id       = Column(Integer, ForeignKey("reports.id"), nullable=False)
    run_by          = Column(Integer, ForeignKey("employees.id"), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    format          = Column(SQLEnum(ReportFormat), default=ReportFormat.JSON)
    result_url      = Column(String(500), nullable=True)   # URL to generated file
    row_count       = Column(Integer, nullable=True)
    duration_ms     = Column(Integer, nullable=True)       # how long it took
    ran_at          = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<ReportRun id={self.id} report_id={self.report_id}>"
