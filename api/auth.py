from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

SECRET_KEY = os.getenv("API_SECRET_KEY", "test-only-secret-key-not-for-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 1

# Role → permissions mapping
# Each permission string maps to a specific endpoint capability
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "guest":    set(),
    "analyst":  {"bom:read", "suppliers:read"},
    "engineer": {"bom:read", "suppliers:read", "risk_scores:read", "classified:read"},
    "admin":    {"bom:read", "suppliers:read", "risk_scores:read",
                 "classified:read", "contact:read", "users:read", "users:write"},
}


class TokenData(BaseModel):
    username: str
    role: str
    permissions: set[str]


def create_access_token(role: str, username: str = "test_user") -> str:
    """Creates a signed JWT for the given role. Used by tests to generate credentials."""
    if role not in ROLE_PERMISSIONS:
        raise ValueError(f"Unknown role: '{role}'. Valid roles: {list(ROLE_PERMISSIONS)}")

    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> TokenData:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated — Bearer token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        role = payload.get("role", "guest")
        username = payload.get("sub", "unknown")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )

    return TokenData(
        username=username,
        role=role,
        permissions=ROLE_PERMISSIONS.get(role, set()),
    )


def require_permission(permission: str):
    """FastAPI dependency factory — enforces a specific permission on an endpoint."""
    def _checker(user: TokenData = Depends(get_current_user)) -> TokenData:
        if permission not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Permission '{permission}' required. "
                    f"Role '{user.role}' is not authorised for this endpoint."
                ),
            )
        return user
    return _checker