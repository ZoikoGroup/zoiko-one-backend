"""
modules/time/router.py
----------------------
HTTP endpoints for the Zoiko Time module.

Endpoints:
  TIME ENTRIES
    POST   /time/entries           → Clock in / create entry
    GET    /time/entries           → List entries
    PUT    /time/entries/{id}      → Clock out / update entry

  LEAVE REQUESTS
    POST   /time/leaves            → Submit leave request
    GET    /time/leaves            → List leave requests
    PUT    /time/leaves/{id}/review → Approve or reject leave
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user, get_current_admin
from app.modules.time import service
from app.modules.time.schemas import (
    TimeEntryCreate, TimeEntryUpdate, TimeEntryResponse,
    LeaveRequestCreate, LeaveRequestUpdate, LeaveRequestResponse,
)

time_router = APIRouter(prefix="/time", tags=["🕐 Time Module"])


# ── Time Entry Endpoints ──────────────────────────────────────────────────────

@time_router.post("/entries", response_model=TimeEntryResponse, summary="Create a time entry")
def create_entry(data: TimeEntryCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.create_time_entry(db, data)


@time_router.get("/entries", response_model=list[TimeEntryResponse], summary="List time entries")
def list_entries(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    employee_id: Optional[int] = Query(None, description="Filter by employee"),
):
    return service.get_time_entries(db, employee_id)


@time_router.put("/entries/{entry_id}", response_model=TimeEntryResponse, summary="Update a time entry")
def update_entry(entry_id: int, data: TimeEntryUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.update_time_entry(db, entry_id, data)


# ── Leave Request Endpoints ───────────────────────────────────────────────────

@time_router.post("/leaves", response_model=LeaveRequestResponse, summary="Submit a leave request")
def create_leave(data: LeaveRequestCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return service.create_leave_request(db, current_user.id, data)


@time_router.get("/leaves", response_model=list[LeaveRequestResponse], summary="List leave requests")
def list_leaves(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    employee_id: Optional[int] = Query(None, description="Filter by employee"),
):
    return service.get_leave_requests(db, employee_id)


@time_router.put("/leaves/{leave_id}/review", response_model=LeaveRequestResponse, summary="Approve or reject a leave request")
def review_leave(
    leave_id: int, 
    data: LeaveRequestUpdate, 
    db: Session = Depends(get_db), 
    current_user=Depends(get_current_user),
    _=Depends(get_current_admin)  # Maintained admin check dependency guard
):
    return service.review_leave_request(db, leave_id, current_user.id, data)