"""
modules/billing/router.py
-------------------------
HTTP endpoints for the Zoiko Billing module.

  CLIENTS
    POST   /billing/clients         → Create client
    GET    /billing/clients         → List clients
    GET    /billing/clients/{id}    → Get client
    PUT    /billing/clients/{id}    → Update client

  INVOICES
    POST   /billing/invoices        → Create invoice
    GET    /billing/invoices        → List invoices
    GET    /billing/invoices/{id}   → Get invoice
    PUT    /billing/invoices/{id}   → Update invoice status
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user, get_current_org_admin
from app.modules.billing import service
from app.modules.billing.schemas import (
    ClientCreate, ClientUpdate, ClientResponse,
    InvoiceCreate, InvoiceUpdate, InvoiceResponse,
    SuccessResponse,
)

billing_router = APIRouter(prefix="/billing", tags=["🧾 Billing Module"])


@billing_router.post("/clients", response_model=ClientResponse, summary="Create a client", dependencies=[Depends(get_current_org_admin)])
def create_client(data: ClientCreate, db: Session = Depends(get_db)):
    return service.create_client(db, data)


@billing_router.get("/clients", response_model=list[ClientResponse], summary="List all clients")
def list_clients(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_all_clients(db)


@billing_router.get("/clients/{client_id}", response_model=ClientResponse, summary="Get a client")
def get_client(client_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_client_by_id(db, client_id)


@billing_router.put("/clients/{client_id}", response_model=ClientResponse, summary="Update a client", dependencies=[Depends(get_current_org_admin)])
def update_client(client_id: int, data: ClientUpdate, db: Session = Depends(get_db)):
    return service.update_client(db, client_id, data)


@billing_router.post("/invoices", response_model=InvoiceResponse, summary="Create an invoice", dependencies=[Depends(get_current_org_admin)])
def create_invoice(data: InvoiceCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return service.create_invoice(db, current_user.id, data)


@billing_router.get("/invoices", response_model=list[InvoiceResponse], summary="List invoices")
def list_invoices(db: Session = Depends(get_db), _=Depends(get_current_user), client_id: Optional[int] = Query(None)):
    return service.get_all_invoices(db, client_id)


@billing_router.get("/invoices/{invoice_id}", response_model=InvoiceResponse, summary="Get an invoice")
def get_invoice(invoice_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_invoice_by_id(db, invoice_id)


@billing_router.put("/invoices/{invoice_id}", response_model=InvoiceResponse, summary="Update invoice status", dependencies=[Depends(get_current_org_admin)])
def update_invoice(invoice_id: int, data: InvoiceUpdate, db: Session = Depends(get_db)):
    return service.update_invoice(db, invoice_id, data)
