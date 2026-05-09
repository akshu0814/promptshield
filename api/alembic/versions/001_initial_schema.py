"""Initial schema — all 4 tables

Revision ID: 001
Revises:
Create Date: 2026-05-06
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scan_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("app_id", sa.String(), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("verdict", sa.String(10), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("severity", sa.String(10), nullable=True),
        sa.Column("matched_rule", sa.String(100), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("scan_duration_ms", sa.Float(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scan_events_app_id", "scan_events", ["app_id"])
    op.create_index("ix_scan_events_created_at", "scan_events", ["created_at"])

    op.create_table(
        "rules",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("rule_id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("pattern", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_id"),
    )
    op.create_index("ix_rules_rule_id", "rules", ["rule_id"])

    op.create_table(
        "apps",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("app_id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("api_key", sa.String(200), nullable=False),
        sa.Column("block_mode", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("app_id"),
    )
    op.create_index("ix_apps_app_id", "apps", ["app_id"])

    op.create_table(
        "alert_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("scan_event_id", sa.String(), nullable=False),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_logs_scan_event_id", "alert_logs", ["scan_event_id"])


def downgrade() -> None:
    op.drop_table("alert_logs")
    op.drop_table("apps")
    op.drop_table("rules")
    op.drop_table("scan_events")
