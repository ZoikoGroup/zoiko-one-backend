"""
Email service for sending approval workflow notifications.
Templates are stored in app/email_templates/ as HTML files.
"""

import os
import logging

logger = logging.getLogger("zoiko")

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "email_templates")


def _load_template(name: str) -> str:
    """Load an HTML email template from the templates directory."""
    path = os.path.join(TEMPLATE_DIR, name)
    if not os.path.exists(path):
        logger.warning(f"Email template not found: {path}")
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _render_template(template: str, context: dict) -> str:
    """Simple template renderer replacing {{key}} with context values."""
    result = template
    for key, value in context.items():
        if value is None:
            value = ""
        result = result.replace("{{" + key + "}}", str(value))
    return result


def send_approval_email(email: str, template_name: str, context: dict) -> bool:
    """Send an approval workflow email.

    Currently logs the email. In production, integrate with SMTP settings.
    """
    template = _load_template(template_name)
    if not template:
        logger.warning(f"Cannot send email to {email}: template {template_name} not found")
        return False

    body = _render_template(template, context)

    logger.info(f"[email] To: {email}, Template: {template_name}")
    logger.info(f"[email] Body preview: {body[:200]}...")

    # In production, integrate with your SMTP provider here:
    # from app.modules.super_admin.models import PlatformSetting
    # smtp_host = db.query(PlatformSetting).filter(PlatformSetting.key == "smtp_host").first()
    # ... send email via smtplib ...

    return True


def send_registration_received(email: str, org_name: str):
    return send_approval_email(email, "registration_received.html", {
        "organization_name": org_name,
    })


def send_approved(email: str, org_name: str, login_url: str = "http://localhost:5173/login"):
    return send_approval_email(email, "approved.html", {
        "organization_name": org_name,
        "login_url": login_url,
    })


def send_rejected(email: str, org_name: str, reason: str):
    return send_approval_email(email, "rejected.html", {
        "organization_name": org_name,
        "reason": reason,
    })


def send_suspended(email: str, org_name: str):
    return send_approval_email(email, "suspended.html", {
        "organization_name": org_name,
    })


def send_reactivated(email: str, org_name: str, login_url: str = "http://localhost:5173/login"):
    return send_approval_email(email, "reactivated.html", {
        "organization_name": org_name,
        "login_url": login_url,
    })


def send_password_reset(email: str, temp_password: str, first_name: str):
    return send_approval_email(email, "password_reset.html", {
        "first_name": first_name,
        "temporary_password": temp_password,
        "login_url": "http://localhost:5173/login",
    })
