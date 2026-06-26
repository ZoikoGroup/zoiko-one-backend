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
        sa_employee_id = 1  # Super Admin
        user_resp = client.get("/super-admin/users", headers=sa_headers)
        admin_user_id = None
        for u in user_resp.json().get("users", []):
            if u["email"] == "approval.test@test.com":
                admin_user_id = u["id"]
                break
        if admin_user_id:
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

        # ── Phase 9: Suspend the organization ──
        resp = client.put(f"/super-admin/organizations/{org_id}/suspend", headers=sa_headers)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # Verify suspended status
        resp = client.get(f"/super-admin/organizations/{org_id}/details", headers=sa_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "SUSPENDED"

        # ── Phase 10: Login blocked when suspended ──
        resp = client.post("/auth/login", json={
            "email": "approval.test@test.com",
            "password": "TestPass123!"
        })
        assert resp.status_code == 401
        assert "suspended" in resp.json()["message"].lower()
        assert "contact support" in resp.json()["message"].lower()

        # ── Phase 11: Reactivate the organization ──
        resp = client.put(f"/super-admin/organizations/{org_id}/reactivate", headers=sa_headers)
        assert resp.status_code == 200
        assert resp.json()["message"] == "Organization reactivated"

        # Verify reactivated status
        resp = client.get(f"/super-admin/organizations/{org_id}/details", headers=sa_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ACTIVE"

        # ── Phase 12: Login succeeds after reactivation ──
        resp = client.post("/auth/login", json={
            "email": "approval.test@test.com",
            "password": "TestPass123!"
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

        # ── Phase 13: Register and reject a second organization ──
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

        # ── Phase 14: Login blocked with rejection reason ──
        resp = client.post("/auth/login", json={
            "email": "reject.test@test.com",
            "password": "TestPass123!"
        })
        assert resp.status_code == 401
        assert "rejected" in resp.json()["message"].lower()
        assert "incomplete" in resp.json()["message"].lower()

        # ── Phase 15: Dashboard shows new status fields ──
        resp = client.get("/super-admin/dashboard", headers=sa_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "pending_organizations" in data
        assert "rejected_organizations" in data
        assert "suspended_organizations" in data
        assert "recent_registrations" in data

        # ── Phase 16: Approval history is recorded ──
        resp = client.get(f"/super-admin/organizations/{org_id}/approval-history", headers=sa_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2
        actions = [h["action"] for h in data["history"]]
        assert "approved" in actions
        assert "suspended" in actions or "reactivated" in actions

        # ── Phase 17: RBAC — regular admin denied ──
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
