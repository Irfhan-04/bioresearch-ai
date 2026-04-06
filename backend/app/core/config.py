"""
Core configuration for the application
Manages environment variables and settings with IPv4 enforcement
"""

import os
import secrets
import socket
from typing import List, Optional

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

def get_ipv4_address(hostname: str) -> str:
    """
    Resolve hostname to IPv4 address to avoid IPv6 issues
    This is critical for environments that don't support IPv6
    """
    try:
        # Force IPv4 resolution
        addr_info = socket.getaddrinfo(
            hostname, None, socket.AF_INET, socket.SOCK_STREAM  # Force IPv4
        )
        if addr_info:
            ipv4_address = addr_info[0][4][0]
            print(f"[OK] Resolved {hostname} to IPv4: {ipv4_address}")
            return ipv4_address
    except Exception as e:
        print(f"[WARN] Could not resolve {hostname} to IPv4: {e}")

    return hostname

class CommaSeparatedOriginsMixin:
    def prepare_field_value(self, field_name: str, field, value, value_is_complex: bool):
        if field_name == "BACKEND_CORS_ORIGINS" and isinstance(value, str):
            stripped_value = value.strip()
            if stripped_value and not stripped_value.startswith("["):
                return [item.strip() for item in stripped_value.split(",") if item.strip()]
        return super().prepare_field_value(field_name, field, value, value_is_complex)


class SettingsEnvSource(CommaSeparatedOriginsMixin, EnvSettingsSource):
    pass


class SettingsDotEnvSource(CommaSeparatedOriginsMixin, DotEnvSettingsSource):
    pass

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """

    # App Info
    APP_NAME: str = "BioResearch AI"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "AI-powered biotech research intelligence"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    FRONTEND_URL: str = "http://localhost:3000"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://yourdomain.com",
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

    # Database - Supabase PostgreSQL
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_KEY: str

    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30

    # Force IPv4 for database connections
    USE_IPV4_ONLY: bool = True

    # Redis - Upstash
    REDIS_URL: str
    REDIS_CACHE_TTL: int = 3600
    REDIS_SESSION_TTL: int = 86400

    # Email - Resend
    RESEND_API_KEY: str
    RESEND_FROM_EMAIL: str = "noreply@yourdomain.com"

    # Object Storage
    SUPABASE_STORAGE_BUCKET: str = "exports"

    # External APIs — PubMed / NCBI Entrez
    PUBMED_EMAIL: str
    PUBMED_API_KEY: Optional[str] = None
    # Server-wide search defaults (can be overridden per-request via API filters)
    PUBMED_DEFAULT_YEARS_BACK: int = 3
    PUBMED_MAX_RESULTS_PER_QUERY: int = 50

    # Google Custom Search API — LinkedIn profile finder (FREE: 100 req/day)
    # Setup: https://programmablesearchengine.google.com (see Step 2 guide)
    GOOGLE_CSE_API_KEY: Optional[str] = None
    GOOGLE_CSE_ID: Optional[str] = None

    # Hunter.io — Email finding (FREE: 25 searches/month, no credit card)
    # Get key: https://hunter.io → Sign up free → Dashboard → API
    # Used ONLY for leads with propensity_score >= 70 (HIGH tier)
    HUNTER_API_KEY: Optional[str] = None

    # Clearbit — Company enrichment (FREE: 50 lookups/month, no credit card)
    # Get key: https://clearbit.com → Start for free → Dashboard → API Keys
    # Used ONLY for pharma/unknown leads with propensity_score >= 50
    CLEARBIT_API_KEY: Optional[str] = None
    CRUNCHBASE_API_KEY: Optional[str] = None

    # Enrichment quota thresholds (change to tune API spend)
    HUNTER_MIN_SCORE_FOR_API: int = 70
    CLEARBIT_MIN_SCORE_FOR_API: int = 50

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # Subscription Limits
    FREE_TIER_LEADS_PER_MONTH: int = 100
    PRO_TIER_LEADS_PER_MONTH: int = 1000
    TEAM_TIER_LEADS_PER_MONTH: int = 5000

    TIER_LIMITS: dict = {
        "free": {"leads": 100, "searches": 50, "exports": 10, "api_calls": 500},
        "pro": {"leads": 1000, "searches": 500, "exports": 100, "api_calls": 5000},
        "team": {"leads": 5000, "searches": 2000, "exports": 500, "api_calls": 20000},
        "enterprise": {"leads": 999999, "searches": 999999, "exports": 999999, "api_calls": 999999},
    }

    # Scoring Weights
    DEFAULT_ROLE_WEIGHT: int = 30
    DEFAULT_PUBLICATION_WEIGHT: int = 40
    DEFAULT_FUNDING_WEIGHT: int = 20
    DEFAULT_LOCATION_WEIGHT: int = 10

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    FIRST_SUPERUSER_EMAIL: str = "admin@yourdomain.com"
    FIRST_SUPERUSER_PASSWORD: str = "ChangeMe123!"

    # Feature Flags
    ENABLE_ML_SCORING: bool = False
    ENABLE_EMAIL_NOTIFICATIONS: bool = True
    ENABLE_WEBHOOKS: bool = True
    ENABLE_BACKGROUND_JOBS: bool = True
    ENABLE_SMART_ALERTS: bool = True
    HIGH_VALUE_LEAD_THRESHOLD: int = 70
    DAILY_DIGEST_ENABLED: bool = True
    SCORE_RECALC_BATCH_SIZE: int = 500

    model_config = SettingsConfigDict(
        env_file=os.environ.get("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Create settings instance
settings = Settings()


def get_database_url(force_ipv4: bool = None) -> str:
    """
    Get database URL with IPv4 enforcement
    """
    if force_ipv4 is None:
        force_ipv4 = settings.USE_IPV4_ONLY

    url = settings.DATABASE_URL

    # Ensure psycopg2 driver for sync operations
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)

    # Force IPv4 if enabled
    if force_ipv4:
        from urllib.parse import urlparse, urlunparse

        parsed = urlparse(url)

        # Get IPv4 address for hostname
        if parsed.hostname and not parsed.hostname.replace(".", "").isdigit():
            ipv4_address = get_ipv4_address(parsed.hostname)

            # Rebuild netloc with IPv4
            netloc = f"{parsed.username}:{parsed.password}@{ipv4_address}"
            if parsed.port:
                netloc += f":{parsed.port}"

            # Reconstruct URL
            url = urlunparse(
                (
                    parsed.scheme,
                    netloc,
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment,
                )
            )

    return url


def get_async_database_url() -> str:
    """
    Get async database URL (asyncpg driver)
    """
    url = get_database_url(force_ipv4=True)

    # Convert to asyncpg for async operations
    if url.startswith("postgresql+psycopg2://"):
        url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)

    return url


def get_redis_url() -> str:
    """
    Get Redis URL
    """
    return settings.REDIS_URL


def get_supabase_client():
    """
    Create Supabase client
    """
    from supabase import create_client

    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# Export settings
__all__ = [
    "settings",
    "Settings",
    "get_database_url",
    "get_async_database_url",
    "get_redis_url",
    "get_supabase_client",
    "is_production",
    "is_development",
]
