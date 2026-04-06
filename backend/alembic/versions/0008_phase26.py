"""Phase 2.6 — CRM, activity tables, assigned_to column.

Revision ID: 0008_phase26
Revises: 0007_phase25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

revision = "0008_phase26"
down_revision = "0007_phase25"
branch_labels = None
depends_on = None


def upgrade():
    crm_provider = sa.Enum("hubspot", "pipedrive", "salesforce", "custom", name="crm_provider")
    sync_direction = sa.Enum("push", "pull", "both", name="sync_direction")
    activity_type = sa.Enum(
        "note",
        "comment",
        "assignment",
        "status_change",
        "reminder",
        "mention",
        "enrichment",
        "score_change",
        name="activity_type",
    )
    for enum_type in (crm_provider, sync_direction, activity_type):
        enum_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "crm_connections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", crm_provider, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("credentials_encrypted", sa.Text(), nullable=False),
        sa.Column("field_map", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("sync_direction", sync_direction, nullable=False, server_default="push"),
        sa.Column("auto_sync", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sync_filter", JSONB, nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_status", sa.String(50), nullable=True),
        sa.Column("total_synced_leads", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_crm_connections_user", "crm_connections", ["user_id"])

    op.create_table(
        "crm_sync_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "connection_id",
            UUID(as_uuid=True),
            sa.ForeignKey("crm_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("leads_pushed", sa.Integer(), server_default="0"),
        sa.Column("leads_updated", sa.Integer(), server_default="0"),
        sa.Column("leads_failed", sa.Integer(), server_default="0"),
        sa.Column("error_detail", sa.Text(), nullable=True),
    )
    op.create_index("idx_crm_sync_logs_conn", "crm_sync_logs", ["connection_id"])

    op.create_table(
        "lead_activities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "lead_id",
            UUID(as_uuid=True),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("activity_type", activity_type, nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("mentioned_user_ids", ARRAY(UUID(as_uuid=True)), nullable=True),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("reminder_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reminder_done", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_la_lead", "lead_activities", ["lead_id"])
    op.create_index("idx_la_type", "lead_activities", ["lead_id", "activity_type"])
    op.create_index("idx_la_reminder", "lead_activities", ["reminder_due_at"])

    op.add_column(
        "leads",
        sa.Column(
            "assigned_to",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("idx_leads_assigned", "leads", ["assigned_to"])


def downgrade():
    op.drop_index("idx_leads_assigned", "leads")
    op.drop_column("leads", "assigned_to")
    op.drop_index("idx_la_reminder", "lead_activities")
    op.drop_index("idx_la_type", "lead_activities")
    op.drop_index("idx_la_lead", "lead_activities")
    op.drop_table("lead_activities")
    op.drop_index("idx_crm_sync_logs_conn", "crm_sync_logs")
    op.drop_table("crm_sync_logs")
    op.drop_index("idx_crm_connections_user", "crm_connections")
    op.drop_table("crm_connections")
    op.execute("DROP TYPE IF EXISTS activity_type;")
    op.execute("DROP TYPE IF EXISTS sync_direction;")
    op.execute("DROP TYPE IF EXISTS crm_provider;")
