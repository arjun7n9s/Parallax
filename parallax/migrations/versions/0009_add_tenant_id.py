"""Add tenant_id columns for API multi-tenancy scoping."""

import sqlalchemy as sa
from alembic import op

revision = "0009_add_tenant_id"
down_revision = "0008_add_batch_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("submissions", "iocs", "audit_log"):
        op.add_column(
            table,
            sa.Column("tenant_id", sa.String(length=128), nullable=False, server_default="default"),
        )
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
        op.alter_column(table, "tenant_id", server_default=None)
    op.drop_constraint("submissions_sha256_key", "submissions", type_="unique")
    op.create_unique_constraint(
        "uq_submissions_tenant_sha256",
        "submissions",
        ["tenant_id", "sha256"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_submissions_tenant_sha256", "submissions", type_="unique")
    op.create_unique_constraint("submissions_sha256_key", "submissions", ["sha256"])
    for table in ("audit_log", "iocs", "submissions"):
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_column(table, "tenant_id")
