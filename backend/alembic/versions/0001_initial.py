"""Initial migration — anchor for the migration chain.

Revision ID: 0001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Anchor revision — actual schema managed by subsequent migrations.
    # Run all migrations from a blank database: alembic upgrade head
    pass


def downgrade() -> None:
    pass
