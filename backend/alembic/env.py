"""
Alembic migration environment with IPv4 enforcement
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, text

from alembic import context

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load .env file if it exists (before any config imports)
try:
    from dotenv import load_dotenv

    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"[OK] Loaded .env from {env_path}")
    else:
        # Try parent directory
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"
        )
        if os.path.exists(env_path):
            load_dotenv(env_path)
            print(f"[OK] Loaded .env from {env_path}")
except ImportError:
    print("[WARN] python-dotenv not installed, skipping .env load")
except Exception as e:
    print(f"[WARN] Could not load .env: {e}")

# Import config and models
from app.core.config import get_database_url, settings
from app.core.database import SYNC_CONNECT_ARGS, Base
# Import all models so Alembic can detect them
from app.models.export import Export
from app.models.researcher import Researcher
from app.models.pipeline import Pipeline
from app.models.search import Search
from app.models.user import User

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate
target_metadata = Base.metadata

# Get database URL with IPv4 enforcement
database_url = get_database_url(force_ipv4=True)

import socket
# Additional IPv4 resolution attempt if the URL still contains hostname
from urllib.parse import urlparse, urlunparse

parsed = urlparse(database_url)
if parsed.hostname and not parsed.hostname.replace(".", "").isdigit():
    # Check for manual IPv4 override via environment variable
    ipv4_override = os.getenv("DATABASE_IPV4_ADDRESS")
    if ipv4_override:
        print(f"[OK] Using IPv4 address from DATABASE_IPV4_ADDRESS: {ipv4_override}")
        ipv4_address = ipv4_override
    else:
        # Try to resolve to IPv4 using multiple methods
        ipv4_address = None

        # Method 1: Try getaddrinfo with IPv4 only
        try:
            addr_info = socket.getaddrinfo(
                parsed.hostname,
                parsed.port or 5432,
                socket.AF_INET,  # Force IPv4
                socket.SOCK_STREAM,
            )
            if addr_info:
                ipv4_address = addr_info[0][4][0]
                print(f"[OK] Resolved {parsed.hostname} to IPv4: {ipv4_address}")
        except Exception as e:
            print(f"[WARN] Method 1 failed: {e}")

        # Method 2: Try gethostbyname (legacy, but sometimes works)
        if not ipv4_address:
            try:
                ipv4_address = socket.gethostbyname(parsed.hostname)
                # Verify it's actually IPv4
                socket.inet_aton(ipv4_address)
                print(
                    f"[OK] Resolved {parsed.hostname} to IPv4 (method 2): {ipv4_address}"
                )
            except Exception as e:
                print(f"[WARN] Method 2 failed: {e}")

    # If we got an IPv4 address, update the URL
    if ipv4_address:
        netloc = f"{parsed.username}:{parsed.password}@{ipv4_address}"
        if parsed.port:
            netloc += f":{parsed.port}"
        database_url = urlunparse(
            (
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )
    else:
        print(f"[WARN] Could not resolve {parsed.hostname} to IPv4")
        print(f"[WARN] Will try using hostname directly (may use IPv6 if available)")
        print(f"\n[TIP] Alternative Solutions:")
        print(f"   1. Use Supabase Connection Pooler (better IPv4 support):")
        print(
            f"      Change hostname from 'db.xxx.supabase.co' to 'aws-0-xx.pooler.supabase.com'"
        )
        print(f"   2. Use Supabase Direct Connection with IPv4:")
        print(
            f"      Get connection string from: Supabase Dashboard > Settings > Database"
        )
        print(f"   3. Enable IPv6 on your network/VPN")
        print(f"   4. Use a different network environment")

config.set_main_option("sqlalchemy.url", database_url)
print(f"[INFO] Using database URL: {database_url.split('@')[0]}@...")


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Get configuration
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url")

    # Add connection pool settings
    configuration["sqlalchemy.pool_pre_ping"] = "True"
    configuration["sqlalchemy.pool_recycle"] = "3600"

    # Create engine with custom connect_args
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Use NullPool for migrations
        connect_args=SYNC_CONNECT_ARGS,
    )

    # Test connection before running migrations (non-fatal for autogenerate)
    print("[INFO] Testing database connection...")
    connection_ok = False
    try:
        with connectable.connect() as test_conn:
            result = test_conn.execute(text("SELECT 1"))
            result.fetchone()
            print("[OK] Database connection successful!")
            connection_ok = True
    except Exception as e:
        error_msg = str(e)
        print(f"[WARN] Database connection test failed: {error_msg}")

        # Check if it's an IPv6/network issue
        if (
            "Network is unreachable" in error_msg
            or "2406:" in error_msg
            or "IPv6" in error_msg
        ):
            print("\n[WARN] IPv6 Connection Issue Detected!")
            print("=" * 60)
            print("Your network environment doesn't support IPv6 connections.")
            print("\n[TIP] Solutions:")
            print("1. Use a VPN that supports IPv6")
            print("2. Contact your network administrator to enable IPv6")
            print("3. Use Supabase connection pooling (different endpoint)")
            print("4. Try using the Supabase direct connection URL")
            print("\n[INFO] To get IPv4 connection string from Supabase:")
            print("   - Go to Supabase Dashboard > Settings > Database")
            print("   - Look for 'Connection string' with 'Direct connection'")
            print("   - Or use the 'Connection pooling' option")
            print("=" * 60)
        else:
            print("\n[TIP] General Troubleshooting:")
            print("1. Check your DATABASE_URL in .env")
            print("2. Verify Supabase project is active")
            print("3. Check network connectivity")
            print("4. Run: python scripts/test_db_direct.py")

        # For autogenerate, we'll try to proceed anyway
        # The actual migration will fail if connection doesn't work
        print(
            "\n[INFO] Continuing with migration attempt (connection will be retried)..."
        )

    # Run migrations
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
