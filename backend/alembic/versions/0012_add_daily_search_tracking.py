"""Add daily search tracking columns to users.

Revision ID: 0012
Revises: 0011
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def _col_exists(bind, table, col):
    try:
        return col in {c["name"] for c in inspect(bind).get_columns(table)}
    except Exception:
        return False


def upgrade() -> None:
    bind = op.get_bind()
    if not _col_exists(bind, "users", "daily_searches"):
        op.add_column("users", sa.Column(
            "daily_searches", sa.Integer(), nullable=False,
            server_default="0",
            comment="Searches performed today by this registered user"
        ))
    if not _col_exists(bind, "users", "daily_searches_reset_at"):
        op.add_column("users", sa.Column(
            "daily_searches_reset_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ))


def downgrade() -> None:
    op.drop_column("users", "daily_searches_reset_at")
    op.drop_column("users", "daily_searches")
