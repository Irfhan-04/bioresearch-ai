"""Research intelligence schema — rename leads table and add AI columns.

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import inspect

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def _has_table(bind, table_name: str) -> bool:
    return table_name in inspect(bind).get_table_names()


def _has_column(bind, table_name: str, column_name: str) -> bool:
    cols = {col["name"] for col in inspect(bind).get_columns(table_name)}
    return column_name in cols


def _has_index(bind, table_name: str, index_name: str) -> bool:
    return any(ix["name"] == index_name for ix in inspect(bind).get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()

    if _has_table(bind, "leads") and not _has_table(bind, "researchers"):
        op.rename_table("leads", "researchers")

    if _has_table(bind, "researchers") and _has_column(bind, "researchers", "propensity_score"):
        op.alter_column("researchers", "propensity_score", new_column_name="relevance_score")

    if _has_table(bind, "researchers") and _has_column(bind, "researchers", "propensity_tier") and not _has_column(bind, "researchers", "relevance_tier"):
        op.alter_column("researchers", "propensity_tier", new_column_name="relevance_tier")

    if _has_table(bind, "researchers") and _has_column(bind, "researchers", "is_decision_maker") and not _has_column(bind, "researchers", "is_senior_researcher"):
        op.alter_column("researchers", "is_decision_maker", new_column_name="is_senior_researcher")

    if _has_table(bind, "researchers") and _has_column(bind, "researchers", "email_confidence") and not _has_column(bind, "researchers", "contact_confidence"):
        op.alter_column("researchers", "email_confidence", new_column_name="contact_confidence")

    new_columns = [
        ("abstract_text", sa.Column("abstract_text", sa.Text(), nullable=True, comment="Raw PubMed abstract text for embedding")),
        ("abstract_embedding_id", sa.Column("abstract_embedding_id", sa.String(255), nullable=True, comment="ChromaDB document ID for this researcher's embedding")),
        ("abstract_relevance_score", sa.Column("abstract_relevance_score", sa.Float(), nullable=True, comment="Cosine similarity vs default biotech query")),
        ("research_area", sa.Column("research_area", sa.String(100), nullable=True, comment="Research area classifier output")),
        ("domain_coverage_score", sa.Column("domain_coverage_score", sa.Float(), nullable=True, comment="Domain keyword coverage score")),
        ("relevance_tier", sa.Column("relevance_tier", sa.String(20), nullable=True, comment="XGBoost prediction: high / medium / low")),
        ("relevance_confidence", sa.Column("relevance_confidence", sa.Float(), nullable=True, comment="Model probability for predicted relevance tier")),
        ("shap_contributions", sa.Column("shap_contributions", JSONB(), nullable=True, comment="Top 5 SHAP feature contributions")),
        ("intelligence", sa.Column("intelligence", JSONB(), nullable=True, comment="LLM-generated research intelligence JSON")),
        ("intelligence_generated_at", sa.Column("intelligence_generated_at", sa.DateTime(timezone=True), nullable=True, comment="Timestamp of last intelligence generation")),
        ("contact_confidence", sa.Column("contact_confidence", sa.Float(), nullable=True, comment="Confidence score for discovered contact information")),
    ]

    for name, column in new_columns:
        if _has_table(bind, "researchers") and not _has_column(bind, "researchers", name):
            op.add_column("researchers", column)

    if _has_table(bind, "researchers") and not _has_index(bind, "researchers", "ix_researchers_research_area"):
        op.create_index("ix_researchers_research_area", "researchers", ["research_area"])

    if _has_table(bind, "researchers") and not _has_index(bind, "researchers", "ix_researchers_relevance_tier"):
        op.create_index("ix_researchers_relevance_tier", "researchers", ["relevance_tier"])


def downgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "researchers") and _has_index(bind, "researchers", "ix_researchers_relevance_tier"):
        op.drop_index("ix_researchers_relevance_tier", table_name="researchers")
    if _has_table(bind, "researchers") and _has_index(bind, "researchers", "ix_researchers_research_area"):
        op.drop_index("ix_researchers_research_area", table_name="researchers")

    for col in [
        "contact_confidence",
        "intelligence_generated_at",
        "intelligence",
        "shap_contributions",
        "relevance_confidence",
        "domain_coverage_score",
        "research_area",
        "abstract_relevance_score",
        "abstract_embedding_id",
        "abstract_text",
    ]:
        if _has_table(bind, "researchers") and _has_column(bind, "researchers", col):
            op.drop_column("researchers", col)

    if _has_table(bind, "researchers") and _has_column(bind, "researchers", "relevance_score") and not _has_column(bind, "researchers", "propensity_score"):
        op.alter_column("researchers", "relevance_score", new_column_name="propensity_score")

    if _has_table(bind, "researchers") and not _has_table(bind, "leads"):
        op.rename_table("researchers", "leads")
