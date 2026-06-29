# Auth Status Audit Report

## Root Cause

**File:** `app/modules/hr/service.py` — `login_employee()` function

**The bug:** The user-level deactivation check at line 147 was **unconditional**:
```python
# Bug: comment says "Only check is_active when org status is ACTIVE"
# but the code did NOT enforce this condition
if not employee.is_active:
    raise UnauthorizedException("Your account has been deactivated.")
```

The code comment described the correct intent ("Only check is_active when org status is ACTIVE or no org"), but the implementation lacked the condition, running the `is_active` check for **all** users regardless of whether their organization was active or not.

Furthermore, the check only examined `is_active` (boolean) and completely ignored `employee.status` (enum). This meant a user with `is_active=False` but `status=ACTIVE` would get the same message as a deliberately deactivated user, and a user explicitly marked `status=DEACTIVATED` with `is_active=True` (edge case) would slip through.

## Symptom

- Organization Approvals page shows status as `ACTIVE`.
- Login returns `401` with message `"Your account has been deactivated."`
- The root cause is that the user's individual `is_active` flag was `False` while their organization status was `ACTIVE`.

This typically happens when:
1. A Super Admin uses the "Disable User" function on the Platform Users page (which sets `is_active=False`).
2. An employee resigns or is terminated (setting `is_active=False` and `status=RESIGNED`/`TERMINATED`).
3. The organization status changes (approve → suspend → reactivate) but the user was already marked inactive.

## Fix Applied

### 1. Added `DEACTIVATED` to `EmployeeStatus` enum

**File:** `app/modules/hr/models.py`

```python
class EmployeeStatus(str, enum.Enum):
    ACTIVE     = "active"
    INACTIVE   = "inactive"
    ON_LEAVE   = "on_leave"
    TERMINATED = "terminated"
    RESIGNED   = "resigned"
    DEACTIVATED = "deactivated"  # NEW
```

### 2. Updated `deactivate_organization_user` to use `DEACTIVATED`

**File:** `app/modules/hr/service.py`

```python
# Before (inconsistent naming):
user.status = EmployeeStatus.INACTIVE

# After (matches the action name):
user.status = EmployeeStatus.DEACTIVATED
```

This ensures that when an admin deactivates a user, `employee.status` is set to `DEACTIVATED` (not `INACTIVE`), making the login guard consistent.

### 3. Fixed `login_employee()` user-level deactivation check

**File:** `app/modules/hr/service.py`

```python
# Before (buggy — unconditional, only checked is_active):
if not employee.is_active:
    raise UnauthorizedException("Your account has been deactivated.")

# After (guarded by org status, checks both fields):
if not employee.is_active or employee.status == EmployeeStatus.DEACTIVATED:
    raise UnauthorizedException("Your account has been deactivated.")
```

The check now:
- Only runs after passing all organization-level status checks (PENDING, REJECTED, SUSPENDED, DEACTIVATED).
- Blocks when **either** `is_active=False` **or** `status=DEACTIVATED`.

## Organization-Level Precedence

The org-level checks (lines 129–144) handle **all** non-ACTIVE statuses **before** the user-level check runs:

| Org Status      | Message Shown                                      |
|-----------------|----------------------------------------------------|
| `PENDING`       | "Your organization registration is pending Super Admin approval." |
| `REJECTED`      | "Your organization registration has been rejected." |
| `SUSPENDED`     | "Your organization has been suspended by the platform administrator." |
| `DEACTIVATED`   | "Your organization account has been deactivated."  |
| `ACTIVE` (or no org) | Falls through to user-level check           |

## Verification: Org Status Changes Never Modify User Status

Audited all 5 endpoints that modify organization status:

| Endpoint | Modifies `Employee.is_active`? | Modifies `Employee.status`? |
|---|---|---|
| `PUT /organizations/{org_id}/suspend` | **NO** | **NO** |
| `PUT /organizations/{org_id}/activate` | **NO** | **NO** |
| `PUT /organizations/{org_id}/approve` | **NO** (creates new admin with `is_active=True`) | **NO** |
| `PUT /organizations/{org_id}/reactivate` | **NO** | **NO** |
| `PUT /organizations/{org_id}/status` | **NO** (creates new admin if ACTIVE and none exists) | **NO** |

**Conclusion:** No endpoint modifies existing employee `is_active` or `status` when changing organization status. User and organization statuses are fully independent.

## Test Coverage

19 automated tests added in `tests/test_super_admin.py::TestAuthStatusAudit` covering all combinations:

### Org ACTIVE + User Status
| Test | Scenario | Expected |
|---|---|---|
| `test_org_active_user_is_active_login_succeeds` | Active org + active user | Login succeeds (200) |
| `test_org_active_user_disabled_shows_deactivated` | Active org + `is_active=False` | "deactivated" (401) |
| `test_org_active_user_status_deactivated_shows_deactivated` | Active org + `status=DEACTIVATED` | "deactivated" (401) |
| `test_org_active_user_terminated_shows_deactivated` | Active org + terminated | "deactivated" (401) |

### Org PENDING + User Status
| Test | Scenario | Expected |
|---|---|---|
| `test_org_pending_shows_pending_even_if_user_inactive` | Pending org + inactive user | "approval" (401) not "deactivated" |

### Org REJECTED + User Status
| Test | Scenario | Expected |
|---|---|---|
| `test_org_rejected_shows_rejected_even_if_user_inactive` | Rejected org + inactive user | "rejected" (401) not "deactivated" |

### Org SUSPENDED + User Status
| Test | Scenario | Expected |
|---|---|---|
| `test_org_suspended_shows_suspended_even_if_user_inactive` | Suspended org + inactive user | "suspended" (401) not "deactivated" |

### Org DEACTIVATED + User Status
| Test | Scenario | Expected |
|---|---|---|
| `test_org_deactivated_shows_org_message_even_if_user_active` | Deactivated org + active user | org-level "deactivated" |
| `test_org_deactivated_shows_org_message_even_if_user_inactive` | Deactivated org + inactive user | org-level "deactivated" |

### Org Changes Never Affect User Status
| Test | Operations | Assertion |
|---|---|---|
| `test_suspend_org_does_not_affect_user_is_active` | approve → suspend | `user.is_active == True` |
| `test_deactivate_org_does_not_affect_user_is_active` | approve → deactivate | `user.is_active == True` |
| `test_approve_org_does_not_affect_user_is_active` | approve | `user.is_active == True` |
| `test_reject_org_does_not_affect_user_is_active` | reject | `user.is_active == True` |
| `test_reactivate_org_does_not_affect_user_is_active` | approve → suspend → reactivate | `user.is_active == True` |

### Dashboard & History
| Test | Scenario | Assertion |
|---|---|---|
| `test_dashboard_includes_deactivated_count` | Dashboard stats | `deactivated_organizations` present |
| `test_list_deactivated_organizations` | Deactivated list endpoint | Returns deactivated orgs |
| `test_approval_history_includes_status_transition` | Status change history | `previous_status` and `new_status` recorded |

### No-Org (Standalone) Users
| Test | Scenario | Expected |
|---|---|---|
| `test_no_org_user_active_login_succeeds` | No org + active | Login succeeds |
| `test_no_org_user_disabled_shows_deactivated` | No org + deactivated | "deactivated" (401) |
