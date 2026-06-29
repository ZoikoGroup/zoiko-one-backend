"""
modules/comply/models.py
------------------------
SQLAlchemy ORM models for the Zoiko Comply module.

Tables:
  - CompliancePolicy  → company policies and procedures
  - PolicyAcknowledgement → employee acknowledgement of policies
"""

import enum
from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class PolicyStatus(str, enum.Enum):
    DRAFT     = "draft"
    ACTIVE    = "active"
    ARCHIVED  = "archived"


class PolicyCategory(str, enum.Enum):
    HR          = "hr"
    SECURITY    = "security"
    FINANCE     = "finance"
    OPERATIONS  = "operations"
    LEGAL       = "legal"
    OTHER       = "other"


class CompliancePolicy(Base):
    __tablename__ = "compliance_policies"

    id              = Column(Integer, primary_key=True, index=True)
    title           = Column(String(300), nullable=False)
    category        = Column(SQLEnum(PolicyCategory), nullable=False)
    status          = Column(SQLEnum(PolicyStatus), default=PolicyStatus.DRAFT)
    content         = Column(Text, nullable=False)
    version         = Column(String(20), default="1.0")
    effective_date  = Column(Date, nullable=True)
    review_date     = Column(Date, nullable=True)
    created_by      = Column(Integer, ForeignKey("employees.id"), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    acknowledgements = relationship("PolicyAcknowledgement", back_populates="policy")

    def __repr__(self):
        return f"<CompliancePolicy id={self.id} title={self.title}>"


class PolicyAcknowledgement(Base):
    __tablename__ = "policy_acknowledgements"

    id              = Column(Integer, primary_key=True, index=True)
    policy_id       = Column(Integer, ForeignKey("compliance_policies.id"), nullable=False)
    employee_id     = Column(Integer, ForeignKey("employees.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    acknowledged_at = Column(DateTime(timezone=True), server_default=func.now())
    ip_address      = Column(String(50), nullable=True)

    policy          = relationship("CompliancePolicy", back_populates="acknowledgements")

    def __repr__(self):
        return f"<PolicyAcknowledgement policy={self.policy_id} employee={self.employee_id}>"
