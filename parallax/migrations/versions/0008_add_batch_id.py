"""
Add submissions.batch_id to group APKs submitted together via POST /analyze/batch.

Hand-written to match the Submission model. Nullable + indexed; no backfill.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0008_add_batch_id"
down_revision = "0007_add_webhook_url"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "submissions",
        sa.Column("batch_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_submissions_batch_id", "submissions", ["batch_id"])


def downgrade() -> None:
    op.drop_index("ix_submissions_batch_id", table_name="submissions")
    op.drop_column("submissions", "batch_id")
