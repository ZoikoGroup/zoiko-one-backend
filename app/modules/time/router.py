"""
modules/time/router.py
----------------------
HTTP endpoints for the Zoiko Time module.

Endpoints:
  TIME ENTRIES
    POST   /time/entries           → Clock in / create entry
    GET    /time/entries           → List entries
    GET    /time/entries/{id}      → Get single entry
    PUT    /time/entries/{id}      → Clock out / update entry

  LEAVE REQUESTS
    POST   /time/leaves            → Submit leave request
    GET    /time/leaves            → List leave requests
    GET    /time/leaves/{id}       → Get leave request
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
def create_entry(
    data: TimeEntryCreate, 
    db: Session = Depends(get_db), 
    current_user=Depends(get_current_user)
):
    return service.create_time_entry(db, data, current_user.organization_id)


@time_router.get("/entries", response_model=list[TimeEntryResponse], summary="List time entries")
def list_entries(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    employee_id: Optional[int] = Query(None, description="Filter by employee"),
):
    return service.get_time_entries(db, employee_id, current_user.organization_id)


@time_router.get("/entries/{entry_id}", response_model=TimeEntryResponse, summary="Get a time entry")
def get_entry(
    entry_id: int, 
    db: Session = Depends(get_db), 
    current_user=Depends(get_current_user)
):
    return service.get_time_entry_by_id(db, entry_id, current_user.organization_id)


@time_router.put("/entries/{entry_id}", response_model=TimeEntryResponse, summary="Update a time entry")
def update_entry(
    entry_id: int, 
    data: TimeEntryUpdate, 
    db: Session = Depends(get_db), 
    current_user=Depends(get_current_user)
):
    return service.update_time_entry(db, entry_id, data, current_user.organization_id)


# ── Leave Request Endpoints ───────────────────────────────────────────────────

@time_router.post("/leaves", response_model=LeaveRequestResponse, summary="Submit a leave request")
def create_leave(
    data: LeaveRequestCreate, 
    db: Session = Depends(get_db), 
    current_user=Depends(get_current_user)
):
    return service.create_leave_request(db, current_user.id, data, current_user.organization_id)


@time_router.get("/leaves", response_model=list[LeaveRequestResponse], summary="List leave requests")
def list_leaves(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    employee_id: Optional[int] = Query(None, description="Filter by employee"),
):
    return service.get_leave_requests(db, employee_id, current_user.organization_id)


@time_router.get("/leaves/{leave_id}", response_model=LeaveRequestResponse, summary="Get a leave request")
def get_leave(
    leave_id: int, 
    db: Session = Depends(get_db), 
    current_user=Depends(get_current_user)
):
    return service.get_leave_request_by_id(db, leave_id, current_user.organization_id)


@time_router.put("/leaves/{leave_id}/review", response_model=LeaveRequestResponse, summary="Approve or reject a leave request")
def review_leave(
    leave_id: int, 
    data: LeaveRequestUpdate, 
    db: Session = Depends(get_db), 
    current_user=Depends(get_current_user),
    _=Depends(get_current_admin)
):
    return service.review_leave_request(db, leave_id, current_user.id, data, current_user.organization_id)