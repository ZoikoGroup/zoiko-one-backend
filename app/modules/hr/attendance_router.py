"""
modules/hr/attendance_router.py
-------------------------------
Defines all HTTP endpoints for the Attendance module.

Endpoints:
  DASHBOARD
    GET    /hr/attendance/dashboard                    → Dashboard stats

  DAILY ATTENDANCE (RECORDS)
    GET    /hr/attendance/records                      → List records (paginated, filterable)
    POST   /hr/attendance/records                      → Create record
    GET    /hr/attendance/records/{id}                 → Get one record
    PUT    /hr/attendance/records/{id}                 → Update record
    DELETE /hr/attendance/records/{id}                 → Soft delete record

  CLOCK IN/OUT
    POST   /hr/attendance/clock-in                     → Clock in
    POST   /hr/attendance/clock-out/{id}               → Clock out
    POST   /hr/attendance/break-start/{id}             → Break start
    POST   /hr/attendance/break-end/{id}               → Break end

  REGULARIZATION
    GET    /hr/attendance/regularizations              → List regularization requests
    POST   /hr/attendance/regularizations              → Create regularization
    GET    /hr/attendance/regularizations/{id}          → Get one
    PUT    /hr/attendance/regularizations/{id}/approve-manager → Manager approve
    PUT    /hr/attendance/regularizations/{id}/approve-hr      → HR approve
    PUT    /hr/attendance/regularizations/{id}/reject           → Reject
    PUT    /hr/attendance/regularizations/{id}/cancel           → Cancel

  POLICIES
    GET    /hr/attendance/policies                     → List policies
    POST   /hr/attendance/policies                     → Create policy
    GET    /hr/attendance/policies/{id}                → Get one
    PUT    /hr/attendance/policies/{id}                → Update
    DELETE /hr/attendance/policies/{id}                → Delete

  SHIFTS
    GET    /hr/attendance/shifts                       → List shifts
    POST   /hr/attendance/shifts                       → Create shift
    GET    /hr/attendance/shifts/{id}                  → Get one
    PUT    /hr/attendance/shifts/{id}                  → Update
    DELETE /hr/attendance/shifts/{id}                  → Delete

  SHIFT ROSTERS
    GET    /hr/attendance/rosters                      → List rosters
    POST   /hr/attendance/rosters                      → Create roster
    POST   /hr/attendance/rosters/bulk                 → Bulk assign
    DELETE /hr/attendance/rosters/{id}                 → Delete roster

  MY ATTENDANCE
    GET    /hr/attendance/my-attendance                → Current user's records
    GET    /hr/attendance/employee/{eid}/summary       → Monthly summary
    GET    /hr/attendance/employee/{eid}/history       → Attendance history
    GET    /hr/attendance/employee/{eid}/score         → Attendance score

  BIOMETRIC
    GET    /hr/attendance/biometric/devices            → List devices
    POST   /hr/attendance/biometric/devices            → Register device
    PUT    /hr/attendance/biometric/devices/{id}       → Update device
    DELETE /hr/attendance/biometric/devices/{id}       → Delete device
    POST   /hr/attendance/biometric/sync              → Sync logs
    POST   /hr/attendance/biometric/import             → Import logs
    GET    /hr/attendance/biometric/device-health/{id} → Device health

  GEOFENCING
    GET    /hr/attendance/geofencing                   → List locations
    POST   /hr/attendance/geofencing                   → Create location
    GET    /hr/attendance/geofencing/{id}              → Get one
    PUT    /hr/attendance/geofencing/{id}              → Update
    DELETE /hr/attendance/geofencing/{id}              → Delete

  OVERTIME
    GET    /hr/attendance/overtime                     → List overtime
    POST   /hr/attendance/overtime                     → Create
    GET    /hr/attendance/overtime/{id}                → Get one
    PUT    /hr/attendance/overtime/{id}/approve        → Approve
    PUT    /hr/attendance/overtime/{id}/reject         → Reject
    GET    /hr/attendance/overtime/reports             → Overtime reports

  EXCEPTIONS
    GET    /hr/attendance/exceptions                   → List exceptions
    POST   /hr/attendance/exceptions                   → Create exception
    PUT    /hr/attendance/exceptions/{id}/resolve      → Resolve
    PUT    /hr/attendance/exceptions/{id}/escalate     → Escalate
    GET    /hr/attendance/exceptions/{id}              → Get one

  HOLIDAYS
    GET    /hr/attendance/holidays                     → List holidays
    POST   /hr/attendance/holidays                     → Create holiday
    GET    /hr/attendance/holidays/{id}                → Get one
    PUT    /hr/attendance/holidays/{id}                → Update
    DELETE /hr/attendance/holidays/{id}                → Delete
    POST   /hr/attendance/holidays/import              → Bulk import

  WEEKEND CONFIG
    GET    /hr/attendance/weekends                     → List configs
    POST   /hr/attendance/weekends                     → Create config
    PUT    /hr/attendance/weekends/{id}                → Update
    DELETE /hr/attendance/weekends/{id}                → Delete

  AUDIT LOGS
    GET    /hr/attendance/audit-logs                   → List audit logs

  EXPORTS
    GET    /hr/attendance/export/csv                   → Export CSV
    GET    /hr/attendance/export/excel                 → Export Excel
    GET    /hr/attendance/export/reports/csv           → Report CSV
    GET    /hr/attendance/export/reports/excel         → Report Excel

  REPORTS
    GET    /hr/attendance/reports/daily                → Daily report
    GET    /hr/attendance/reports/monthly              → Monthly report
    GET    /hr/attendance/reports/department           → Department report
    GET    /hr/attendance/reports/shift                → Shift report
    GET    /hr/attendance/reports/late-arrivals        → Late arrivals report
    GET    /hr/attendance/reports/overtime             → Overtime report
    GET    /hr/attendance/reports/absentee             → Absentee report
    GET    /hr/attendance/reports/compliance           → Compliance report

  ANALYTICS
    GET    /hr/attendance/analytics/trends             → Attendance trends
    GET    /hr/attendance/analytics/department         → Department analysis
    GET    /hr/attendance/analytics/overtime           → Overtime analytics
    GET    /hr/attendance/analytics/shift-efficiency   → Shift efficiency
"""

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Body, status, Request
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user, get_current_admin
from app.core.rate_limiter import limiter

