"""Phase 2.4 — Multi-Tenancy: teams, usage, flags, and support tickets."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0004_phase24"
down_revision = "0003_phase23"
branch_labels = None
depends_on = None


def upgrade():
    team_role = sa.Enum("admin", "member", "viewer", name="team_role")
    invite_status = sa.Enum("pending", "accepted", "declined", "expired", name="invite_status")
    usage_type = sa.Enum(
        "lead_created",
        "lead_enriched",
        "search_executed",
        "export_generated",
        "api_call",
        "pipeline_run",
        name="usage_event_type",
    )
    ticket_status = sa.Enum("open", "in_progress", "resolved", "closed", name="ticket_status")
    ticket_prio = sa.Enum("low", "medium", "high", "critical", name="ticket_priority")

    for enum in (team_role, invite_status, usage_type, ticket_status, ticket_prio):
        enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "teams",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("settings", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_teams_owner", "teams", ["owner_id"])
    op.create_index("idx_teams_slug", "teams", ["slug"])

    op.create_table(
        "team_memberships",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", team_role, nullable=False, server_default="member"),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("team_id", "user_id"),
    )
    op.create_index("idx_tm_team", "team_memberships", ["team_id"])
    op.create_index("idx_tm_user", "team_memberships", ["user_id"])

    op.create_table(
        "team_invitations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invited_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", team_role, nullable=False, server_default="member"),
        sa.Column("token", sa.String(64), nullable=False, unique=True),
        sa.Column("status", invite_status, nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_inv_token", "team_invitations", ["token"])
    op.create_index("idx_inv_email", "team_invitations", ["email"])

    op.add_column(
        "leads",
        sa.Column("team_id", UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("idx_leads_team", "leads", ["team_id"])

    op.create_table(
        "usage_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("team_id", UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", usage_type, nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_ue_user", "usage_events", ["user_id", "occurred_at"])
    op.create_index("idx_ue_team", "usage_events", ["team_id", "occurred_at"])

    op.create_table(
        "feature_flags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(100), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("target", JSONB, nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "support_tickets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("status", ticket_status, nullable=False, server_default="open"),
        sa.Column("priority", ticket_prio, nullable=False, server_default="medium"),
        sa.Column("admin_notes", sa.Text, nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_tickets_user", "support_tickets", ["user_id"])
    op.create_index("idx_tickets_status", "support_tickets", ["status"])


def downgrade():
    op.drop_table("support_tickets")
    op.drop_table("feature_flags")
    op.drop_index("idx_ue_team", "usage_events")
    op.drop_index("idx_ue_user", "usage_events")
    op.drop_table("usage_events")
    op.drop_index("idx_leads_team", "leads")
    op.drop_column("leads", "team_id")
    op.drop_table("team_invitations")
    op.drop_table("team_memberships")
    op.drop_table("teams")

    for name in (
        "team_role",
        "invite_status",
        "usage_event_type",
        "ticket_status",
        "ticket_priority",
    ):
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)
