"""
modules/payroll/router.py
-------------------------
HTTP endpoints for the Zoiko Payroll module.

  POST   /payroll/runs              → Create payroll run
  GET    /payroll/runs              → List payroll runs
  GET    /payroll/runs/{id}         → Get single run
  PUT    /payroll/runs/{id}         → Update run status
  POST   /payroll/runs/{id}/items   → Add payslip item to run
  GET    /payroll/runs/{id}/items   → List payslips for run
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user, get_current_org_admin
from app.modules.payroll import service
from app.modules.payroll.schemas import (
    PayrollRunCreate, PayrollRunUpdate, PayrollRunResponse,
    PayslipItemCreate, PayslipItemResponse, SuccessResponse,
)

payroll_router = APIRouter(prefix="/payroll", tags=["💳 Payroll Module"])


@payroll_router.post("/runs", response_model=PayrollRunResponse, summary="Create a payroll run", dependencies=[Depends(get_current_org_admin)])
def create_run(
    data: PayrollRunCreate, 
    db: Session = Depends(get_db), 
    current_user=Depends(get_current_user)
):
    return service.create_payroll_run(db, current_user.id, data, current_user.organization_id)


@payroll_router.get("/runs", response_model=list[PayrollRunResponse], summary="List all payroll runs")
def list_runs(
    db: Session = Depends(get_db), 
    current_user=Depends(get_current_user)
):
    return service.get_payroll_runs(db, current_user.organization_id)


@payroll_router.get("/runs/{run_id}", response_model=PayrollRunResponse, summary="Get a payroll run")
def get_run(
    run_id: int, 
    db: Session = Depends(get_db), 
    current_user=Depends(get_current_user)
):
    return service.get_payroll_run_by_id(db, run_id, current_user.organization_id)


@payroll_router.put("/runs/{run_id}", response_model=PayrollRunResponse, summary="Update payroll run status", dependencies=[Depends(get_current_org_admin)])
def update_run(
    run_id: int, 
    data: PayrollRunUpdate, 
    db: Session = Depends(get_db), 
    current_user=Depends(get_current_user)
):
    return service.update_payroll_run(db, run_id, data, current_user.organization_id)


@payroll_router.post("/runs/{run_id}/items", response_model=PayslipItemResponse, summary="Add employee payslip to run", dependencies=[Depends(get_current_org_admin)])
def add_item(
    run_id: int, 
    data: PayslipItemCreate, 
    db: Session = Depends(get_db), 
    current_user=Depends(get_current_user)
):
    return service.add_payslip_item(db, run_id, data, current_user.organization_id)


@payroll_router.get("/runs/{run_id}/items", response_model=list[PayslipItemResponse], summary="List payslips in a run")
def list_items(
    run_id: int, 
    db: Session = Depends(get_db), 
    current_user=Depends(get_current_user)
):
    return service.get_payslips_for_run(db, run_id, current_user.organization_id)
