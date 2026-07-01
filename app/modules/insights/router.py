"""
modules/insights/router.py
--------------------------
HTTP endpoints for the Zoiko Insights module.

  POST   /insights/reports              → Create report definition
  GET    /insights/reports              → List reports
  GET    /insights/reports/{id}         → Get report
  PUT    /insights/reports/{id}         → Update report
  POST   /insights/reports/{id}/run     → Execute a report
  GET    /insights/reports/{id}/runs    → List past runs
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user, get_current_org_admin
from app.modules.insights import service
from app.modules.insights.schemas import (
    ReportCreate, ReportUpdate, ReportResponse,
    ReportRunCreate, ReportRunResponse, SuccessResponse,
)

insights_router = APIRouter(prefix="/insights", tags=["📊 Insights Module"])


@insights_router.post("/reports", response_model=ReportResponse, summary="Create a report definition", dependencies=[Depends(get_current_org_admin)])
def create_report(data: ReportCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return service.create_report(db, current_user.id, data, current_user.organization_id)


@insights_router.get("/reports", response_model=list[ReportResponse], summary="List all reports")
def list_reports(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return service.get_all_reports(db, current_user.organization_id)


@insights_router.get("/reports/{report_id}", response_model=ReportResponse, summary="Get a report")
def get_report(report_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return service.get_report_by_id(db, report_id, current_user.organization_id)


@insights_router.put("/reports/{report_id}", response_model=ReportResponse, summary="Update a report", dependencies=[Depends(get_current_org_admin)])
def update_report(report_id: int, data: ReportUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return service.update_report(db, report_id, data, current_user.organization_id)


@insights_router.post("/reports/{report_id}/run", response_model=ReportRunResponse, summary="Run a report")
def run_report(report_id: int, data: ReportRunCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return service.run_report(db, report_id, current_user.id, data, current_user.organization_id)


@insights_router.get("/reports/{report_id}/runs", response_model=list[ReportRunResponse], summary="List past report runs")
def list_runs(report_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return service.get_report_runs(db, report_id, current_user.organization_id)
