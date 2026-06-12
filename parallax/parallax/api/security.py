"""API authentication.

Single shared API key supplied via the ``X-API-Key`` header, validated with a
constant-time comparison. When ``API_KEY`` is unset the check is disabled so
local development stays frictionless — the startup log warns loudly so an open
deployment is never an accident.
"""

from __future__ import annotations

import hmac
import logging

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from parallax.core.config import settings

logger = logging.getLogger(__name__)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """FastAPI dependency enforcing the configured API key on a route."""
    if not settings.API_KEY:
        return  # auth disabled (development mode)
    if not api_key or not hmac.compare_digest(api_key, settings.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Supply it in the X-API-Key header.",
        )


def warn_if_auth_disabled() -> None:
    if not settings.API_KEY:
        logger.warning(
            "API_KEY is not set — the API is running WITHOUT authentication. "
            "Set API_KEY in the environment before exposing this service."
        )
