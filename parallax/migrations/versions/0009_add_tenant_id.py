"""Add tenant_id columns for API multi-tenancy scoping."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0009_add_tenant_id"
down_revision = "0008_add_batch_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    for table in ("submissions", "iocs", "audit_log"):
        op.add_column(
            table,
            sa.Column("tenant_id", sa.String(length=128), nullable=False, server_default="default"),
        )
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
        op.alter_column(table, "tenant_id", server_default=None)

    constraints = {item["name"] for item in inspector.get_unique_constraints("submissions")}
    indexes = {item["name"]: item for item in inspector.get_indexes("submissions")}
    if "submissions_sha256_key" in constraints:
        op.drop_constraint("submissions_sha256_key", "submissions", type_="unique")
    if indexes.get("ix_submissions_sha256", {}).get("unique"):
        op.drop_index("ix_submissions_sha256", table_name="submissions")
        op.create_index("ix_submissions_sha256", "submissions", ["sha256"])

    op.create_unique_constraint(
        "uq_submissions_tenant_sha256",
        "submissions",
        ["tenant_id", "sha256"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = {item["name"]: item for item in inspector.get_indexes("submissions")}

    op.drop_constraint("uq_submissions_tenant_sha256", "submissions", type_="unique")
    if "ix_submissions_sha256" in indexes:
        op.drop_index("ix_submissions_sha256", table_name="submissions")
    op.create_index("ix_submissions_sha256", "submissions", ["sha256"], unique=True)
    for table in ("audit_log", "iocs", "submissions"):
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_column(table, "tenant_id")
