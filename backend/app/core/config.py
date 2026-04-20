"""
Core configuration for BioResearch AI.
Manages environment variables and settings.
"""

import os
import secrets
import socket
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


def get_ipv4_address(hostname: str) -> str:
    """Resolve hostname to IPv4 address (required for Supabase on some hosting envs)."""
    try:
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)
        if addr_info:
            ipv4 = addr_info[0][4][0]
            print(f"[OK] Resolved {hostname} → {ipv4}")
            return ipv4
    except Exception as exc:
        print(f"[WARN] Could not resolve {hostname} to IPv4: {exc}")
    return hostname


class CommaSeparatedOriginsMixin:
    def prepare_field_value(self, field_name: str, field, value, value_is_complex: bool):
        if field_name == "BACKEND_CORS_ORIGINS" and isinstance(value, str):
            stripped = value.strip()
            if stripped and not stripped.startswith("["):
                return [item.strip() for item in stripped.split(",") if item.strip()]
        return super().prepare_field_value(field_name, field, value, value_is_complex)


class SettingsEnvSource(CommaSeparatedOriginsMixin, EnvSettingsSource):
    pass


class SettingsDotEnvSource(CommaSeparatedOriginsMixin, DotEnvSettingsSource):
    pass


class Settings(BaseSettings):
    """Application settings — loaded from environment variables."""

    # ── App identity ─────────────────────────────────────────────────────────
    APP_NAME: str = "BioResearch AI"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "AI-powered biotech research intelligence"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # ── Server ───────────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # ── Security ─────────────────────────────────────────────────────────────
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24      # 24 hours
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    FRONTEND_URL: str = "https://bioresearch-ai.vercel.app"

    # ── CORS ─────────────────────────────────────────────────────────────────
    BACKEND_CORS_ORIGINS: List[str] = [
        "https://bioresearch-ai.vercel.app",
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError(v)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            SettingsEnvSource(settings_cls),
            SettingsDotEnvSource(settings_cls),
            file_secret_settings,
        )

    # ── Database (Supabase PostgreSQL) ────────────────────────────────────────
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_SERVICE_KEY: Optional[str] = None

    DATABASE_URL: Optional[str] = None
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    USE_IPV4_ONLY: bool = True

    # ── Redis (Upstash) ───────────────────────────────────────────────────────
    REDIS_URL: Optional[str] = None
    REDIS_CACHE_TTL: int = 3600
    REDIS_SESSION_TTL: int = 86400

    # ── Object storage ────────────────────────────────────────────────────────
    SUPABASE_STORAGE_BUCKET: str = "exports"

    # ── PubMed / NCBI Entrez ─────────────────────────────────────────────────
    # Optional at deploy time; required by NCBI policy when making real requests.
    # We keep a safe default so missing env vars do not crash app startup.
    PUBMED_EMAIL: str = "noreply@bioresearch.ai"
    PUBMED_API_KEY: Optional[str] = None
    PUBMED_DEFAULT_YEARS_BACK: int = 3
    PUBMED_MAX_RESULTS_PER_QUERY: int = 50

    # ── LLM Intelligence — Component 3 ───────────────────────────────────────
    # Google Gemini 2.0 Flash (FREE via Google AI Studio)
    # Get key: https://aistudio.google.com/app/apikey
    # Free tier: 15 req/min · 1M tokens/min · 1,500 req/day · $0
    # Optional — if absent, intelligence_service returns None gracefully.
    # The system runs with 3/4 AI components (ML scorer + embeddings + SHAP)
    # without this key.
    GEMINI_API_KEY: Optional[str] = None

    # Gemini model identifier.
    # gemini-3-flash-preview — free, fast, excellent structured JSON output.
    # gemini-2.5-flash — upgrade path (also free on AI Studio).
    GEMINI_MODEL: str = "gemini-3-flash-preview"

    # ── Deployment control ────────────────────────────────────────────────────
    # Set SEED_ON_STARTUP=true in Render env vars on first deploy only.
    # After seeding completes, set back to false to prevent re-seeding on restart.
    SEED_ON_STARTUP: bool = False

    # ── Optional enrichment APIs (all have free tiers) ────────────────────────
    # Google Custom Search — LinkedIn profile finder (100 req/day free)
    GOOGLE_CSE_API_KEY: Optional[str] = None
    GOOGLE_CSE_ID: Optional[str] = None

    # Hunter.io — email finding (25 searches/month free)
    # Used ONLY for researchers with relevance_score >= 70 (HIGH tier)
    HUNTER_API_KEY: Optional[str] = None

    # Clearbit — company enrichment (50 lookups/month free)
    # Used ONLY for researchers with relevance_score >= 50
    CLEARBIT_API_KEY: Optional[str] = None
    CRUNCHBASE_API_KEY: Optional[str] = None

    # Enrichment score thresholds
    HUNTER_MIN_SCORE_FOR_API: int = 70
    CLEARBIT_MIN_SCORE_FOR_API: int = 50

    # ── Rate limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # ── Superuser seed ────────────────────────────────────────────────────────
    FIRST_SUPERUSER_EMAIL: str = "admin@yourdomain.com"
    FIRST_SUPERUSER_PASSWORD: str = "ChangeMe123!"

    # ── Daily search limits (no billing, two tiers) ───────────────────────────
    GUEST_DAILY_SEARCHES: int = 3         # IP-based, no login required
    REGISTERED_DAILY_SEARCHES: int = 20   # Free account, email + password

    model_config = SettingsConfigDict(
        env_file=os.environ.get("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# ── Module-level singleton ────────────────────────────────────────────────────
settings = Settings()


def get_database_url(force_ipv4: bool = None) -> str:
    """Get database URL with optional IPv4 enforcement."""
    if force_ipv4 is None:
        force_ipv4 = settings.USE_IPV4_ONLY

    url = settings.DATABASE_URL

    # Guard: if DATABASE_URL is not set, return a harmless placeholder
    # and emit a warning so imports don't crash with AttributeError.
    if not url:
        import warnings

        warnings.warn(
            "DATABASE_URL is not set. Database connections will fail. "
            "Set DATABASE_URL in your environment or Render Dashboard.",
            RuntimeWarning,
            stacklevel=2,
        )
        return "postgresql+psycopg2://localhost/bioresearch_placeholder"

    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)

    if force_ipv4:
        from urllib.parse import urlparse, urlunparse

        parsed = urlparse(url)
        if parsed.hostname and not parsed.hostname.replace(".", "").isdigit():
            ipv4 = get_ipv4_address(parsed.hostname)
            netloc = f"{parsed.username}:{parsed.password}@{ipv4}"
            if parsed.port:
                netloc += f":{parsed.port}"
            url = urlunparse((
                parsed.scheme, netloc, parsed.path,
                parsed.params, parsed.query, parsed.fragment,
            ))

    return url


def get_async_database_url() -> str:
    """Get async database URL (asyncpg driver)."""
    url = get_database_url(force_ipv4=True)
    if url.startswith("postgresql+psycopg2://"):
        url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    return url


def get_redis_url() -> str:
    return settings.REDIS_URL


def get_supabase_client():
    from supabase import create_client
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


__all__ = [
    "settings",
    "Settings",
    "get_database_url",
    "get_async_database_url",
    "get_redis_url",
    "get_supabase_client",
]
