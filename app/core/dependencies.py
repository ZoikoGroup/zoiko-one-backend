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


def can_create_role(creator_role, target_role) -> bool:
    """
    Check if a user with creator_role is allowed to create a user with target_role.
    Based on role hierarchy: creator must be strictly higher than target.
    """
    creator_level = ROLE_HIERARCHY.get(creator_role)
    target_level = ROLE_HIERARCHY.get(target_role)
    if creator_level is None or target_level is None:
        return False
    return creator_level < target_level


def get_role_level(role) -> int:
    """Get the hierarchy level for a role value. Lower = higher privilege."""
    return ROLE_HIERARCHY.get(role, 999)


def get_allowed_creation_roles(creator_role) -> list:
    """Return the list of target roles the creator_role is allowed to create."""
    creator_level = ROLE_HIERARCHY.get(creator_role, 999)
    return [r for r, lvl in ROLE_HIERARCHY.items() if lvl > creator_level]


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
