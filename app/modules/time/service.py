"""
modules/time/service.py
-----------------------
Business logic for the Zoiko Time module.
Handles time entries and leave requests.
"""

from typing import List, Optional
from datetime import date, datetime
from sqlalchemy.orm import Session

from app.modules.time.models import TimeEntry
from app.modules.hr.models import LeaveRequest  # Pointed to Master HR Table
from app.modules.time.schemas import (
    TimeEntryCreate, TimeEntryUpdate,
    LeaveRequestCreate, LeaveRequestUpdate,
)
from app.core.exceptions import NotFoundException, BadRequestException


# ── Time Entry Services ───────────────────────────────────────────────────────

def create_time_entry(db: Session, data: TimeEntryCreate) -> TimeEntry:
    entry = TimeEntry(**data.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_time_entries(db: Session, employee_id: Optional[int] = None) -> List[TimeEntry]:
    query = db.query(TimeEntry)
    if employee_id:
        query = query.filter(TimeEntry.employee_id == employee_id)
    return query.order_by(TimeEntry.work_date.desc()).all()


def update_time_entry(db: Session, entry_id: int, data: TimeEntryUpdate) -> TimeEntry:
    entry = db.query(TimeEntry).filter(TimeEntry.id == entry_id).first()
    if not entry:
        raise NotFoundException(f"Time entry {entry_id} not found.")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return entry


# ── Leave Request Services ────────────────────────────────────────────────────

def create_leave_request(db: Session, employee_id: int, data: LeaveRequestCreate) -> LeaveRequest:
    delta = (data.end_date - data.start_date).days + 1
    if delta <= 0:
        raise BadRequestException("End date must be greater than or equal to start date.")
        
    leave = LeaveRequest(
        employee_id=employee_id,
        total_days=delta,
        leave_type=data.leave_type,
        start_date=data.start_date,
        end_date=data.end_date,
        reason=data.reason,
        status="pending"  # String fallback match for master HR schema default
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return leave


def get_leave_requests(db: Session, employee_id: Optional[int] = None) -> List[LeaveRequest]:
    query = db.query(LeaveRequest)
    if employee_id:
        query = query.filter(LeaveRequest.employee_id == employee_id)
    return query.order_by(LeaveRequest.created_at.desc()).all()


def review_leave_request(
    db: Session, leave_id: int, reviewer_id: int, data: LeaveRequestUpdate
) -> LeaveRequest:
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        raise NotFoundException(f"Leave request {leave_id} not found.")
        
    if data.status:
        leave.status = data.status
    if data.review_note:
        leave.review_note = data.review_note
        
    leave.reviewed_by = reviewer_id
    leave.reviewed_at = datetime.now()
    
    db.commit()
    db.refresh(leave)
    return leave