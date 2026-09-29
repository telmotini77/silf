"""Validaciones de secretos en los límites HTTP."""

import hmac
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings

admin_api_key_header = APIKeyHeader(name="X-Admin-Token", auto_error=False)


def compare_constant_time(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode(), right.encode())


async def require_admin(api_key: Optional[str] = Security(admin_api_key_header)) -> str:
    if not settings.ADMIN_TOKEN:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Admin endpoint is not configured")
    if not api_key or not compare_constant_time(api_key, settings.ADMIN_TOKEN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return api_key

