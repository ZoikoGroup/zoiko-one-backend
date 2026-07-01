"""
modules/comply/schemas.py
-------------------------
Pydantic schemas for the Zoiko Comply module.
"""

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.modules.comply.models import PolicyStatus, PolicyCategory


class PolicyCreate(BaseModel):
    title:          str
    category:       PolicyCategory
    content:        str
    version:        Optional[str] = "1.0"
    effective_date: Optional[date] = None
    review_date:    Optional[date] = None


class PolicyUpdate(BaseModel):
    title:          Optional[str] = None
    content:        Optional[str] = None
    status:         Optional[PolicyStatus] = None
    version:        Optional[str] = None
    effective_date: Optional[date] = None
    review_date:    Optional[date] = None


class PolicyResponse(BaseModel):
    id:             int
    title:          str
    category:       PolicyCategory
    status:         PolicyStatus
    version:        str
    effective_date: Optional[date]
    review_date:    Optional[date]
    created_at:     datetime

    model_config = ConfigDict(from_attributes=True)


class PolicyDetailResponse(PolicyResponse):
    content: str


class AcknowledgementResponse(BaseModel):
    id:              int
    policy_id:       int
    employee_id:     int
    acknowledged_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SuccessResponse(BaseModel):
    message: str
