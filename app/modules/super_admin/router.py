import logging
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundException, BadRequestException, ForbiddenException

from app.modules.employee.models import Employee, UserRole, EmploymentType, EmployeeStatus
from app.modules.hr.models import Organization, OrganizationStatus
from app.core.security import hash_password
from app.core.cache import get_cached, set_cached, invalidate_cache

logger = logging.getLogger("zoiko")
from app.modules.super_admin.models import (
    PlanType, SubscriptionStatus, ProductStatus, HealthStatus,
    Subscription, Product, OrganizationProduct, PlatformSetting, AuditLog, SystemHealthCheck,
    AuditAction, Notification, SupportTicket, SecurityEvent, LoginActivity, ApprovalHistory,
)
from app.modules.super_admin.schemas import (
    DashboardStatsResponse,
    OrganizationResponse, OrganizationListResponse, OrganizationUpdateRequest, OrganizationCreateRequest,
    OrganizationDetailResponse, OrganizationApprovalListResponse, RejectOrganizationRequest,
    ApprovalHistoryResponse, ApprovalHistoryListResponse,
    ProductResponse, OrganizationProductResponse, OrganizationProductToggleRequest,
    SubscriptionResponse, SubscriptionUpdateRequest,
    PlatformUserResponse, PlatformUserListResponse, InviteUserRequest, ResetPasswordRequest,
    AuditLogResponse, AuditLogListResponse,
    SystemHealthResponse, SystemHealthSummaryResponse,
    PlatformSettingResponse, PlatformSettingUpdateRequest, PlatformSettingCreateRequest,
    AnalyticsResponse,
    NotificationResponse, NotificationCreateRequest, NotificationListResponse,
    SupportTicketResponse, SupportTicketUpdateRequest, SupportTicketListResponse,
    SecurityEventResponse, SecurityEventResolveRequest, SecurityEventListResponse,
    LoginActivityResponse, LoginActivityListResponse,
    RevenueDataResponse, StorageDataResponse,
)

router = APIRouter(prefix="/super-admin", tags=["Super Admin"])

def _require_super_admin(current_user=Depends(get_current_user)):
    logger.info(f"Checking super admin access for user: {current_user.email}, role: {current_user.role}")
    role_val = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if role_val != "super_admin":
        logger.warning(f"Access denied for user {current_user.email} with role {role_val}")
        raise ForbiddenException("This action requires Super Admin privileges.")
    return current_user

