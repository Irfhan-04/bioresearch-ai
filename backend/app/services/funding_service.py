"""
Funding Service - Phase 2.3 Step 4
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.cache import Cache
from app.models.lead import Lead

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

try:
    from src.data_sources.funding_scraper import NIHReporterScraper
    _SCRAPER_AVAILABLE = True
except ImportError:
    _SCRAPER_AVAILABLE = False
    NIHReporterScraper = None  # type: ignore

logger = logging.getLogger(__name__)

# ── Cache TTLs ────────────────────────────────────────────────────────────────
_TTL_KEYWORD_SEARCH = 86_400        # 24 hours
_TTL_PI_LOOKUP      = 86_400 * 7   # 7 days

# ── Score boost constants ─────────────────────────────────────────────────────
_BOOST_ACTIVE_GRANT  = 20
_BOOST_R01_OR_HIGHER = 8
_BOOST_MENTIONS_3D   = 5
_BOOST_HIGH_AWARD    = 5


class FundingService:
    """Manages NIH funding data for lead discovery and enrichment."""

    def __init__(self) -> None:
        self._available = _SCRAPER_AVAILABLE
        if _SCRAPER_AVAILABLE:
            self._scraper = NIHReporterScraper()
        else:
            self._scraper = None
            logger.warning(
                "FundingService: NIHReporterScraper not available - "
                "check src/data_sources/funding_scraper.py"
            )

    # =========================================================================
    # PUBLIC - Search entry point (DataSourceManager)
    # =========================================================================

    async def search_leads(
        self,
        query: str,
        fiscal_years: Optional[List[int]] = None,
        max_results: int = 50,
        mechanisms: Optional[List[str]] = None,
        active_only: bool = True,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """Search NIH RePORTER for PIs with grants matching a query."""
        if not self._available:
            return []

        keywords     = _tokenise_query(query)
        fiscal_years = fiscal_years or _default_fiscal_years()

        cache_key = _build_cache_key(
            "nih:keywords",
            ":".join(keywords),
            ":".join(str(y) for y in sorted(fiscal_years)),
            str(active_only),
        )

        if use_cache:
            cached = await Cache.get(cache_key)
            if cached is not None:
                logger.debug("NIH keyword cache HIT: '%s'", query[:50])
                return cached[:max_results]

        loop     = asyncio.get_event_loop()
        projects = await loop.run_in_executor(
            None,
            self._scraper.search_by_keywords,
            keywords,
            fiscal_years,
            max_results,
            mechanisms,
            active_only,
        )

        if projects:
            await Cache.set(cache_key, projects, ttl=_TTL_KEYWORD_SEARCH)
            logger.info("NIH search '%s' → %d projects (cached 24h)", query[:50], len(projects))
        else:
            await Cache.set(cache_key, [], ttl=3_600)  # cache empty result for 1h
            logger.info("NIH search '%s' → 0 results", query[:50])

        return projects[:max_results]

    # =========================================================================
    # PUBLIC - Enrichment entry point (EnrichmentService)
    # =========================================================================

    async def get_grants_for_pi(
        self,
        pi_name: str,
        fiscal_years: Optional[List[int]] = None,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """Retrieve all NIH grants for a specific PI name."""
        if not self._available or not pi_name:
            return []

        norm      = pi_name.strip().lower()
        cache_key = _build_cache_key("nih:pi", norm)

        if use_cache:
            cached = await Cache.get(cache_key)
            if cached is not None:
                logger.debug("NIH PI cache HIT: '%s'", pi_name)
                return cached

        fiscal_years = fiscal_years or _default_fiscal_years(years_back=5)

        loop   = asyncio.get_event_loop()
        grants = await loop.run_in_executor(
            None,
            self._scraper.search_by_pi_name,
            pi_name,
            fiscal_years,
            10,
        )

        await Cache.set(cache_key, grants or [], ttl=_TTL_PI_LOOKUP)

        if grants:
            logger.info("NIH PI lookup '%s' → %d grants (cached 7d)", pi_name, len(grants))
        else:
            logger.debug("NIH PI lookup '%s' → 0 grants", pi_name)

        return grants or []

    # =========================================================================
    # PUBLIC - Score boost computation
    # =========================================================================

    def compute_funding_score_boost(self, grants: List[Dict[str, Any]]) -> int:
        if not grants:
            return 0

        boost  = 0
        active = [g for g in grants if g.get("is_active")]

        if active:
            boost += _BOOST_ACTIVE_GRANT

        mechanisms = {g.get("mechanism", "") for g in grants}
        if mechanisms & {"R01", "U01", "P01", "P50", "RM1", "DP2"}:
            boost += _BOOST_R01_OR_HIGHER

        if any(g.get("uses_3d_models") for g in grants):
            boost += _BOOST_MENTIONS_3D

        max_award = max((g.get("award_amount", 0) or 0 for g in grants), default=0)
        if max_award > 400_000:
            boost += _BOOST_HIGH_AWARD

        return min(boost, 38)

    # =========================================================================
    # PUBLIC - Lead model conversion
    # =========================================================================

    def convert_to_lead_model(
        self, grant_dict: Dict[str, Any], user_id: str
    ) -> Lead:
        """
        Convert a grant dict (from search_leads) to a Lead ORM instance.
        Called by SearchService._dict_to_lead() when source == "funding".
        """
        lead = Lead(
            user_id=user_id,
            name=grant_dict.get("name", "Unknown"),
            title=grant_dict.get("title", "Principal Investigator"),
            company=grant_dict.get("company", "Unknown"),
            location=grant_dict.get("location", "Unknown"),
            company_hq=grant_dict.get("company_hq", "Unknown"),
            email=grant_dict.get("email") or None,
            company_funding=grant_dict.get("company_funding", "NIH Grant"),
            uses_3d_models=grant_dict.get("uses_3d_models", False),
            recent_publication=False,
            status="NEW",
        )

        lead.add_data_source("funding")

        lead.set_enrichment("nih_grants", {
            "grants":        [grant_dict],
            "total_grants":  1,
            "active_grants": 1 if grant_dict.get("is_active") else 0,
            "max_award":     grant_dict.get("award_amount", 0),
            "mechanisms":    [grant_dict.get("mechanism", "")],
            "score_boost":   self.compute_funding_score_boost([grant_dict]),
            "enriched_at":   datetime.utcnow().isoformat(),
        })

        # Tags
        lead.add_tag("nih-funded")
        if grant_dict.get("is_active"):
            lead.add_tag("active-grant")
        if grant_dict.get("uses_3d_models"):
            lead.add_tag("3d-models-grant")
        if grant_dict.get("mechanism", "") in ("R01", "U01", "P01"):
            lead.add_tag("major-grant")

        return lead

    async def get_service_status(self) -> Dict[str, Any]:
        """Return service capability info for /search/status/sources."""
        return {
            "service":           "funding",
            "available":         self._available,
            "source":            "NIH RePORTER REST API",
            "api_url":           "https://api.reporter.nih.gov/v2/projects/search",
            "auth":              "none - completely free",
            "cache_ttl":         {"keyword_search": "24h", "pi_lookup": "7d"},
            "cost":              "free",
            "update_frequency":  "NIH updates weekly",
        }


# =============================================================================
# Module-level helpers
# =============================================================================

def _tokenise_query(query: str) -> List[str]:
    """Split query into tokens, filter stopwords, limit to 5 tokens."""
    stopwords = {
        "the", "and", "or", "in", "of", "a", "an", "to",
        "for", "with", "on", "at", "by", "from", "is",
    }
    tokens = [
        t.strip(".,;:").lower()
        for t in query.split()
        if len(t) >= 3 and t.lower() not in stopwords
    ]
    seen = dict.fromkeys(tokens)
    return list(seen.keys())[:5]


def _build_cache_key(*parts: str) -> str:
    """
    Build a collision-safe Redis cache key using SHA-256.
    """
    combined = "|".join(parts)
    digest   = hashlib.sha256(combined.encode()).hexdigest()
    prefix   = parts[0] if parts else "nih"
    return f"{prefix}:{digest}"


def _default_fiscal_years(years_back: int = 3) -> List[int]:
    """Return list of fiscal years from (current - years_back) to current."""
    current = datetime.now().year
    return list(range(current - years_back, current + 1))





# =============================================================================
# Singleton
# =============================================================================

_funding_service: Optional[FundingService] = None


def get_funding_service() -> FundingService:
    global _funding_service
    if _funding_service is None:
        _funding_service = FundingService()
    return _funding_service


__all__ = ["FundingService", "get_funding_service"]
