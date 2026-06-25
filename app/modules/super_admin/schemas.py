from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

# ── Dashboard ─────────────────────────────────────────────────────────────────
class DashboardStatsResponse(BaseModel):
    total_organizations: int = 0
    active_organizations: int = 0
    trial_organizations: int = 0
    suspended_organizations: int = 0
    total_users: int = 0
    hr_admin_count: int = 0
    employee_count: int = 0
    active_products: int = 0
    platform_stats: dict = {}
    recent_activity: list[dict] = []

# ── Organization ──────────────────────────────────────────────────────────────
class OrganizationResponse(BaseModel):
    id: int
    name: str
    code: str
    is_active: bool
    subscription_plan: str = "free"
    user_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class OrganizationListResponse(BaseModel):
    organizations: list[OrganizationResponse]
    total: int
    page: int
    page_size: int

class OrganizationUpdateRequest(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None

# ── Products ──────────────────────────────────────────────────────────────────
class ProductResponse(BaseModel):
    id: int
    name: str
    code: str
    description: Optional[str] = None
    icon: Optional[str] = None
    status: str
    is_core: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

class OrganizationProductResponse(BaseModel):
    id: int
    organization_id: int
    product_id: int
    product_name: str
    product_code: str
    is_enabled: bool
    enabled_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class OrganizationProductToggleRequest(BaseModel):
    is_enabled: bool

# ── Subscriptions ─────────────────────────────────────────────────────────────
class SubscriptionResponse(BaseModel):
    id: int
    organization_id: int
    organization_name: str
    plan_type: str
    status: str
    start_date: datetime
    end_date: Optional[datetime] = None
    max_users: int
    max_storage_gb: int
    created_at: datetime

    class Config:
        from_attributes = True

class SubscriptionUpdateRequest(BaseModel):
    plan_type: Optional[str] = None
    status: Optional[str] = None
    max_users: Optional[int] = None
    max_storage_gb: Optional[int] = None
    end_date: Optional[datetime] = None

# ── Platform Users ────────────────────────────────────────────────────────────
class PlatformUserResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    organization_id: int
    organization_name: str
    department_name: Optional[str] = None
    job_title: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class PlatformUserListResponse(BaseModel):
    users: list[PlatformUserResponse]
    total: int
    page: int
    page_size: int

# ── Audit Logs ────────────────────────────────────────────────────────────────
class AuditLogResponse(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    performed_by: Optional[int] = None
    performed_by_email: Optional[str] = None
    details: Optional[Any] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AuditLogListResponse(BaseModel):
    logs: list[AuditLogResponse]
    total: int
    page: int
    page_size: int

# ── System Health ─────────────────────────────────────────────────────────────
class SystemHealthResponse(BaseModel):
    id: int
    component: str
    status: str
    message: Optional[str] = None
    response_time_ms: Optional[float] = None
    checked_at: datetime

    class Config:
        from_attributes = True

class SystemHealthSummaryResponse(BaseModel):
    components: list[SystemHealthResponse]
    overall_status: str
    last_checked: Optional[datetime] = None

# ── Platform Settings ─────────────────────────────────────────────────────────
class PlatformSettingResponse(BaseModel):
    id: int
    key: str
    value: Optional[str] = None
    description: Optional[str] = None
    category: str = "general"
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PlatformSettingUpdateRequest(BaseModel):
    value: str
    description: Optional[str] = None

class PlatformSettingCreateRequest(BaseModel):
    key: str
    value: str
    description: Optional[str] = None
    category: str = "general"

# ── Analytics ─────────────────────────────────────────────────────────────────
class AnalyticsResponse(BaseModel):
    organization_growth: list[dict] = []
    user_growth: list[dict] = []
    subscription_distribution: list[dict] = []
    product_adoption: list[dict] = []
    revenue_data: list[dict] = []
