"""
modules/insights/service.py
---------------------------
Business logic for the Zoiko Insights module.
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.modules.insights.models import Report, ReportRun
from app.modules.insights.schemas import ReportCreate, ReportUpdate, ReportRunCreate
from app.core.exceptions import NotFoundException


def _apply_org_filter(query, organization_id: int = None):
    if organization_id:
        return query.filter(Report.organization_id == organization_id)
    return query


def _apply_run_org_filter(query, organization_id: int = None):
    if organization_id:
        return query.filter(ReportRun.organization_id == organization_id)
    return query


def create_report(db: Session, created_by: int, data: ReportCreate, organization_id: int = None) -> Report:
    report = Report(created_by=created_by, **data.model_dump())
    if organization_id:
        report.organization_id = organization_id
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_all_reports(db: Session, organization_id: int = None) -> List[Report]:
    query = db.query(Report).filter(Report.is_active == True).order_by(Report.created_at.desc())
    return _apply_org_filter(query, organization_id).all()


def get_report_by_id(db: Session, report_id: int, organization_id: int = None) -> Report:
    query = db.query(Report).filter(Report.id == report_id)
    query = _apply_org_filter(query, organization_id)
    r = query.first()
    if not r:
        raise NotFoundException(f"Report {report_id} not found.")
    return r


def update_report(db: Session, report_id: int, data: ReportUpdate, organization_id: int = None) -> Report:
    r = get_report_by_id(db, report_id, organization_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(r, field, value)
    db.commit()
    db.refresh(r)
    return r


def run_report(db: Session, report_id: int, run_by: int, data: ReportRunCreate, organization_id: int = None) -> ReportRun:
    get_report_by_id(db, report_id, organization_id)  # ensure report exists
    run = ReportRun(
        report_id=report_id,
        run_by=run_by,
        format=data.format,
    )
    if organization_id:
        run.organization_id = organization_id
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def get_report_runs(db: Session, report_id: int, organization_id: int = None) -> List[ReportRun]:
    query = db.query(ReportRun).filter(ReportRun.report_id == report_id).order_by(ReportRun.ran_at.desc())
    return _apply_run_org_filter(query, organization_id).all()
