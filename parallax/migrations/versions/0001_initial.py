"""0001_initial - Create submissions, iocs, and audit_log tables.

Revision ID: 0001
Revises: None
Create Date: 2026-06-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- Enum types
    analysis_status = sa.Enum(
        "queued", "triaging", "static", "dynamic", "reasoning", "complete", "failed",
        name="analysis_status",
    )
    analysis_priority = sa.Enum("critical", "high", "normal", "low", name="analysis_priority")
    ioc_type = sa.Enum(
        "ip", "domain", "url", "hash", "email", "certificate", "yara_rule",
        name="ioc_type",
    )

    # -- submissions
    op.create_table(
        "submissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("sha256", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("md5", sa.String(32), nullable=False),
        sa.Column("file_name", sa.String(512), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=False),
        sa.Column("package_name", sa.String(512), nullable=True),
        sa.Column("status", analysis_status, server_default="queued"),
        sa.Column("priority", analysis_priority, server_default="normal"),
        sa.Column("triage_score", sa.Float, nullable=True),
        sa.Column("final_score", sa.Float, nullable=True),
        sa.Column("verdict", sa.String(64), nullable=True),
        sa.Column("s3_path", sa.String(1024), nullable=False),
        sa.Column("metadata_json", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # -- iocs
    op.create_table(
        "iocs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("submission_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("ioc_type", ioc_type, nullable=False),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("context", sa.Text, nullable=True),
        sa.Column("confidence", sa.Float, server_default="0.0"),
        sa.Column("source_agent", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # -- audit_log
    op.create_table(
        "audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("submission_id", UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("action", sa.String(256), nullable=False),
        sa.Column("detail", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("iocs")
    op.drop_table("submissions")
    sa.Enum(name="analysis_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="analysis_priority").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="ioc_type").drop(op.get_bind(), checkfirst=True)
