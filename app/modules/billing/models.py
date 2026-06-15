"""
modules/billing/models.py
-------------------------
SQLAlchemy ORM models for the Zoiko Billing module.

Tables:
  - Client    → external clients/customers
  - Invoice   → invoices issued to clients
  - InvoiceLine → individual line items on an invoice
"""

import enum
from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, Enum as SQLEnum, ForeignKey, Text, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class InvoiceStatus(str, enum.Enum):
    DRAFT       = "draft"
    SENT        = "sent"
    PAID        = "paid"
    OVERDUE     = "overdue"
    CANCELLED   = "cancelled"


class Client(Base):
    __tablename__ = "clients"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(200), nullable=False)
    email         = Column(String(255), unique=True, nullable=True)
    phone         = Column(String(30), nullable=True)
    address       = Column(Text, nullable=True)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())

    invoices      = relationship("Invoice", back_populates="client")

    def __repr__(self):
        return f"<Client id={self.id} name={self.name}>"


class Invoice(Base):
    __tablename__ = "invoices"

    id              = Column(Integer, primary_key=True, index=True)
    invoice_number  = Column(String(50), unique=True, nullable=False)
    client_id       = Column(Integer, ForeignKey("clients.id"), nullable=False)
    status          = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    issue_date      = Column(Date, nullable=False)
    due_date        = Column(Date, nullable=False)
    subtotal        = Column(Numeric(14, 2), default=0)
    tax_amount      = Column(Numeric(14, 2), default=0)
    total_amount    = Column(Numeric(14, 2), default=0)
    notes           = Column(Text, nullable=True)
    created_by      = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    client          = relationship("Client", back_populates="invoices")
    line_items      = relationship("InvoiceLine", back_populates="invoice")

    def __repr__(self):
        return f"<Invoice id={self.id} number={self.invoice_number} status={self.status}>"


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id          = Column(Integer, primary_key=True, index=True)
    invoice_id  = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    description = Column(String(500), nullable=False)
    quantity    = Column(Numeric(10, 2), nullable=False, default=1)
    unit_price  = Column(Numeric(12, 2), nullable=False)
    total       = Column(Numeric(14, 2), nullable=False)

    invoice     = relationship("Invoice", back_populates="line_items")
