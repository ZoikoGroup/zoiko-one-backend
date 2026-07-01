"""
modules/time/schemas.py
-----------------------
Pydantic schemas for the Zoiko Time module.
"""

from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict

# Imported explicit Enum representations from our master HR layout
from app.modules.hr.models import LeaveType, RequestStatus


# ── Time Entry Schemas ────────────────────────────────────────────────────────

class TimeEntryCreate(BaseModel):
    employee_id: int
    clock_in:    datetime
    clock_out:   Optional[datetime] = None
    work_date:   date
    notes:       Optional[str] = None


class TimeEntryUpdate(BaseModel):
    clock_out:   Optional[datetime] = None
    notes:       Optional[str] = None
    is_approved: Optional[bool] = None


class TimeEntryResponse(BaseModel):
    id:          int
    employee_id: int
    clock_in:    datetime
    clock_out:   Optional[datetime]
    work_date:   date
    notes:       Optional[str]
    is_approved: bool
    created_at:  datetime

    model_config = ConfigDict(from_attributes=True)


# ── Leave Request Schemas ─────────────────────────────────────────────────────

class LeaveRequestCreate(BaseModel):
    leave_type: LeaveType
    start_date: date
    end_date:   date
    reason:     Optional[str] = None


class LeaveRequestUpdate(BaseModel):
    status:      Optional[RequestStatus] = None
    review_note: Optional[str] = None


class LeaveRequestResponse(BaseModel):
    id:          int
    employee_id: int
    leave_type:  str  # Read as String to comply seamlessly with HR storage column
    status:      str  # Read as String to comply seamlessly with HR storage column
    start_date:  date
    end_date:    date
    total_days:  Decimal
    reason:      Optional[str]
    reviewed_by: Optional[int]
    reviewed_at: Optional[datetime]
    review_note: Optional[str]
    created_at:  datetime

    model_config = ConfigDict(from_attributes=True)


class SuccessResponse(BaseModel):
    message: str