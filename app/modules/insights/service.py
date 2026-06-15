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


def create_report(db: Session, created_by: int, data: ReportCreate) -> Report:
    report = Report(created_by=created_by, **data.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_all_reports(db: Session) -> List[Report]:
    return db.query(Report).filter(Report.is_active == True).order_by(Report.created_at.desc()).all()


def get_report_by_id(db: Session, report_id: int) -> Report:
    r = db.query(Report).filter(Report.id == report_id).first()
    if not r:
        raise NotFoundException(f"Report {report_id} not found.")
    return r


def update_report(db: Session, report_id: int, data: ReportUpdate) -> Report:
    r = get_report_by_id(db, report_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(r, field, value)
    db.commit()
    db.refresh(r)
    return r


def run_report(db: Session, report_id: int, run_by: int, data: ReportRunCreate) -> ReportRun:
    get_report_by_id(db, report_id)  # ensure report exists
    run = ReportRun(
        report_id=report_id,
        run_by=run_by,
        format=data.format,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def get_report_runs(db: Session, report_id: int) -> List[ReportRun]:
    return db.query(ReportRun).filter(ReportRun.report_id == report_id).order_by(ReportRun.ran_at.desc()).all()
