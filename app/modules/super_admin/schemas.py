from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from datetime import datetime

# ── Dashboard ─────────────────────────────────────────────────────────────────
class DashboardStatsResponse(BaseModel):
    total_organizations: int = 0
    active_organizations: int = 0
    pending_organizations: int = 0
    rejected_organizations: int = 0
    trial_organizations: int = 0
    suspended_organizations: int = 0
    deactivated_organizations: int = 0
    total_users: int = 0
    enabled_users: int = 0
    disabled_users: int = 0
    locked_users: int = 0
    pending_invitations: int = 0
    hr_admin_count: int = 0
    employee_count: int = 0
    active_products: int = 0
    total_revenue: float = 0
    total_storage_gb: float = 0
    storage_used_gb: float = 0
    api_requests_24h: int = 0
    active_sessions: int = 0
    failed_logins_24h: int = 0
    open_support_tickets: int = 0
    unread_notifications: int = 0
    unresolved_security_events: int = 0
    platform_stats: dict = {}
    recent_activity: list[dict] = []
    recent_registrations: list[dict] = []

# ── Organization ──────────────────────────────────────────────────────────────
class OrganizationResponse(BaseModel):
    id: int
    name: str
    code: str
    is_active: bool
    status: str = "pending"
    subscription_plan: str = "FREE"
    user_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class OrganizationListResponse(BaseModel):
    organizations: list[OrganizationResponse]
    total: int
    page: int
    page_size: int

