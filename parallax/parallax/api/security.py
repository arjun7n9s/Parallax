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

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from parallax.core.config import settings

logger = logging.getLogger(__name__)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def _tenant_map() -> dict[str, str]:
    pairs: dict[str, str] = {}
    for raw in settings.API_KEY_TENANT_MAP.split(","):
        if not raw.strip() or ":" not in raw:
            continue
        key, tenant = raw.split(":", 1)
        if key.strip() and tenant.strip():
            pairs[key.strip()] = tenant.strip()
    if settings.API_KEY:
        pairs.setdefault(settings.API_KEY, settings.TENANT_ID)
    return pairs


def tenant_from_api_key(api_key: str | None) -> str:
    if not settings.API_KEY:
        return settings.TENANT_ID
    return _tenant_map().get(api_key or "", "")


def get_request_tenant(request: Request) -> str:
    return str(getattr(request.state, "tenant_id", settings.TENANT_ID))


def get_request_actor(request: Request) -> str:
    return str(getattr(request.state, "actor", "system"))


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


async def require_api_key(request: Request, api_key: str | None = Security(_api_key_header)) -> str:
    """FastAPI dependency enforcing the configured API key on a route."""
    if not settings.API_KEY:
        request.state.tenant_id = settings.TENANT_ID
        request.state.actor = "dev"
        return settings.TENANT_ID  # auth disabled (development mode)

    tenant_id = tenant_from_api_key(api_key)
    valid = bool(tenant_id) and any(
        hmac.compare_digest(api_key or "", configured) for configured in _tenant_map()
    )
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Supply it in the X-API-Key header.",
        )
    request.state.tenant_id = tenant_id
    request.state.actor = f"api_key:{tenant_id}"
    return tenant_id


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
