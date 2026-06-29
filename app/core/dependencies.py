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


# ── Re-export get_db for convenience ─────────────────────────────────────────
# So other files can do: from app.core.dependencies import get_db
# instead of: from app.database import get_db
# Both work — this is just a convenience re-export.
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
    # Decode the token
    payload = decode_access_token(token)
    if payload is None:
        raise UnauthorizedException("Invalid or expired token. Please log in again.")

    # Extract the user's email from the token payload
    # "sub" is the standard JWT field for the subject (usually email or user id)
    email: str = payload.get("sub")
    if email is None:
        raise UnauthorizedException("Token is missing user information.")

    # Import here to avoid circular imports
    from app.modules.employee.models import Employee

    # Look up the user in the database
    user = db.query(Employee).filter(Employee.email == email).first()
    if user is None:
        raise UnauthorizedException("User account not found. Please log in again.")

    return user


# ── Require Admin Role ────────────────────────────────────────────────────────
def get_current_admin(current_user=Depends(get_current_user)):
    """
    Same as get_current_user, but additionally checks that the user
    has the 'admin', 'hr_admin', or 'hr_manager' role.

    Use this on routes that HR and platform admins should access.
    """
    allowed_roles = ["admin", "hr_admin", "hr_manager", "super_admin"]
    if current_user.role not in allowed_roles:
        raise ForbiddenException(
            f"This action requires admin privileges. Your role: {current_user.role}"
        )
    return current_user


# ── Require Organization Admin Role (non-HR modules) ──────────────────────────
def get_current_org_admin(current_user=Depends(get_current_user)):
    """
    More restrictive admin check for non-HR modules (payroll, billing, comply,
    insights). Only 'admin' and 'super_admin' roles are allowed — HR Admin
    is blocked from these modules.
    """
    allowed_roles = ["admin", "super_admin"]
    if current_user.role not in allowed_roles:
        raise ForbiddenException(
            f"This action requires organization admin privileges. Your role: {current_user.role}"
        )
    return current_user
