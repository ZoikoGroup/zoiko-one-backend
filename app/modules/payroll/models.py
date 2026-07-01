"""
modules/payroll/models.py
-------------------------
SQLAlchemy ORM models for the Zoiko Payroll module.

Tables:
  - PayrollRun      → a single payroll processing run (e.g. June 2025)
  - PayslipItem     → individual salary components per employee per run
"""

import enum
from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, Enum as SQLEnum, ForeignKey, Text, Numeric
from sqlalchemy.sql import func
from app.database import Base


class PayrollStatus(str, enum.Enum):
    DRAFT       = "draft"
    PROCESSING  = "processing"
    COMPLETED   = "completed"
    PAID        = "paid"


class PayrollRun(Base):
    """One payroll cycle (monthly/bi-weekly)."""
    __tablename__ = "payroll_runs"

    id            = Column(Integer, primary_key=True, index=True)
    period_label  = Column(String(50), nullable=False)   # e.g. "June 2025"
    period_start  = Column(Date, nullable=False)
    period_end    = Column(Date, nullable=False)
    status        = Column(SQLEnum(PayrollStatus), default=PayrollStatus.DRAFT)
    total_gross   = Column(Numeric(14, 2), default=0)
    total_net     = Column(Numeric(14, 2), default=0)
    notes         = Column(Text, nullable=True)
    created_by    = Column(Integer, ForeignKey("employees.id"), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<PayrollRun id={self.id} period={self.period_label} status={self.status}>"


class PayslipItem(Base):
    """One employee's payslip within a payroll run."""
    __tablename__ = "payslip_items"

    id              = Column(Integer, primary_key=True, index=True)
    payroll_run_id  = Column(Integer, ForeignKey("payroll_runs.id"), nullable=False)
    employee_id     = Column(Integer, ForeignKey("employees.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)

    basic_salary    = Column(Numeric(12, 2), default=0)
    allowances      = Column(Numeric(12, 2), default=0)
    deductions      = Column(Numeric(12, 2), default=0)
    tax             = Column(Numeric(12, 2), default=0)
    gross_pay       = Column(Numeric(12, 2), default=0)
    net_pay         = Column(Numeric(12, 2), default=0)

    is_paid         = Column(Boolean, default=False)
    paid_at         = Column(DateTime(timezone=True), nullable=True)
    notes           = Column(Text, nullable=True)

    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<PayslipItem id={self.id} employee_id={self.employee_id} net={self.net_pay}>"
