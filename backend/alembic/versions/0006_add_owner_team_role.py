"""Add 'owner' value to the team_role enum.

Revision ID: 0006_owner_role
Revises:     0005_indexes
"""

from alembic import op

revision      = "0006_add_owner_team_role"
down_revision = "0005_indexes"
branch_labels = None
depends_on    = None


def upgrade():
    # PostgreSQL requires ALTER TYPE … ADD VALUE for native enum types.
    # 'IF NOT EXISTS' prevents failure on re-run (idempotent).
    # The value is added BEFORE 'admin' so it sorts first in the enum.
    op.execute(
        "ALTER TYPE team_role ADD VALUE IF NOT EXISTS 'owner' BEFORE 'admin';"
    )

    # Backfill: set existing team creators (Team.owner_id) to role=OWNER
    # so historical data is consistent with the new role.
    op.execute(
        """
        UPDATE team_memberships tm
        SET    role = 'owner'
        FROM   teams t
        WHERE  tm.team_id = t.id
          AND  tm.user_id = t.owner_id
          AND  tm.role    = 'admin';
        """
    )


def downgrade():
    # Revert the backfill — restore owner rows to 'admin'
    op.execute(
        """
        UPDATE team_memberships tm
        SET    role = 'admin'
        FROM   teams t
        WHERE  tm.team_id = t.id
          AND  tm.user_id = t.owner_id
          AND  tm.role    = 'owner';
        """
    )
    # Note: PostgreSQL does not support removing enum values without
    # recreating the type. Leave 'owner' in the DB type after downgrade
    # to avoid breaking existing rows — the code will simply not use it.