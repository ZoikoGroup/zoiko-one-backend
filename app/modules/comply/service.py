"""
modules/comply/service.py
-------------------------
Business logic for the Zoiko Comply module.
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.modules.comply.models import CompliancePolicy, PolicyAcknowledgement, PolicyStatus
from app.modules.comply.schemas import PolicyCreate, PolicyUpdate
from app.core.exceptions import NotFoundException


def _apply_org_filter(query, organization_id: int = None):
    if organization_id:
        return query.filter(CompliancePolicy.organization_id == organization_id)
    return query


def _apply_ack_org_filter(query, organization_id: int = None):
    if organization_id:
        return query.filter(PolicyAcknowledgement.organization_id == organization_id)
    return query


def create_policy(db: Session, created_by: int, data: PolicyCreate, organization_id: int = None) -> CompliancePolicy:
    policy = CompliancePolicy(created_by=created_by, **data.model_dump())
    if organization_id:
        policy.organization_id = organization_id
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def get_all_policies(db: Session, category: Optional[str] = None, organization_id: int = None) -> List[CompliancePolicy]:
    query = db.query(CompliancePolicy)
    query = _apply_org_filter(query, organization_id)
    if category:
        query = query.filter(CompliancePolicy.category == category)
    return query.order_by(CompliancePolicy.created_at.desc()).all()


def get_policy_by_id(db: Session, policy_id: int, organization_id: int = None) -> CompliancePolicy:
    query = db.query(CompliancePolicy).filter(CompliancePolicy.id == policy_id)
    query = _apply_org_filter(query, organization_id)
    p = query.first()
    if not p:
        raise NotFoundException(f"Policy {policy_id} not found.")
    return p


def update_policy(db: Session, policy_id: int, data: PolicyUpdate, organization_id: int = None) -> CompliancePolicy:
    p = get_policy_by_id(db, policy_id, organization_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(p, field, value)
    db.commit()
    db.refresh(p)
    return p


def acknowledge_policy(db: Session, policy_id: int, employee_id: int, organization_id: int = None) -> PolicyAcknowledgement:
    get_policy_by_id(db, policy_id, organization_id)  # ensure policy exists
    ack = PolicyAcknowledgement(policy_id=policy_id, employee_id=employee_id)
    if organization_id:
        ack.organization_id = organization_id
    db.add(ack)
    db.commit()
    db.refresh(ack)
    return ack


def get_acknowledgements(db: Session, policy_id: int, organization_id: int = None) -> List[PolicyAcknowledgement]:
    query = db.query(PolicyAcknowledgement).filter(PolicyAcknowledgement.policy_id == policy_id)
    query = _apply_ack_org_filter(query, organization_id)
    return query.all()
