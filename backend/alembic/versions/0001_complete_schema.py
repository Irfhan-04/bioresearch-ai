"""BioResearch AI — Complete schema (single migration, final state).

Replaces: 0001_initial, 0003_phase23, 0005_add_missing_indexes,
          0010_research_intelligence, 0011_drop_subscription_tier,
          0012_add_daily_search_tracking

This is the single source of truth for the database schema.
Run on a blank database: alembic upgrade head
Run on an existing database: alembic upgrade head (idempotent — skips
  existing tables and columns, safe to re-run).

Revision ID: 0001_complete_schema
Revises: (none — this is the root)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy import inspect, text

revision = "0001_complete_schema"
down_revision = None
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Helpers — all DDL operations are idempotent (safe to re-run)
# ---------------------------------------------------------------------------

def _has_table(bind, table_name: str) -> bool:
    """Return True if the table already exists in the database."""
    try:
        return table_name in inspect(bind).get_table_names()
    except Exception:
        return False


def _has_column(bind, table_name: str, column_name: str) -> bool:
    """Return True if the column already exists in the given table."""
    try:
        cols = {col["name"] for col in inspect(bind).get_columns(table_name)}
        return column_name in cols
    except Exception:
        return False


def _has_index(bind, table_name: str, index_name: str) -> bool:
    """Return True if the named index already exists on the given table."""
    try:
        return any(
            ix["name"] == index_name
            for ix in inspect(bind).get_indexes(table_name)
        )
    except Exception:
        return False


def _add_column_if_missing(bind, table_name: str, column_name: str, column_def: str) -> None:
    """Add a column only if it does not already exist."""
    if not _has_column(bind, table_name, column_name):
        bind.execute(text(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"
        ))
        print(f"[OK] Added {table_name}.{column_name}")
    else:
        print(f"[SKIP] {table_name}.{column_name} already exists")


# ---------------------------------------------------------------------------
# upgrade — create the complete final schema
# ---------------------------------------------------------------------------

def upgrade() -> None:
    bind = op.get_bind()

    # ── 1. USERS TABLE ──────────────────────────────────────────────────────
    # Final state: no subscription/Stripe columns, WITH daily search tracking.
    if not _has_table(bind, "users"):
        op.create_table(
            "users",
            sa.Column(
                "id",
                UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("password_hash", sa.String(255), nullable=False),
            sa.Column("full_name", sa.String(255), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("api_keys", JSONB(), nullable=False, server_default="[]"),
            sa.Column("usage_stats", JSONB(), nullable=False, server_default="{}"),
            sa.Column("preferences", JSONB(), nullable=False, server_default="{}"),
            # Daily search rate-limiting (no billing — two tiers: guest IP-based, registered account)
            sa.Column(
                "daily_searches",
                sa.Integer(),
                nullable=False,
                server_default="0",
                comment="Searches performed today by this registered user",
            ),
            sa.Column(
                "daily_searches_reset_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
                comment="Last time daily_searches was reset to 0",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        )
        bind.execute(text("CREATE UNIQUE INDEX ix_users_email ON users (email)"))
        bind.execute(text("CREATE INDEX ix_users_id ON users (id)"))
        print("[OK] Created users table")
    else:
        # Table exists — apply incremental column additions for pre-existing databases
        print("[SKIP] users table already exists — applying incremental column additions")

        # Remove billing columns if they survived earlier cleanup
        for col in [
            "subscription_tier", "stripe_customer_id", "stripe_subscription_id",
            "stripe_price_id", "stripe_subscription_status", "subscription_period_end",
        ]:
            if _has_column(bind, "users", col):
                bind.execute(text(f"ALTER TABLE users DROP COLUMN IF EXISTS {col}"))
                print(f"[OK] Dropped users.{col}")

        # Add daily search tracking if missing
        _add_column_if_missing(
            bind, "users", "daily_searches",
            "INTEGER NOT NULL DEFAULT 0"
        )
        _add_column_if_missing(
            bind, "users", "daily_searches_reset_at",
            "TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()"
        )

    # ── 2. RESEARCHERS TABLE ─────────────────────────────────────────────────
    # Final state: renamed from leads, with all AI/ML intelligence columns.
    if not _has_table(bind, "researchers"):
        # Handle legacy: if the old leads table still exists, rename it first
        if _has_table(bind, "leads"):
            op.rename_table("leads", "researchers")
            print("[OK] Renamed leads → researchers")
            # Rename legacy score column if present
            if _has_column(bind, "researchers", "propensity_score"):
                bind.execute(text(
                    "ALTER TABLE researchers RENAME COLUMN propensity_score TO relevance_score"
                ))
                print("[OK] Renamed researchers.propensity_score → relevance_score")
        else:
            # Fresh database — create from scratch
            op.create_table(
                "researchers",
                sa.Column(
                    "id",
                    UUID(as_uuid=True),
                    primary_key=True,
                    server_default=sa.text("gen_random_uuid()"),
                ),
                # Owner
                sa.Column(
                    "user_id",
                    UUID(as_uuid=True),
                    sa.ForeignKey("users.id", ondelete="CASCADE"),
                    nullable=False,
                ),
                sa.Column(
                    "assigned_to",
                    UUID(as_uuid=True),
                    sa.ForeignKey("users.id", ondelete="SET NULL"),
                    nullable=True,
                ),

                # ── Identity ─────────────────────────────────────────────────
                sa.Column("name", sa.String(255), nullable=False),
                sa.Column("title", sa.String(255), nullable=True),
                sa.Column("company", sa.String(255), nullable=True),
                sa.Column("location", sa.String(255), nullable=True),
                sa.Column("company_hq", sa.String(255), nullable=True),

                # ── Contact ──────────────────────────────────────────────────
                sa.Column("email", sa.String(255), nullable=True),
                sa.Column("phone", sa.String(50), nullable=True),
                sa.Column("linkedin_url", sa.String(500), nullable=True),
                sa.Column("twitter_url", sa.String(500), nullable=True),
                sa.Column("website", sa.String(500), nullable=True),

                # ── ML Relevance Scoring (Component 1 + 4) ───────────────────
                sa.Column("relevance_score", sa.Integer(), nullable=True,
                          comment="0–100 score from XGBoost/RandomForest classifier"),
                sa.Column("rank", sa.Integer(), nullable=True),
                sa.Column("relevance_tier", sa.String(20), nullable=True,
                          comment="HIGH / MEDIUM / LOW — predicted class from ML model"),
                sa.Column("relevance_confidence", sa.Float(), nullable=True,
                          comment="Model probability for predicted tier"),
                sa.Column("shap_contributions", JSONB(), nullable=True,
                          comment="Top 5 SHAP feature contributions — drives ScoreExplanationCard UI"),

                # ── Semantic Embeddings (Component 2) ────────────────────────
                sa.Column("abstract_text", sa.Text(), nullable=True,
                          comment="Raw PubMed abstract — source for embedding_service"),
                sa.Column("abstract_embedding_id", sa.String(255), nullable=True,
                          comment="ChromaDB document ID for this researcher"),
                sa.Column("abstract_relevance_score", sa.Float(), nullable=True,
                          comment=(
                              "Cosine similarity vs default biotech query, stored at enrichment time. "
                              "Used as ML feature 12. NOT the per-query semantic score."
                          )),

                # ── Research Area Classifier (Component 2 dependency) ─────────
                sa.Column("research_area", sa.String(100), nullable=True,
                          comment=(
                              "Output of research_area_classifier.py: "
                              "toxicology / drug_safety / drug_discovery / "
                              "preclinical / organoids / in_vitro / biomarkers / general_biotech"
                          )),
                sa.Column("domain_coverage_score", sa.Float(), nullable=True,
                          comment="Domain keyword coverage across title + abstract — ML feature 11"),

                # ── LLM Intelligence (Component 3) ───────────────────────────
                sa.Column("intelligence", JSONB(), nullable=True,
                          comment=(
                              "Structured JSON from intelligence_service.py: "
                              "research_summary, domain_significance, research_connections, "
                              "key_topics, research_area_tags, activity_level, data_gaps"
                          )),
                sa.Column("intelligence_generated_at", sa.DateTime(timezone=True), nullable=True,
                          comment="Timestamp for Redis cache invalidation"),

                # ── Contact Discovery ─────────────────────────────────────────
                sa.Column("contact_confidence", sa.Float(), nullable=True,
                          comment="Confidence of contact discovery (0–1)"),

                # ── Publication metadata (PubMed) ─────────────────────────────
                sa.Column("recent_publication", sa.Boolean(), nullable=False, server_default="false"),
                sa.Column("publication_year", sa.Integer(), nullable=True),
                sa.Column("publication_title", sa.Text(), nullable=True),
                sa.Column("publication_count", sa.Integer(), nullable=False, server_default="0"),

                # ── Institution ───────────────────────────────────────────────
                sa.Column("company_funding", sa.String(50), nullable=True),
                sa.Column("company_size", sa.String(50), nullable=True),
                sa.Column("uses_3d_models", sa.Boolean(), nullable=False, server_default="false"),

                # ── Enrichment metadata ───────────────────────────────────────
                sa.Column("data_sources", JSONB(), nullable=False, server_default="[]",
                          comment='Array of source identifiers e.g. ["pubmed","hunter.io"]'),
                sa.Column("enrichment_data", JSONB(), nullable=False, server_default="{}"),
                sa.Column("custom_fields", JSONB(), nullable=False, server_default="{}"),
                sa.Column("tags", JSONB(), nullable=False, server_default="[]"),
                sa.Column("notes", sa.Text(), nullable=True),
                sa.Column("status", sa.String(50), nullable=False, server_default="'NEW'",
                          comment="NEW / REVIEWING / NOTED / CONTACTED / ARCHIVED"),

                # ── Timestamps ────────────────────────────────────────────────
                sa.Column("last_contacted_at", sa.DateTime(timezone=True), nullable=True),
                sa.Column("created_at", sa.DateTime(timezone=True),
                          nullable=False, server_default=sa.text("now()")),
                sa.Column("updated_at", sa.DateTime(timezone=True),
                          nullable=False, server_default=sa.text("now()")),
            )
            print("[OK] Created researchers table")

    # Add any AI columns missing from pre-existing researchers tables
    ai_columns = {
        "abstract_text":             "TEXT",
        "abstract_embedding_id":     "VARCHAR(255)",
        "abstract_relevance_score":  "FLOAT",
        "research_area":             "VARCHAR(100)",
        "domain_coverage_score":     "FLOAT",
        "relevance_confidence":      "FLOAT",
        "shap_contributions":        "JSONB",
        "intelligence":              "JSONB",
        "intelligence_generated_at": "TIMESTAMP WITH TIME ZONE",
        "contact_confidence":        "FLOAT",
    }
    for col_name, col_def in ai_columns.items():
        _add_column_if_missing(bind, "researchers", col_name, col_def)

    # Indexes on researchers
    if not _has_index(bind, "researchers", "ix_researchers_id"):
        bind.execute(text("CREATE INDEX ix_researchers_id ON researchers (id)"))
    if not _has_index(bind, "researchers", "ix_researchers_user_id"):
        bind.execute(text("CREATE INDEX ix_researchers_user_id ON researchers (user_id)"))
    if not _has_index(bind, "researchers", "ix_researchers_relevance_score"):
        bind.execute(text("CREATE INDEX ix_researchers_relevance_score ON researchers (relevance_score)"))
    if not _has_index(bind, "researchers", "ix_researchers_research_area"):
        bind.execute(text("CREATE INDEX ix_researchers_research_area ON researchers (research_area)"))

    # ── 3. SEARCHES TABLE ────────────────────────────────────────────────────
    if not _has_table(bind, "searches"):
        op.create_table(
            "searches",
            sa.Column(
                "id",
                UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "user_id",
                UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("query", sa.Text(), nullable=False),
            sa.Column("search_type", sa.String(50), nullable=False),
            sa.Column("filters", JSONB(), nullable=False, server_default="{}"),
            sa.Column("results_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("results_snapshot", JSONB(), nullable=False, server_default="[]"),
            sa.Column("is_saved", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("saved_name", sa.String(255), nullable=True),
            sa.Column("execution_time_ms", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True),
                      nullable=False, server_default=sa.text("now()")),
        )
        bind.execute(text("CREATE INDEX ix_searches_id ON searches (id)"))
        bind.execute(text("CREATE INDEX ix_searches_user_id ON searches (user_id)"))
        bind.execute(text("CREATE INDEX ix_searches_search_type ON searches (search_type)"))
        print("[OK] Created searches table")

    # ── 4. EXPORTS TABLE ─────────────────────────────────────────────────────
    if not _has_table(bind, "exports"):
        # Create enums first (idempotent via IF NOT EXISTS)
        bind.execute(text(
            "DO $$ BEGIN "
            "  CREATE TYPE exportformat AS ENUM ('csv','excel','json','pdf'); "
            "EXCEPTION WHEN duplicate_object THEN NULL; "
            "END $$;"
        ))
        bind.execute(text(
            "DO $$ BEGIN "
            "  CREATE TYPE exportstatus AS ENUM ('pending','processing','completed','failed','expired'); "
            "EXCEPTION WHEN duplicate_object THEN NULL; "
            "END $$;"
        ))
        op.create_table(
            "exports",
            sa.Column(
                "id",
                UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "user_id",
                UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("file_name", sa.String(255), nullable=False),
            sa.Column("file_url", sa.String(1000), nullable=True),
            sa.Column("file_size_bytes", sa.Integer(), nullable=True),
            sa.Column("format", sa.Text(), nullable=False),    # exportformat enum
            sa.Column("status", sa.Text(), nullable=False, server_default="'pending'"),
            sa.Column("records_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("filters", JSONB(), nullable=False, server_default="{}"),
            sa.Column("columns", JSONB(), nullable=False, server_default="[]"),
            sa.Column("error_message", sa.String(500), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("downloaded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("download_count", sa.Integer(), nullable=False, server_default="0"),
            # completed_at is referenced in Export.mark_as_completed() and to_dict()
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True),
                      nullable=False, server_default=sa.text("now()")),
        )
        bind.execute(text("CREATE INDEX ix_exports_id ON exports (id)"))
        bind.execute(text("CREATE INDEX ix_exports_user_id ON exports (user_id)"))
        bind.execute(text("CREATE INDEX ix_exports_expires_at ON exports (expires_at)"))
        print("[OK] Created exports table")

    print("\n[DONE] BioResearch AI complete schema applied successfully.")
    print("       Tables: users, researchers, searches, exports")


# ---------------------------------------------------------------------------
# downgrade — not supported for a complete-schema migration
# ---------------------------------------------------------------------------

def downgrade() -> None:
    # This is the root migration — downgrade is intentionally not implemented.
    # To reset: drop all tables manually and re-run alembic upgrade head.
    raise NotImplementedError(
        "Downgrade not supported for root migration. "
        "Drop all tables manually and run: alembic upgrade head"
    )