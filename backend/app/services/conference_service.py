"""
Conference Service - Phase 2.3 Step 3
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.cache import Cache
from app.models.lead import Lead

# ── Import src-layer scrapers ─────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

try:
    from src.data_sources.conference_scraper import SCRAPERS, get_scraper
    _SCRAPERS_AVAILABLE = True
except ImportError:
    _SCRAPERS_AVAILABLE = False
    SCRAPERS = {}

logger = logging.getLogger(__name__)

# ── Cache TTL ─────────────────────────────────────────────────────────────────
_TTL_CONFERENCE_SPEAKERS = 86_400 * 365   # 365 days - annual event

# ── Default conferences ───────────────────────────────────────────────────────
_DEFAULT_CONFERENCES = ["sot", "aacr", "ashp"]

# ── Relevance keywords for biotech/DILI domain ───────────────────────────────
_RELEVANCE_KEYWORDS = [
    "toxicol", "toxicity", "dili", "liver", "hepat", "safety",
    "pharmacol", "drug", "3d", "organoid", "spheroid", "in vitro",
    "biomarker", "preclinical", "adme", "nonclinical", "efficacy",
    "oncol", "cancer", "immuno", "biologics", "antibody",
    "translational", "clinical", "pharmacokinet",
]


class ConferenceService:
    """
    Manages conference speaker data for lead generation.

    Two modes:
      1. search_leads(query)          - query-filtered, used by search endpoint
      2. get_all_speakers(conf, year) - full unfiltered scrape, used by pipelines
    """

    def __init__(self) -> None:
        self._available = _SCRAPERS_AVAILABLE
        if not self._available:
            logger.warning(
                "ConferenceService: scrapers unavailable - "
                "check src/data_sources/conference_scraper.py"
            )

    # =========================================================================
    # PUBLIC - Search entry point (called by DataSourceManager)
    # =========================================================================

    async def search_leads(
        self,
        query: str,
        conferences: Optional[List[str]] = None,
        year: Optional[int] = None,
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Search conference speaker data for leads matching a query.

        Workflow:
          1. For each conference: check Redis → if miss, scrape + cache 365d
          2. Pool all speakers
          3. Score relevance against query + domain keywords
          4. Return top-N leads sorted by score descending
        """
        if not self._available:
            return []

        conferences = conferences or _DEFAULT_CONFERENCES
        year        = year or datetime.now().year

        # Fetch speakers concurrently
        tasks = [self._get_speakers(key, year) for key in conferences]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_speakers: List[Dict] = []
        for conf_key, result in zip(conferences, results):
            if isinstance(result, Exception):
                logger.error("ConferenceService: error fetching %s: %s", conf_key, result)
                continue
            all_speakers.extend(result)

        if not all_speakers:
            logger.info("ConferenceService: no speakers found for %s", conferences)
            return []

        # Score and filter
        query_terms = _tokenise(query)
        scored: List[tuple] = [
            (self._relevance_score(sp, query_terms), sp)
            for sp in all_speakers
        ]
        scored = [(s, sp) for s, sp in scored if s > 0]
        scored.sort(key=lambda x: x[0], reverse=True)

        leads = [
            self._convert_to_lead_dict(sp, score)
            for score, sp in scored[:max_results]
        ]

        logger.info(
            "ConferenceService: query '%s' → %d/%d speakers matched",
            query[:50], len(leads), len(all_speakers),
        )
        return leads

    async def get_all_speakers(
        self,
        conference_key: str,
        year: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return all scraped speakers for a single conference.
        Used by the annual pipeline refresh task.
        """
        year = year or datetime.now().year
        return await self._get_speakers(conference_key, year)

    # =========================================================================
    # PUBLIC - Lead conversion
    # =========================================================================

    def convert_to_lead_model(
        self,
        conference_lead: Dict[str, Any],
        user_id: str,
    ) -> Lead:
        """
        Convert a conference lead dict to a Lead ORM instance.
        Called by DataSourceManager.search_and_convert_to_leads()
        and SearchService._dict_to_lead().
        """
        lead = Lead(
            user_id=user_id,
            name=conference_lead.get("name", "Unknown"),
            title=conference_lead.get("title", "Speaker"),
            company=conference_lead.get("company", "Unknown"),
            location=conference_lead.get("location", "Unknown"),
            email=conference_lead.get("email") or None,
            linkedin_url=conference_lead.get("linkedin") or None,
            recent_publication=False,
            status="NEW",
        )

        lead.add_data_source("conference")

        lead.set_enrichment("conference", {
            "conference_name":    conference_lead.get("conference_name", ""),
            "conference_key":     conference_lead.get("conference_key", ""),
            "conference_year":    conference_lead.get("conference_year"),
            "presentation_title": conference_lead.get("presentation_title", ""),
            "presentation_type":  conference_lead.get("presentation_type", ""),
            "session_name":       conference_lead.get("session_name", ""),
            "relevance_score":    conference_lead.get("relevance_score", 0),
            "institution_type":   conference_lead.get("institution_type", "unknown"),
            "scraped_at":         datetime.utcnow().isoformat(),
        })

        lead.add_tag("conference-speaker")
        if conference_lead.get("presentation_type") in ("Platform Talk", "Keynote"):
            lead.add_tag("platform-speaker")
        if conference_lead.get("is_senior_role"):
            lead.add_tag("senior-role")

        return lead

    async def get_service_status(self) -> Dict[str, Any]:
        """Return service capability info for status endpoints."""
        year = datetime.now().year
        cached_count = 0
        for conf_key in _DEFAULT_CONFERENCES:
            key = _cache_key(conf_key, year)
            if await Cache.exists(key):
                cached_count += 1

        return {
            "service":             "conference",
            "available":           self._available,
            "scrapers_loaded":     list(SCRAPERS.keys()) if _SCRAPERS_AVAILABLE else [],
            "default_conferences": _DEFAULT_CONFERENCES,
            "cache_ttl_days":      365,
            "current_year":        year,
            "conferences_cached":  f"{cached_count}/{len(_DEFAULT_CONFERENCES)}",
            "cost":                "free",
        }

    # =========================================================================
    # PRIVATE - Cache-or-scrape
    # =========================================================================

    async def _get_speakers(
        self,
        conference_key: str,
        year: int,
    ) -> List[Dict[str, Any]]:
        """Return speakers from cache; fall back to live scrape."""
        key = _cache_key(conference_key, year)
        cached = await Cache.get(key)
        if cached is not None:
            logger.debug(
                "Conference cache HIT: %s %d (%d speakers)",
                conference_key, year, len(cached),
            )
            return cached

        logger.info(
            "Conference cache MISS: %s %d - scraping now …",
            conference_key, year,
        )
        loop = asyncio.get_event_loop()
        try:
            scraper  = get_scraper(conference_key)
            speakers = await loop.run_in_executor(
                None, scraper.scrape_speakers, year
            )
        except ValueError as exc:
            logger.error("Unknown conference key '%s': %s", conference_key, exc)
            return []
        except Exception as exc:
            logger.error(
                "Error scraping %s %d: %s", conference_key, year, exc, exc_info=True
            )
            return []

        if speakers:
            await Cache.set(key, speakers, ttl=_TTL_CONFERENCE_SPEAKERS)
            logger.info(
                "Conference scraped + cached: %s %d → %d speakers (TTL 365d)",
                conference_key, year, len(speakers),
            )
        else:
            # Cache empty list for 24 h to avoid hammering a site with no programme yet
            await Cache.set(key, [], ttl=86_400)
            logger.warning(
                "Conference scrape returned 0 speakers for %s %d "
                "(cached empty 24h - programme may not be published yet)",
                conference_key, year,
            )

        return speakers

    # =========================================================================
    # PRIVATE - Relevance scoring
    # =========================================================================

    @staticmethod
    def _relevance_score(speaker: Dict[str, Any], query_terms: List[str]) -> int:
        """
        Score a speaker's relevance to a query.

        +3 per query term found in presentation_title  (strongest signal)
        +2 per query term found in title/role
        +1 per query term found in other fields
        +1 per global domain keyword match
        +2 if is_senior_role
        +1 if institution_type == "pharma"

        Returns 0 if nothing matches (will be filtered out).
        """
        score = 0
        haystack = " ".join([
            speaker.get("name", ""),
            speaker.get("title", ""),
            speaker.get("company", ""),
            speaker.get("presentation_title", ""),
            speaker.get("session_name", ""),
        ]).lower()

        for term in query_terms:
            if term in speaker.get("presentation_title", "").lower():
                score += 3
            elif term in speaker.get("title", "").lower():
                score += 2
            elif term in haystack:
                score += 1

        for kw in _RELEVANCE_KEYWORDS:
            if kw in haystack:
                score += 1

        if speaker.get("is_senior_role"):
            score += 2
        if speaker.get("institution_type") == "pharma":
            score += 1

        return score

    @staticmethod
    def _convert_to_lead_dict(speaker: Dict[str, Any], score: int) -> Dict[str, Any]:
        """Normalise a speaker dict to the standard lead dict schema."""
        return {
            "name":               speaker.get("name", "Unknown"),
            "title":              speaker.get("title", "Speaker"),
            "company":            speaker.get("company", "Unknown"),
            "location":           speaker.get("location", "Unknown"),
            "email":              speaker.get("email"),
            "linkedin":           None,
            "recent_publication": False,
            "company_funding":    "Unknown",
            "uses_3d_models":     False,
            "data_sources":       ["conference"],
            "conference_name":    speaker.get("conference_name", ""),
            "conference_key":     speaker.get("conference_key", ""),
            "conference_year":    speaker.get("conference_year"),
            "presentation_title": speaker.get("presentation_title", ""),
            "presentation_type":  speaker.get("presentation_type", ""),
            "session_name":       speaker.get("session_name", ""),
            "institution_type":   speaker.get("institution_type", "unknown"),
            "is_senior_role":     speaker.get("is_senior_role", False),
            "relevance_score":    score,
        }


# =============================================================================
# Module-level helpers
# =============================================================================

def _cache_key(conference_key: str, year: int) -> str:
    """Redis key format: conference:speakers:{key}:{year}"""
    return f"conference:speakers:{conference_key.lower()}:{year}"


def _tokenise(query: str) -> List[str]:
    """
    Split query into lowercase tokens, removing stopwords and short tokens.
    """
    stopwords = {
        "the", "and", "or", "in", "of", "a", "an", "to", "for",
        "with", "on", "at", "by", "from", "is", "are", "was",
    }
    tokens = [
        t.lower().strip(".,;:")
        for t in query.split()
        if len(t) >= 3 and t.lower() not in stopwords
    ]
    return list(dict.fromkeys(tokens))  # deduplicate, preserve order


# =============================================================================
# Singleton
# =============================================================================

_conference_service: Optional[ConferenceService] = None


def get_conference_service() -> ConferenceService:
    global _conference_service
    if _conference_service is None:
        _conference_service = ConferenceService()
    return _conference_service


__all__ = ["ConferenceService", "get_conference_service"]
