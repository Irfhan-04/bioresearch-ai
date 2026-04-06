"""Add missing indexes from Phase 2.4 spec.

Revision ID: 0005_indexes
Revises:     0004_phase24
"""

from alembic import op

revision      = "0005_indexes"
down_revision = "0004_phase24"
branch_labels = None
depends_on    = None


def upgrade():
    # ------------------------------------------------------------------
    # 1. Composite functional index for monthly quota enforcement.
    #
    #    TierQuotaService.check_and_enforce() runs:
    #      WHERE user_id = X AND event_type = Y AND occurred_at >= <month>
    #
    #    A functional index on date_trunc('month', occurred_at) lets
    #    PostgreSQL satisfy the month filter without scanning old rows.
    #
    #    op.execute() is required here because Alembic's create_index()
    #    does not support SQL expressions as index columns.
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_usage_events_type_month
        ON usage_events (user_id, event_type, date_trunc('month', occurred_at));
        """
    )

    # ------------------------------------------------------------------
    # 2. Standard B-tree index for team-scoped invitation lookups.
    #
    #    Specified in the Phase 2.4 SQL schema alongside idx_inv_token
    #    and idx_inv_email, but omitted from the 0004 migration.
    # ------------------------------------------------------------------
    op.create_index(
        "idx_invitations_team",
        "team_invitations",
        ["team_id"],
    )


def downgrade():
    op.drop_index("idx_invitations_team", table_name="team_invitations")
    op.execute("DROP INDEX IF EXISTS idx_usage_events_type_month;")
