"""
modules/billing/schemas.py
--------------------------
Pydantic schemas for the Zoiko Billing module.
"""

from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, EmailStr
from app.modules.billing.models import InvoiceStatus


class ClientCreate(BaseModel):
    name:    str
    email:   Optional[str] = None
    phone:   Optional[str] = None
    address: Optional[str] = None


class ClientUpdate(BaseModel):
    name:      Optional[str] = None
    email:     Optional[str] = None
    phone:     Optional[str] = None
    address:   Optional[str] = None
    is_active: Optional[bool] = None


class ClientResponse(BaseModel):
    id:         int
    name:       str
    email:      Optional[str]
    phone:      Optional[str]
    address:    Optional[str]
    is_active:  bool
    created_at: datetime

    class Config:
        from_attributes = True


class InvoiceLineCreate(BaseModel):
    description: str
    quantity:    Decimal = Decimal("1")
    unit_price:  Decimal


class InvoiceLineResponse(BaseModel):
    id:          int
    description: str
    quantity:    Decimal
    unit_price:  Decimal
    total:       Decimal

    class Config:
        from_attributes = True


class InvoiceCreate(BaseModel):
    client_id:      int
    issue_date:     date
    due_date:       date
    line_items:     List[InvoiceLineCreate]
    notes:          Optional[str] = None


class InvoiceUpdate(BaseModel):
    status:     Optional[InvoiceStatus] = None
    due_date:   Optional[date] = None
    notes:      Optional[str] = None


class InvoiceResponse(BaseModel):
    id:             int
    invoice_number: str
    client_id:      int
    status:         InvoiceStatus
    issue_date:     date
    due_date:       date
    subtotal:       Decimal
    tax_amount:     Decimal
    total_amount:   Decimal
    notes:          Optional[str]
    line_items:     List[InvoiceLineResponse] = []
    created_at:     datetime

    class Config:
        from_attributes = True


class SuccessResponse(BaseModel):
    message: str
