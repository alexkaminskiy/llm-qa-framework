"""
RBAC Enforcement Suite

Parameterized matrix covering every (role, endpoint) pair in the access
control policy. Each test asserts the exact HTTP status code defined by
the policy — 200 PERMITTED, 401 UNAUTHENTICATED, 403 UNAUTHORISED.

Any deviation is a security defect regardless of severity:
- A 200 where 403 is expected = privilege escalation
- A 403 where 200 is expected = legitimate user locked out
- A 401 where 403 is expected = leaks information about endpoint existence
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.auth import create_access_token

pytestmark = pytest.mark.requirement("SYS-REQ-014")

# ---------------------------------------------------------------------------
# Access control matrix — single source of truth for the RBAC policy
# Format: (role, method, endpoint, expected_http_status)
# ---------------------------------------------------------------------------
RBAC_MATRIX = [
    # ── Public ─────────────────────────────────────────────────────────────
    ("guest",    "GET", "/health",                              200),

    # ── BOM — analyst, engineer, admin ─────────────────────────────────────
    ("guest",    "GET", "/api/v1/bom",                          401),
    ("analyst",  "GET", "/api/v1/bom",                          200),
    ("engineer", "GET", "/api/v1/bom",                          200),
    ("admin",    "GET", "/api/v1/bom",                          200),

    ("guest",    "GET", "/api/v1/bom/AV-100001",                401),
    ("analyst",  "GET", "/api/v1/bom/AV-100001",                200),
    ("engineer", "GET", "/api/v1/bom/AV-100001",                200),
    ("admin",    "GET", "/api/v1/bom/AV-100001",                200),

    # ── Suppliers — analyst, engineer, admin ────────────────────────────────
    ("guest",    "GET", "/api/v1/suppliers",                    401),
    ("analyst",  "GET", "/api/v1/suppliers",                    200),
    ("engineer", "GET", "/api/v1/suppliers",                    200),
    ("admin",    "GET", "/api/v1/suppliers",                    200),

    # ── Risk scores — engineer, admin ───────────────────────────────────────
    ("analyst",  "GET", "/api/v1/suppliers/risk-scores",        403),
    ("engineer", "GET", "/api/v1/suppliers/risk-scores",        200),
    ("admin",    "GET", "/api/v1/suppliers/risk-scores",        200),

    # ── Supplier contact (PII) — admin only ─────────────────────────────────
    ("analyst",  "GET", "/api/v1/suppliers/SUP-001/contact",    403),
    ("engineer", "GET", "/api/v1/suppliers/SUP-001/contact",    403),
    ("admin",    "GET", "/api/v1/suppliers/SUP-001/contact",    200),

    # ── Classified specs — engineer, admin ──────────────────────────────────
    ("analyst",  "GET", "/api/v1/classified/specs",             403),
    ("engineer", "GET", "/api/v1/classified/specs",             200),
    ("admin",    "GET", "/api/v1/classified/specs",             200),

    # ── Admin users (PII) — admin only ──────────────────────────────────────
    ("analyst",  "GET", "/api/v1/admin/users",                  403),
    ("engineer", "GET", "/api/v1/admin/users",                  403),
    ("admin",    "GET", "/api/v1/admin/users",                  200),
]


@pytest.fixture(scope="module")
def api_call():
    """
    Returns a callable that makes API requests with the correct JWT for a role.
    'guest' sends no Authorization header — tests the unauthenticated path.
    """
    client = TestClient(app, raise_server_exceptions=False)

    def _call(role: str, method: str, endpoint: str):
        headers = (
            {} if role == "guest"
            else {"Authorization": f"Bearer {create_access_token(role)}"}
        )
        return getattr(client, method.lower())(endpoint, headers=headers)

    return _call


@pytest.mark.parametrize(
    "role, method, endpoint, expected_status",
    RBAC_MATRIX,
    ids=[f"{r}·{m}·{e}" for r, m, e, _ in RBAC_MATRIX],
)
def test_rbac_enforcement(
    role: str,
    method: str,
    endpoint: str,
    expected_status: int,
    api_call,
) -> None:
    response = api_call(role, method, endpoint)

    assert response.status_code == expected_status, (
        f"\nRBAC VIOLATION detected:\n"
        f"  Role     : {role}\n"
        f"  Request  : {method} {endpoint}\n"
        f"  Expected : HTTP {expected_status}\n"
        f"  Received : HTTP {response.status_code}\n"
        f"  Body     : {response.text[:300]}"
    )