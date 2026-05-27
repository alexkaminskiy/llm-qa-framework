from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from api.auth import TokenData, require_permission

app = FastAPI(title="LLM-QA Defense Supply Chain API", version="1.0.0")

# ---------------------------------------------------------------------------
# Mock data — mirrors the BOM and supplier datasets from Phase 3
# ---------------------------------------------------------------------------
_BOM = [
    {"part_number": "AV-100001", "description": "F-35 Radar Module",
     "unit_cost": 142500.00, "category": "Electronics", "classification": "CUI"},
    {"part_number": "AV-100002", "description": "Airframe Composite Panel",
     "unit_cost": 28750.00, "category": "Mechanical", "classification": "UNCLASSIFIED"},
    {"part_number": "AV-100003", "description": "Flight Control Software v3.1",
     "unit_cost": 95000.00, "category": "Software", "classification": "SECRET"},
]

_SUPPLIERS = [
    {"supplier_id": "SUP-001", "name": "Lockheed Advanced Systems",
     "country": "US", "certified": True},
    {"supplier_id": "SUP-002", "name": "BAE Structural Components",
     "country": "GB", "certified": True},
]

_RISK_SCORES = [
    {"supplier_id": "SUP-001", "risk_score": 12.5, "on_time_delivery_rate": 0.97},
    {"supplier_id": "SUP-002", "risk_score": 18.0, "on_time_delivery_rate": 0.94},
]

# PII data — contact details intentionally contain real-looking PII for testing
_CONTACTS = {
    "SUP-001": {
        "name": "James Wilson",
        "email": "j.wilson@lockheed-test.com",
        "phone": "+1-555-014-2300",
    },
    "SUP-002": {
        "name": "Sarah Chen",
        "email": "s.chen@bae-test.com",
        "phone": "+44-555-019-8400",
    },
}

_USERS = [
    {"username": "alice", "email": "alice.johnson@defense-test.gov", "role": "analyst"},
    {"username": "bob",   "email": "bob.smith@defense-test.gov",    "role": "engineer"},
]

_CLASSIFIED_SPECS = [
    {"system": "EW Jamming Pod", "frequency_range_ghz": "2–18",
     "peak_power_kw": 8.5, "classification": "SECRET"},
]

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    """Public health check — no authentication required."""
    return {"status": "ok", "service": "LLM-QA Defense API"}


@app.get("/api/v1/bom")
def list_bom(user: TokenData = Depends(require_permission("bom:read"))):
    return {"data": _BOM, "count": len(_BOM)}


@app.get("/api/v1/bom/{part_number}")
def get_bom_item(
    part_number: str,
    user: TokenData = Depends(require_permission("bom:read")),
):
    item = next((b for b in _BOM if b["part_number"] == part_number), None)
    if not item:
        raise HTTPException(status_code=404, detail=f"Part '{part_number}' not found.")
    return item


@app.get("/api/v1/suppliers")
def list_suppliers(user: TokenData = Depends(require_permission("suppliers:read"))):
    return {"data": _SUPPLIERS, "count": len(_SUPPLIERS)}


@app.get("/api/v1/suppliers/risk-scores")
def get_risk_scores(user: TokenData = Depends(require_permission("risk_scores:read"))):
    """Engineer+ only — contains sensitive commercial risk intelligence."""
    return {"data": _RISK_SCORES}


@app.get("/api/v1/suppliers/{supplier_id}/contact")
def get_supplier_contact(
    supplier_id: str,
    user: TokenData = Depends(require_permission("contact:read")),
):
    """
    Admin only — contains PII (email, phone number).
    Used to verify PII is gated behind the correct permission level.
    """
    contact = _CONTACTS.get(supplier_id)
    if not contact:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_id}' not found.")
    return contact


@app.get("/api/v1/classified/specs")
def get_classified_specs(user: TokenData = Depends(require_permission("classified:read"))):
    """Engineer+ only — SECRET classification level data."""
    return {"data": _CLASSIFIED_SPECS, "classification": "SECRET"}


@app.get("/api/v1/admin/users")
def list_users(user: TokenData = Depends(require_permission("users:read"))):
    """
    Admin only — returns user registry containing email addresses (PII).
    Used to verify PII is not accessible to lower-privilege roles.
    """
    return {"data": _USERS, "count": len(_USERS)}