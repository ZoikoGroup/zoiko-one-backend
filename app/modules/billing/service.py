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


def _apply_org_filter(query, organization_id: int = None):
    if organization_id:
        return query.filter(Client.organization_id == organization_id)
    return query


def _apply_invoice_org_filter(query, organization_id: int = None):
    if organization_id:
        return query.filter(Invoice.organization_id == organization_id)
    return query


def _next_invoice_number(db: Session, organization_id: int = None) -> str:
    q = db.query(Invoice)
    if organization_id:
        q = q.filter(Invoice.organization_id == organization_id)
    count = q.count()
    return f"INV-{str(count + 1).zfill(5)}"


# ── Client ────────────────────────────────────────────────────────────────────

def create_client(db: Session, data: ClientCreate, organization_id: int = None) -> Client:
    client = Client(**data.model_dump())
    if organization_id:
        client.organization_id = organization_id
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def get_all_clients(db: Session, organization_id: int = None) -> List[Client]:
    query = db.query(Client).filter(Client.is_active == True)
    return _apply_org_filter(query, organization_id).all()


def get_client_by_id(db: Session, client_id: int, organization_id: int = None) -> Client:
    query = db.query(Client).filter(Client.id == client_id)
    query = _apply_org_filter(query, organization_id)
    c = query.first()
    if not c:
        raise NotFoundException(f"Client {client_id} not found.")
    return c


def update_client(db: Session, client_id: int, data: ClientUpdate, organization_id: int = None) -> Client:
    c = get_client_by_id(db, client_id, organization_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(c, field, value)
    db.commit()
    db.refresh(c)
    return c


# ── Invoice ───────────────────────────────────────────────────────────────────

def create_invoice(db: Session, created_by: int, data: InvoiceCreate, organization_id: int = None) -> Invoice:
    # Verify client belongs to organization
    client = get_client_by_id(db, data.client_id, organization_id)
    
    subtotal = sum(item.quantity * item.unit_price for item in data.line_items)
    invoice = Invoice(
        invoice_number=_next_invoice_number(db, organization_id),
        client_id=data.client_id,
        issue_date=data.issue_date,
        due_date=data.due_date,
        subtotal=subtotal,
        total_amount=subtotal,
        notes=data.notes,
        created_by=created_by,
    )
    if organization_id:
        invoice.organization_id = organization_id
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


def get_all_invoices(db: Session, client_id: Optional[int] = None, organization_id: int = None) -> List[Invoice]:
    query = db.query(Invoice)
    query = _apply_invoice_org_filter(query, organization_id)
    if client_id:
        query = query.filter(Invoice.client_id == client_id)
    return query.order_by(Invoice.created_at.desc()).all()


def get_invoice_by_id(db: Session, invoice_id: int, organization_id: int = None) -> Invoice:
    query = db.query(Invoice).filter(Invoice.id == invoice_id)
    query = _apply_invoice_org_filter(query, organization_id)
    inv = query.first()
    if not inv:
        raise NotFoundException(f"Invoice {invoice_id} not found.")
    return inv


def update_invoice(db: Session, invoice_id: int, data: InvoiceUpdate, organization_id: int = None) -> Invoice:
    inv = get_invoice_by_id(db, invoice_id, organization_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(inv, field, value)
    db.commit()
    db.refresh(inv)
    return inv
