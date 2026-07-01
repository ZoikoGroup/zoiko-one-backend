"""
modules/payroll/schemas.py
--------------------------
Pydantic schemas for the Zoiko Payroll module.
"""

from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from app.modules.payroll.models import PayrollStatus


class PayrollRunCreate(BaseModel):
    period_label: str
    period_start: date
    period_end:   date
    notes:        Optional[str] = None


class PayrollRunUpdate(BaseModel):
    status:      Optional[PayrollStatus] = None
    notes:       Optional[str] = None


class PayrollRunResponse(BaseModel):
    id:           int
    period_label: str
    period_start: date
    period_end:   date
    status:       PayrollStatus
    total_gross:  Decimal
    total_net:    Decimal
    notes:        Optional[str]
    created_at:   datetime

    model_config = ConfigDict(from_attributes=True)


class PayslipItemCreate(BaseModel):
    employee_id:    int
    basic_salary:   Decimal
    allowances:     Optional[Decimal] = Decimal("0")
    deductions:     Optional[Decimal] = Decimal("0")
    tax:            Optional[Decimal] = Decimal("0")
    notes:          Optional[str] = None


class PayslipItemResponse(BaseModel):
    id:             int
    payroll_run_id: int
    employee_id:    int
    basic_salary:   Decimal
    allowances:     Decimal
    deductions:     Decimal
    tax:            Decimal
    gross_pay:      Decimal
    net_pay:        Decimal
    is_paid:        bool
    paid_at:        Optional[datetime]
    notes:          Optional[str]
    created_at:     datetime

    model_config = ConfigDict(from_attributes=True)


class SuccessResponse(BaseModel):
    message: str