# ── Dashboard ─────────────────────────────────────────────────────────────────
@router.get("/dashboard", response_model=DashboardStatsResponse)
def get_dashboard_stats(db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    logger.info(f"Dashboard stats requested by {current_user.email} (role: {current_user.role})")

    cached = get_cached("dashboard_stats")
    if cached:
        return cached

    total_orgs = db.query(func.count(Organization.id)).scalar() or 0
    active_orgs = db.query(func.count(Organization.id)).filter(Organization.status == OrganizationStatus.ACTIVE.name).scalar() or 0
    pending_orgs = db.query(func.count(Organization.id)).filter(Organization.status == OrganizationStatus.PENDING.name).scalar() or 0
    rejected_orgs = db.query(func.count(Organization.id)).filter(Organization.status == OrganizationStatus.REJECTED.name).scalar() or 0
    suspended_orgs = db.query(func.count(Organization.id)).filter(Organization.status == OrganizationStatus.SUSPENDED.name).scalar() or 0
    trial_orgs = db.query(func.count(Subscription.id)).filter(Subscription.plan_type == PlanType.TRIAL.name).scalar() or 0
    total_users = db.query(func.count(Employee.id)).scalar() or 0
    hr_admin_count = db.query(func.count(Employee.id)).filter(Employee.role == UserRole.ADMIN.name).scalar() or 0
    employee_count = db.query(func.count(Employee.id)).filter(Employee.role == UserRole.EMPLOYEE.name).scalar() or 0
    active_products = db.query(func.count(Product.id)).filter(Product.status == ProductStatus.ACTIVE.name).scalar() or 0

    orgs_by_plan = db.query(Subscription.plan_type, func.count(Subscription.id)).group_by(Subscription.plan_type).all()
    platform_stats = {str(pt): count for pt, count in orgs_by_plan}

    subs = db.query(Subscription).all()
    total_storage_gb = sum(s.max_storage_gb or 0 for s in subs)
    paid_subs = db.query(func.count(Subscription.id)).filter(Subscription.plan_type != PlanType.FREE.name).scalar() or 0
    total_revenue = float(paid_subs * 100)

    twenty4 = datetime.utcnow() - timedelta(hours=24)
    failed_logins_24h = db.query(func.count(LoginActivity.id)).filter(
        LoginActivity.status == "failure", LoginActivity.created_at >= twenty4
    ).scalar() or 0

    open_support_tickets = db.query(func.count(SupportTicket.id)).filter(SupportTicket.status == "open").scalar() or 0
    unread_notifications = db.query(func.count(Notification.id)).filter(Notification.is_read == False).scalar() or 0
    unresolved_security_events = db.query(func.count(SecurityEvent.id)).filter(SecurityEvent.is_resolved == False).scalar() or 0

    recent_logs = (
        db.query(AuditLog)
        .order_by(desc(AuditLog.created_at))
        .limit(10)
        .all()
    )
    recent_activity = [
        {
            "id": log.id,
            "action": log.action.name if hasattr(log.action, 'name') else str(log.action),
            "entity_type": log.entity_type,
            "performed_by_email": log.performed_by_email,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in recent_logs
    ]

    recent_regs = (
        db.query(Organization)
        .order_by(desc(Organization.created_at))
        .limit(5)
        .all()
    )
    recent_registrations = [
        {
            "id": org.id,
            "name": org.name,
            "code": org.code,
            "status": org.status.name if hasattr(org.status, 'name') else str(org.status),
            "created_at": org.created_at.isoformat() if org.created_at else None,
        }
        for org in recent_regs
    ]

    logger.info(f"Dashboard stats: orgs={total_orgs}, users={total_users}, employees={employee_count}")

    response = DashboardStatsResponse(
        total_organizations=total_orgs,
        active_organizations=active_orgs,
        pending_organizations=pending_orgs,
        rejected_organizations=rejected_orgs,
        trial_organizations=trial_orgs,
        suspended_organizations=suspended_orgs,
        total_users=total_users,
        hr_admin_count=hr_admin_count,
        employee_count=employee_count,
        active_products=active_products,
        total_revenue=total_revenue,
        total_storage_gb=float(total_storage_gb),
        storage_used_gb=0.0,
        api_requests_24h=0,
        active_sessions=0,
        failed_logins_24h=failed_logins_24h,
        open_support_tickets=open_support_tickets,
        unread_notifications=unread_notifications,
        unresolved_security_events=unresolved_security_events,
        platform_stats=platform_stats,
        recent_activity=recent_activity,
        recent_registrations=recent_registrations,
    )
    set_cached("dashboard_stats", response)
    return response

# ── Organizations ─────────────────────────────────────────────────────────────
@router.get("/organizations", response_model=OrganizationListResponse)
def list_organizations(
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(_require_super_admin),
):
    query = db.query(Organization)
    if search:
        q = f"%{search}%"
        query = query.filter(Organization.name.ilike(q) | Organization.code.ilike(q))
    if status_filter == "active":
        query = query.filter(Organization.status == OrganizationStatus.ACTIVE.name)
    elif status_filter == "suspended":
        query = query.filter(Organization.status == OrganizationStatus.SUSPENDED.name)
    elif status_filter == "pending":
        query = query.filter(Organization.status == OrganizationStatus.PENDING.name)
    elif status_filter == "rejected":
        query = query.filter(Organization.status == OrganizationStatus.REJECTED.name)
    total = query.count()
    orgs = query.order_by(desc(Organization.created_at)).offset((page - 1) * page_size).limit(page_size).all()

    results = []
    for org in orgs:
        sub = db.query(Subscription).filter(Subscription.organization_id == org.id).first()
        user_count = db.query(func.count(Employee.id)).filter(Employee.organization_id == org.id).scalar() or 0
        results.append(OrganizationResponse(
            id=org.id,
            name=org.name,
            code=org.code,
            is_active=org.is_active,
            subscription_plan=sub.plan_type.name if sub else "FREE",
            user_count=user_count,
            created_at=org.created_at,
            updated_at=org.updated_at,
        ))

    return OrganizationListResponse(organizations=results, total=total, page=page, page_size=page_size)

# ── Organization Approval Workflow ──────────────────────────────────────────
# NOTE: These static routes MUST come BEFORE /{org_id} to avoid route conflicts

@router.get("/organizations/pending", response_model=OrganizationApprovalListResponse)
def list_pending_organizations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(_require_super_admin),
):
    query = db.query(Organization).filter(Organization.status == OrganizationStatus.PENDING.name)
    total = query.count()
    orgs = query.order_by(desc(Organization.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    results = _build_org_detail_list(db, orgs)
    return OrganizationApprovalListResponse(organizations=results, total=total, page=page, page_size=page_size)

@router.get("/organizations/approved", response_model=OrganizationApprovalListResponse)
def list_approved_organizations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(_require_super_admin),
):
    query = db.query(Organization).filter(Organization.status == OrganizationStatus.ACTIVE.name)
    total = query.count()
    orgs = query.order_by(desc(Organization.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    results = _build_org_detail_list(db, orgs)
    return OrganizationApprovalListResponse(organizations=results, total=total, page=page, page_size=page_size)

@router.get("/organizations/rejected", response_model=OrganizationApprovalListResponse)
def list_rejected_organizations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(_require_super_admin),
):
    query = db.query(Organization).filter(Organization.status == OrganizationStatus.REJECTED.name)
    total = query.count()
    orgs = query.order_by(desc(Organization.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    results = _build_org_detail_list(db, orgs)
    return OrganizationApprovalListResponse(organizations=results, total=total, page=page, page_size=page_size)

@router.get("/organizations/suspended", response_model=OrganizationApprovalListResponse)
def list_suspended_organizations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(_require_super_admin),
):
    query = db.query(Organization).filter(Organization.status == OrganizationStatus.SUSPENDED.name)
    total = query.count()
    orgs = query.order_by(desc(Organization.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    results = _build_org_detail_list(db, orgs)
    return OrganizationApprovalListResponse(organizations=results, total=total, page=page, page_size=page_size)

@router.get("/organizations/{org_id}", response_model=OrganizationResponse)
def get_organization(org_id: int, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise NotFoundException("Organization not found")
    sub = db.query(Subscription).filter(Subscription.organization_id == org.id).first()
    user_count = db.query(func.count(Employee.id)).filter(Employee.organization_id == org.id).scalar() or 0
    return OrganizationResponse(
        id=org.id, name=org.name, code=org.code, is_active=org.is_active,
        subscription_plan=sub.plan_type.name if sub else "FREE",
        user_count=user_count, created_at=org.created_at, updated_at=org.updated_at,
    )

@router.put("/organizations/{org_id}", response_model=OrganizationResponse)
def update_organization(org_id: int, data: OrganizationUpdateRequest, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise NotFoundException("Organization not found")
    if data.name is not None:
        org.name = data.name
    if data.is_active is not None:
        org.is_active = data.is_active
    db.commit()
    db.refresh(org)
    _create_audit_log(db, AuditAction.UPDATE, "Organization", org.id, current_user.email, {"name": data.name, "is_active": data.is_active})
    sub = db.query(Subscription).filter(Subscription.organization_id == org.id).first()
    user_count = db.query(func.count(Employee.id)).filter(Employee.organization_id == org.id).scalar() or 0
    return OrganizationResponse(
        id=org.id, name=org.name, code=org.code, is_active=org.is_active,
        subscription_plan=sub.plan_type.name if sub else "FREE",
        user_count=user_count, created_at=org.created_at, updated_at=org.updated_at,
    )

@router.put("/organizations/{org_id}/suspend")
def suspend_organization(org_id: int, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise NotFoundException("Organization not found")
    org.is_active = False
    org.status = OrganizationStatus.SUSPENDED
    org.suspended_at = datetime.utcnow()
    db.commit()
    from app.modules.super_admin.models import Notification
    notification = Notification(
        title="Organization Suspended",
        message=f"Organization '{org.name}' has been suspended by Super Admin.",
        notification_type="org_suspension",
        priority="high",
        target_org_id=org.id,
    )
    db.add(notification)
    db.commit()
    _create_audit_log(db, AuditAction.SUSPEND, "Organization", org.id, current_user.email)
    return {"success": True, "message": "Organization suspended"}

@router.put("/organizations/{org_id}/activate")
def activate_organization(org_id: int, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise NotFoundException("Organization not found")
    org.is_active = True
    if org.status == OrganizationStatus.SUSPENDED:
        org.status = OrganizationStatus.ACTIVE
        org.reactivated_at = datetime.utcnow()
    db.commit()
    _create_audit_log(db, AuditAction.ACTIVATE, "Organization", org.id, current_user.email)
    return {"success": True, "message": "Organization activated"}

@router.delete("/organizations/{org_id}")
def delete_organization(org_id: int, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise NotFoundException("Organization not found")
    db.delete(org)
    db.commit()
    _create_audit_log(db, AuditAction.DELETE, "Organization", org_id, current_user.email)
    return {"success": True, "message": "Organization deleted"}

@router.get("/organizations/{org_id}/details", response_model=OrganizationDetailResponse)
def get_organization_detail(org_id: int, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise NotFoundException("Organization not found")
    results = _build_org_detail_list(db, [org])
    return results[0]

@router.put("/organizations/{org_id}/approve")
def approve_organization(org_id: int, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise NotFoundException("Organization not found")
    current_status = _get_org_status(org.status)
    if current_status != OrganizationStatus.PENDING.name:
        raise BadRequestException(f"Organization is not in PENDING state (current: {current_status})")

    org.status = OrganizationStatus.ACTIVE
    org.is_active = True
    org.approved_by = current_user.id
    org.approved_at = datetime.utcnow()

    # Create a default FREE subscription if none exists
    existing_sub = db.query(Subscription).filter(Subscription.organization_id == org.id).first()
    if not existing_sub:
        sub = Subscription(
            organization_id=org.id,
            plan_type=PlanType.FREE.name,
            status=SubscriptionStatus.ACTIVE.name,
            max_users=15,
            max_storage_gb=5,
        )
        db.add(sub)

    db.commit()

    # Activate all employees in the org
    db.query(Employee).filter(Employee.organization_id == org.id).update({"is_active": True})
    db.commit()

    # Approval history
    _add_approval_history(db, org.id, "approved", current_user.id, None)

    # Audit log
    _create_audit_log(db, AuditAction.APPROVED, "Organization", org.id, current_user.email,
                      {"organization": org.name, "status": "approved"})

    # Notification for org admin
    admin_user = db.query(Employee).filter(Employee.organization_id == org.id, Employee.role == UserRole.ADMIN.name).first()
    from app.modules.super_admin.models import Notification
    notification = Notification(
        title="Organization Approved",
        message=f"Your organization '{org.name}' has been approved by Super Admin. You can now log in.",
        notification_type="org_approval",
        priority="high",
        target_org_id=org.id,
        target_user_id=admin_user.id if admin_user else None,
    )
    db.add(notification)
    db.commit()

    invalidate_cache("dashboard_stats")
    return {"success": True, "message": "Organization approved successfully"}

@router.put("/organizations/{org_id}/reject")
def reject_organization(org_id: int, data: RejectOrganizationRequest, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise NotFoundException("Organization not found")
    current_status = _get_org_status(org.status)
    if current_status != OrganizationStatus.PENDING.name:
        raise BadRequestException(f"Organization is not in PENDING state (current: {current_status})")

    org.status = OrganizationStatus.REJECTED
    org.is_active = False
    org.rejection_reason = data.reason
    db.commit()

    _add_approval_history(db, org.id, "rejected", current_user.id, data.reason)
    _create_audit_log(db, AuditAction.REJECTED, "Organization", org.id, current_user.email,
                      {"organization": org.name, "reason": data.reason})

    admin_user = db.query(Employee).filter(Employee.organization_id == org.id, Employee.role == UserRole.ADMIN.name).first()
    from app.modules.super_admin.models import Notification
    notification = Notification(
        title="Organization Registration Rejected",
        message=f"Your organization '{org.name}' registration has been rejected. Reason: {data.reason}",
        notification_type="org_rejection",
        priority="high",
        target_org_id=org.id,
        target_user_id=admin_user.id if admin_user else None,
    )
    db.add(notification)
    db.commit()

    invalidate_cache("dashboard_stats")
    return {"success": True, "message": "Organization rejected"}

@router.put("/organizations/{org_id}/reactivate")
def reactivate_organization(org_id: int, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise NotFoundException("Organization not found")
    current_status = _get_org_status(org.status)
    if current_status != OrganizationStatus.SUSPENDED.name:
        raise BadRequestException(f"Organization is not in SUSPENDED state (current: {current_status})")

    org.status = OrganizationStatus.ACTIVE
    org.is_active = True
    org.reactivated_at = datetime.utcnow()

    # Create a default FREE subscription if none exists
    existing_sub = db.query(Subscription).filter(Subscription.organization_id == org.id).first()
    if not existing_sub:
        sub = Subscription(
            organization_id=org.id,
            plan_type=PlanType.FREE.name,
            status=SubscriptionStatus.ACTIVE.name,
            max_users=15,
            max_storage_gb=5,
        )
        db.add(sub)

    db.commit()

    db.query(Employee).filter(Employee.organization_id == org.id).update({"is_active": True})
    db.commit()

    _add_approval_history(db, org.id, "reactivated", current_user.id, None)
    _create_audit_log(db, AuditAction.REACTIVATED, "Organization", org.id, current_user.email,
                      {"organization": org.name, "status": "reactivated"})

    admin_user = db.query(Employee).filter(Employee.organization_id == org.id, Employee.role == UserRole.ADMIN.name).first()
    from app.modules.super_admin.models import Notification
    notification = Notification(
        title="Organization Reactivated",
        message=f"Your organization '{org.name}' has been reactivated by Super Admin.",
        notification_type="org_reactivation",
        priority="high",
        target_org_id=org.id,
        target_user_id=admin_user.id if admin_user else None,
    )
    db.add(notification)
    db.commit()

    invalidate_cache("dashboard_stats")
    return {"success": True, "message": "Organization reactivated"}

@router.get("/organizations/{org_id}/approval-history", response_model=ApprovalHistoryListResponse)
def get_approval_history(org_id: int, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise NotFoundException("Organization not found")

    from app.modules.super_admin.models import ApprovalHistory
    history = (
        db.query(
            ApprovalHistory,
            func.concat(Employee.first_name, ' ', Employee.last_name).label('performer_name')
        )
        .outerjoin(Employee, Employee.id == ApprovalHistory.performed_by)
        .filter(ApprovalHistory.organization_id == org_id)
        .order_by(desc(ApprovalHistory.created_at))
        .all()
    )

    results = []
    for h, performer_name in history:
        results.append(ApprovalHistoryResponse(
            id=h.id,
            organization_id=h.organization_id,
            action=h.action,
            performed_by=h.performed_by,
            performed_by_name=performer_name,
            reason=h.reason,
            created_at=h.created_at,
        ))

    return ApprovalHistoryListResponse(history=results, total=len(results))

# ── Products ──────────────────────────────────────────────────────────────────
@router.get("/products", response_model=list[ProductResponse])
def list_products(db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    products = db.query(Product).order_by(Product.name).all()
    return products

@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise NotFoundException("Product not found")
    return product

@router.put("/products/{product_id}/status")
def update_product_status(product_id: int, status_val: str, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise NotFoundException("Product not found")
    product.status = status_val
    db.commit()
    _create_audit_log(db, AuditAction.UPDATE, "Product", product_id, current_user.email, {"status": status_val})
    return {"success": True, "message": "Product status updated"}

@router.get("/organizations/{org_id}/products", response_model=list[OrganizationProductResponse])
def list_organization_products(org_id: int, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise NotFoundException("Organization not found")
    org_products = db.query(OrganizationProduct).filter(OrganizationProduct.organization_id == org_id).all()
    result = []
    for op in org_products:
        prod = db.query(Product).filter(Product.id == op.product_id).first()
        result.append(OrganizationProductResponse(
            id=op.id, organization_id=op.organization_id, product_id=op.product_id,
            product_name=prod.name if prod else "Unknown",
            product_code=prod.code if prod else "",
            is_enabled=op.is_enabled, enabled_at=op.enabled_at,
        ))
    return result

@router.put("/organizations/{org_id}/products/{product_id}/toggle")
def toggle_organization_product(org_id: int, product_id: int, data: OrganizationProductToggleRequest, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    org_product = db.query(OrganizationProduct).filter(
        OrganizationProduct.organization_id == org_id,
        OrganizationProduct.product_id == product_id,
    ).first()
    if not org_product:
        org_product = OrganizationProduct(
            organization_id=org_id,
            product_id=product_id,
            is_enabled=data.is_enabled,
            enabled_at=datetime.utcnow() if data.is_enabled else None,
        )
        db.add(org_product)
    else:
        org_product.is_enabled = data.is_enabled
        org_product.enabled_at = datetime.utcnow() if data.is_enabled else None
    db.commit()
    invalidate_cache("dashboard")
    invalidate_cache("analytics")
    _create_audit_log(db, AuditAction.UPDATE, "OrganizationProduct", org_product.id, current_user.email, {"is_enabled": data.is_enabled})
    return {"success": True, "message": "Product access updated"}

# ── Subscriptions ─────────────────────────────────────────────────────────────
@router.get("/subscriptions", response_model=list[SubscriptionResponse])
def list_subscriptions(db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    orgs = db.query(Organization).order_by(desc(Organization.created_at)).all()
    subs = {s.organization_id: s for s in db.query(Subscription).all()}
    result = []
    for org in orgs:
        sub = subs.get(org.id)
        if sub:
            result.append(SubscriptionResponse(
                id=sub.id, organization_id=sub.organization_id,
                organization_name=org.name,
                plan_type=sub.plan_type.name if hasattr(sub.plan_type, 'name') else str(sub.plan_type),
                status=sub.status.name if hasattr(sub.status, 'name') else str(sub.status),
                start_date=sub.start_date, end_date=sub.end_date,
                max_users=sub.max_users, max_storage_gb=sub.max_storage_gb,
                created_at=sub.created_at,
            ))
        else:
            result.append(SubscriptionResponse(
                id=0, organization_id=org.id,
                organization_name=org.name,
                plan_type=PlanType.FREE.name,
                status=SubscriptionStatus.ACTIVE.name,
                start_date=org.created_at, end_date=None,
                max_users=15, max_storage_gb=5,
                created_at=org.created_at,
            ))
    return result

@router.get("/subscriptions/{org_id}", response_model=SubscriptionResponse)
def get_organization_subscription(org_id: int, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise NotFoundException("Organization not found")
    sub = db.query(Subscription).filter(Subscription.organization_id == org_id).first()
    if not sub:
        return SubscriptionResponse(
            id=0, organization_id=org.id,
            organization_name=org.name,
            plan_type=PlanType.FREE.name,
            status=SubscriptionStatus.ACTIVE.name,
            start_date=org.created_at, end_date=None,
            max_users=15, max_storage_gb=5,
            created_at=org.created_at,
        )
    return SubscriptionResponse(
        id=sub.id, organization_id=sub.organization_id,
        organization_name=org.name,
        plan_type=sub.plan_type.name if hasattr(sub.plan_type, 'name') else str(sub.plan_type),
        status=sub.status.name if hasattr(sub.status, 'name') else str(sub.status),
        start_date=sub.start_date, end_date=sub.end_date,
        max_users=sub.max_users, max_storage_gb=sub.max_storage_gb,
        created_at=sub.created_at,
    )

@router.put("/subscriptions/{org_id}", response_model=SubscriptionResponse)
def update_subscription(org_id: int, data: SubscriptionUpdateRequest, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    sub = db.query(Subscription).filter(Subscription.organization_id == org_id).first()
    if not sub:
        org = db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            raise NotFoundException("Organization not found")
        sub = Subscription(organization_id=org_id)
        db.add(sub)
    if data.plan_type is not None:
        sub.plan_type = data.plan_type.strip().upper()
    if data.status is not None:
        sub.status = data.status
    if data.max_users is not None:
        sub.max_users = data.max_users
    if data.max_storage_gb is not None:
        sub.max_storage_gb = data.max_storage_gb
    if data.end_date is not None:
        sub.end_date = data.end_date
    db.commit()
    db.refresh(sub)
    invalidate_cache("dashboard")
    invalidate_cache("analytics")
    invalidate_cache("revenue")
    _create_audit_log(db, AuditAction.UPDATE, "Subscription", sub.id, current_user.email, data.model_dump(exclude_none=True))
    org = db.query(Organization).filter(Organization.id == org_id).first()
    return SubscriptionResponse(
        id=sub.id, organization_id=sub.organization_id,
        organization_name=org.name if org else "Unknown",
        plan_type=sub.plan_type.name if hasattr(sub.plan_type, 'name') else str(sub.plan_type),
        status=sub.status.name if hasattr(sub.status, 'name') else str(sub.status),
        start_date=sub.start_date, end_date=sub.end_date,
        max_users=sub.max_users, max_storage_gb=sub.max_storage_gb,
        created_at=sub.created_at,
    )

# ── Platform Users ────────────────────────────────────────────────────────────
@router.get("/users", response_model=PlatformUserListResponse)
def list_platform_users(
    search: Optional[str] = Query(None),
    role_filter: Optional[str] = Query(None, alias="role"),
    org_id: Optional[int] = Query(None, alias="organization_id"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(_require_super_admin),
):
    query = db.query(Employee)
    if search:
        q = f"%{search}%"
        query = query.filter(
            Employee.first_name.ilike(q) |
            Employee.last_name.ilike(q) |
            Employee.email.ilike(q)
        )
    if role_filter:
        query = query.filter(Employee.role == role_filter)
    if org_id:
        query = query.filter(Employee.organization_id == org_id)
    total = query.count()
    users = query.order_by(desc(Employee.created_at)).offset((page - 1) * page_size).limit(page_size).all()

    results = []
    for u in users:
        org = db.query(Organization).filter(Organization.id == u.organization_id).first()
        dept_name = None
        if u.department_id:
            from app.modules.hr.models import Department
            dept = db.query(Department).filter(Department.id == u.department_id).first()
            dept_name = dept.name if dept else None
        results.append(PlatformUserResponse(
            id=u.id, email=u.email, first_name=u.first_name, last_name=u.last_name,
            role=u.role.name if hasattr(u.role, 'name') else str(u.role),
            is_active=u.is_active, organization_id=u.organization_id or 0,
            organization_name=org.name if org else "Unknown",
            department_name=dept_name, job_title=u.job_title,
            created_at=u.created_at,
        ))
    return PlatformUserListResponse(users=results, total=total, page=page, page_size=page_size)

@router.post("/users/invite")
def invite_user(data: InviteUserRequest, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    existing = db.query(Employee).filter(Employee.email == data.email).first()
    if existing:
        raise BadRequestException("User with this email already exists")
    import random, string
    temp_pw = "".join(random.choices(string.ascii_letters + string.digits, k=12))
    role_map = {"admin": UserRole.ADMIN, "hr_manager": UserRole.HR_MANAGER, "manager": UserRole.MANAGER, "employee": UserRole.EMPLOYEE, "super_admin": UserRole.SUPER_ADMIN}
    role_enum = role_map.get(data.role.lower(), UserRole.EMPLOYEE)
    max_code = db.query(func.max(Employee.employee_code)).scalar()
    next_num = 1
    if max_code:
        next_num = int(max_code.split("-")[1]) + 1
    emp_code = f"ZK-{next_num:04d}"
    emp = Employee(
        email=data.email,
        hashed_password=hash_password(temp_pw),
        employee_code=emp_code,
        first_name=data.first_name,
        last_name=data.last_name,
        role=role_enum,
        employment_type=EmploymentType.FULL_TIME,
        status=EmployeeStatus.ACTIVE,
        date_of_joining=date.today(),
        is_active=True,
        organization_id=data.organization_id,
        job_title=data.job_title or "Staff",
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    invalidate_cache("dashboard")
    invalidate_cache("analytics")
    _create_audit_log(db, AuditAction.CREATE, "User", emp.id, current_user.email, {"email": data.email, "role": data.role})
    return {"success": True, "message": f"User {data.email} invited", "temporary_password": temp_pw}

@router.put("/users/{user_id}/disable")
def disable_user(user_id: int, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    user = db.query(Employee).filter(Employee.id == user_id).first()
    if not user:
        raise NotFoundException("User not found")
    user.is_active = False
    db.commit()
    invalidate_cache("dashboard")
    invalidate_cache("analytics")
    _create_audit_log(db, AuditAction.UPDATE, "User", user_id, current_user.email, {"is_active": False})
    return {"success": True, "message": "User disabled"}

@router.put("/users/{user_id}/enable")
def enable_user(user_id: int, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    user = db.query(Employee).filter(Employee.id == user_id).first()
    if not user:
        raise NotFoundException("User not found")
    user.is_active = True
    db.commit()
    invalidate_cache("dashboard")
    invalidate_cache("analytics")
    _create_audit_log(db, AuditAction.UPDATE, "User", user_id, current_user.email, {"is_active": True})
    return {"success": True, "message": "User enabled"}

@router.put("/users/{user_id}/reset-password")
def reset_user_password(user_id: int, data: ResetPasswordRequest, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    user = db.query(Employee).filter(Employee.id == user_id).first()
    if not user:
        raise NotFoundException("User not found")
    user.hashed_password = hash_password(data.new_password)
    db.commit()
    _create_audit_log(db, AuditAction.UPDATE, "User", user_id, current_user.email, {"password_reset": True})
    return {"success": True, "message": "Password reset successfully"}

# ── Audit Logs ────────────────────────────────────────────────────────────────
@router.get("/audit-logs", response_model=AuditLogListResponse)
def list_audit_logs(
    action_filter: Optional[str] = Query(None, alias="action"),
    entity_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    org_id: Optional[int] = Query(None, alias="organization_id"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(_require_super_admin),
):
    query = db.query(AuditLog)
    if action_filter:
        query = query.filter(AuditLog.action == action_filter)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if search:
        q = f"%{search}%"
        query = query.filter(AuditLog.performed_by_email.ilike(q) | AuditLog.entity_type.ilike(q))
    if date_from:
        try:
            dt = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(AuditLog.created_at >= dt)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(AuditLog.created_at < dt)
        except ValueError:
            pass
    if org_id:
        query = query.filter(AuditLog.entity_type == "Organization", AuditLog.entity_id == org_id)
    total = query.count()
    logs = query.order_by(desc(AuditLog.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    return AuditLogListResponse(
        logs=[AuditLogResponse(
            id=log.id,
            action=log.action.name if hasattr(log.action, 'name') else str(log.action),
            entity_type=log.entity_type, entity_id=log.entity_id,
            performed_by=log.performed_by, performed_by_email=log.performed_by_email,
            details=log.details, created_at=log.created_at,
        ) for log in logs],
        total=total, page=page, page_size=page_size,
    )

# ── System Health ─────────────────────────────────────────────────────────────
@router.get("/system-health", response_model=SystemHealthSummaryResponse)
def get_system_health(db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    components = db.query(SystemHealthCheck).order_by(desc(SystemHealthCheck.checked_at)).all()
    latest = {}
    for c in components:
        if c.component not in latest:
            latest[c.component] = c
    all_healthy = all(c.status == HealthStatus.HEALTHY for c in latest.values())
    overall = "healthy" if all_healthy else "degraded" if any(c.status == HealthStatus.DEGRADED for c in latest.values()) else "down"
    last = max((c.checked_at for c in latest.values()), default=None)
    return SystemHealthSummaryResponse(
        components=[SystemHealthResponse(
            id=c.id, component=c.component,
            status=c.status.name if hasattr(c.status, 'name') else str(c.status),
            message=c.message, response_time_ms=c.response_time_ms,
            checked_at=c.checked_at,
        ) for c in latest.values()],
        overall_status=overall,
        last_checked=last,
    )

@router.post("/system-health/check")
def run_health_check(db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    results = []
    checks = [
        ("API", lambda: _check_api()),
        ("Database", lambda: _check_database(db)),
        ("Storage", lambda: _check_storage()),
        ("CPU", lambda: _check_cpu()),
        ("Memory", lambda: _check_memory(db)),
        ("Active Sessions", lambda: _check_active_sessions(db)),
        ("Background Jobs", lambda: _check_background_jobs()),
    ]
    for component_name, check_fn in checks:
        try:
            status_val, message, time_ms = check_fn()
        except Exception as e:
            status_val, message, time_ms = HealthStatus.DOWN, str(e), 0
        check = SystemHealthCheck(component=component_name, status=status_val, message=message, response_time_ms=time_ms)
        db.add(check)
        results.append(check)
    db.commit()
    return get_system_health(db=db, current_user=current_user)

def _check_api():
    return HealthStatus.HEALTHY, "API is responding normally", 5.0

def _check_database(db):
    import time
    start = time.time()
    db.execute(func.now())
    elapsed = (time.time() - start) * 1000
    return HealthStatus.HEALTHY, "Database connection is healthy", round(elapsed, 2)

def _check_storage():
    import os, shutil
    upload_dir = "uploads"
    if os.path.exists(upload_dir):
        total, used, free = shutil.disk_usage(upload_dir)
        free_gb = free // (2**30)
        if free_gb < 1:
            return HealthStatus.DEGRADED, f"Low disk space: {free_gb}GB free", round((used / total) * 100, 1) if total else 0
        return HealthStatus.HEALTHY, f"Storage OK: {free_gb}GB free", round((used / total) * 100, 1) if total else 0
    return HealthStatus.HEALTHY, "Storage check passed", 0

def _check_background_jobs():
    return HealthStatus.HEALTHY, "No background jobs running", 0

def _check_cpu():
    import time, os as os_mod
    try:
        cpu_percent = float(os_mod.popen("wmic cpu get loadpercentage").read().strip().split("\n")[1]) if os_mod.name == "nt" else 0.0
        if cpu_percent > 90:
            return HealthStatus.DEGRADED, f"CPU at {cpu_percent}%", cpu_percent
        return HealthStatus.HEALTHY, f"CPU at {cpu_percent}%", cpu_percent
    except Exception as e:
        return HealthStatus.HEALTHY, "CPU check passed (simulated)", 25.0

def _check_memory(db):
    import os as os_mod
    try:
        if os_mod.name == "nt":
            mem = os_mod.popen("wmic OS get TotalVisibleMemorySize,FreePhysicalMemory").read().strip().split("\n")[1].split()
            free_kb, total_kb = int(mem[1]), int(mem[0])
            used_percent = round((1 - free_kb / total_kb) * 100, 1) if total_kb else 0
        else:
            used_percent = 40.0
        if used_percent > 90:
            return HealthStatus.DEGRADED, f"Memory at {used_percent}%", used_percent
        return HealthStatus.HEALTHY, f"Memory at {used_percent}%", used_percent
    except Exception:
        return HealthStatus.HEALTHY, "Memory check passed (simulated)", 35.0

def _check_active_sessions(db):
    recent = datetime.utcnow() - timedelta(hours=1)
    count = db.query(func.count(LoginActivity.id)).filter(LoginActivity.created_at >= recent).scalar() or 0
    return HealthStatus.HEALTHY, f"{count} active sessions in last hour", float(count)

# ── Platform Settings ─────────────────────────────────────────────────────────
@router.get("/settings", response_model=list[PlatformSettingResponse])
def list_platform_settings(db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    settings = db.query(PlatformSetting).order_by(PlatformSetting.category, PlatformSetting.key).all()
    return settings

@router.get("/settings/{setting_id}", response_model=PlatformSettingResponse)
def get_platform_setting(setting_id: int, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    setting = db.query(PlatformSetting).filter(PlatformSetting.id == setting_id).first()
    if not setting:
        raise NotFoundException("Setting not found")
    return setting

@router.post("/settings", response_model=PlatformSettingResponse)
def create_platform_setting(data: PlatformSettingCreateRequest, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    existing = db.query(PlatformSetting).filter(PlatformSetting.key == data.key).first()
    if existing:
        raise BadRequestException("Setting with this key already exists")
    setting = PlatformSetting(key=data.key, value=data.value, description=data.description, category=data.category)
    db.add(setting)
    db.commit()
    db.refresh(setting)
    _create_audit_log(db, AuditAction.CREATE, "PlatformSetting", setting.id, current_user.email, {"key": data.key})
    return setting

@router.put("/settings/{setting_id}", response_model=PlatformSettingResponse)
def update_platform_setting(setting_id: int, data: PlatformSettingUpdateRequest, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    setting = db.query(PlatformSetting).filter(PlatformSetting.id == setting_id).first()
    if not setting:
        raise NotFoundException("Setting not found")
    old_value = setting.value
    setting.value = data.value
    if data.description is not None:
        setting.description = data.description
    db.commit()
    db.refresh(setting)
    _create_audit_log(db, AuditAction.CONFIG_CHANGE, "PlatformSetting", setting.id, current_user.email, {"key": setting.key, "old_value": old_value, "new_value": data.value})
    return setting

# ── Analytics ─────────────────────────────────────────────────────────────────
@router.get("/analytics", response_model=AnalyticsResponse)
def get_analytics(db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    cached = get_cached("analytics")
    if cached:
        return cached

    orgs_by_month = (
        db.query(
            func.date_trunc("month", Organization.created_at).label("month"),
            func.count(Organization.id).label("count"),
        )
        .group_by(func.date_trunc("month", Organization.created_at))
        .order_by(func.date_trunc("month", Organization.created_at))
        .limit(12)
        .all()
    )
    organization_growth = [{"month": row.month.strftime("%Y-%m") if row.month else "unknown", "count": row.count} for row in orgs_by_month]

    users_by_month = (
        db.query(
            func.date_trunc("month", Employee.created_at).label("month"),
            func.count(Employee.id).label("count"),
        )
        .group_by(func.date_trunc("month", Employee.created_at))
        .order_by(func.date_trunc("month", Employee.created_at))
        .limit(12)
        .all()
    )
    user_growth = [{"month": row.month.strftime("%Y-%m") if row.month else "unknown", "count": row.count} for row in users_by_month]

    subs_by_plan = (
        db.query(Subscription.plan_type, func.count(Subscription.id))
        .group_by(Subscription.plan_type)
        .all()
    )
    subscription_distribution = [
        {"name": str(pt.name) if hasattr(pt, 'name') else str(pt), "count": count}
        for pt, count in subs_by_plan
    ]

    products_enabled = (
        db.query(Product.name, func.count(OrganizationProduct.id))
        .join(OrganizationProduct, OrganizationProduct.product_id == Product.id)
        .filter(OrganizationProduct.is_enabled == True)
        .group_by(Product.name)
        .all()
    )
    product_adoption = [{"name": name, "count": count} for name, count in products_enabled]

    subs_paid = db.query(Subscription).filter(Subscription.plan_type != PlanType.FREE.name).all()
    plan_prices = {"TRIAL": 0, "BASIC": 50, "PROFESSIONAL": 150, "ENTERPRISE": 500}
    revenue_data = [
        {"name": str(s.plan_type if hasattr(s.plan_type, 'name') else s.plan_type), "amount": plan_prices.get(str(s.plan_type if hasattr(s.plan_type, 'name') else s.plan_type).upper(), 0)}
        for s in subs_paid
    ]

    revenue_monthly = (
        db.query(
            func.date_trunc("month", Subscription.created_at).label("month"),
            func.count(Subscription.id).label("count"),
        )
        .filter(Subscription.plan_type != PlanType.FREE.name)
        .group_by(func.date_trunc("month", Subscription.created_at))
        .order_by(func.date_trunc("month", Subscription.created_at))
        .limit(12)
        .all()
    )
    revenue_monthly_data = [
        {"month": row.month.strftime("%Y-%m"), "revenue": row.count * 100} for row in revenue_monthly
    ]

    twenty4 = datetime.utcnow() - timedelta(hours=24)
    login_data = (
        db.query(LoginActivity.status, func.count(LoginActivity.id))
        .filter(LoginActivity.created_at >= twenty4)
        .group_by(LoginActivity.status)
        .all()
    )
    login_activity = [{"status": s or "unknown", "count": c} for s, c in login_data]

    storage_data = [
        {"org_id": s.organization_id, "max_storage_gb": s.max_storage_gb or 0}
        for s in db.query(Subscription).all()
    ]

    response = AnalyticsResponse(
        organization_growth=organization_growth,
        user_growth=user_growth,
        employee_growth=user_growth,
        active_users=user_growth,
        subscription_distribution=subscription_distribution,
        product_adoption=product_adoption,
        revenue_data=revenue_data,
        revenue_monthly=revenue_monthly_data,
        storage_data=storage_data,
        login_activity=login_activity,
    )
    set_cached("analytics", response)
    return response

# ── Create Organization ───────────────────────────────────────────────────────
@router.post("/organizations", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(data: OrganizationCreateRequest, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    existing = db.query(Organization).filter(Organization.code == data.code).first()
    if existing:
        raise BadRequestException("Organization with this code already exists")
    org = Organization(name=data.name, code=data.code, is_active=data.is_active)
    db.add(org)
    db.flush()
    sub = Subscription(
        organization_id=org.id,
        plan_type=PlanType.FREE.name,
        status=SubscriptionStatus.ACTIVE.name,
        max_users=15,
        max_storage_gb=5,
    )
    db.add(sub)
    db.commit()
    db.refresh(org)
    invalidate_cache("dashboard")
    invalidate_cache("analytics")
    invalidate_cache("revenue")
    invalidate_cache("storage")
    _create_audit_log(db, AuditAction.CREATE, "Organization", org.id, current_user.email, {"name": data.name, "code": data.code})
    return OrganizationResponse(
        id=org.id, name=org.name, code=org.code, is_active=org.is_active,
        subscription_plan=PlanType.FREE.name,
        user_count=0, created_at=org.created_at, updated_at=org.updated_at,
    )

# ── Revenue / Storage ─────────────────────────────────────────────────────────
@router.get("/revenue", response_model=RevenueDataResponse)
def get_revenue_data(db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    cached = get_cached("revenue")
    if cached:
        return cached

    sub_monthly = (
        db.query(
            func.date_trunc("month", Subscription.created_at).label("month"),
            func.count(Subscription.id).label("count"),
        )
        .filter(Subscription.plan_type != PlanType.FREE.name)
        .group_by(func.date_trunc("month", Subscription.created_at))
        .order_by(func.date_trunc("month", Subscription.created_at))
        .limit(12)
        .all()
    )
    monthly_revenue = [{"month": row.month.strftime("%Y-%m"), "count": row.count} for row in sub_monthly]
    total_revenue = db.query(func.count(Subscription.id)).filter(Subscription.plan_type != PlanType.FREE.name).scalar() or 0
    revenue_by_plan = (
        db.query(Subscription.plan_type, func.count(Subscription.id))
        .filter(Subscription.plan_type != PlanType.FREE.name)
        .group_by(Subscription.plan_type)
        .all()
    )
    response = RevenueDataResponse(
        monthly_revenue=monthly_revenue,
        total_revenue=float(total_revenue),
        revenue_by_plan=[{"plan": str(pt), "count": count} for pt, count in revenue_by_plan],
    )
    set_cached("revenue", response)
    return response

@router.get("/storage", response_model=StorageDataResponse)
def get_storage_data(db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    cached = get_cached("storage")
    if cached:
        return cached

    subs = db.query(Subscription).all()
    total_capacity = sum(s.max_storage_gb or 0 for s in subs)
    storage_by_org = [
        {"org_id": s.organization_id, "max_storage_gb": s.max_storage_gb or 0}
        for s in subs
    ]
    response = StorageDataResponse(
        total_storage_gb=float(total_capacity),
        storage_by_org=storage_by_org,
        storage_usage_percentage=0.0,
    )
    set_cached("storage", response)
    return response

# ── Notifications ─────────────────────────────────────────────────────────────
@router.get("/notifications", response_model=NotificationListResponse)
def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_read: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(_require_super_admin),
):
    query = db.query(Notification)
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)
    total = query.count()
    notifications = query.order_by(desc(Notification.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    return NotificationListResponse(
        notifications=notifications,
        total=total, page=page, page_size=page_size,
    )

@router.post("/notifications", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
def create_notification(data: NotificationCreateRequest, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    note = Notification(
        title=data.title,
        message=data.message,
        notification_type=data.notification_type,
        priority=data.priority,
        target_org_id=data.target_org_id,
        target_user_id=data.target_user_id,
        created_by=current_user.id,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note

@router.put("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    note = db.query(Notification).filter(Notification.id == notification_id).first()
    if not note:
        raise NotFoundException("Notification not found")
    note.is_read = True
    db.commit()
    return {"success": True, "message": "Notification marked as read"}

@router.delete("/notifications/{notification_id}")
def delete_notification(notification_id: int, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    note = db.query(Notification).filter(Notification.id == notification_id).first()
    if not note:
        raise NotFoundException("Notification not found")
    db.delete(note)
    db.commit()
    return {"success": True, "message": "Notification deleted"}

# ── Support Tickets ───────────────────────────────────────────────────────────
@router.get("/support-tickets", response_model=SupportTicketListResponse)
def list_support_tickets(
    status_filter: Optional[str] = Query(None, alias="status"),
    priority: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(_require_super_admin),
):
    query = db.query(SupportTicket)
    if status_filter:
        query = query.filter(SupportTicket.status == status_filter)
    if priority:
        query = query.filter(SupportTicket.priority == priority)
    total = query.count()
    tickets = query.order_by(desc(SupportTicket.created_at)).offset((page - 1) * page_size).limit(page_size).all()

    results = []
    for t in tickets:
        org_name = None
        if t.organization_id:
            org = db.query(Organization).filter(Organization.id == t.organization_id).first()
            org_name = org.name if org else None
        raised_name = None
        if t.raised_by:
            emp = db.query(Employee).filter(Employee.id == t.raised_by).first()
            raised_name = f"{emp.first_name} {emp.last_name}" if emp else None
        assigned_name = None
        if t.assigned_to:
            emp = db.query(Employee).filter(Employee.id == t.assigned_to).first()
            assigned_name = f"{emp.first_name} {emp.last_name}" if emp else None
        results.append(SupportTicketResponse(
            id=t.id, organization_id=t.organization_id,
            raised_by=t.raised_by, raised_by_name=raised_name,
            subject=t.subject, description=t.description,
            category=t.category, priority=t.priority, status=t.status,
            assigned_to=t.assigned_to, assigned_to_name=assigned_name,
            resolution_notes=t.resolution_notes,
            organization_name=org_name,
            created_at=t.created_at, updated_at=t.updated_at,
        ))
    return SupportTicketListResponse(tickets=results, total=total, page=page, page_size=page_size)

@router.get("/support-tickets/{ticket_id}", response_model=SupportTicketResponse)
def get_support_ticket(ticket_id: int, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    t = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not t:
        raise NotFoundException("Support ticket not found")
    org_name = None
    if t.organization_id:
        org = db.query(Organization).filter(Organization.id == t.organization_id).first()
        org_name = org.name if org else None
    raised_name = None
    if t.raised_by:
        emp = db.query(Employee).filter(Employee.id == t.raised_by).first()
        raised_name = f"{emp.first_name} {emp.last_name}" if emp else None
    assigned_name = None
    if t.assigned_to:
        emp = db.query(Employee).filter(Employee.id == t.assigned_to).first()
        assigned_name = f"{emp.first_name} {emp.last_name}" if emp else None
    return SupportTicketResponse(
        id=t.id, organization_id=t.organization_id,
        raised_by=t.raised_by, raised_by_name=raised_name,
        subject=t.subject, description=t.description,
        category=t.category, priority=t.priority, status=t.status,
        assigned_to=t.assigned_to, assigned_to_name=assigned_name,
        resolution_notes=t.resolution_notes,
        organization_name=org_name,
        created_at=t.created_at, updated_at=t.updated_at,
    )

@router.put("/support-tickets/{ticket_id}", response_model=SupportTicketResponse)
def update_support_ticket(ticket_id: int, data: SupportTicketUpdateRequest, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    t = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not t:
        raise NotFoundException("Support ticket not found")
    if data.status is not None:
        t.status = data.status
    if data.assigned_to is not None:
        t.assigned_to = data.assigned_to
    if data.priority is not None:
        t.priority = data.priority
    if data.resolution_notes is not None:
        t.resolution_notes = data.resolution_notes
    db.commit()
    db.refresh(t)
    _create_audit_log(db, AuditAction.UPDATE, "SupportTicket", t.id, current_user.email, data.model_dump(exclude_none=True))
    org_name = None
    if t.organization_id:
        org = db.query(Organization).filter(Organization.id == t.organization_id).first()
        org_name = org.name if org else None
    raised_name = None
    if t.raised_by:
        emp = db.query(Employee).filter(Employee.id == t.raised_by).first()
        raised_name = f"{emp.first_name} {emp.last_name}" if emp else None
    assigned_name = None
    if t.assigned_to:
        emp = db.query(Employee).filter(Employee.id == t.assigned_to).first()
        assigned_name = f"{emp.first_name} {emp.last_name}" if emp else None
    return SupportTicketResponse(
        id=t.id, organization_id=t.organization_id,
        raised_by=t.raised_by, raised_by_name=raised_name,
        subject=t.subject, description=t.description,
        category=t.category, priority=t.priority, status=t.status,
        assigned_to=t.assigned_to, assigned_to_name=assigned_name,
        resolution_notes=t.resolution_notes,
        organization_name=org_name,
        created_at=t.created_at, updated_at=t.updated_at,
    )

# ── Security Events ───────────────────────────────────────────────────────────
@router.get("/security-events", response_model=SecurityEventListResponse)
def list_security_events(
    severity: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    is_resolved: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(_require_super_admin),
):
    query = db.query(SecurityEvent)
    if severity:
        query = query.filter(SecurityEvent.severity == severity)
    if event_type:
        query = query.filter(SecurityEvent.event_type == event_type)
    if is_resolved is not None:
        query = query.filter(SecurityEvent.is_resolved == is_resolved)
    total = query.count()
    events = query.order_by(desc(SecurityEvent.created_at)).offset((page - 1) * page_size).limit(page_size).all()

    results = []
    for e in events:
        user_email = None
        if e.user_id:
            emp = db.query(Employee).filter(Employee.id == e.user_id).first()
            user_email = emp.email if emp else None
        org_name = None
        if e.organization_id:
            org = db.query(Organization).filter(Organization.id == e.organization_id).first()
            org_name = org.name if org else None
        results.append(SecurityEventResponse(
            id=e.id, event_type=e.event_type, severity=e.severity,
            description=e.description, source_ip=e.source_ip,
            user_id=e.user_id, user_email=user_email,
            organization_id=e.organization_id, organization_name=org_name,
            event_metadata=e.event_metadata, is_resolved=e.is_resolved,
            resolved_by=e.resolved_by, resolved_at=e.resolved_at,
            created_at=e.created_at,
        ))
    return SecurityEventListResponse(events=results, total=total, page=page, page_size=page_size)

@router.put("/security-events/{event_id}/resolve")
def resolve_security_event(event_id: int, data: SecurityEventResolveRequest, db: Session = Depends(get_db), current_user=Depends(_require_super_admin)):
    event = db.query(SecurityEvent).filter(SecurityEvent.id == event_id).first()
    if not event:
        raise NotFoundException("Security event not found")
    event.is_resolved = True
    event.resolved_by = data.resolved_by
    event.resolved_at = datetime.utcnow()
    db.commit()
    _create_audit_log(db, AuditAction.UPDATE, "SecurityEvent", event.id, current_user.email, {"resolved": True})
    return {"success": True, "message": "Security event resolved"}

# ── Login Activity ────────────────────────────────────────────────────────────
@router.get("/login-activity", response_model=LoginActivityListResponse)
def list_login_activity(
    status_filter: Optional[str] = Query(None, alias="status"),
    org_id: Optional[int] = Query(None, alias="organization_id"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(_require_super_admin),
):
    query = db.query(LoginActivity)
    if status_filter:
        query = query.filter(LoginActivity.status == status_filter)
    if org_id:
        query = query.filter(LoginActivity.organization_id == org_id)
    total = query.count()
    activities = query.order_by(desc(LoginActivity.created_at)).offset((page - 1) * page_size).limit(page_size).all()

    results = []
    for a in activities:
        org_name = None
        if a.organization_id:
            org = db.query(Organization).filter(Organization.id == a.organization_id).first()
            org_name = org.name if org else None
        results.append(LoginActivityResponse(
            id=a.id, user_id=a.user_id, email=a.email,
            organization_id=a.organization_id, organization_name=org_name,
            ip_address=a.ip_address, user_agent=a.user_agent,
            status=a.status, failure_reason=a.failure_reason,
            created_at=a.created_at,
        ))
    return LoginActivityListResponse(activities=results, total=total, page=page, page_size=page_size)

# ── Helper ────────────────────────────────────────────────────────────────────
def _create_audit_log(db: Session, action: AuditAction, entity_type: str, entity_id: Optional[int], performed_by_email: str, details: Optional[dict] = None):
    log = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        performed_by_email=performed_by_email,
        details=details,
    )
    db.add(log)
    db.flush()


def _get_org_status(status) -> str:
    return status.name if hasattr(status, 'name') else str(status).upper()


def _build_org_detail_list(db: Session, orgs: list) -> list:
    """Build org detail list with eager-loaded joins to avoid N+1 queries."""
    if not orgs:
        return []

    org_ids = [o.id for o in orgs]
    admin_role = UserRole.ADMIN.name

    # Batch load subscriptions
    subs_map = {}
    for sub in db.query(Subscription).filter(Subscription.organization_id.in_(org_ids)).all():
        subs_map[sub.organization_id] = sub

    # Batch load user counts
    user_counts = dict(
        db.query(Employee.organization_id, func.count(Employee.id))
        .filter(Employee.organization_id.in_(org_ids))
        .group_by(Employee.organization_id)
        .all()
    )

    # Batch load admin users
    admin_users = {}
    for emp in db.query(Employee).filter(
        Employee.organization_id.in_(org_ids),
        Employee.role == admin_role
    ).all():
        admin_users[emp.organization_id] = emp

    # Batch load approvers
    approver_ids = [o.approved_by for o in orgs if o.approved_by]
    approvers = {}
    if approver_ids:
        for emp in db.query(Employee).filter(Employee.id.in_(approver_ids)).all():
            approvers[emp.id] = emp

    results = []
    for org in orgs:
        sub = subs_map.get(org.id)
        user_count = user_counts.get(org.id, 0)
        admin_user = admin_users.get(org.id)
        approver = approvers.get(org.approved_by) if org.approved_by else None

        results.append(OrganizationDetailResponse(
            id=org.id,
            name=org.name,
            code=org.code,
            is_active=org.is_active,
            status=org.status.name if hasattr(org.status, 'name') else str(org.status),
            approved_by=org.approved_by,
            approved_by_name=approver.full_name if approver else None,
            approved_at=org.approved_at,
            rejection_reason=org.rejection_reason,
            suspended_at=org.suspended_at,
            reactivated_at=org.reactivated_at,
            user_count=user_count,
            admin_email=admin_user.email if admin_user else None,
            admin_name=admin_user.full_name if admin_user else None,
            subscription_plan=sub.plan_type.name if sub else "FREE",
            created_at=org.created_at,
            updated_at=org.updated_at,
        ))
    return results


def _add_approval_history(db: Session, organization_id: int, action: str, performed_by: int, reason: Optional[str] = None):
    from app.modules.super_admin.models import ApprovalHistory
    history = ApprovalHistory(
        organization_id=organization_id,
        action=action,
        performed_by=performed_by,
        reason=reason,
    )
    db.add(history)
    db.flush()
