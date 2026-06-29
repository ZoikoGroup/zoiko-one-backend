"""
modules/payroll/service.py
--------------------------
Business logic for the Zoiko Payroll module.
"""

from typing import List, Optional
from decimal import Decimal
from sqlalchemy.orm import Session

from app.modules.payroll.models import PayrollRun, PayslipItem, PayrollStatus
from app.modules.payroll.schemas import PayrollRunCreate, PayrollRunUpdate, PayslipItemCreate
from app.core.exceptions import NotFoundException


def _apply_org_filter(query, organization_id: int = None):
    if organization_id:
        return query.filter(PayrollRun.organization_id == organization_id)
    return query


def _apply_payslip_org_filter(query, organization_id: int = None):
    if organization_id:
        return query.filter(PayslipItem.organization_id == organization_id)
    return query


def create_payroll_run(db: Session, created_by: int, data: PayrollRunCreate, organization_id: int = None) -> PayrollRun:
    run = PayrollRun(created_by=created_by, **data.model_dump())
    if organization_id:
        run.organization_id = organization_id
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def get_payroll_runs(db: Session, organization_id: int = None) -> List[PayrollRun]:
    query = db.query(PayrollRun).order_by(PayrollRun.period_start.desc())
    return _apply_org_filter(query, organization_id).all()


def get_payroll_run_by_id(db: Session, run_id: int, organization_id: int = None) -> PayrollRun:
    query = db.query(PayrollRun).filter(PayrollRun.id == run_id)
    query = _apply_org_filter(query, organization_id)
    run = query.first()
    if not run:
        raise NotFoundException(f"Payroll run {run_id} not found.")
    return run


def update_payroll_run(db: Session, run_id: int, data: PayrollRunUpdate, organization_id: int = None) -> PayrollRun:
    run = get_payroll_run_by_id(db, run_id, organization_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(run, field, value)
    db.commit()
    db.refresh(run)
    return run


def add_payslip_item(db: Session, run_id: int, data: PayslipItemCreate, organization_id: int = None) -> PayslipItem:
    # Verify run exists and belongs to organization
    run = get_payroll_run_by_id(db, run_id, organization_id)
    
    gross = data.basic_salary + (data.allowances or 0)
    net   = gross - (data.deductions or 0) - (data.tax or 0)
    item  = PayslipItem(
        payroll_run_id=run_id,
        gross_pay=gross,
        net_pay=net,
        **data.model_dump(),
    )
    if organization_id:
        item.organization_id = organization_id
    db.add(item)
    # Update totals on the run
    run.total_gross = (run.total_gross or 0) + gross
    run.total_net   = (run.total_net or 0) + net
    db.commit()
    db.refresh(item)
    return item


def get_payslips_for_run(db: Session, run_id: int, organization_id: int = None) -> List[PayslipItem]:
    # Verify run exists and belongs to organization
    get_payroll_run_by_id(db, run_id, organization_id)
    query = db.query(PayslipItem).filter(PayslipItem.payroll_run_id == run_id)
    return _apply_payslip_org_filter(query, organization_id).all()