class OrganizationUpdateRequest(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    is_active: Optional[bool] = None
    subscription_plan: Optional[str] = None
    max_users: Optional[int] = None
    max_storage_gb: Optional[int] = None

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

    model_config = ConfigDict(from_attributes=True)

class OrganizationProductResponse(BaseModel):
    id: int
    organization_id: int
    product_id: int
    product_name: str
    product_code: str
    is_enabled: bool
    enabled_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

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

    model_config = ConfigDict(from_attributes=True)

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
    status: str = "active"
    organization_id: int
    organization_name: str
    department_name: Optional[str] = None
    job_title: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PlatformUserListResponse(BaseModel):
    users: list[PlatformUserResponse]
    total: int
    page: int
    page_size: int
    total_organizations: Optional[int] = None
    total_org_admins: Optional[int] = None
    total_hr_admins: Optional[int] = None
    total_managers: Optional[int] = None
    total_employees: Optional[int] = None

class InviteUserRequest(BaseModel):
    email: str
    first_name: str
    last_name: str
    role: str = "employee"
    organization_id: int = 1
    job_title: Optional[str] = None

class ResetPasswordRequest(BaseModel):
    new_password: str

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

    model_config = ConfigDict(from_attributes=True)

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

    model_config = ConfigDict(from_attributes=True)

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

    model_config = ConfigDict(from_attributes=True)

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
    employee_growth: list[dict] = []
    active_users: list[dict] = []
    subscription_distribution: list[dict] = []
    product_adoption: list[dict] = []
    revenue_data: list[dict] = []
    revenue_monthly: list[dict] = []
    storage_data: list[dict] = []
    login_activity: list[dict] = []

# ── Notifications ─────────────────────────────────────────────────────────────
class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    notification_type: str = "info"
    priority: str = "normal"
    is_read: bool = False
    target_org_id: Optional[int] = None
    target_user_id: Optional[int] = None
    created_by: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class NotificationCreateRequest(BaseModel):
    title: str
    message: str
    notification_type: str = "info"
    priority: str = "normal"
    target_org_id: Optional[int] = None
    target_user_id: Optional[int] = None

class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    total: int
    page: int
    page_size: int

# ── Support Tickets ───────────────────────────────────────────────────────────
class SupportTicketResponse(BaseModel):
    id: int
    organization_id: int
    raised_by: int
    raised_by_name: Optional[str] = None
    subject: str
    description: str
    category: str = "general"
    priority: str = "normal"
    status: str = "open"
    assigned_to: Optional[int] = None
    assigned_to_name: Optional[str] = None
    resolution_notes: Optional[str] = None
    organization_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class SupportTicketUpdateRequest(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[int] = None
    priority: Optional[str] = None
    resolution_notes: Optional[str] = None

class SupportTicketListResponse(BaseModel):
    tickets: list[SupportTicketResponse]
    total: int
    page: int
    page_size: int

# ── Security Events ───────────────────────────────────────────────────────────
class SecurityEventResponse(BaseModel):
    id: int
    event_type: str
    severity: str = "info"
    description: Optional[str] = None
    source_ip: Optional[str] = None
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    organization_id: Optional[int] = None
    organization_name: Optional[str] = None
    event_metadata: Optional[dict] = None
    is_resolved: bool = False
    resolved_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SecurityEventResolveRequest(BaseModel):
    resolved_by: int

class SecurityEventListResponse(BaseModel):
    events: list[SecurityEventResponse]
    total: int
    page: int
    page_size: int

# ── Login Activity ────────────────────────────────────────────────────────────
class LoginActivityResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    email: str
    organization_id: Optional[int] = None
    organization_name: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status: str = "success"
    failure_reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class LoginActivityListResponse(BaseModel):
    activities: list[LoginActivityResponse]
    total: int
    page: int
    page_size: int

# ── Revenue / Storage ─────────────────────────────────────────────────────────
class RevenueDataResponse(BaseModel):
    monthly_revenue: list[dict] = []
    total_revenue: float = 0
    revenue_by_plan: list[dict] = []

class StorageDataResponse(BaseModel):
    total_storage_gb: float = 0
    storage_by_org: list[dict] = []
    storage_usage_percentage: float = 0

# ── Create Organization ───────────────────────────────────────────────────────
class OrganizationCreateRequest(BaseModel):
    name: str
    code: str
    is_active: bool = True

# ── Approval Workflow ─────────────────────────────────────────────────────────
class OrganizationDetailResponse(BaseModel):
    id: int
    name: str
    code: str
    is_active: bool
    status: str
    domain: Optional[str] = None
    approved_by: Optional[int] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    suspended_at: Optional[datetime] = None
    on_hold_at: Optional[datetime] = None
    reactivated_at: Optional[datetime] = None
    user_count: int = 0
    admin_email: Optional[str] = None
    admin_name: Optional[str] = None
    admin_id: Optional[int] = None
    company_email: Optional[str] = None
    contact_person: Optional[str] = None
    created_by: Optional[int] = None
    created_by_name: Optional[str] = None
    subscription_plan: str = "FREE"
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class OrganizationApprovalListResponse(BaseModel):
    organizations: list[OrganizationDetailResponse]
    total: int
    page: int
    page_size: int

class RejectOrganizationRequest(BaseModel):
    reason: str

class UpdateOrganizationStatusRequest(BaseModel):
    status: str
    reason: Optional[str] = None

class ApprovalHistoryResponse(BaseModel):
    id: int
    organization_id: int
    action: str
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    performed_by: int
    performed_by_name: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ApprovalHistoryListResponse(BaseModel):
    history: list[ApprovalHistoryResponse]
    total: int

# ── Organization Statistics ──────────────────────────────────────────────────
class OrganizationStatsResponse(BaseModel):
    total_users: int = 0
    active_users: int = 0
    locked_users: int = 0
    disabled_users: int = 0
    pending_users: int = 0
    org_admin_count: int = 0
    hr_admin_count: int = 0
    manager_count: int = 0
    employee_count: int = 0
    department_count: int = 0
    location_count: int = 0
    storage_used_gb: float = 0
    storage_limit_gb: int = 0

class OrganizationUserResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    status: str
    job_title: Optional[str] = None
    department_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class OrganizationUserListResponse(BaseModel):
    users: list[OrganizationUserResponse]
    total: int
    page: int
    page_size: int
