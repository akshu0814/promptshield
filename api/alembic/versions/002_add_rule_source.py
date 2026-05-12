"""Add source column to rules table

Revision ID: 002
Revises: 001
Create Date: 2026-05-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "rules",
        sa.Column("source", sa.String(20), nullable=False, server_default="custom"),
    )


def downgrade() -> None:
    op.drop_column("rules", "source")
