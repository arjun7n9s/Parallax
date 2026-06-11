"""
Add taint_flows table for FlowDroid analysis results.

Hand-written to match the TaintFlow dataclass structure.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0005_add_taint_flows"
down_revision = "0004_add_observations_and_links"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "taint_flows",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("submission_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("source_class", sa.String(length=512), nullable=False),
        sa.Column("source_method", sa.String(length=256), nullable=False),
        sa.Column("sink_class", sa.String(length=512), nullable=False),
        sa.Column("sink_method", sa.String(length=256), nullable=False),
        sa.Column("path", sa.dialects.postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("risk", sa.String(length=32), nullable=False, server_default="MEDIUM"),
        sa.Column("attck_technique", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_taint_flows_submission_id", "taint_flows", ["submission_id"])
    op.create_index("ix_taint_flows_risk", "taint_flows", ["risk"])

def downgrade() -> None:
    op.drop_index("ix_taint_flows_risk", table_name="taint_flows")
    op.drop_index("ix_taint_flows_submission_id", table_name="taint_flows")
    op.drop_table("taint_flows")
