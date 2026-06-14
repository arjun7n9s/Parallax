"""widen observations.captured_at_ms to BigInteger

Epoch milliseconds (Date.now() ~1.7e12) overflow a 32-bit Integer, so inserting
any real frida/mitmproxy observation rolled back the entire dynamic transaction
and silently lost all runtime evidence. Widen to BigInteger.

Revision ID: 0006_observation_captured_at_bigint
Revises: 0005_add_taint_flows
"""

import sqlalchemy as sa
from alembic import op

revision = "0006_captured_at_bigint"
down_revision = "0005_add_taint_flows"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "observations",
        "captured_at_ms",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "observations",
        "captured_at_ms",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
