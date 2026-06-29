"""
modules/time/models.py
----------------------
SQLAlchemy ORM models for the Zoiko Time module.

Tables defined here:
  - TimeEntry   → stores employee clock-in/clock-out records
"""

import enum
from datetime import datetime, date

from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime,
    Enum as SQLEnum, ForeignKey, Text, Numeric, Time
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TimeEntry(Base):
    """
    Records each clock-in / clock-out event for an employee.
    """
    __tablename__ = "time_entries"

    id            = Column(Integer, primary_key=True, index=True)
    employee_id   = Column(Integer, ForeignKey("employees.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)

    clock_in      = Column(DateTime(timezone=True), nullable=False)
    clock_out     = Column(DateTime(timezone=True), nullable=True)
    work_date     = Column(Date, nullable=False)

    notes         = Column(Text, nullable=True)
    is_approved   = Column(Boolean, default=False)

    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<TimeEntry id={self.id} employee_id={self.employee_id} date={self.work_date}>"