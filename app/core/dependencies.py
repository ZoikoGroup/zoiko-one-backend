"""
core/dependencies.py
--------------------
Reusable "dependencies" injected into routes via FastAPI's Depends().

Think of dependencies like plug-in helpers. Instead of writing the same
"get database session" or "check who is logged in" code in every single
route, you write it once here and inject it wherever needed.

Usage in a route:
    @router.get("/something")
    def my_route(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
        ...
"""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import decode_access_token
from app.core.exceptions import ForbiddenException, UnauthorizedException

# This tells FastAPI: "tokens are sent to /auth/login endpoint"
# FastAPI uses this to show a login button in the /docs page
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── Role Hierarchy ───────────────────────────────────────────────────────────
# Lower number = higher privilege
ROLE_HIERARCHY = {
    "super_admin": 0,
    "admin": 1,
    "hr_admin": 2,
    "hr_manager": 3,
    "manager": 4,
    "employee": 5,
}

# ── Role Creation Rules ─────────────────────────────────────────────────────
# Explicit mapping of which target roles each creator role is allowed to create.
# This overrides the simple hierarchy check to match specific business rules.
ROLE_CREATION_RULES = {
    "super_admin": ["admin"],
    "admin": ["admin", "hr_admin", "manager", "employee"],
    "hr_admin": ["hr_admin", "hr_manager", "manager", "employee"],
    "hr_manager": ["hr_manager", "manager", "employee"],
    "manager": [],
    "employee": [],
}


def can_create_role(creator_role, target_role) -> bool:
    """
    Check if a user with creator_role is allowed to create a user with target_role.
    Uses explicit ROLE_CREATION_RULES mapping.
    """
    allowed = ROLE_CREATION_RULES.get(creator_role, [])
    return target_role in allowed


def get_role_level(role) -> int:
    """Get the hierarchy level for a role value. Lower = higher privilege."""
    return ROLE_HIERARCHY.get(role, 999)


def get_allowed_creation_roles(creator_role) -> list:
    """Return the list of target roles the creator_role is allowed to create."""
    return ROLE_CREATION_RULES.get(creator_role, [])


# ── Re-export get_db for convenience ─────────────────────────────────────────
__all__ = ["get_db", "get_current_user", "get_current_admin", "get_current_org_admin"]


# ── Get Current Logged-In User ────────────────────────────────────────────────
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    Reads the JWT token from the request header, decodes it,
    and returns the current user's information.

    FastAPI automatically reads the Authorization header:
        Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

    Raises UnauthorizedException if:
      - No token provided
      - Token is expired
      - Token is invalid / tampered
      - User no longer exists in DB
    """
    payload = decode_access_token(token)
    if payload is None:
        raise UnauthorizedException("Invalid or expired token. Please log in again.")

    email: str = payload.get("sub")
    if email is None:
        raise UnauthorizedException("Token is missing user information.")

    from app.modules.hr.models import Employee

    user = db.query(Employee).filter(Employee.email == email).first()
    if user is None:
        raise UnauthorizedException("User account not found. Please log in again.")

    return user


# ── Require Admin Role ────────────────────────────────────────────────────────
def get_current_admin(current_user=Depends(get_current_user)):
    """
    Same as get_current_user, but additionally checks that the user
    has an admin-level role based on role hierarchy.
    """
    allowed_roles = ["admin", "hr_admin", "hr_manager", "super_admin"]
    role_val = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    import logging; logging.getLogger(__name__).warning(f"[get_current_admin] user={current_user.email} role_raw={current_user.role!r} role_val={role_val} type={type(current_user.role).__name__}")
    if role_val not in allowed_roles:
        raise ForbiddenException(
            f"This action requires admin privileges. Your role: {role_val}"
        )
    return current_user


# ── Require Organization Admin Role (non-HR modules) ──────────────────────────
def get_current_org_admin(current_user=Depends(get_current_user)):
    """
    More restrictive admin check for non-HR modules (payroll, billing, comply,
    insights). Only 'admin' and 'super_admin' roles are allowed — HR Admin
    is blocked from these modules.
    """
    role_val = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    allowed_roles = ["admin", "super_admin"]
    if role_val not in allowed_roles:
        raise ForbiddenException(
            f"This action requires organization admin privileges. Your role: {role_val}"
        )
    return current_user


# ── Organization Isolation Dependency ────────────────────────────────────────
def get_organization_id(current_user=Depends(get_current_user)) -> int:
    """
    Returns the current user's organization_id.
    Raises ForbiddenException if user has no organization_id.
    Super Admin can bypass organization filtering via get_super_admin_organization_id.
    """
    role_val = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    
    if role_val == "super_admin":
        raise ForbiddenException(
            "Super Admin must use get_super_admin_organization_id() to explicitly select an organization."
        )
    
    if current_user.organization_id is None:
        raise ForbiddenException("User is not associated with any organization.")
    
    return current_user.organization_id


def get_super_admin_organization_id(
    organization_id: int = None,
    current_user=Depends(get_current_user)
) -> int:
    """
    Returns organization_id for Super Admin.
    Super Admin MUST explicitly provide organization_id via query parameter or header.
    Non-Super Admin users cannot use this dependency.
    """
    role_val = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    
    if role_val != "super_admin":
        raise ForbiddenException("Only Super Admin can use this dependency.")
    
    if organization_id is None:
        raise ForbiddenException(
            "Super Admin must provide organization_id query parameter to access organization data."
        )
    
    from app.database import get_db
    from app.modules.hr.models import Organization
    from sqlalchemy.orm import Session
    from fastapi import Depends
    
    # Note: We can't use Depends here since this is already a dependency.
    # The validation will happen in the service layer.
    return organization_id


def require_organization_access(
    target_organization_id: int,
    current_user=Depends(get_current_user)
) -> bool:
    """
    Dependency to verify that the current user has access to the target organization.
    - Super Admin: can access any organization (if explicitly provided)
    - Other roles: can only access their own organization_id
    """
    role_val = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    
    if role_val == "super_admin":
        return True
    
    if current_user.organization_id != target_organization_id:
        raise ForbiddenException(
            f"Access denied: You can only access data from your own organization (ID: {current_user.organization_id})."
        )
    
    return True
