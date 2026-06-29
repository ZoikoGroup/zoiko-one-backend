"""
modules/comply/router.py
------------------------
HTTP endpoints for the Zoiko Comply module.

  POST   /comply/policies              → Create policy
  GET    /comply/policies              → List policies
  GET    /comply/policies/{id}         → Get policy detail
  PUT    /comply/policies/{id}         → Update policy
  POST   /comply/policies/{id}/ack     → Acknowledge a policy
  GET    /comply/policies/{id}/acks    → List acknowledgements
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user, get_current_org_admin
from app.modules.comply import service
from app.modules.comply.schemas import (
    PolicyCreate, PolicyUpdate, PolicyResponse, PolicyDetailResponse,
    AcknowledgementResponse, SuccessResponse,
)

comply_router = APIRouter(prefix="/comply", tags=["📋 Comply Module"])


@comply_router.post("/policies", response_model=PolicyResponse, summary="Create a compliance policy", dependencies=[Depends(get_current_org_admin)])
def create_policy(data: PolicyCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return service.create_policy(db, current_user.id, data, current_user.organization_id)


@comply_router.get("/policies", response_model=list[PolicyResponse], summary="List policies")
def list_policies(db: Session = Depends(get_db), current_user=Depends(get_current_user), category: Optional[str] = Query(None)):
    return service.get_all_policies(db, category, current_user.organization_id)


@comply_router.get("/policies/{policy_id}", response_model=PolicyDetailResponse, summary="Get policy detail")
def get_policy(policy_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return service.get_policy_by_id(db, policy_id, current_user.organization_id)


@comply_router.put("/policies/{policy_id}", response_model=PolicyResponse, summary="Update a policy", dependencies=[Depends(get_current_org_admin)])
def update_policy(policy_id: int, data: PolicyUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return service.update_policy(db, policy_id, data, current_user.organization_id)


@comply_router.post("/policies/{policy_id}/ack", response_model=AcknowledgementResponse, summary="Acknowledge a policy")
def acknowledge(policy_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return service.acknowledge_policy(db, policy_id, current_user.id, current_user.organization_id)


@comply_router.get("/policies/{policy_id}/acks", response_model=list[AcknowledgementResponse], summary="List acknowledgements", dependencies=[Depends(get_current_org_admin)])
def list_acks(policy_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return service.get_acknowledgements(db, policy_id, current_user.organization_id)