from app.modules.hr import attendance_service
from app.modules.hr.models import (
    AttendanceStatus, CorrectionType, RegularizationStatus,
    ExceptionStatus, ExceptionType, OvertimeStatus,
)
from app.modules.hr.schemas import (
    AttendanceCreate, AttendanceUpdate, AttendanceResponse, AttendanceDashboardResponse,
    RegularizationCreate, RegularizationResponse,
    AttendancePolicyCreate, AttendancePolicyUpdate, AttendancePolicyResponse,
    ShiftCreate, ShiftUpdate, ShiftResponse,
    ShiftRosterCreate, ShiftRosterResponse,
    GeofenceCreate, GeofenceUpdate, GeofenceResponse,
    OvertimeCreate, OvertimeResponse,
    AttendanceExceptionResponse,
    HolidayCreate, HolidayUpdate, HolidayResponse,
    WeekendConfigCreate, WeekendConfigResponse,
    BiometricDeviceCreate, BiometricDeviceUpdate, BiometricDeviceResponse,
    AttendanceAuditLogResponse,
    SuccessResponse,
)

attendance_router = APIRouter(prefix="/hr/attendance", tags=["Attendance"])


# ════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ════════════════════════════════════════════════════════════════════════════

@attendance_router.get(
    "/dashboard",
    response_model=AttendanceDashboardResponse,
    summary="Attendance dashboard statistics",
    description="Returns attendance summary counts, present/absent breakdown, and shift utilization.",
)
def attendance_dashboard(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_attendance_dashboard(db)


# ════════════════════════════════════════════════════════════════════════════
# ATTENDANCE RECORDS CRUD
# ════════════════════════════════════════════════════════════════════════════

@attendance_router.get(
    "/records",
    summary="List attendance records with search, filters, and sorting",
)
def list_attendance_records(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    page:        int                    = Query(1,    ge=1,   description="Page number"),
    per_page:    int                    = Query(20,   ge=1,   le=100, description="Results per page"),
    search:      Optional[str]          = Query(None, description="Search by employee name/code"),
    status:      Optional[AttendanceStatus] = Query(None, description="Filter by status"),
    department:  Optional[str]          = Query(None, description="Filter by department"),
    date_from:   Optional[date]         = Query(None, description="Filter from date"),
    date_to:     Optional[date]         = Query(None, description="Filter to date"),
    employee_id: Optional[int]          = Query(None, description="Filter by employee ID"),
    sort_by:     Optional[str]          = Query("date", description="Sort field"),
    sort_order:  Optional[str]          = Query("desc", description="Sort direction (asc/desc)"),
):
    return attendance_service.get_attendance_records(
        db, page, per_page, search, status, department, date_from, date_to, employee_id, sort_by, sort_order,
    )


@attendance_router.post(
    "/records",
    response_model=AttendanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an attendance record",
)
def create_attendance_record(
    data: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    return attendance_service.create_attendance_record(db, data, created_by=current_user.id)


@attendance_router.get(
    "/records/{record_id}",
    response_model=AttendanceResponse,
    summary="Get a single attendance record by ID",
)
def get_attendance_record(
    record_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_attendance_record_by_id(db, record_id)


@attendance_router.put(
    "/records/{record_id}",
    response_model=AttendanceResponse,
    summary="Update an attendance record",
)
def update_attendance_record(
    record_id: int,
    data: AttendanceUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    return attendance_service.update_attendance_record(db, record_id, data, updated_by=current_user.id)


@attendance_router.delete(
    "/records/{record_id}",
    response_model=SuccessResponse,
    summary="Delete an attendance record",
)
def delete_attendance_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    attendance_service.delete_attendance_record(db, record_id, deleted_by=current_user.id)
    return {"message": f"Attendance record {record_id} has been deleted successfully."}


# ════════════════════════════════════════════════════════════════════════════
# CLOCK IN/OUT
# ════════════════════════════════════════════════════════════════════════════

@attendance_router.post(
    "/clock-in",
    response_model=AttendanceResponse,
    summary="Clock in for an employee",
)
def clock_in(
    employee_id: Optional[int] = Body(None, embed=True, description="Employee ID"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    emp_id = employee_id or current_user.id
    return attendance_service.clock_in(db, emp_id, created_by=current_user.id)


@attendance_router.post(
    "/clock-out/{record_id}",
    response_model=AttendanceResponse,
    summary="Clock out for an attendance record",
)
def clock_out(
    record_id: int,
    clock_out_time: Optional[datetime] = Body(None, embed=True, description="Clock out time"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.clock_out(db, record_id, clock_out_time)


@attendance_router.post(
    "/break-start/{record_id}",
    response_model=AttendanceResponse,
    summary="Start break for an attendance record",
)
def break_start(
    record_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.break_start(db, record_id)


@attendance_router.post(
    "/break-end/{record_id}",
    response_model=AttendanceResponse,
    summary="End break for an attendance record",
)
def break_end(
    record_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.break_end(db, record_id)


# ════════════════════════════════════════════════════════════════════════════
# ATTENDANCE REGULARIZATION
# ════════════════════════════════════════════════════════════════════════════

@attendance_router.get(
    "/regularizations",
    summary="List regularization requests with filters",
)
def list_regularizations(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    page:           int                         = Query(1,    ge=1,   description="Page number"),
    per_page:       int                         = Query(20,   ge=1,   le=100, description="Results per page"),
    status:         Optional[RegularizationStatus] = Query(None, description="Filter by status"),
    employee_id:    Optional[int]               = Query(None, description="Filter by employee ID"),
    correction_type: Optional[CorrectionType]   = Query(None, description="Filter by correction type"),
):
    return attendance_service.get_regularizations(db, page, per_page, status, employee_id, correction_type)


@attendance_router.post(
    "/regularizations",
    response_model=RegularizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a regularization request",
)
def create_regularization(
    data: RegularizationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return attendance_service.create_regularization(db, data, created_by=current_user.id)


@attendance_router.get(
    "/regularizations/{reg_id}",
    response_model=RegularizationResponse,
    summary="Get a regularization request by ID",
)
def get_regularization(
    reg_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_regularization_by_id(db, reg_id)


@attendance_router.put(
    "/regularizations/{reg_id}/approve-manager",
    response_model=RegularizationResponse,
    summary="Manager approve a regularization request",
)
def approve_regularization_manager(
    reg_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return attendance_service.approve_regularization_manager(db, reg_id, manager_id=current_user.id)


@attendance_router.put(
    "/regularizations/{reg_id}/approve-hr",
    response_model=RegularizationResponse,
    summary="HR approve a regularization request",
    dependencies=[Depends(get_current_admin)],
)
def approve_regularization_hr(reg_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return attendance_service.approve_regularization_hr(db, reg_id, hr_id=current_user.id)


@attendance_router.put(
    "/regularizations/{reg_id}/reject",
    response_model=RegularizationResponse,
    summary="Reject a regularization request",
)
def reject_regularization(
    reg_id: int,
    rejection_reason: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return attendance_service.reject_regularization(db, reg_id, rejected_by=current_user.id, rejection_reason=rejection_reason)


@attendance_router.put(
    "/regularizations/{reg_id}/cancel",
    response_model=RegularizationResponse,
    summary="Cancel a regularization request",
)
def cancel_regularization(
    reg_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.cancel_regularization(db, reg_id)


# ════════════════════════════════════════════════════════════════════════════
# ATTENDANCE POLICIES
# ════════════════════════════════════════════════════════════════════════════

@attendance_router.get(
    "/policies",
    response_model=list[AttendancePolicyResponse],
    summary="List attendance policies",
)
def list_attendance_policies(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_attendance_policies(db)


@attendance_router.post(
    "/policies",
    response_model=AttendancePolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an attendance policy",
    dependencies=[Depends(get_current_admin)],
)
def create_attendance_policy(data: AttendancePolicyCreate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return attendance_service.create_attendance_policy(db, data, created_by=current_user.id)


@attendance_router.get(
    "/policies/{policy_id}",
    response_model=AttendancePolicyResponse,
    summary="Get an attendance policy by ID",
)
def get_attendance_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_attendance_policy_by_id(db, policy_id)


@attendance_router.put(
    "/policies/{policy_id}",
    response_model=AttendancePolicyResponse,
    summary="Update an attendance policy",
    dependencies=[Depends(get_current_admin)],
)
def update_attendance_policy(policy_id: int, data: AttendancePolicyUpdate, db: Session = Depends(get_db)):
    return attendance_service.update_attendance_policy(db, policy_id, data)


@attendance_router.delete(
    "/policies/{policy_id}",
    response_model=SuccessResponse,
    summary="Delete an attendance policy",
    dependencies=[Depends(get_current_admin)],
)
def delete_attendance_policy(policy_id: int, db: Session = Depends(get_db)):
    attendance_service.delete_attendance_policy(db, policy_id)
    return {"message": f"Attendance policy {policy_id} has been deleted successfully."}


# ════════════════════════════════════════════════════════════════════════════
# SHIFTS
# ════════════════════════════════════════════════════════════════════════════

@attendance_router.get(
    "/shifts",
    response_model=list[ShiftResponse],
    summary="List shifts",
)
def list_shifts(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_shifts(db)


@attendance_router.post(
    "/shifts",
    response_model=ShiftResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a shift",
    dependencies=[Depends(get_current_admin)],
)
def create_shift(data: ShiftCreate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return attendance_service.create_shift(db, data, created_by=current_user.id)


@attendance_router.get(
    "/shifts/{shift_id}",
    response_model=ShiftResponse,
    summary="Get a shift by ID",
)
def get_shift(
    shift_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_shift_by_id(db, shift_id)


@attendance_router.put(
    "/shifts/{shift_id}",
    response_model=ShiftResponse,
    summary="Update a shift",
    dependencies=[Depends(get_current_admin)],
)
def update_shift(shift_id: int, data: ShiftUpdate, db: Session = Depends(get_db)):
    return attendance_service.update_shift(db, shift_id, data)


@attendance_router.delete(
    "/shifts/{shift_id}",
    response_model=SuccessResponse,
    summary="Delete a shift",
    dependencies=[Depends(get_current_admin)],
)
def delete_shift(shift_id: int, db: Session = Depends(get_db)):
    attendance_service.delete_shift(db, shift_id)
    return {"message": f"Shift {shift_id} has been deleted successfully."}


# ════════════════════════════════════════════════════════════════════════════
# SHIFT ROSTERS
# ════════════════════════════════════════════════════════════════════════════

@attendance_router.get(
    "/rosters",
    summary="List shift rosters with filters",
)
def list_shift_rosters(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    page:       int  = Query(1,  ge=1,   description="Page number"),
    per_page:   int  = Query(20, ge=1,   le=100, description="Results per page"),
    date_filter: Optional[date] = Query(None, alias="date", description="Filter by date"),
    employee_id: Optional[int]  = Query(None, description="Filter by employee ID"),
    shift_id:   Optional[int]  = Query(None, description="Filter by shift ID"),
):
    return attendance_service.get_shift_rosters(db, page, per_page, date_filter, employee_id, shift_id)


@attendance_router.post(
    "/rosters",
    response_model=ShiftRosterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a shift roster assignment",
)
def create_shift_roster(
    data: ShiftRosterCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    return attendance_service.create_shift_roster(db, data, assigned_by=current_user.id)


@attendance_router.post(
    "/rosters/bulk",
    status_code=status.HTTP_201_CREATED,
    summary="Bulk assign shifts",
    dependencies=[Depends(get_current_admin)],
)
def bulk_assign_shifts(
    assignments: list[dict] = Body(..., description="List of {employee_id, shift_id, date}"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    return attendance_service.bulk_assign_shifts(db, assignments, assigned_by=current_user.id)


@attendance_router.delete(
    "/rosters/{roster_id}",
    response_model=SuccessResponse,
    summary="Delete a shift roster",
    dependencies=[Depends(get_current_admin)],
)
def delete_shift_roster(roster_id: int, db: Session = Depends(get_db)):
    attendance_service.delete_shift_roster(db, roster_id)
    return {"message": f"Shift roster {roster_id} has been deleted successfully."}


# ════════════════════════════════════════════════════════════════════════════
# MY ATTENDANCE
# ════════════════════════════════════════════════════════════════════════════

@attendance_router.get(
    "/my-attendance",
    summary="Get current user's attendance records",
)
def my_attendance(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    page:     int = Query(1,  ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
):
    return attendance_service.get_my_attendance(db, current_user.id, page, per_page)


@attendance_router.get(
    "/employee/{employee_id}/summary",
    summary="Monthly attendance summary for an employee",
)
def employee_attendance_summary(
    employee_id: int,
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    year:  int = Query(..., ge=2020, description="Year"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_employee_summary(db, employee_id, month, year)


@attendance_router.get(
    "/employee/{employee_id}/history",
    summary="Attendance history for an employee",
)
def employee_attendance_history(
    employee_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    page:      int           = Query(1,  ge=1, description="Page number"),
    per_page:  int           = Query(20, ge=1, le=100, description="Results per page"),
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to:   Optional[date] = Query(None, description="Filter to date"),
):
    return attendance_service.get_employee_history(db, employee_id, page, per_page, date_from, date_to)


@attendance_router.get(
    "/employee/{employee_id}/score",
    summary="Attendance score for an employee",
)
def employee_attendance_score(
    employee_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_employee_score(db, employee_id)


# ════════════════════════════════════════════════════════════════════════════
# BIOMETRIC INTEGRATION
# ════════════════════════════════════════════════════════════════════════════

@attendance_router.get(
    "/biometric/devices",
    response_model=list[BiometricDeviceResponse],
    summary="List biometric devices",
)
def list_biometric_devices(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_biometric_devices(db)


@attendance_router.post(
    "/biometric/devices",
    response_model=BiometricDeviceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a biometric device",
    dependencies=[Depends(get_current_admin)],
)
def register_biometric_device(data: BiometricDeviceCreate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return attendance_service.register_biometric_device(db, data, created_by=current_user.id)


@attendance_router.put(
    "/biometric/devices/{device_id}",
    response_model=BiometricDeviceResponse,
    summary="Update a biometric device",
    dependencies=[Depends(get_current_admin)],
)
def update_biometric_device(device_id: int, data: BiometricDeviceUpdate, db: Session = Depends(get_db)):
    return attendance_service.update_biometric_device(db, device_id, data)


@attendance_router.delete(
    "/biometric/devices/{device_id}",
    response_model=SuccessResponse,
    summary="Delete a biometric device",
    dependencies=[Depends(get_current_admin)],
)
def delete_biometric_device(device_id: int, db: Session = Depends(get_db)):
    attendance_service.delete_biometric_device(db, device_id)
    return {"message": f"Biometric device {device_id} has been deleted successfully."}


@attendance_router.post(
    "/biometric/sync",
    summary="Sync logs from a biometric device",
    dependencies=[Depends(get_current_admin)],
)
def sync_biometric_logs(
    device_id: int = Body(..., embed=True),
    logs: list[dict] = Body(..., embed=True, description="List of {employee_id, punch_time}"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    return attendance_service.sync_biometric_logs(db, device_id, logs, synced_by=current_user.id)


@attendance_router.post(
    "/biometric/import",
    summary="Import biometric logs",
    dependencies=[Depends(get_current_admin)],
)
def import_biometric_logs(
    logs: list[dict] = Body(..., description="List of {employee_id, punch_time}"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    return attendance_service.import_biometric_logs(db, logs, imported_by=current_user.id)


@attendance_router.get(
    "/biometric/device-health/{device_id}",
    summary="Check biometric device health",
)
def biometric_device_health(
    device_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_biometric_device_health(db, device_id)


# ════════════════════════════════════════════════════════════════════════════
# GEOFENCING
# ════════════════════════════════════════════════════════════════════════════

@attendance_router.get(
    "/geofencing",
    response_model=list[GeofenceResponse],
    summary="List geofence locations",
)
def list_geofence_locations(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_geofence_locations(db)


@attendance_router.post(
    "/geofencing",
    response_model=GeofenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a geofence location",
    dependencies=[Depends(get_current_admin)],
)
def create_geofence_location(data: GeofenceCreate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return attendance_service.create_geofence_location(db, data, created_by=current_user.id)


@attendance_router.get(
    "/geofencing/{location_id}",
    response_model=GeofenceResponse,
    summary="Get a geofence location by ID",
)
def get_geofence_location(
    location_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_geofence_location_by_id(db, location_id)


@attendance_router.put(
    "/geofencing/{location_id}",
    response_model=GeofenceResponse,
    summary="Update a geofence location",
    dependencies=[Depends(get_current_admin)],
)
def update_geofence_location(location_id: int, data: GeofenceUpdate, db: Session = Depends(get_db)):
    return attendance_service.update_geofence_location(db, location_id, data)


@attendance_router.delete(
    "/geofencing/{location_id}",
    response_model=SuccessResponse,
    summary="Delete a geofence location",
    dependencies=[Depends(get_current_admin)],
)
def delete_geofence_location(location_id: int, db: Session = Depends(get_db)):
    attendance_service.delete_geofence_location(db, location_id)
    return {"message": f"Geofence location {location_id} has been deleted successfully."}


# ════════════════════════════════════════════════════════════════════════════
# OVERTIME
# ════════════════════════════════════════════════════════════════════════════

@attendance_router.get(
    "/overtime",
    summary="List overtime requests",
)
def list_overtime_requests(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    page:       int                 = Query(1,    ge=1,   description="Page number"),
    per_page:   int                 = Query(20,   ge=1,   le=100, description="Results per page"),
    status:     Optional[OvertimeStatus] = Query(None, description="Filter by status"),
    employee_id: Optional[int]      = Query(None, description="Filter by employee ID"),
    date_from:  Optional[date]      = Query(None, description="Filter from date"),
    date_to:    Optional[date]      = Query(None, description="Filter to date"),
):
    return attendance_service.get_overtime_requests(db, page, per_page, status, employee_id, date_from, date_to)


@attendance_router.post(
    "/overtime",
    response_model=OvertimeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an overtime request",
)
def create_overtime_request(
    data: OvertimeCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return attendance_service.create_overtime_request(db, data, created_by=current_user.id)


@attendance_router.get(
    "/overtime/{ot_id}",
    response_model=OvertimeResponse,
    summary="Get an overtime request by ID",
)
def get_overtime_request(
    ot_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_overtime_request_by_id(db, ot_id)


@attendance_router.put(
    "/overtime/{ot_id}/approve",
    response_model=OvertimeResponse,
    summary="Approve an overtime request",
    dependencies=[Depends(get_current_admin)],
)
def approve_overtime_request(
    ot_id: int,
    hours_approved: Optional[float] = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    return attendance_service.approve_overtime_request(db, ot_id, approved_by=current_user.id, hours_approved=hours_approved)


@attendance_router.put(
    "/overtime/{ot_id}/reject",
    response_model=OvertimeResponse,
    summary="Reject an overtime request",
    dependencies=[Depends(get_current_admin)],
)
def reject_overtime_request(
    ot_id: int,
    rejection_reason: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    return attendance_service.reject_overtime_request(db, ot_id, rejected_by=current_user.id, rejection_reason=rejection_reason)


@attendance_router.get(
    "/overtime/reports",
    summary="Overtime reports",
)
def overtime_reports(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to:   Optional[date] = Query(None, description="Filter to date"),
):
    return attendance_service.get_overtime_reports(db, date_from, date_to)


# ════════════════════════════════════════════════════════════════════════════
# ATTENDANCE EXCEPTIONS
# ════════════════════════════════════════════════════════════════════════════

@attendance_router.get(
    "/exceptions",
    summary="List attendance exceptions",
)
def list_attendance_exceptions(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    page:           int                    = Query(1,    ge=1,   description="Page number"),
    per_page:       int                    = Query(20,   ge=1,   le=100, description="Results per page"),
    status:         Optional[ExceptionStatus] = Query(None, description="Filter by status"),
    exception_type: Optional[ExceptionType]   = Query(None, description="Filter by exception type"),
    employee_id:    Optional[int]          = Query(None, description="Filter by employee ID"),
):
    return attendance_service.get_attendance_exceptions(db, page, per_page, status, exception_type, employee_id)


@attendance_router.post(
    "/exceptions",
    response_model=AttendanceExceptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an attendance exception (auto-detect)",
)
def create_attendance_exception(
    employee_id: int = Body(..., embed=True),
    attendance_record_id: Optional[int] = Body(None, embed=True),
    exception_type: ExceptionType = Body(ExceptionType.ATTENDANCE_VIOLATION, embed=True),
    description: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.create_attendance_exception(db, employee_id, attendance_record_id, exception_type, description)


@attendance_router.put(
    "/exceptions/{exc_id}/resolve",
    response_model=AttendanceExceptionResponse,
    summary="Resolve an attendance exception",
)
def resolve_attendance_exception(
    exc_id: int,
    resolution_notes: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return attendance_service.resolve_attendance_exception(db, exc_id, resolved_by=current_user.id, resolution_notes=resolution_notes)


@attendance_router.put(
    "/exceptions/{exc_id}/escalate",
    response_model=AttendanceExceptionResponse,
    summary="Escalate an attendance exception",
)
def escalate_attendance_exception(
    exc_id: int,
    escalated_to: int = Body(..., embed=True, description="Employee ID to escalate to"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.escalate_attendance_exception(db, exc_id, escalated_to)


@attendance_router.get(
    "/exceptions/{exc_id}",
    response_model=AttendanceExceptionResponse,
    summary="Get an attendance exception by ID",
)
def get_attendance_exception(
    exc_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_attendance_exception_by_id(db, exc_id)


# ════════════════════════════════════════════════════════════════════════════
# HOLIDAYS
# ════════════════════════════════════════════════════════════════════════════

@attendance_router.get(
    "/holidays",
    response_model=list[HolidayResponse],
    summary="List holidays",
)
def list_holidays(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_holidays(db)


@attendance_router.post(
    "/holidays",
    response_model=HolidayResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a holiday",
    dependencies=[Depends(get_current_admin)],
)
def create_holiday(data: HolidayCreate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return attendance_service.create_holiday(db, data, created_by=current_user.id)


@attendance_router.get(
    "/holidays/{holiday_id}",
    response_model=HolidayResponse,
    summary="Get a holiday by ID",
)
def get_holiday(
    holiday_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_holiday_by_id(db, holiday_id)


@attendance_router.put(
    "/holidays/{holiday_id}",
    response_model=HolidayResponse,
    summary="Update a holiday",
    dependencies=[Depends(get_current_admin)],
)
def update_holiday(holiday_id: int, data: HolidayUpdate, db: Session = Depends(get_db)):
    return attendance_service.update_holiday(db, holiday_id, data)


@attendance_router.delete(
    "/holidays/{holiday_id}",
    response_model=SuccessResponse,
    summary="Delete a holiday",
    dependencies=[Depends(get_current_admin)],
)
def delete_holiday(holiday_id: int, db: Session = Depends(get_db)):
    attendance_service.delete_holiday(db, holiday_id)
    return {"message": f"Holiday {holiday_id} has been deleted successfully."}


@attendance_router.post(
    "/holidays/import",
    status_code=status.HTTP_201_CREATED,
    summary="Import holidays in bulk",
    dependencies=[Depends(get_current_admin)],
)
def import_holidays(
    holidays: list[dict] = Body(..., description="List of {name, date, type, is_recurring, description}"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    return attendance_service.import_holidays(db, holidays, created_by=current_user.id)


# ════════════════════════════════════════════════════════════════════════════
# WEEKEND CONFIG
# ════════════════════════════════════════════════════════════════════════════

@attendance_router.get(
    "/weekends",
    response_model=list[WeekendConfigResponse],
    summary="List weekend configurations",
)
def list_weekend_configs(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_weekend_configs(db)


@attendance_router.post(
    "/weekends",
    response_model=WeekendConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a weekend configuration",
    dependencies=[Depends(get_current_admin)],
)
def create_weekend_config(data: WeekendConfigCreate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    return attendance_service.create_weekend_config(db, data, created_by=current_user.id)


@attendance_router.put(
    "/weekends/{config_id}",
    response_model=WeekendConfigResponse,
    summary="Update a weekend configuration",
    dependencies=[Depends(get_current_admin)],
)
def update_weekend_config(config_id: int, data: WeekendConfigCreate, db: Session = Depends(get_db)):
    return attendance_service.update_weekend_config(db, config_id, data)


@attendance_router.delete(
    "/weekends/{config_id}",
    response_model=SuccessResponse,
    summary="Delete a weekend configuration",
    dependencies=[Depends(get_current_admin)],
)
def delete_weekend_config(config_id: int, db: Session = Depends(get_db)):
    attendance_service.delete_weekend_config(db, config_id)
    return {"message": f"Weekend configuration {config_id} has been deleted successfully."}


# ════════════════════════════════════════════════════════════════════════════
# AUDIT LOGS
# ════════════════════════════════════════════════════════════════════════════

@attendance_router.get(
    "/audit-logs",
    summary="List attendance audit logs",
)
def list_audit_logs(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    page:        int           = Query(1,    ge=1,   description="Page number"),
    per_page:    int           = Query(20,   ge=1,   le=100, description="Results per page"),
    action:      Optional[str] = Query(None, description="Filter by action"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
    date_from:   Optional[date] = Query(None, description="Filter from date"),
    date_to:     Optional[date] = Query(None, description="Filter to date"),
):
    return attendance_service.get_audit_logs(db, page, per_page, action, entity_type, employee_id, date_from, date_to)


# ════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ════════════════════════════════════════════════════════════════════════════

@attendance_router.get(
    "/export/csv",
    summary="Export attendance records as CSV",
)
def export_attendance_csv(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    search:      Optional[str]          = Query(None, description="Search filter"),
    status:      Optional[AttendanceStatus] = Query(None, description="Filter by status"),
    department:  Optional[str]          = Query(None, description="Filter by department"),
    date_from:   Optional[date]         = Query(None, description="Filter from date"),
    date_to:     Optional[date]         = Query(None, description="Filter to date"),
    employee_id: Optional[int]          = Query(None, description="Filter by employee ID"),
    sort_by:     Optional[str]          = Query("date", description="Sort field"),
    sort_order:  Optional[str]          = Query("desc", description="Sort direction"),
):
    csv_data = attendance_service.export_attendance_csv(db, search, status, department, date_from, date_to, employee_id, sort_by, sort_order)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance_export.csv"},
    )


@attendance_router.get(
    "/export/excel",
    summary="Export attendance records as Excel",
)
def export_attendance_excel(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    search:      Optional[str]          = Query(None, description="Search filter"),
    status:      Optional[AttendanceStatus] = Query(None, description="Filter by status"),
    department:  Optional[str]          = Query(None, description="Filter by department"),
    date_from:   Optional[date]         = Query(None, description="Filter from date"),
    date_to:     Optional[date]         = Query(None, description="Filter to date"),
    employee_id: Optional[int]          = Query(None, description="Filter by employee ID"),
    sort_by:     Optional[str]          = Query("date", description="Sort field"),
    sort_order:  Optional[str]          = Query("desc", description="Sort direction"),
):
    xlsx_data = attendance_service.export_attendance_excel(db, search, status, department, date_from, date_to, employee_id, sort_by, sort_order)
    return Response(
        content=xlsx_data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=attendance_export.xlsx"},
    )


@attendance_router.get(
    "/export/reports/csv",
    summary="Export report data as CSV",
)
def export_report_csv(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    report_type: str = Query(..., description="Report type (daily, monthly, department, etc.)"),
    date_from:   Optional[date] = Query(None, description="Filter from date"),
    date_to:     Optional[date] = Query(None, description="Filter to date"),
):
    csv_data = attendance_service.export_report_csv(db, report_type, date_from, date_to)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={report_type}_report.csv"},
    )


@attendance_router.get(
    "/export/reports/excel",
    summary="Export report data as Excel",
)
def export_report_excel(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    report_type: str = Query(..., description="Report type (daily, monthly, department, etc.)"),
    date_from:   Optional[date] = Query(None, description="Filter from date"),
    date_to:     Optional[date] = Query(None, description="Filter to date"),
):
    xlsx_data = attendance_service.export_report_excel(db, report_type, date_from, date_to)
    return Response(
        content=xlsx_data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={report_type}_report.xlsx"},
    )


# ════════════════════════════════════════════════════════════════════════════
# REPORTS
# ════════════════════════════════════════════════════════════════════════════

@attendance_router.get(
    "/reports/daily",
    summary="Daily attendance report",
)
def daily_report(
    date_filter: Optional[date] = Query(None, alias="date", description="Date for the report"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_daily_report(db, date_filter)


@attendance_router.get(
    "/reports/monthly",
    summary="Monthly attendance report",
)
def monthly_report(
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    year:  int = Query(..., ge=2020, description="Year"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_monthly_report(db, month, year)


@attendance_router.get(
    "/reports/department",
    summary="Department-wise attendance report",
)
def department_report(
    department_name: Optional[str] = Query(None, description="Filter by department name"),
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to:   Optional[date] = Query(None, description="Filter to date"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_department_report(db, department_name, date_from, date_to)


@attendance_router.get(
    "/reports/shift",
    summary="Shift attendance report",
)
def shift_report(
    shift_id: Optional[int] = Query(None, description="Filter by shift ID"),
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to:   Optional[date] = Query(None, description="Filter to date"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_shift_report(db, shift_id, date_from, date_to)


@attendance_router.get(
    "/reports/late-arrivals",
    summary="Late arrivals report",
)
def late_arrival_report(
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to:   Optional[date] = Query(None, description="Filter to date"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_late_arrival_report(db, date_from, date_to)


@attendance_router.get(
    "/reports/overtime",
    summary="Overtime report",
)
def overtime_report(
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to:   Optional[date] = Query(None, description="Filter to date"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_overtime_report_data(db, date_from, date_to)


@attendance_router.get(
    "/reports/absentee",
    summary="Absentee report",
)
def absentee_report(
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to:   Optional[date] = Query(None, description="Filter to date"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_absentee_report(db, date_from, date_to)


@attendance_router.get(
    "/reports/compliance",
    summary="Compliance report",
)
def compliance_report(
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to:   Optional[date] = Query(None, description="Filter to date"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_compliance_report(db, date_from, date_to)


# ════════════════════════════════════════════════════════════════════════════
# ANALYTICS
# ════════════════════════════════════════════════════════════════════════════

@attendance_router.get(
    "/analytics/trends",
    summary="Attendance trends data",
)
def attendance_trends(
    months: int = Query(6, ge=1, le=24, description="Number of months to analyze"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_attendance_trends(db, months)


@attendance_router.get(
    "/analytics/department",
    summary="Department analysis",
)
def department_analysis(
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to:   Optional[date] = Query(None, description="Filter to date"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_department_analysis(db, date_from, date_to)


@attendance_router.get(
    "/analytics/overtime",
    summary="Overtime analytics",
)
def overtime_analytics(
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to:   Optional[date] = Query(None, description="Filter to date"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_overtime_analytics(db, date_from, date_to)


@attendance_router.get(
    "/analytics/shift-efficiency",
    summary="Shift efficiency analytics",
)
def shift_efficiency(
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to:   Optional[date] = Query(None, description="Filter to date"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return attendance_service.get_shift_efficiency(db, date_from, date_to)
