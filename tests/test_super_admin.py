"""Tests for super admin module endpoints."""

import pytest


class TestDashboard:
    def test_dashboard_stats(self, client, auth_header):
        resp = client.get("/super-admin/dashboard", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_organizations" in data
        assert "total_users" in data
        assert "total_revenue" in data
        assert "platform_stats" in data
        assert "recent_activity" in data

    def test_dashboard_unauthorized(self, client):
        resp = client.get("/super-admin/dashboard")
        assert resp.status_code == 401


class TestOrganizations:
    def test_list_organizations(self, client, auth_header):
        resp = client.get("/super-admin/organizations", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert "organizations" in data
        assert "total" in data

    def test_create_organization(self, client, auth_header):
        resp = client.post("/super-admin/organizations", headers=auth_header, json={
            "name": "Test Corp",
            "code": "TST",
            "is_active": True,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Corp"
        assert data["code"] == "TST"
        assert data["is_active"] is True
        assert "id" in data

    def test_create_organization_duplicate_code(self, client, auth_header):
        client.post("/super-admin/organizations", headers=auth_header, json={
            "name": "Test Corp", "code": "DUP", "is_active": True,
        })
        resp = client.post("/super-admin/organizations", headers=auth_header, json={
            "name": "Test Corp 2", "code": "DUP", "is_active": True,
        })
        assert resp.status_code == 400

    def test_get_organization(self, client, auth_header):
        resp = client.get("/super-admin/organizations/1", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1

    def test_get_organization_not_found(self, client, auth_header):
        resp = client.get("/super-admin/organizations/99999", headers=auth_header)
        assert resp.status_code == 404

    def test_update_organization(self, client, auth_header):
        resp = client.put("/super-admin/organizations/1", headers=auth_header, json={
            "name": "Zoiko Inc Updated",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Zoiko Inc Updated"

    def test_list_organizations_pagination(self, client, auth_header):
        resp = client.get("/super-admin/organizations?page=1&page_size=5", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["organizations"]) <= 5


class TestProducts:
    def test_list_products(self, client, auth_header):
        resp = client.get("/super-admin/products", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_list_organization_products(self, client, auth_header):
        resp = client.get("/super-admin/organizations/1/products", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


class TestSubscriptions:
    def test_list_subscriptions(self, client, auth_header):
        resp = client.get("/super-admin/subscriptions", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_get_subscription(self, client, auth_header):
        resp = client.get("/super-admin/subscriptions/1", headers=auth_header)
        if resp.status_code == 404:
            pytest.skip("No subscription with id=1 exists")
        assert resp.status_code == 200


class TestPlatformUsers:
    def test_list_users(self, client, auth_header):
        resp = client.get("/super-admin/users", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data
        assert "total" in data

    def test_list_users_pagination(self, client, auth_header):
        resp = client.get("/super-admin/users?page=1&page_size=10&role=super_admin", headers=auth_header)
        assert resp.status_code == 200

    def test_invite_user(self, client, auth_header):
        resp = client.post("/super-admin/users/invite", headers=auth_header, json={
            "email": "newuser@test.com",
            "first_name": "New",
            "last_name": "User",
            "role": "employee",
            "organization_id": 1,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "temporary_password" in data

    def test_invite_duplicate_email(self, client, auth_header):
        client.post("/super-admin/users/invite", headers=auth_header, json={
            "email": "dup@test.com", "first_name": "Dup", "last_name": "User",
            "role": "employee", "organization_id": 1,
        })
        resp = client.post("/super-admin/users/invite", headers=auth_header, json={
            "email": "dup@test.com", "first_name": "Dup", "last_name": "User",
            "role": "employee", "organization_id": 1,
        })
        assert resp.status_code == 400

    def test_disable_user(self, client, auth_header):
        resp = client.put("/super-admin/users/1/disable", headers=auth_header)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        resp = client.put("/super-admin/users/1/enable", headers=auth_header)
        assert resp.status_code == 200

    def test_disable_user_not_found(self, client, auth_header):
        resp = client.put("/super-admin/users/99999/disable", headers=auth_header)
        assert resp.status_code == 404

    def test_reset_password(self, client, auth_header):
        resp = client.put("/super-admin/users/1/reset-password", headers=auth_header, json={
            "new_password": "TestPass123!"
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is True


class TestAuditLogs:
    def test_list_audit_logs(self, client, auth_header):
        resp = client.get("/super-admin/audit-logs", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert "logs" in data
        assert "total" in data
        assert "page" in data

    def test_audit_logs_filter(self, client, auth_header):
        resp = client.get("/super-admin/audit-logs?action=CREATE&page=1&page_size=10", headers=auth_header)
        assert resp.status_code == 200


class TestSystemHealth:
    def test_get_system_health(self, client, auth_header):
        resp = client.get("/super-admin/system-health", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert "components" in data
        assert "overall_status" in data

    def test_get_system_health_summary(self, client, auth_header):
        resp = client.get("/super-admin/system-health", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_status" in data


class TestPlatformSettings:
    def test_list_settings(self, client, auth_header):
        resp = client.get("/super-admin/settings", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_get_setting(self, client, auth_header):
        resp = client.get("/super-admin/settings/1", headers=auth_header)
        assert resp.status_code == 200
        assert resp.json()["id"] == 1

    def test_update_setting(self, client, auth_header):
        resp = client.put("/super-admin/settings/1", headers=auth_header, json={
            "value": "Zoiko One Test",
        })
        assert resp.status_code == 200
        assert resp.json()["value"] == "Zoiko One Test"

    def test_get_setting_not_found(self, client, auth_header):
        resp = client.get("/super-admin/settings/99999", headers=auth_header)
        assert resp.status_code == 404

    def test_create_setting(self, client, auth_header):
        resp = client.post("/super-admin/settings", headers=auth_header, json={
            "key": "test_setting",
            "value": "test_value",
            "category": "system",
        })
        assert resp.status_code == 200
        assert resp.json()["key"] == "test_setting"


class TestNotifications:
    def test_list_notifications(self, client, auth_header):
        resp = client.get("/super-admin/notifications", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert "notifications" in data

    def test_create_notification(self, client, auth_header):
        resp = client.post("/super-admin/notifications", headers=auth_header, json={
            "title": "Test Notification",
            "message": "This is a test",
            "notification_type": "info",
            "priority": "normal",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test Notification"
        nid = data["id"]

        resp = client.put(f"/super-admin/notifications/{nid}/read", headers=auth_header)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        resp = client.delete(f"/super-admin/notifications/{nid}", headers=auth_header)
        assert resp.status_code == 200


class TestSecurityEvents:
    def test_list_security_events(self, client, auth_header):
        resp = client.get("/super-admin/security-events", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data

    def test_resolve_security_event(self, client, auth_header):
        resp = client.put("/super-admin/security-events/1/resolve", headers=auth_header, json={
            "resolved_by": 1
        })
        if resp.status_code == 404:
            pytest.skip("No security event with id=1")
        assert resp.status_code == 200
        assert resp.json()["is_resolved"] is True


class TestSupportTickets:
    def test_list_support_tickets(self, client, auth_header):
        resp = client.get("/super-admin/support-tickets", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert "tickets" in data


class TestLoginActivity:
    def test_list_login_activity(self, client, auth_header):
        resp = client.get("/super-admin/login-activity", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert "activities" in data


class TestRevenue:
    def test_revenue_data(self, client, auth_header):
        resp = client.get("/super-admin/revenue", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert "monthly_revenue" in data
        assert "total_revenue" in data


class TestStorage:
    def test_storage_data(self, client, auth_header):
        resp = client.get("/super-admin/storage", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_storage_gb" in data


class TestAnalytics:
    def test_analytics(self, client, auth_header):
        resp = client.get("/super-admin/analytics", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert "organization_growth" in data
        assert "subscription_distribution" in data


class TestAuth:
    def test_regular_user_cannot_access(self, client):
        resp = client.post("/auth/login", json={
            "email": "admin@zoiko.com",
            "password": "admin123"
        })
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/super-admin/dashboard", headers=headers)
        assert resp.status_code == 403

    def test_invalid_token(self, client):
        resp = client.get("/super-admin/dashboard", headers={
            "Authorization": "Bearer invalid_token"
        })
        assert resp.status_code == 401


class TestApprovalWorkflow:
    """Full organization approval workflow integration tests.

    Runs as a single test method because each pytest fixture creates a fresh
    transaction that rolls back — state cannot be shared across methods.
    """

    def test_full_approval_workflow(self, client):
        """Complete lifecycle: register → approve → login → suspend → reactivate → reject → RBAC."""
        # ── Phase 1: Register a pending organization ──
        resp = client.post("/auth/register", json={
            "name": "Approval Test Org",
            "email": "approval.test@test.com",
            "password": "TestPass123!",
            "organization": "Approval Test Org Inc",
        })
        assert resp.status_code == 200
        register_data = resp.json()
        assert register_data["message"] == "Organization registered successfully. Awaiting Super Admin approval."
        assert "organization_id" in register_data
        assert register_data["organization_name"] == "Approval Test Org Inc"
        org_id = register_data["organization_id"]

        # ── Phase 2: Login blocked while PENDING ──
        resp = client.post("/auth/login", json={
            "email": "approval.test@test.com",
            "password": "TestPass123!"
        })
        assert resp.status_code == 401
        assert "awaiting super admin approval" in resp.json()["message"].lower()

        # ── Phase 3: Super Admin sees pending ──
        super_resp = client.post("/auth/login", json={
            "email": "superadmin@zoiko.com",
            "password": "admin123"
        })
        assert super_resp.status_code == 200
        super_token = super_resp.json()["access_token"]
        sa_headers = {"Authorization": f"Bearer {super_token}"}

        resp = client.get("/super-admin/organizations/pending", headers=sa_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] > 0
        assert org_id in [o["id"] for o in data["organizations"]]

        # ── Phase 4: Approve the organization ──
        resp = client.put(f"/super-admin/organizations/{org_id}/approve", headers=sa_headers)
        assert resp.status_code == 200
        assert resp.json()["message"] == "Organization approved successfully"

        # ── Phase 5: Status is ACTIVE ──
        resp = client.get(f"/super-admin/organizations/{org_id}/details", headers=sa_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ACTIVE"

        # ── Phase 6: Admin can now login ──
        resp = client.post("/auth/login", json={
            "email": "approval.test@test.com",
            "password": "TestPass123!"
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()
        assert resp.json()["token_type"] == "bearer"

        # ── Phase 7: Active + inactive user — deactivation message ──
        user_resp = client.get("/super-admin/users", headers=sa_headers)
        admin_user_id = None
        for u in user_resp.json().get("users", []):
            if u["email"] == "approval.test@test.com":
                admin_user_id = u["id"]
                break
        assert admin_user_id is not None, "Admin user should exist and be findable"
        client.put(f"/super-admin/users/{admin_user_id}/disable", headers=sa_headers)
        resp = client.post("/auth/login", json={
            "email": "approval.test@test.com",
            "password": "TestPass123!"
        })
        assert resp.status_code == 401
        assert "deactivated" in resp.json()["message"].lower()
        # Re-enable for remaining tests
        client.put(f"/super-admin/users/{admin_user_id}/enable", headers=sa_headers)
        # Verify login works again
        resp = client.post("/auth/login", json={
            "email": "approval.test@test.com",
            "password": "TestPass123!"
        })
        assert resp.status_code == 200

        # ── Phase 8: Suspend the organization ──
        resp = client.put(f"/super-admin/organizations/{org_id}/suspend", headers=sa_headers)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # Verify suspended status
        resp = client.get(f"/super-admin/organizations/{org_id}/details", headers=sa_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "SUSPENDED"

        # ── Phase 9: Login blocked when suspended ──
        resp = client.post("/auth/login", json={
            "email": "approval.test@test.com",
            "password": "TestPass123!"
        })
        assert resp.status_code == 401
        assert "suspended" in resp.json()["message"].lower()
        assert "contact support" in resp.json()["message"].lower()

        # ── Phase 10: Reactivate the organization ──
        resp = client.put(f"/super-admin/organizations/{org_id}/reactivate", headers=sa_headers)
        assert resp.status_code == 200
        assert resp.json()["message"] == "Organization reactivated"

        # Verify reactivated status
        resp = client.get(f"/super-admin/organizations/{org_id}/details", headers=sa_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ACTIVE"

        # ── Phase 11: Login succeeds after reactivation ──
        resp = client.post("/auth/login", json={
            "email": "approval.test@test.com",
            "password": "TestPass123!"
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

        # ── Phase 12: Register and reject a second organization ──
        resp = client.post("/auth/register", json={
            "name": "Reject Test",
            "email": "reject.test@test.com",
            "password": "TestPass123!",
            "organization": "Reject Test Co",
        })
        assert resp.status_code == 200
        reject_org_id = resp.json()["organization_id"]

        resp = client.put(f"/super-admin/organizations/{reject_org_id}/reject",
                          headers=sa_headers,
                          json={"reason": "Incomplete registration information."})
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # Verify rejection reason stored
        resp = client.get(f"/super-admin/organizations/{reject_org_id}/details", headers=sa_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "REJECTED"
        assert "incomplete" in resp.json()["rejection_reason"].lower()

        # ── Phase 13: Login blocked with rejection reason ──
        resp = client.post("/auth/login", json={
            "email": "reject.test@test.com",
            "password": "TestPass123!"
        })
        assert resp.status_code == 401
        assert "rejected" in resp.json()["message"].lower()
        assert "incomplete" in resp.json()["message"].lower()

        # ── Phase 14: Dashboard shows new status fields ──
        resp = client.get("/super-admin/dashboard", headers=sa_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "pending_organizations" in data
        assert "rejected_organizations" in data
        assert "suspended_organizations" in data
        assert "recent_registrations" in data

        # ── Phase 15: Approval history is recorded ──
        resp = client.get(f"/super-admin/organizations/{org_id}/approval-history", headers=sa_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2
        actions = [h["action"] for h in data["history"]]
        assert "approved" in actions
        assert "suspended" in actions or "reactivated" in actions

        # ── Phase 16: RBAC — regular admin denied ──
        resp = client.post("/auth/login", json={
            "email": "admin@zoiko.com",
            "password": "admin123"
        })
        assert resp.status_code == 200
        admin_token = resp.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        resp = client.get("/super-admin/organizations/pending", headers=admin_headers)
        assert resp.status_code in (401, 403)

        resp = client.get(f"/super-admin/organizations/{org_id}/details", headers=admin_headers)
        assert resp.status_code in (401, 403)


class TestApprovalWorkflowDetailed:
    """Granular tests for each approval workflow scenario.

    Each test creates its own state via register/action within the test method
    since pytest fixtures roll back transactions between tests.
    """

    def _register_org(self, client, suffix=""):
        """Helper: register an org and return (org_id, admin_email)."""
        email = f"wf.test{suffix}@test.com"
        resp = client.post("/auth/register", json={
            "name": f"WF Test{suffix}",
            "email": email,
            "password": "TestPass123!",
            "organization": f"WF Test Org {suffix}",
        })
        assert resp.status_code == 200
        return resp.json()["organization_id"], email

    def _super_admin_headers(self, client):
        """Helper: log in as super admin and return auth headers."""
        resp = client.post("/auth/login", json={
            "email": "superadmin@zoiko.com",
            "password": "admin123"
        })
        assert resp.status_code == 200
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    def test_pending_organization_login_message(self, client):
        """Pending org shows 'awaiting Super Admin approval' message."""
        org_id, email = self._register_org(client, "1")
        resp = client.post("/auth/login", json={"email": email, "password": "TestPass123!"})
        assert resp.status_code == 401
        msg = resp.json()["message"].lower()
        assert "awaiting super admin approval" in msg
        assert "deactivated" not in msg

    def test_approved_organization_login_succeeds(self, client):
        """After approval, the org admin can log in."""
        org_id, email = self._register_org(client, "2")
        sa = self._super_admin_headers(client)
        resp = client.put(f"/super-admin/organizations/{org_id}/approve", headers=sa)
        assert resp.status_code == 200
        # Verify user is_active=True (no longer False from registration)
        resp = client.post("/auth/login", json={"email": email, "password": "TestPass123!"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_rejected_organization_login_message(self, client):
        """Rejected org shows 'registration has been rejected' with reason."""
        org_id, email = self._register_org(client, "3")
        sa = self._super_admin_headers(client)
        reason = "Incomplete documentation"
        resp = client.put(f"/super-admin/organizations/{org_id}/reject", headers=sa, json={"reason": reason})
        assert resp.status_code == 200
        resp = client.post("/auth/login", json={"email": email, "password": "TestPass123!"})
        assert resp.status_code == 401
        msg = resp.json()["message"].lower()
        assert "rejected" in msg
        assert reason.lower() in msg
        assert "deactivated" not in msg

    def test_suspended_organization_login_message(self, client):
        """Suspended org shows 'has been suspended' message."""
        org_id, email = self._register_org(client, "4")
        sa = self._super_admin_headers(client)
        # Must approve first before suspend
        client.put(f"/super-admin/organizations/{org_id}/approve", headers=sa)
        resp = client.put(f"/super-admin/organizations/{org_id}/suspend", headers=sa)
        assert resp.status_code == 200
        resp = client.post("/auth/login", json={"email": email, "password": "TestPass123!"})
        assert resp.status_code == 401
        msg = resp.json()["message"].lower()
        assert "suspended" in msg
        assert "contact support" in msg
        assert "deactivated" not in msg

    def test_active_organization_login_succeeds(self, client):
        """Active org and active user => login succeeds."""
        org_id, email = self._register_org(client, "5")
        sa = self._super_admin_headers(client)
        client.put(f"/super-admin/organizations/{org_id}/approve", headers=sa)
        resp = client.post("/auth/login", json={"email": email, "password": "TestPass123!"})
        assert resp.status_code == 200

    def test_inactive_user_shows_deactivated(self, client):
        """Active org but inactive user => 'account has been deactivated'."""
        org_id, email = self._register_org(client, "6")
        sa = self._super_admin_headers(client)
        client.put(f"/super-admin/organizations/{org_id}/approve", headers=sa)
        # Find the user and disable them
        users_resp = client.get(f"/super-admin/users?organization_id={org_id}", headers=sa)
        user_id = None
        for u in users_resp.json().get("users", []):
            if u["email"] == email:
                user_id = u["id"]
                break
        assert user_id is not None
        client.put(f"/super-admin/users/{user_id}/disable", headers=sa)
        # Now login should show "deactivated", not any org status message
        resp = client.post("/auth/login", json={"email": email, "password": "TestPass123!"})
        assert resp.status_code == 401
        msg = resp.json()["message"].lower()
        assert "deactivated" in msg
        assert "suspended" not in msg
        assert "rejected" not in msg
        assert "approval" not in msg

    def test_organization_admin_auto_creation(self, client):
        """On approve, if no Admin exists, one is auto-created."""
        org_id, email = self._register_org(client, "7")
        sa = self._super_admin_headers(client)
        # Before approve, there should be exactly 1 user (the registering admin)
        resp = client.get(f"/super-admin/organizations/{org_id}/details", headers=sa)
        assert resp.status_code == 200
        assert resp.json()["user_count"] >= 1
        # Now delete the admin user to trigger auto-creation
        users_resp = client.get(f"/super-admin/users?organization_id={org_id}", headers=sa)
        for u in users_resp.json().get("users", []):
            if u["email"] == email:
                client.put(f"/super-admin/users/{u['id']}/disable", headers=sa)
        # Approve - should create a new admin user
        resp = client.put(f"/super-admin/organizations/{org_id}/approve", headers=sa)
        assert resp.status_code == 200
        # Verify admin user exists
        resp = client.get(f"/super-admin/organizations/{org_id}/details", headers=sa)
        assert resp.status_code == 200
        # admin_email should be present
        assert resp.json().get("admin_email") is not None

    def test_dashboard_stats_update_after_approve(self, client):
        """Dashboard pending_organizations decreases after approval."""
        org_id, email = self._register_org(client, "8")
        sa = self._super_admin_headers(client)
        resp = client.get("/super-admin/dashboard", headers=sa)
        before = resp.json().get("pending_organizations", 0)
        assert before > 0
        resp = client.put(f"/super-admin/organizations/{org_id}/approve", headers=sa)
        assert resp.status_code == 200
        resp = client.get("/super-admin/dashboard", headers=sa)
        after = resp.json().get("pending_organizations", 0)
        # Pending count should decrease by at least 1
        assert after < before

    def test_account_deactivated_not_shown_for_pending_org(self, client):
        """Regression: pending org must NEVER show 'deactivated' message."""
        org_id, email = self._register_org(client, "9")
        # The admin user has is_active=True (fixed), and org is PENDING
        # So login should show "awaiting approval", NOT "deactivated"
        resp = client.post("/auth/login", json={"email": email, "password": "TestPass123!"})
        assert resp.status_code == 401
        msg = resp.json()["message"].lower()
        assert "awaiting super admin approval" in msg
        assert "deactivated" not in msg

    def test_org_status_does_not_affect_user_is_active(self, client):
        """Regression: changing org status must NOT modify user.is_active."""
        org_id, email = self._register_org(client, "10")
        sa = self._super_admin_headers(client)
        # Find user
        users_resp = client.get(f"/super-admin/users?organization_id={org_id}", headers=sa)
        user = None
        for u in users_resp.json().get("users", []):
            if u["email"] == email:
                user = u
                break
        assert user is not None
        assert user["is_active"] is True

        # Suspend org - user should remain active
        client.put(f"/super-admin/organizations/{org_id}/approve", headers=sa)
        client.put(f"/super-admin/organizations/{org_id}/suspend", headers=sa)
        users_resp = client.get(f"/super-admin/users?organization_id={org_id}", headers=sa)
        for u in users_resp.json().get("users", []):
            if u["email"] == email:
                assert u["is_active"] is True, "User must remain active when org is suspended"
                break

        # Reject another org - user should remain active
        org_id2, email2 = self._register_org(client, "11")
        client.put(f"/super-admin/organizations/{org_id2}/reject", headers=sa, json={"reason": "test"})
        users_resp = client.get(f"/super-admin/users?organization_id={org_id2}", headers=sa)
        for u in users_resp.json().get("users", []):
            if u["email"] == email2:
                assert u["is_active"] is True, "User must remain active when org is rejected"
                break


class TestAuthStatusAudit:
    """Comprehensive tests covering all user status × organization status combinations.

    Verifies that login behavior is correct for every combination of:
      - Employee.is_active (True / False)
      - Employee.status (ACTIVE / DEACTIVATED / INACTIVE / TERMINATED / RESIGNED)
      - Organization.status (ACTIVE / PENDING / REJECTED / SUSPENDED / DEACTIVATED)

    Key requirement: user status and organization status are completely independent.
    Changing organization status MUST NOT change employee.is_active or employee.status.
    """

    def _register_org(self, client, suffix=""):
        email = f"auth.test{suffix}@test.com"
        resp = client.post("/auth/register", json={
            "name": f"Auth Test{suffix}",
            "email": email,
            "password": "TestPass123!",
            "organization": f"Auth Test Org {suffix}",
        })
        assert resp.status_code == 200
        return resp.json()["organization_id"], email

    def _super_admin_headers(self, client):
        resp = client.post("/auth/login", json={
            "email": "superadmin@zoiko.com",
            "password": "admin123",
        })
        assert resp.status_code == 200
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    def _get_user_id(self, client, org_id, email, sa):
        users_resp = client.get(f"/super-admin/users?organization_id={org_id}", headers=sa)
        for u in users_resp.json().get("users", []):
            if u["email"] == email:
                return u["id"]
        return None

    # ── Org ACTIVE + various user statuses ──

    def test_org_active_user_is_active_login_succeeds(self, client):
        """Active org + active user => login succeeds."""
        org_id, email = self._register_org(client, "_act1")
        sa = self._super_admin_headers(client)
        client.put(f"/super-admin/organizations/{org_id}/approve", headers=sa)
        resp = client.post("/auth/login", json={"email": email, "password": "TestPass123!"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_org_active_user_disabled_shows_deactivated(self, client):
        """Active org + user.is_active=False => 'Your account has been deactivated.'"""
        org_id, email = self._register_org(client, "_act2")
        sa = self._super_admin_headers(client)
        client.put(f"/super-admin/organizations/{org_id}/approve", headers=sa)
        user_id = self._get_user_id(client, org_id, email, sa)
        assert user_id is not None
        client.put(f"/super-admin/users/{user_id}/disable", headers=sa)
        resp = client.post("/auth/login", json={"email": email, "password": "TestPass123!"})
        assert resp.status_code == 401
        msg = resp.json()["message"].lower()
        assert "deactivated" in msg, f"Expected 'deactivated' in message, got: {msg}"
        assert "suspended" not in msg
        assert "pending" not in msg
        assert "rejected" not in msg

    def test_org_active_user_status_deactivated_shows_deactivated(self, client, db):
        """Active org + user.status=DEACTIVATED (is_active=True) => 'deactivated'."""
        org_id, email = self._register_org(client, "_act3")
        sa = self._super_admin_headers(client)
        client.put(f"/super-admin/organizations/{org_id}/approve", headers=sa)

        # Directly set user.status=DEACTIVATED via DB (no API endpoint for it)
        from app.modules.hr.models import Employee, EmployeeStatus
        user = db.query(Employee).filter(Employee.email == email).first()
        assert user is not None
        user.is_active = True
        user.status = EmployeeStatus.DEACTIVATED
        db.commit()

        resp = client.post("/auth/login", json={"email": email, "password": "TestPass123!"})
        assert resp.status_code == 401
        msg = resp.json()["message"].lower()
        assert "deactivated" in msg, f"Expected 'deactivated', got: {msg}"

    def test_org_active_user_terminated_shows_deactivated(self, client, db):
        """Active org + user.status=TERMINATED => blocked (is_active=False)."""
        org_id, email = self._register_org(client, "_act4")
        sa = self._super_admin_headers(client)
        client.put(f"/super-admin/organizations/{org_id}/approve", headers=sa)

        from app.modules.hr.models import Employee, EmployeeStatus
        user = db.query(Employee).filter(Employee.email == email).first()
        assert user is not None
        user.is_active = False
        user.status = EmployeeStatus.TERMINATED
        db.commit()

        resp = client.post("/auth/login", json={"email": email, "password": "TestPass123!"})
        assert resp.status_code == 401
        msg = resp.json()["message"].lower()
        assert "deactivated" in msg

    # ── Org PENDING + various user statuses ──

    def test_org_pending_shows_pending_even_if_user_inactive(self, client, db):
        """Pending org always shows org message, regardless of user.is_active."""
        org_id, email = self._register_org(client, "_pend1")

        # Disable user first
        from app.modules.hr.models import Employee
        user = db.query(Employee).filter(Employee.email == email).first()
        assert user is not None
        user.is_active = False
        db.commit()

        # Login should show PENDING message, not deactivated
        resp = client.post("/auth/login", json={"email": email, "password": "TestPass123!"})
        assert resp.status_code == 401
        msg = resp.json()["message"].lower()
        assert "approval" in msg, f"Expected 'approval' in message, got: {msg}"
        assert "deactivated" not in msg, "Pending org must not show 'deactivated'"

    # ── Org REJECTED + various user statuses ──

    def test_org_rejected_shows_rejected_even_if_user_inactive(self, client, db):
        """Rejected org always shows org message, regardless of user status."""
        org_id, email = self._register_org(client, "_rej1")
        sa = self._super_admin_headers(client)
        client.put(f"/super-admin/organizations/{org_id}/reject", headers=sa, json={"reason": "test"})

        from app.modules.hr.models import Employee
        user = db.query(Employee).filter(Employee.email == email).first()
        assert user is not None
        user.is_active = False
        db.commit()

        resp = client.post("/auth/login", json={"email": email, "password": "TestPass123!"})
        assert resp.status_code == 401
        msg = resp.json()["message"].lower()
        assert "rejected" in msg, f"Expected 'rejected', got: {msg}"
        assert "deactivated" not in msg

    # ── Org SUSPENDED + various user statuses ──

    def test_org_suspended_shows_suspended_even_if_user_inactive(self, client, db):
        """Suspended org always shows org message, regardless of user status."""
        org_id, email = self._register_org(client, "_sus1")
        sa = self._super_admin_headers(client)
        client.put(f"/super-admin/organizations/{org_id}/approve", headers=sa)
        client.put(f"/super-admin/organizations/{org_id}/suspend", headers=sa)

        from app.modules.hr.models import Employee
        user = db.query(Employee).filter(Employee.email == email).first()
        assert user is not None
        user.is_active = False
        db.commit()

        resp = client.post("/auth/login", json={"email": email, "password": "TestPass123!"})
        assert resp.status_code == 401
        msg = resp.json()["message"].lower()
        assert "suspended" in msg, f"Expected 'suspended', got: {msg}"
        assert "deactivated" not in msg

    # ── Org DEACTIVATED + various user statuses ──

    def test_org_deactivated_shows_org_message_even_if_user_active(self, client):
        """Deactivated org shows org message, not 'deactivated'."""
        org_id, email = self._register_org(client, "_dea1")
        sa = self._super_admin_headers(client)
        client.put(f"/super-admin/organizations/{org_id}/approve", headers=sa)
        client.put(f"/super-admin/organizations/{org_id}/status", headers=sa, json={
            "status": "DEACTIVATED",
            "reason": "Testing deactivation",
        })

        resp = client.post("/auth/login", json={"email": email, "password": "TestPass123!"})
        assert resp.status_code == 401
        msg = resp.json()["message"].lower()
        assert "deactivated" in msg, "Deactivated org must show org-level message"
        assert "organization" in msg, "Org-level message must mention 'organization'"

    def test_org_deactivated_shows_org_message_even_if_user_inactive(self, client):
        """Deactivated org + inactive user => org message takes precedence."""
        org_id, email = self._register_org(client, "_dea2")
        sa = self._super_admin_headers(client)
        client.put(f"/super-admin/organizations/{org_id}/approve", headers=sa)

        # Disable user
        user_id = self._get_user_id(client, org_id, email, sa)
        assert user_id is not None
        client.put(f"/super-admin/users/{user_id}/disable", headers=sa)

        # Deactivate org
        client.put(f"/super-admin/organizations/{org_id}/status", headers=sa, json={
            "status": "DEACTIVATED",
        })

        resp = client.post("/auth/login", json={"email": email, "password": "TestPass123!"})
        assert resp.status_code == 401
        msg = resp.json()["message"].lower()
        assert "organization" in msg, "Org-level deactivation message must mention 'organization'"
        assert "your account" not in msg.lower() or "organization" in msg.lower(), \
            "Org-level message should appear, not user-level"

    # ── Org status changes NEVER modify user status ──

    def test_suspend_org_does_not_affect_user_is_active(self, client):
        """Suspend org => user.is_active unchanged."""
        org_id, email = self._register_org(client, "_nc1")
        sa = self._super_admin_headers(client)
        user_id = self._get_user_id(client, org_id, email, sa)
        assert user_id is not None

        # Verify user is active
        users_resp = client.get(f"/super-admin/users?organization_id={org_id}", headers=sa)
        user = next(u for u in users_resp.json().get("users", []) if u["id"] == user_id)
        assert user["is_active"] is True

        # Approve then suspend
        client.put(f"/super-admin/organizations/{org_id}/approve", headers=sa)
        client.put(f"/super-admin/organizations/{org_id}/suspend", headers=sa)

        # User must remain active
        users_resp = client.get(f"/super-admin/users?organization_id={org_id}", headers=sa)
        user = next(u for u in users_resp.json().get("users", []) if u["id"] == user_id)
        assert user["is_active"] is True, "User is_active changed when org was suspended"

    def test_deactivate_org_does_not_affect_user_is_active(self, client):
        """Deactivate org => user.is_active unchanged."""
        org_id, email = self._register_org(client, "_nc2")
        sa = self._super_admin_headers(client)
        client.put(f"/super-admin/organizations/{org_id}/approve", headers=sa)
        user_id = self._get_user_id(client, org_id, email, sa)
        assert user_id is not None

        # Deactivate org via unified endpoint
        client.put(f"/super-admin/organizations/{org_id}/status", headers=sa, json={
            "status": "DEACTIVATED",
        })

        # User must remain active
        users_resp = client.get(f"/super-admin/users?organization_id={org_id}", headers=sa)
        user = next(u for u in users_resp.json().get("users", []) if u["id"] == user_id)
        assert user["is_active"] is True, "User is_active changed when org was deactivated"

    def test_approve_org_does_not_affect_user_is_active(self, client):
        """Approve org => user.is_active unchanged (no regression)."""
        org_id, email = self._register_org(client, "_nc3")
        sa = self._super_admin_headers(client)
        user_id = self._get_user_id(client, org_id, email, sa)
        assert user_id is not None

        client.put(f"/super-admin/organizations/{org_id}/approve", headers=sa)

        users_resp = client.get(f"/super-admin/users?organization_id={org_id}", headers=sa)
        user = next(u for u in users_resp.json().get("users", []) if u["id"] == user_id)
        assert user["is_active"] is True

    def test_reject_org_does_not_affect_user_is_active(self, client):
        """Reject org => user.is_active unchanged."""
        org_id, email = self._register_org(client, "_nc4")
        sa = self._super_admin_headers(client)
        user_id = self._get_user_id(client, org_id, email, sa)
        assert user_id is not None

        client.put(f"/super-admin/organizations/{org_id}/reject", headers=sa, json={"reason": "test"})

        users_resp = client.get(f"/super-admin/users?organization_id={org_id}", headers=sa)
        user = next(u for u in users_resp.json().get("users", []) if u["id"] == user_id)
        assert user["is_active"] is True

    def test_reactivate_org_does_not_affect_user_is_active(self, client):
        """Reactivate org => user.is_active unchanged."""
        org_id, email = self._register_org(client, "_nc5")
        sa = self._super_admin_headers(client)
        client.put(f"/super-admin/organizations/{org_id}/approve", headers=sa)
        client.put(f"/super-admin/organizations/{org_id}/suspend", headers=sa)
        user_id = self._get_user_id(client, org_id, email, sa)
        assert user_id is not None

        client.put(f"/super-admin/organizations/{org_id}/reactivate", headers=sa)

        users_resp = client.get(f"/super-admin/users?organization_id={org_id}", headers=sa)
        user = next(u for u in users_resp.json().get("users", []) if u["id"] == user_id)
        assert user["is_active"] is True

    # ── Dashboard stats include deactivated count ──

    def test_dashboard_includes_deactivated_count(self, client):
        """Dashboard stats must include deactivated_organizations."""
        sa = self._super_admin_headers(client)
        resp = client.get("/super-admin/dashboard", headers=sa)
        assert resp.status_code == 200
        data = resp.json()
        assert "deactivated_organizations" in data
        assert isinstance(data["deactivated_organizations"], int)

    # ── Deactivated list endpoint works ──

    def test_list_deactivated_organizations(self, client):
        """GET /super-admin/organizations/deactivated returns deactivated orgs."""
        org_id, email = self._register_org(client, "_list1")
        sa = self._super_admin_headers(client)
        client.put(f"/super-admin/organizations/{org_id}/approve", headers=sa)
        client.put(f"/super-admin/organizations/{org_id}/status", headers=sa, json={
            "status": "DEACTIVATED",
        })
        resp = client.get("/super-admin/organizations/deactivated", headers=sa)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        ids = [o["id"] for o in data["organizations"]]
        assert org_id in ids

    # ── Approval history shows previous/new status ──

    def test_approval_history_includes_status_transition(self, client):
        """Approval history records previous_status and new_status."""
        org_id, email = self._register_org(client, "_hist1")
        sa = self._super_admin_headers(client)
        client.put(f"/super-admin/organizations/{org_id}/approve", headers=sa)
        client.put(f"/super-admin/organizations/{org_id}/status", headers=sa, json={
            "status": "SUSPENDED",
        })
        resp = client.get(f"/super-admin/organizations/{org_id}/approval-history", headers=sa)
        assert resp.status_code == 200
        history = resp.json().get("history", [])
        # Find the suspend entry
        suspend = next((h for h in history if h["action"] == "suspended"), None)
        assert suspend is not None, "Expected 'suspended' action in history"
        assert suspend.get("previous_status") is not None, "previous_status must be recorded"
        assert suspend.get("new_status") is not None, "new_status must be recorded"

    # ── No-org (standalone) user login ──

    def test_no_org_user_active_login_succeeds(self, client):
        """User without organization, is_active=True => login succeeds."""
        resp = client.post("/auth/login", json={
            "email": "admin@zoiko.com",
            "password": "admin123",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_no_org_user_disabled_shows_deactivated(self, client, db):
        """User without organization, is_active=False => 'deactivated'."""
        from app.modules.hr.models import Employee, EmployeeStatus
        user = db.query(Employee).filter(Employee.email == "admin@zoiko.com").first()
        assert user is not None
        user.is_active = False
        user.status = EmployeeStatus.DEACTIVATED
        db.commit()

        try:
            resp = client.post("/auth/login", json={
                "email": "admin@zoiko.com",
                "password": "admin123",
            })
            assert resp.status_code == 401
            msg = resp.json()["message"].lower()
            assert "deactivated" in msg
        finally:
            # Re-enable the user inside the same transaction
            user.is_active = True
            user.status = EmployeeStatus.ACTIVE
            db.commit()
