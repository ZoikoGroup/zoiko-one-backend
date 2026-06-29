# Auth Flow Trace Report

## 1. Complete Login Flow

### Frontend → Backend Trace

```
LoginPage.jsx                          →  User enters email + password, clicks "Sign In"
  └─ handleSubmit()                    →  calls login() from AuthContext
      └─ AuthContext.jsx               →  calls loginRequest() from authService.js
          └─ authService.js            →  api.post("/auth/login", { email, password }, { auth: false })
              └─ api.js                →  fetch POST http://localhost:8000/auth/login
                                        ↓
hr/router.py:149                       →  login() receives request
  └─ service.login_employee(db, data)  →  executes auth business logic
      └─ returns TokenResponse         →  { access_token, refresh_token, token_type, employee }
                                        ↓
authService.js:18                      →  setSession() stores accessToken, refreshToken, user in localStorage
AuthContext.jsx:46                     →  setUser(loggedInUser)
LoginPage.jsx:79                       →  navigate(from, { replace: true })  →  redirects to role-based default
```

## 2. Decision Points in `login_employee()` (hr/service.py:120-196)

```
START: LoginRequest(email, password)
│
├─ STEP 1: User Lookup
│   └─ Query: Employee WHERE email = data.email
│   ├── NOT FOUND → 401 "Invalid email or password."  ← STOP
│   └── FOUND → Log user details, continue
│
├─ STEP 2: Password Validation
│   └─ verify_password(data.password, employee.hashed_password)
│   ├── INVALID → 401 "Invalid email or password."  ← STOP
│   └── VALID   → continue
│
├─ STEP 3: Organization Lookup (multi-tenant resolution)
│   └─ Only if employee.organization_id is not None
│   ├── Query: Organization WHERE id = employee.organization_id
│   ├── ORG NOT FOUND → Log warning, continue (unusual state)
│   └── ORG FOUND → continue to Step 4
│
├─ STEP 4: Organization Status Check (takes precedence over user status)
│   ├── PENDING     → 401 "Your organization registration is pending Super Admin approval."  ← STOP
│   ├── REJECTED    → 401 "Your organization registration has been rejected."  ← STOP
│   ├── SUSPENDED   → 401 "Your organization has been suspended by the platform administrator."  ← STOP
│   ├── DEACTIVATED → 401 "Your organization account has been deactivated."  ← STOP
│   └── ACTIVE      → continue to Step 5
│
├─ STEP 5: User Status Check (only reached if org is ACTIVE or no org)
│   ├── is_active=False   → 401 "Your account has been deactivated."  ← STOP  *** ROOT CAUSE ***
│   ├── status=DEACTIVATED → 401 "Your account has been deactivated."  ← STOP
│   └── Both pass         → continue
│
└─ STEP 6: Token Generation
    └─ create_access_token(sub=email, role=role, id=id)
    └─ create_refresh_token(sub=email, id=id, expires=7d)
    └─ Return { access_token, refresh_token, token_type, employee }
```

## 3. Root Cause of the Failed Login

### Symptom
- Organization "Zoiko" (id=135, code=ZOIKO_1) is **ACTIVE**.
- Login for user `Lennox@gmail.com` returns: **"Your account has been deactivated."**

### Database Evidence

```
Organization (id=135):
  name=Zoiko, code=ZOIKO_1, is_active=True, status=ACTIVE  ← Org is fine

Employee (id=188):
  email=Lennox@gmail.com, organization_id=135
  is_active=False, status=ACTIVE                            ← User is inactive!
```

### Root Cause: User `is_active=False`

The user `Lennox@gmail.com` has **`is_active=False`** while their organization "Zoiko" is **ACTIVE**.

The login flow proceeds through:
1. ✅ User found
2. ✅ Password valid
3. ✅ Organization found (Zoiko, id=135)
4. ✅ Organization status = ACTIVE (passes through)
5. ❌ **Blocked at Step 5**: `not employee.is_active` is `True` → raises `UnauthorizedException("Your account has been deactivated.")`

The `is_active=False` was likely set by:
- A Super Admin using the "Disable User" function on the Platform Users page (`PUT /super-admin/users/{id}/disable`), or
- An admin action in the user's org that set `is_active=False` without changing `status`

## 4. Resolution

To fix: re-enable the user by setting `is_active=True` and `status=ACTIVE`.

```python
# Via direct DB fix:
user = db.query(Employee).filter(Employee.email == "Lennox@gmail.com").first()
user.is_active = True
user.status = EmployeeStatus.ACTIVE
db.commit()
```

Or via the Super Admin enable API: `PUT /super-admin/users/{id}/enable`

## 5. Multi-Tenant Login Verification

The login correctly resolves multi-tenant context:

```
employee.organization_id  →  used to look up the Organization
                           →  org.status checked against OrganizationStatus enum
```

This ensures that:
- A user in org A is only checked against org A's status (not org B's)
- If a user has no organization_id, only user-level checks apply
- Super admins with org_id=1 (Zoiko Inc) are checked against Zoiko Inc's status

## 6. Org Status ↔ User Status Independence

**Confirmed: Changing organization status NEVER modifies user `is_active` or `status`.**

Audited all 5 org status endpoints:

| Endpoint | Modifies Employee.is_active? | Modifies Employee.status? |
|---|---|---|
| `PUT /organizations/{org_id}/status` (unified) | **NO** (comment explicit: "NEVER modifies user.is_active or user.status") | **NO** |
| `PUT /organizations/{org_id}/suspend` | **NO** | **NO** |
| `PUT /organizations/{org_id}/activate` | **NO** | **NO** |
| `PUT /organizations/{org_id}/approve` | **NO** (creates new admin with `is_active=True`, never touches existing) | **NO** |
| `PUT /organizations/{org_id}/reactivate` | **NO** | **NO** |
| `PUT /organizations/{org_id}/reject` | **NO** | **NO** |

## 7. Auth Logging Added (Development Only)

Added `[AUTH]`-prefixed log statements at every decision point in `hr/service.py:login_employee()`:

```
[AUTH] User found: id=..., email=..., is_active=..., status=..., organization_id=..., role=...
[AUTH] Password valid for user: ...
[AUTH] Organization found: id=..., name=..., status=..., is_active=...
[AUTH] Organization status OK: ACTIVE for user ...
[AUTH] User has no organization_id (standalone): ...
[AUTH] Login blocked: user is_active=False for email=...     ← Key diagnostic line
[AUTH] Login blocked: user status=DEACTIVATED for email=...
[AUTH] Login blocked: org PENDING/REJECTED/SUSPENDED/DEACTIVATED for user ...
[AUTH] All checks passed for user: ...
[AUTH] Login successful: email=..., id=..., role=...
[AUTH] User not found: email=...
[AUTH] Invalid password for user: ...
[AUTH] Organization not found: id=... for user ...
```

Set `log_level = "DEBUG"` in config to see these in the server output.

## 8. Summary of All Findings

| # | Finding | Status |
|---|---|---|
| 1 | Org "Zoiko" (id=135) is ACTIVE | ✅ Confirmed |
| 2 | User `Lennox@gmail.com` has `is_active=False` | ✅ Confirmed |
| 3 | Step 5 (user deactivation check) is what returns "deactivated" | ✅ Confirmed |
| 4 | Org-level org and user-level status are independent | ✅ Confirmed |
| 5 | Org status changes never modify user records | ✅ Confirmed |
| 6 | Multi-tenant resolution correctly uses employee.organization_id | ✅ Confirmed |
| 7 | Detailed [AUTH] logging added to `login_employee()` | ✅ Done |
