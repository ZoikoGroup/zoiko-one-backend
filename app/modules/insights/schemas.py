"""
modules/insights/schemas.py
---------------------------
Pydantic schemas for the Zoiko Insights module.
"""

from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, ConfigDict
from app.modules.insights.models import ReportType, ReportFormat


class ReportCreate(BaseModel):
    name:        str
    description: Optional[str] = None
    report_type: ReportType
    filters:     Optional[Dict[str, Any]] = None


class ReportUpdate(BaseModel):
    name:        Optional[str] = None
    description: Optional[str] = None
    filters:     Optional[Dict[str, Any]] = None
    is_active:   Optional[bool] = None


class ReportResponse(BaseModel):
    id:          int
    name:        str
    description: Optional[str]
    report_type: ReportType
    filters:     Optional[Dict[str, Any]]
    is_active:   bool
    created_at:  datetime

    model_config = ConfigDict(from_attributes=True)


class ReportRunCreate(BaseModel):
    format: ReportFormat = ReportFormat.JSON


class ReportRunResponse(BaseModel):
    id:          int
    report_id:   int
    format:      ReportFormat
    result_url:  Optional[str]
    row_count:   Optional[int]
    duration_ms: Optional[int]
    ran_at:      datetime

    model_config = ConfigDict(from_attributes=True)


class SuccessResponse(BaseModel):
    message: str
