"""API authentication.

Single shared API key supplied via the ``X-API-Key`` header, validated with a
constant-time comparison. When ``API_KEY`` is unset the check is disabled so
local development stays frictionless — the startup log warns loudly so an open
deployment is never an accident. Administrative endpoints require a *separate*
``X-Admin-Key`` so a leaked analyst key cannot escalate.
"""

from __future__ import annotations

import hmac
import logging

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from parallax.core.config import settings

logger = logging.getLogger(__name__)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def redact_secrets(text: str) -> str:
    """Scrub configured secret *values* from a string before it is logged or
    returned. Cheap insurance for the CI secret-grep gate — a stack trace or
    error that happens to embed a key never leaks it."""
    out = str(text)
    for secret in (
        settings.API_KEY,
        settings.ADMIN_API_KEY,
        settings.AIML_API,
        settings.ANTHROPIC_API_KEY,
        settings.OPENAI_API_KEY,
    ):
        if secret and len(secret) >= 6:
            out = out.replace(secret, "***REDACTED***")
    return out


async def require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """FastAPI dependency enforcing the configured API key on a route."""
    if not settings.API_KEY:
        return  # auth disabled (development mode)
    if not api_key or not hmac.compare_digest(api_key, settings.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Supply it in the X-API-Key header.",
        )


async def require_admin_key(admin_key: str | None = Security(_admin_key_header)) -> None:
    """FastAPI dependency for administrative endpoints. Requires the dedicated
    admin key. When neither key is configured the service is in open dev mode
    and admin access is allowed; but if API_KEY is set while ADMIN_API_KEY is
    not, admin endpoints are locked down (fail closed) rather than falling back
    to the analyst key."""
    if not settings.API_KEY and not settings.ADMIN_API_KEY:
        return  # fully open dev mode
    if not settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin endpoints are disabled: ADMIN_API_KEY is not configured.",
        )
    if not admin_key or not hmac.compare_digest(admin_key, settings.ADMIN_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing admin key. Supply it in the X-Admin-Key header.",
        )


def warn_if_auth_disabled() -> None:
    if not settings.API_KEY:
        logger.warning(
            "API_KEY is not set — the API is running WITHOUT authentication. "
            "Set API_KEY in the environment before exposing this service."
        )
