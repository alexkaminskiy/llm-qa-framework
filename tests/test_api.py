"""
API Tests for Defense Supply Chain LLM-QA Framework

Comprehensive test coverage for:
- 6 API endpoints (health, BOM, suppliers, risk-scores, contact, classified, users)
- 4 roles (guest, analyst, engineer, admin)
- Permission enforcement (24 role×endpoint scenarios)
- Error cases (401 Unauthorized, 403 Forbidden, 404 Not Found)
- Happy paths (200 OK)

Tests follow pytest conventions and use FastAPI TestClient.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.auth import create_access_token


# =============================================================================
# Fixtures & Helpers
# =============================================================================

@pytest.fixture
def client():
    """FastAPI TestClient for the app."""
    return TestClient(app)


@pytest.fixture
def tokens():
    """Generate JWT tokens for all 4 roles for use in tests."""
    return {
        "guest": create_access_token("guest", "guest_user"),
        "analyst": create_access_token("analyst", "analyst_user"),
        "engineer": create_access_token("engineer", "engineer_user"),
        "admin": create_access_token("admin", "admin_user"),
    }


def get_auth_header(token: str) -> dict:
    """Convert JWT token to FastAPI Bearer auth header."""
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# Tests: Public Endpoints (No Auth Required)
# =============================================================================

class TestHealthEndpoint:
    """Health check endpoint — publicly accessible, no authentication required."""

    def test_health_check_returns_ok(self, client):
        """Verify health check returns 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data


# =============================================================================
# Tests: BOM Endpoints (bom:read permission)
# =============================================================================

