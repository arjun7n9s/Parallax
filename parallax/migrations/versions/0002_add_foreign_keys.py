"""0002_add_foreign_keys - Add FK constraints to iocs and audit_log tables.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-08
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # IOCs → Submissions (CASCADE delete — when submission is deleted, its IOCs go too)
    op.create_foreign_key(
        "fk_iocs_submission_id",
        "iocs",
        "submissions",
        ["submission_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # AuditLog → Submissions (SET NULL — audit records survive submission deletion)
    op.create_foreign_key(
        "fk_audit_log_submission_id",
        "audit_log",
        "submissions",
        ["submission_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_audit_log_submission_id", "audit_log", type_="foreignkey")
    op.drop_constraint("fk_iocs_submission_id", "iocs", type_="foreignkey")
