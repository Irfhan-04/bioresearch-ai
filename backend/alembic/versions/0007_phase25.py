"""Phase 2.5 — add alert_rules table and webhook enum values.

Revision ID: 0007_phase25
Revises: 0006_add_owner_team_role
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0007_phase25"
down_revision = "0006_add_owner_team_role"
branch_labels = None
depends_on = None


def upgrade():
    alert_trigger = sa.Enum("high_value_lead", "new_nih_grant", "conference_match", "score_increase", name="alert_trigger")
    alert_channel = sa.Enum("email", "webhook", "both", name="alert_channel")
    alert_trigger.create(op.get_bind(), checkfirst=True)
    alert_channel.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "alert_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("trigger", alert_trigger, nullable=False),
        sa.Column("channel", alert_channel, nullable=False, server_default="email"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("conditions", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("throttle_seconds", sa.Integer(), nullable=False, server_default="3600"),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trigger_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_alert_rules_user", "alert_rules", ["user_id"])
    op.create_index("idx_alert_rules_active", "alert_rules", ["user_id", "is_active"])
    op.execute("ALTER TYPE webhookeventtype ADD VALUE IF NOT EXISTS 'lead.scored';")
    op.execute("ALTER TYPE webhookeventtype ADD VALUE IF NOT EXISTS 'lead.high_value';")
    op.execute("CREATE INDEX IF NOT EXISTS idx_leads_score ON leads (user_id, propensity_score DESC);")


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_leads_score;")
    op.drop_index("idx_alert_rules_active", table_name="alert_rules")
    op.drop_index("idx_alert_rules_user", table_name="alert_rules")
    op.drop_table("alert_rules")
    op.execute("DROP TYPE IF EXISTS alert_trigger;")
    op.execute("DROP TYPE IF EXISTS alert_channel;")
