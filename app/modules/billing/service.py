"""
modules/billing/service.py
--------------------------
Business logic for the Zoiko Billing module.
"""

from typing import List, Optional
from decimal import Decimal
from sqlalchemy.orm import Session

from app.modules.billing.models import Client, Invoice, InvoiceLine, InvoiceStatus
from app.modules.billing.schemas import ClientCreate, ClientUpdate, InvoiceCreate, InvoiceUpdate
from app.core.exceptions import NotFoundException


def _next_invoice_number(db: Session) -> str:
    count = db.query(Invoice).count()
    return f"INV-{str(count + 1).zfill(5)}"


# ── Client ────────────────────────────────────────────────────────────────────

def create_client(db: Session, data: ClientCreate) -> Client:
    client = Client(**data.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def get_all_clients(db: Session) -> List[Client]:
    return db.query(Client).filter(Client.is_active == True).all()


def get_client_by_id(db: Session, client_id: int) -> Client:
    c = db.query(Client).filter(Client.id == client_id).first()
    if not c:
        raise NotFoundException(f"Client {client_id} not found.")
    return c


def update_client(db: Session, client_id: int, data: ClientUpdate) -> Client:
    c = get_client_by_id(db, client_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(c, field, value)
    db.commit()
    db.refresh(c)
    return c


# ── Invoice ───────────────────────────────────────────────────────────────────

def create_invoice(db: Session, created_by: int, data: InvoiceCreate) -> Invoice:
    subtotal = sum(item.quantity * item.unit_price for item in data.line_items)
    invoice = Invoice(
        invoice_number=_next_invoice_number(db),
        client_id=data.client_id,
        issue_date=data.issue_date,
        due_date=data.due_date,
        subtotal=subtotal,
        total_amount=subtotal,
        notes=data.notes,
        created_by=created_by,
    )
    db.add(invoice)
    db.flush()
    for item in data.line_items:
        line = InvoiceLine(
            invoice_id=invoice.id,
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total=item.quantity * item.unit_price,
        )
        db.add(line)
    db.commit()
    db.refresh(invoice)
    return invoice


def get_all_invoices(db: Session, client_id: Optional[int] = None) -> List[Invoice]:
    q = db.query(Invoice)
    if client_id:
        q = q.filter(Invoice.client_id == client_id)
    return q.order_by(Invoice.created_at.desc()).all()


def get_invoice_by_id(db: Session, invoice_id: int) -> Invoice:
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise NotFoundException(f"Invoice {invoice_id} not found.")
    return inv


def update_invoice(db: Session, invoice_id: int, data: InvoiceUpdate) -> Invoice:
    inv = get_invoice_by_id(db, invoice_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(inv, field, value)
    db.commit()
    db.refresh(inv)
    return inv
