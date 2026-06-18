"""
Add submissions.webhook_url for per-submission completion webhooks.

Hand-written to match the Submission model. Nullable, no backfill needed.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0007_add_webhook_url"
down_revision = "0006_captured_at_bigint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "submissions",
        sa.Column("webhook_url", sa.String(length=2048), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("submissions", "webhook_url")