class TestBOMEndpoints:
    """
    BOM (Bill of Materials) endpoints.
    Permission: bom:read
    Allowed roles: analyst, engineer, admin
    Denied roles: guest
    """

    @pytest.mark.parametrize("role,expected_status", [
        ("guest", 403),           # No permission
        ("analyst", 200),         # Has bom:read
        ("engineer", 200),        # Has bom:read
        ("admin", 200),           # Has bom:read
    ])
    def test_list_bom_with_rbac(self, client, tokens, role, expected_status):
        """Test RBAC for GET /api/v1/bom across all 4 roles."""
        response = client.get(
            "/api/v1/bom",
            headers=get_auth_header(tokens[role])
        )
        assert response.status_code == expected_status

        if expected_status == 200:
            data = response.json()
            assert "data" in data
            assert "count" in data
            assert len(data["data"]) == 3  # 3 BOM items in mock data

    def test_list_bom_without_token_returns_401(self, client):
        """Test GET /api/v1/bom returns 401 without token."""
        response = client.get("/api/v1/bom")
        assert response.status_code == 401

    def test_list_bom_with_invalid_token_returns_401(self, client):
        """Test GET /api/v1/bom returns 401 with invalid token."""
        response = client.get(
            "/api/v1/bom",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert response.status_code == 401

    @pytest.mark.parametrize("role,expected_status", [
        ("guest", 403),
        ("analyst", 200),
        ("engineer", 200),
        ("admin", 200),
    ])
    def test_get_bom_item_with_rbac(self, client, tokens, role, expected_status):
        """Test RBAC for GET /api/v1/bom/{part_number} across all 4 roles."""
        response = client.get(
            "/api/v1/bom/AV-100001",
            headers=get_auth_header(tokens[role])
        )
        assert response.status_code == expected_status

        if expected_status == 200:
            data = response.json()
            assert data["part_number"] == "AV-100001"
            assert "description" in data
            assert "unit_cost" in data

    def test_get_bom_item_not_found(self, client, tokens):
        """Test GET /api/v1/bom/{part_number} returns 404 for invalid part."""
        response = client.get(
            "/api/v1/bom/INVALID-PART",
            headers=get_auth_header(tokens["analyst"])
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()


# =============================================================================
# Tests: Suppliers Endpoints (suppliers:read permission)
# =============================================================================

class TestSuppliersEndpoints:
    """
    Suppliers endpoints.
    Permission: suppliers:read
    Allowed roles: analyst, engineer, admin
    Denied roles: guest
    """

    @pytest.mark.parametrize("role,expected_status", [
        ("guest", 403),
        ("analyst", 200),
        ("engineer", 200),
        ("admin", 200),
    ])
    def test_list_suppliers_with_rbac(self, client, tokens, role, expected_status):
        """Test RBAC for GET /api/v1/suppliers across all 4 roles."""
        response = client.get(
            "/api/v1/suppliers",
            headers=get_auth_header(tokens[role])
        )
        assert response.status_code == expected_status

        if expected_status == 200:
            data = response.json()
            assert "data" in data
            assert "count" in data
            assert len(data["data"]) == 2  # 2 suppliers in mock data

    def test_list_suppliers_without_token_returns_401(self, client):
        """Test GET /api/v1/suppliers returns 401 without token."""
        response = client.get("/api/v1/suppliers")
        assert response.status_code == 401


# =============================================================================
# Tests: Risk Scores Endpoint (risk_scores:read permission)
# =============================================================================

class TestRiskScoresEndpoint:
    """
    Risk scores endpoint — sensitive commercial intelligence.
    Permission: risk_scores:read
    Allowed roles: engineer, admin
    Denied roles: guest, analyst
    """

    @pytest.mark.parametrize("role,expected_status", [
        ("guest", 403),         # No permission
        ("analyst", 403),       # No permission (sensitive data)
        ("engineer", 200),      # Has risk_scores:read
        ("admin", 200),         # Has risk_scores:read
    ])
    def test_get_risk_scores_with_rbac(self, client, tokens, role, expected_status):
        """Test RBAC for GET /api/v1/suppliers/risk-scores across all 4 roles."""
        response = client.get(
            "/api/v1/suppliers/risk-scores",
            headers=get_auth_header(tokens[role])
        )
        assert response.status_code == expected_status

        if expected_status == 200:
            data = response.json()
            assert "data" in data
            assert len(data["data"]) == 2  # 2 risk scores in mock data
            # Verify sensitive data is present (risk_score, on_time_delivery_rate)
            assert "risk_score" in data["data"][0]
            assert "on_time_delivery_rate" in data["data"][0]

    def test_get_risk_scores_without_token_returns_401(self, client):
        """Test GET /api/v1/suppliers/risk-scores returns 401 without token."""
        response = client.get("/api/v1/suppliers/risk-scores")
        assert response.status_code == 401

    def test_analyst_cannot_access_risk_scores(self, client, tokens):
        """Test that analysts are blocked from risk scores (engineer+ only)."""
        response = client.get(
            "/api/v1/suppliers/risk-scores",
            headers=get_auth_header(tokens["analyst"])
        )
        assert response.status_code == 403


# =============================================================================
# Tests: Supplier Contact Endpoint (contact:read permission — PII)
# =============================================================================

class TestSupplierContactEndpoint:
    """
    Supplier contact endpoint — contains PII (names, emails, phone numbers).
    Permission: contact:read
    Allowed roles: admin
    Denied roles: guest, analyst, engineer
    """

    @pytest.mark.parametrize("role,expected_status", [
        ("guest", 403),         # No permission
        ("analyst", 403),       # No permission (PII access)
        ("engineer", 403),      # No permission (PII access)
        ("admin", 200),         # Only admin can access PII
    ])
    def test_get_supplier_contact_with_rbac(self, client, tokens, role, expected_status):
        """Test RBAC for GET /api/v1/suppliers/{id}/contact across all 4 roles."""
        response = client.get(
            "/api/v1/suppliers/SUP-001/contact",
            headers=get_auth_header(tokens[role])
        )
        assert response.status_code == expected_status

        if expected_status == 200:
            data = response.json()
            # Verify PII fields are present
            assert "name" in data
            assert "email" in data
            assert "phone" in data
            assert data["name"] == "James Wilson"

    def test_get_supplier_contact_not_found(self, client, tokens):
        """Test GET /api/v1/suppliers/{id}/contact returns 404 for invalid supplier."""
        response = client.get(
            "/api/v1/suppliers/INVALID-SUP/contact",
            headers=get_auth_header(tokens["admin"])
        )
        assert response.status_code == 404

    def test_engineer_cannot_access_supplier_pii(self, client, tokens):
        """Test that engineers cannot access supplier PII (contact info)."""
        response = client.get(
            "/api/v1/suppliers/SUP-001/contact",
            headers=get_auth_header(tokens["engineer"])
        )
        assert response.status_code == 403


# =============================================================================
# Tests: Classified Specs Endpoint (classified:read permission)
# =============================================================================

class TestClassifiedSpecsEndpoint:
    """
    Classified specs endpoint — SECRET classification level data.
    Permission: classified:read
    Allowed roles: engineer, admin
    Denied roles: guest, analyst
    """

    @pytest.mark.parametrize("role,expected_status", [
        ("guest", 403),         # No permission
        ("analyst", 403),       # No permission (classified data)
        ("engineer", 200),      # Has classified:read
        ("admin", 200),         # Has classified:read
    ])
    def test_get_classified_specs_with_rbac(self, client, tokens, role, expected_status):
        """Test RBAC for GET /api/v1/classified/specs across all 4 roles."""
        response = client.get(
            "/api/v1/classified/specs",
            headers=get_auth_header(tokens[role])
        )
        assert response.status_code == expected_status

        if expected_status == 200:
            data = response.json()
            assert "data" in data
            assert data["classification"] == "SECRET"
            assert len(data["data"]) == 1
            assert data["data"][0]["system"] == "EW Jamming Pod"

    def test_get_classified_specs_without_token_returns_401(self, client):
        """Test GET /api/v1/classified/specs returns 401 without token."""
        response = client.get("/api/v1/classified/specs")
        assert response.status_code == 401

    def test_analyst_cannot_access_classified_data(self, client, tokens):
        """Test that analysts cannot access classified data."""
        response = client.get(
            "/api/v1/classified/specs",
            headers=get_auth_header(tokens["analyst"])
        )
        assert response.status_code == 403


# =============================================================================
# Tests: Admin Users Endpoint (users:read permission)
# =============================================================================

class TestAdminUsersEndpoint:
    """
    Admin users endpoint — contains PII (user email addresses).
    Permission: users:read
    Allowed roles: admin
    Denied roles: guest, analyst, engineer
    """

    @pytest.mark.parametrize("role,expected_status", [
        ("guest", 403),         # No permission
        ("analyst", 403),       # No permission (admin-only)
        ("engineer", 403),      # No permission (admin-only)
        ("admin", 200),         # Only admin can access
    ])
    def test_list_users_with_rbac(self, client, tokens, role, expected_status):
        """Test RBAC for GET /api/v1/admin/users across all 4 roles."""
        response = client.get(
            "/api/v1/admin/users",
            headers=get_auth_header(tokens[role])
        )
        assert response.status_code == expected_status

        if expected_status == 200:
            data = response.json()
            assert "data" in data
            assert "count" in data
            assert len(data["data"]) == 2  # 2 users in mock data
            # Verify PII (email) is present for admins
            assert "email" in data["data"][0]

    def test_list_users_without_token_returns_401(self, client):
        """Test GET /api/v1/admin/users returns 401 without token."""
        response = client.get("/api/v1/admin/users")
        assert response.status_code == 401

    def test_engineer_cannot_access_user_list(self, client, tokens):
        """Test that engineers cannot access user list (admin only)."""
        response = client.get(
            "/api/v1/admin/users",
            headers=get_auth_header(tokens["engineer"])
        )
        assert response.status_code == 403


# =============================================================================
# Tests: RBAC Matrix Summary
# =============================================================================

class TestRBACMatrix:
    """
    Summary test validating the complete RBAC matrix.
    Ensures all 4 roles are properly constrained across all protected endpoints.
    """

    RBAC_MATRIX = {
        # endpoint: {role: expected_status_code}
        "/api/v1/bom": {
            "guest": 403,
            "analyst": 200,
            "engineer": 200,
            "admin": 200,
        },
        "/api/v1/suppliers": {
            "guest": 403,
            "analyst": 200,
            "engineer": 200,
            "admin": 200,
        },
        "/api/v1/suppliers/risk-scores": {
            "guest": 403,
            "analyst": 403,
            "engineer": 200,
            "admin": 200,
        },
        "/api/v1/suppliers/SUP-001/contact": {
            "guest": 403,
            "analyst": 403,
            "engineer": 403,
            "admin": 200,
        },
        "/api/v1/classified/specs": {
            "guest": 403,
            "analyst": 403,
            "engineer": 200,
            "admin": 200,
        },
        "/api/v1/admin/users": {
            "guest": 403,
            "analyst": 403,
            "engineer": 403,
            "admin": 200,
        },
    }

    @pytest.mark.parametrize("endpoint,role_expectations", [
        (endpoint, role_status)
        for endpoint, role_status in RBAC_MATRIX.items()
    ])
    def test_complete_rbac_matrix(self, client, tokens, endpoint, role_expectations):
        """
        Test that the complete RBAC matrix is enforced correctly.
        Ensures each role has correct access to each endpoint.
        """
        for role, expected_status in role_expectations.items():
            response = client.get(
                endpoint,
                headers=get_auth_header(tokens[role])
            )
            assert response.status_code == expected_status, (
                f"Endpoint {endpoint} with role {role}: "
                f"expected {expected_status}, got {response.status_code}"
            )


# =============================================================================
# Tests: Error Handling
# =============================================================================

class TestErrorHandling:
    """Test error handling for malformed requests and invalid conditions."""

    def test_invalid_bearer_token_format_returns_401(self, client):
        """Test that malformed Bearer token returns 401."""
        response = client.get(
            "/api/v1/bom",
            headers={"Authorization": "NotABearerToken"}
        )
        # Should fail because it's not a valid Bearer token or is missing the token
        assert response.status_code == 401

    def test_missing_authorization_header_returns_401(self, client):
        """Test that missing auth header returns 401."""
        response = client.get("/api/v1/bom")
        assert response.status_code == 401

    def test_empty_authorization_header_returns_401(self, client):
        """Test that empty auth header returns 401."""
        response = client.get(
            "/api/v1/bom",
            headers={"Authorization": ""}
        )
        assert response.status_code == 401


# =============================================================================
# Tests: Markers for Requirement Traceability
# =============================================================================

@pytest.mark.requirement("SYS-REQ-RBAC-001")
class TestRBACCompliance:
    """Tests validating RBAC enforcement for system requirement SYS-REQ-RBAC-001."""

    def test_guest_role_has_no_permissions(self, client, tokens):
        """Verify guest role has zero permissions."""
        # Guest should fail on all protected endpoints
        protected_endpoints = [
            "/api/v1/bom",
            "/api/v1/suppliers",
            "/api/v1/suppliers/risk-scores",
            "/api/v1/suppliers/SUP-001/contact",
            "/api/v1/classified/specs",
            "/api/v1/admin/users",
        ]
        for endpoint in protected_endpoints:
            response = client.get(
                endpoint,
                headers=get_auth_header(tokens["guest"])
            )
            assert response.status_code == 403, f"Guest should not access {endpoint}"
