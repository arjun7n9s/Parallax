"""Small helpers for writing tenant-aware audit records."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from parallax.core.models import AuditLog


async def write_audit_log(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor: str,
    action: str,
    submission_id: uuid.UUID | None = None,
    detail: dict[str, Any] | None = None,
) -> AuditLog:
    """Attach an audit event to the current transaction."""
    entry = AuditLog(
        tenant_id=tenant_id,
        actor=actor,
        action=action,
        submission_id=submission_id,
        detail=detail,
    )
    db.add(entry)
    await db.flush()
    return entry
