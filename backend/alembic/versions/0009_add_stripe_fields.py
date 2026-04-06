"""Add Stripe billing fields to users table.

Revision ID: 0009_add_stripe_fields
Revises: 0008_phase26
Create Date: 2024-01-09 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0009_add_stripe_fields"
down_revision = "0008_phase26"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    insp = inspect(conn)
    return column in [c["name"] for c in insp.get_columns(table)]


def upgrade() -> None:
    columns = [
        ("stripe_customer_id", sa.String(255)),
        ("stripe_subscription_id", sa.String(255)),
        ("stripe_price_id", sa.String(255)),
        ("stripe_subscription_status", sa.String(50)),
        ("subscription_period_end", sa.DateTime(timezone=True)),
    ]
    for col_name, col_type in columns:
        if not _column_exists("users", col_name):
            op.add_column("users", sa.Column(col_name, col_type, nullable=True))

    # Create index only if it doesn't already exist
    conn = op.get_bind()
    insp = inspect(conn)
    existing_indexes = [i["name"] for i in insp.get_indexes("users")]
    if "ix_users_stripe_customer_id" not in existing_indexes:
        op.create_index("ix_users_stripe_customer_id", "users", ["stripe_customer_id"])


def downgrade() -> None:
    op.drop_index("ix_users_stripe_customer_id", table_name="users")
    op.drop_column("users", "subscription_period_end")
    op.drop_column("users", "stripe_subscription_status")
    op.drop_column("users", "stripe_price_id")
    op.drop_column("users", "stripe_subscription_id")
    op.drop_column("users", "stripe_customer_id")