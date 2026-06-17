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


def create_policy(db: Session, created_by: int, data: PolicyCreate) -> CompliancePolicy:
    policy = CompliancePolicy(created_by=created_by, **data.model_dump())
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def get_all_policies(db: Session, category: Optional[str] = None) -> List[CompliancePolicy]:
    q = db.query(CompliancePolicy)
    if category:
        q = q.filter(CompliancePolicy.category == category)
    return q.order_by(CompliancePolicy.created_at.desc()).all()


def get_policy_by_id(db: Session, policy_id: int) -> CompliancePolicy:
    p = db.query(CompliancePolicy).filter(CompliancePolicy.id == policy_id).first()
    if not p:
        raise NotFoundException(f"Policy {policy_id} not found.")
    return p


def update_policy(db: Session, policy_id: int, data: PolicyUpdate) -> CompliancePolicy:
    p = get_policy_by_id(db, policy_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(p, field, value)
    db.commit()
    db.refresh(p)
    return p


def acknowledge_policy(db: Session, policy_id: int, employee_id: int) -> PolicyAcknowledgement:
    get_policy_by_id(db, policy_id)  # ensure policy exists
    ack = PolicyAcknowledgement(policy_id=policy_id, employee_id=employee_id)
    db.add(ack)
    db.commit()
    db.refresh(ack)
    return ack


def get_acknowledgements(db: Session, policy_id: int) -> List[PolicyAcknowledgement]:
    return db.query(PolicyAcknowledgement).filter(PolicyAcknowledgement.policy_id == policy_id).all()
