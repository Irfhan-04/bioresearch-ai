"""
Tests for Phase 2.5 — Automation & Intelligence.

Covers:
  ScoringService — feature extraction, weighted scoring, batch rescore
  PipelineTemplates — list, get, create_from_template
  SmartAlertService — rule evaluation, throttle logic
  Alert endpoints — CRUD
  Scoring endpoints — config, stats, weights
"""

import types
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.deps import get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.api.v1.endpoints.alerts import (
    create_alert_rule,
    delete_alert_rule,
    get_alert_rule,
    list_alert_rules,
    update_alert_rule,
)
from app.api.v1.endpoints.pipelines import (
    create_from_template as create_pipeline_from_template,
    list_pipeline_templates,
)
from app.api.v1.endpoints.scoring import (
    ScoreWeights,
    get_scoring_config,
    get_scoring_stats,
    update_scoring_config,
)
from app.models.alert import AlertRule
from app.models.user import SubscriptionTier, User
from app.services.scoring_service import (
    DEFAULT_WEIGHTS,
    FeatureExtractor,
    ScoringService,
    WeightedScorer,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
async def test_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncSession:
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncClient:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as async_client:
        yield async_client

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        email="test@example.com",
        password_hash=get_password_hash("TestPass123!"),
        full_name="Test User",
        subscription_tier=SubscriptionTier.FREE,
        is_active=True,
        is_verified=True,
        is_superuser=False,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
async def auth_client(client: AsyncClient, test_user: User) -> AsyncClient:
    token = create_access_token(data={"sub": str(test_user.id)})
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client




def _make_user(**kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "email": "test@example.com",
        "password_hash": "hash",
        "full_name": "Test User",
        "subscription_tier": SubscriptionTier.FREE,
        "is_active": True,
        "is_verified": True,
        "is_superuser": False,
        "preferences": {},
    }
    return User(**{**defaults, **kwargs})


class _FakeResult:
    def __init__(self, value):
        self.value = value

    def scalars(self):
        return self

    def all(self):
        return list(self.value)

    def scalar_one_or_none(self):
        if isinstance(self.value, list):
            return self.value[0] if self.value else None
        return self.value

    def first(self):
        return self.value

    def __iter__(self):
        return iter(self.value)


class _FakePipelineDB:
    def add(self, obj):
        now = datetime.now(timezone.utc)
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        if getattr(obj, "created_at", None) is None:
            obj.created_at = now
        if getattr(obj, "updated_at", None) is None:
            obj.updated_at = now
        if getattr(obj, "last_run_results", None) is None:
            obj.last_run_results = {}
        if getattr(obj, "run_count", None) is None:
            obj.run_count = 0
        if getattr(obj, "success_count", None) is None:
            obj.success_count = 0
        if getattr(obj, "error_count", None) is None:
            obj.error_count = 0
        if getattr(obj, "total_leads_generated", None) is None:
            obj.total_leads_generated = 0
        self.obj = obj

    async def commit(self):
        return None

    async def refresh(self, obj):
        return None


class _FakeAlertDB:
    def __init__(self):
        self.rules = {}

    def add(self, rule):
        if getattr(rule, "id", None) is None:
            rule.id = uuid.uuid4()
        if getattr(rule, "is_active", None) is None:
            rule.is_active = True
        if getattr(rule, "conditions", None) is None:
            rule.conditions = {}
        if getattr(rule, "created_at", None) is None:
            rule.created_at = datetime.now(timezone.utc)
        self.rules[rule.id] = rule

    async def commit(self):
        return None

    async def refresh(self, rule):
        return None

    async def delete(self, rule):
        self.rules.pop(rule.id, None)

    async def execute(self, query):
        params = query.compile().params
        rule_id = next((value for key, value in params.items() if key.startswith("id_")), None)
        user_id = next((value for key, value in params.items() if key.startswith("user_id_")), None)
        rules = list(self.rules.values())
        if user_id is not None:
            rules = [rule for rule in rules if rule.user_id == user_id]
        if rule_id is not None:
            for rule in rules:
                if rule.id == rule_id:
                    return _FakeResult(rule)
            return _FakeResult(None)
        return _FakeResult(sorted(rules, key=lambda rule: rule.created_at or datetime.now(timezone.utc), reverse=True))


class _FakeScoringStatsDB:
    def __init__(self):
        self._results = [
            _FakeResult(types.SimpleNamespace(total=3, average=72.5, minimum=55, maximum=90)),
            _FakeResult([("HIGH", 1), ("MEDIUM", 2)]),
        ]

    async def execute(self, _query):
        return self._results.pop(0)


def _make_lead(**kwargs):
    """
    Build a lightweight lead stub without touching the database.

    Uses types.SimpleNamespace so attribute access works identically
    to a SQLAlchemy ORM instance, with stub implementations of the
    three methods ScoringService calls during scoring.
    """
    defaults = {
        "id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "name": "Dr. Test User",
        "title": "Director of Toxicology",
        "company": "Genentech Inc.",
        "location": "South San Francisco, CA",
        "email": "test@genentech.com",
        "linkedin_url": "https://linkedin.com/in/test",
        "recent_publication": True,
        "publication_count": 8,
        "company_funding": "Public",
        "propensity_score": None,
        "data_sources": ["pubmed"],
        "enrichment_data": {},
        "tags": [],
        "priority_tier": None,
    }
    data = {**defaults, **kwargs}

    def update_priority_tier():
        score = data.get("propensity_score")
        if score is None:
            data["priority_tier"] = "UNSCORED"
        elif score >= 70:
            data["priority_tier"] = "HIGH"
        elif score >= 50:
            data["priority_tier"] = "MEDIUM"
        else:
            data["priority_tier"] = "LOW"

    def set_enrichment(key, value):
        data.setdefault("enrichment_data", {})[key] = value

    def get_priority_tier():
        return data.get("priority_tier") or "UNSCORED"

    lead = types.SimpleNamespace(**data)
    lead.update_priority_tier = update_priority_tier
    lead.set_enrichment = set_enrichment
    lead.get_priority_tier = get_priority_tier
    return lead


# =============================================================================
# Feature Extractor
# =============================================================================

class TestFeatureExtractor:
    """Unit tests for FeatureExtractor — verifies correct feature derivation."""

    def test_extracts_all_features(self):
        """Every key in DEFAULT_WEIGHTS must be present in the output dict."""
        features = FeatureExtractor().extract(_make_lead())
        assert set(features.keys()) == set(DEFAULT_WEIGHTS.keys())

    def test_all_features_in_0_1_range(self):
        """No feature may fall outside [0.0, 1.0]."""
        for name, value in FeatureExtractor().extract(_make_lead()).items():
            assert 0.0 <= value <= 1.0, f"{name} = {value} is out of [0, 1]"

    def test_seniority_director(self):
        """'Director' in title must yield the maximum seniority score (1.0)."""
        features = FeatureExtractor().extract(_make_lead(title="Director of Toxicology"))
        assert features["seniority_score"] == 1.0

    def test_seniority_unknown_title(self):
        """A None title must yield a low (but non-zero) seniority score."""
        features = FeatureExtractor().extract(_make_lead(title=None))
        assert features["seniority_score"] < 1.0
        assert features["seniority_score"] >= 0.0

    def test_no_email_sets_zero(self):
        """Leads without an email must score 0.0 on has_email."""
        features = FeatureExtractor().extract(_make_lead(email=None))
        assert features["has_email"] == 0.0

    def test_nih_active_grant_sets_feature(self):
        """Active NIH grant must set has_nih_active = 1.0 and nih_award_norm > 0."""
        lead = _make_lead(enrichment_data={
            "nih_grants": {"active_grants": 2, "max_award": 450_000}
        })
        features = FeatureExtractor().extract(lead)
        assert features["has_nih_active"] == 1.0
        assert features["nih_award_norm"] > 0.0

    def test_pub_count_normalised(self):
        """More publications must yield a proportionally higher pub_count_norm."""
        low_features = FeatureExtractor().extract(_make_lead(publication_count=2))
        high_features = FeatureExtractor().extract(_make_lead(publication_count=20))
        assert high_features["pub_count_norm"] > low_features["pub_count_norm"]


# =============================================================================
# Weighted Scorer
# =============================================================================

class TestWeightedScorer:
    """Unit tests for WeightedScorer — verifies correct weight application."""

    def test_zero_total_weight_raises_value_error(self):
        """Zero-sum effective weights must fail fast to avoid divide-by-zero."""
        with pytest.raises(ValueError, match="must sum to a positive value"):
            WeightedScorer({key: 0.0 for key in DEFAULT_WEIGHTS})

    def test_score_in_0_100_range(self):
        """Score must always be an integer in [0, 100]."""
        features = {k: 0.5 for k in DEFAULT_WEIGHTS}
        score = WeightedScorer().score(features)
        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_all_zeros_gives_zero(self):
        """All-zero features must produce a score of 0."""
        features = {k: 0.0 for k in DEFAULT_WEIGHTS}
        assert WeightedScorer().score(features) == 0

    def test_all_ones_gives_100(self):
        """All-maximum features must produce a score of exactly 100."""
        features = {k: 1.0 for k in DEFAULT_WEIGHTS}
        assert WeightedScorer().score(features) == 100

    def test_custom_weights_applied(self):
        """A single non-zero feature with a large override weight must produce score > 0."""
        features = {k: 0.0 for k in DEFAULT_WEIGHTS}
        features["has_nih_active"] = 1.0
        scorer = WeightedScorer(weight_overrides={"has_nih_active": 50.0})
        assert scorer.score(features) > 0

    def test_breakdown_sums_to_score(self):
        """sum(score_breakdown.values()) must equal score() within rounding error."""
        features = {k: 0.5 for k in DEFAULT_WEIGHTS}
        scorer = WeightedScorer()
        score = scorer.score(features)
        breakdown = scorer.score_breakdown(features)
        assert abs(sum(breakdown.values()) - score) < 1


# =============================================================================
# Scoring Service
# =============================================================================

class TestScoringService:
    """Unit tests for ScoringService — covers sync scoring and ordering guarantees."""

    def test_score_lead_sync_returns_tuple(self):
        """score_lead_sync must return (int, dict) with correct shapes."""
        svc = ScoringService()
        score, breakdown = svc.score_lead_sync(_make_lead())

        assert isinstance(score, int)
        assert 0 <= score <= 100
        assert isinstance(breakdown, dict)
        assert len(breakdown) == len(DEFAULT_WEIGHTS)

    def test_rich_lead_scores_higher_than_empty(self):
        """A lead with full enrichment must score higher than an empty lead."""
        svc = ScoringService()

        rich_lead = _make_lead(
            email="x@genentech.com",
            recent_publication=True,
            publication_count=10,
            company_funding="Public",
            enrichment_data={"nih_grants": {"active_grants": 1, "max_award": 500_000}},
        )
        empty_lead = _make_lead(
            email=None,
            recent_publication=False,
            publication_count=0,
            company_funding=None,
            enrichment_data={},
        )

        rich_score, _ = svc.score_lead_sync(rich_lead)
        empty_score, _ = svc.score_lead_sync(empty_lead)
        assert rich_score > empty_score

    def test_nih_active_grant_boosts_score(self):
        """Adding an active NIH grant must increase the lead's score."""
        svc = ScoringService()

        no_nih = _make_lead(enrichment_data={})
        has_nih = _make_lead(enrichment_data={
            "nih_grants": {"active_grants": 1, "max_award": 450_000}
        })

        score_without, _ = svc.score_lead_sync(no_nih)
        score_with, _ = svc.score_lead_sync(has_nih)
        assert score_with > score_without


# =============================================================================
# Pipeline Templates
# =============================================================================

class TestPipelineTemplates:
    """Endpoint-level tests for pipeline template helpers."""

    @pytest.mark.asyncio
    async def test_list_templates_endpoint(self):
        templates = await list_pipeline_templates(current_user=_make_user())
        assert isinstance(templates, list)
        assert len(templates) >= 4
        keys = {tpl["key"] for tpl in templates}
        assert "dili_toxicology" in keys
        assert "oncology_research" in keys
        assert "pharma_safety_scientists" in keys
        assert "nih_grant_holders" in keys

    @pytest.mark.asyncio
    async def test_create_from_template(self):
        pipeline = await create_pipeline_from_template(
            template_key="dili_toxicology",
            name="My DILI Pipeline",
            current_user=_make_user(),
            db=_FakePipelineDB(),
        )
        assert pipeline.name == "My DILI Pipeline"
        assert pipeline.schedule.value == "weekly"

    @pytest.mark.asyncio
    async def test_unknown_template_returns_404(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await create_pipeline_from_template(
                template_key="nonexistent_key",
                name=None,
                current_user=_make_user(),
                db=_FakePipelineDB(),
            )

        assert exc_info.value.status_code == 404


# =============================================================================
# Alert Rules CRUD

# =============================================================================

# =============================================================================
# Alert Rules CRUD
# =============================================================================

class TestAlertRuleCRUD:
    """Endpoint-level tests for alert rule CRUD helpers."""

    @pytest.mark.asyncio
    async def test_create_alert_rule(self):
        db = _FakeAlertDB()
        user = _make_user()
        rule = await create_alert_rule(
            payload=types.SimpleNamespace(model_dump=lambda: {
                "name": "High-Value Alert",
                "trigger": "high_value_lead",
                "channel": "email",
                "conditions": {"min_score": 75},
            }),
            current_user=user,
            db=db,
        )
        assert rule.trigger == "high_value_lead"
        assert rule.conditions["min_score"] == 75
        assert rule.is_active is True

    @pytest.mark.asyncio
    async def test_list_alert_rules(self):
        db = _FakeAlertDB()
        user = _make_user()
        await create_alert_rule(
            payload=types.SimpleNamespace(model_dump=lambda: {
                "name": "List Test Rule",
                "trigger": "new_nih_grant",
                "channel": "email",
                "conditions": {},
            }),
            current_user=user,
            db=db,
        )
        rules = await list_alert_rules(current_user=user, db=db)
        assert isinstance(rules, list)
        assert len(rules) == 1

    @pytest.mark.asyncio
    async def test_update_alert_rule(self):
        db = _FakeAlertDB()
        user = _make_user()
        created = await create_alert_rule(
            payload=types.SimpleNamespace(model_dump=lambda: {
                "name": "Update Me",
                "trigger": "score_increase",
                "channel": "email",
                "conditions": {"min_delta": 10},
            }),
            current_user=user,
            db=db,
        )
        updated = await update_alert_rule(
            rule_id=created.id,
            payload=types.SimpleNamespace(model_dump=lambda exclude_none=True: {"is_active": False}),
            current_user=user,
            db=db,
        )
        assert updated.is_active is False

    @pytest.mark.asyncio
    async def test_delete_alert_rule(self):
        from fastapi import HTTPException

        db = _FakeAlertDB()
        user = _make_user()
        created = await create_alert_rule(
            payload=types.SimpleNamespace(model_dump=lambda: {
                "name": "Delete Me",
                "trigger": "high_value_lead",
                "channel": "email",
                "conditions": {},
            }),
            current_user=user,
            db=db,
        )
        await delete_alert_rule(rule_id=created.id, current_user=user, db=db)
        with pytest.raises(HTTPException) as exc_info:
            await get_alert_rule(rule_id=created.id, current_user=user, db=db)
        assert exc_info.value.status_code == 404


# =============================================================================
# Smart Alert Service — throttle unit tests

# =============================================================================

# =============================================================================
# Smart Alert Service — throttle unit tests
# =============================================================================

class TestSmartAlertService:
    """
    Unit tests for AlertRule.is_throttled().

    We test the method directly on a SimpleNamespace stub — no DB required.
    This confirms the throttle gate works correctly for all three states.
    """

    def test_throttle_blocks_recent_trigger(self):
        """A rule triggered 30 min ago (throttle=1h) must be throttled."""
        rule = types.SimpleNamespace(
            throttle_seconds=3600,
            last_triggered_at=datetime.now(timezone.utc) - timedelta(minutes=30),
        )
        assert AlertRule.is_throttled(rule) is True

    def test_throttle_allows_stale_trigger(self):
        """A rule triggered 2h ago (throttle=1h) must NOT be throttled."""
        rule = types.SimpleNamespace(
            throttle_seconds=3600,
            last_triggered_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        assert AlertRule.is_throttled(rule) is False

    def test_throttle_allows_never_triggered(self):
        """A rule that has never been triggered must NOT be throttled."""
        rule = types.SimpleNamespace(
            throttle_seconds=3600,
            last_triggered_at=None,
        )
        assert AlertRule.is_throttled(rule) is False


# =============================================================================
# Scoring Endpoints
# =============================================================================

class TestScoringEndpoints:
    """Endpoint-level tests for the scoring API helpers."""

    @pytest.mark.asyncio
    async def test_update_scoring_weights_rejects_zero_sum_overrides(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await update_scoring_config(
                weights=ScoreWeights(**{key: 0.0 for key in DEFAULT_WEIGHTS}),
                current_user=_make_user(),
                db=types.SimpleNamespace(add=lambda obj: None, commit=lambda: None),
            )
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail == "Scoring weights must sum to a positive value"

    @pytest.mark.asyncio
    async def test_get_scoring_config(self):
        user = _make_user(preferences={"scoring_weights": {"has_nih_active": 20.0}})
        data = await get_scoring_config(current_user=user)
        assert "default_weights" in data
        assert "effective_weights" in data
        assert data["algorithm"] == "weighted_feature_scoring_v1"
        assert data["effective_weights"]["has_nih_active"] == 20.0

    @pytest.mark.asyncio
    async def test_get_scoring_stats(self):
        data = await get_scoring_stats(current_user=_make_user(), db=_FakeScoringStatsDB())
        assert data["total_leads"] == 3
        assert data["tier_distribution"]["HIGH"] == 1
        assert data["average_score"] == 72.5

    @pytest.mark.asyncio
    async def test_update_scoring_weights(self):
        class _FakeDB:
            def add(self, _obj):
                return None

            async def commit(self):
                return None

        user = _make_user(preferences={})
        data = await update_scoring_config(
            weights=ScoreWeights(has_nih_active=20.0, title_relevance=15.0),
            current_user=user,
            db=_FakeDB(),
        )
        assert data["status"] == "saved"
        assert data["overrides"]["has_nih_active"] == 20.0
