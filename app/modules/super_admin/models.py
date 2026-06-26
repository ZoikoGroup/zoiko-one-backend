import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class PlanType(str, enum.Enum):
    TRIAL = "trial"
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING = "pending"

class ProductStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"

class AuditAction(str, enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SUSPEND = "suspend"
    ACTIVATE = "activate"
    LOGIN = "login"
    LOGOUT = "logout"
    CONFIG_CHANGE = "config_change"
    APPROVED = "approved"
    REJECTED = "rejected"
    REACTIVATED = "reactivated"

class HealthStatus(str, enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"

class Subscription(Base):
    __tablename__ = "super_admin_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, unique=True)
    plan_type = Column(Enum(PlanType), nullable=False, default=PlanType.FREE)
    status = Column(Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.PENDING)
    start_date = Column(DateTime, server_default=func.now())
    end_date = Column(DateTime, nullable=True)
    max_users = Column(Integer, default=15)
    max_storage_gb = Column(Integer, default=5)
    features = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    organization = relationship("Organization", backref="subscription")

class Product(Base):
    __tablename__ = "super_admin_products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(100), nullable=True)
    status = Column(Enum(ProductStatus), nullable=False, default=ProductStatus.ACTIVE)
    is_core = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

class OrganizationProduct(Base):
    __tablename__ = "super_admin_organization_products"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("super_admin_products.id"), nullable=False)
    is_enabled = Column(Boolean, default=False)
    enabled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    organization = relationship("Organization")
    product = relationship("Product")

class PlatformSetting(Base):
    __tablename__ = "super_admin_platform_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(200), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), default="general")
    is_encrypted = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

class AuditLog(Base):
    __tablename__ = "super_admin_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(Enum(AuditAction), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(Integer, nullable=True)
    performed_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    performed_by_email = Column(String(255), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    performer = relationship("Employee", backref="audit_logs")

class SystemHealthCheck(Base):
    __tablename__ = "super_admin_system_health"

    id = Column(Integer, primary_key=True, index=True)
    component = Column(String(100), nullable=False)
    status = Column(Enum(HealthStatus), nullable=False)
    message = Column(Text, nullable=True)
    response_time_ms = Column(Float, nullable=True)
    checked_at = Column(DateTime, server_default=func.now())


class Notification(Base):
    __tablename__ = "super_admin_notifications"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), default="info")
    priority = Column(String(20), default="normal")
    is_read = Column(Boolean, default=False)
    target_org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    target_user_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class SupportTicket(Base):
    __tablename__ = "super_admin_support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    raised_by = Column(Integer, ForeignKey("employees.id"), nullable=False)
    subject = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), default="general")
    priority = Column(String(20), default="normal")
    status = Column(String(20), default="open")
    assigned_to = Column(Integer, ForeignKey("employees.id"), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    organization = relationship("Organization")
    raised_by_user = relationship("Employee", foreign_keys=[raised_by])
    assigned_to_user = relationship("Employee", foreign_keys=[assigned_to])


class SecurityEvent(Base):
    __tablename__ = "super_admin_security_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(100), nullable=False)
    severity = Column(String(20), default="info")
    description = Column(Text, nullable=True)
    source_ip = Column(String(50), nullable=True)
    user_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    event_metadata = Column("metadata", JSON, nullable=True)
    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("Employee", foreign_keys=[user_id])
    resolver = relationship("Employee", foreign_keys=[resolved_by])


class ApprovalHistory(Base):
    __tablename__ = "super_admin_approval_history"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    action = Column(String(50), nullable=False)
    performed_by = Column(Integer, ForeignKey("employees.id"), nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    organization = relationship("Organization", foreign_keys=[organization_id])
    performer = relationship("Employee", foreign_keys=[performed_by])


class LoginActivity(Base):
    __tablename__ = "super_admin_login_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    email = Column(String(255), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    status = Column(String(20), default="success")
    failure_reason = Column(String(200), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("Employee", foreign_keys=[user_id])
