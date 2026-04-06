"""
PubMed Search Service — Phase 2.3 Enhanced
===========================================

What's new vs Phase 2.1:
  - get_author_profile()      → full citation profile for enrichment service
  - _fetch_citation_count()   → NCBI elink for citation data (free)
  - _classify_institution()   → regex-based institution type classifier
  - _build_cache_key()        → SHA-256 hash — safe for all query lengths
  - _search_with_retry()      → exponential backoff on NCBI rate-limit errors
  - Advanced search filters   → year range, journal, MeSH terms, study type
  - Author scoring signals    → publication velocity, recency score

All tools used are FREE:
  - Biopython / NCBI Entrez API (unlimited, rate-limited)
  - Redis via Upstash free tier (10,000 commands/day)
  - Python stdlib: hashlib, asyncio, re, datetime
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os

import re  # used by _classify_institution for future regex patterns
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.cache import Cache
from app.core.config import settings
from app.models.lead import Lead

# ── Phase 1 scraper import (unchanged) ──────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

try:
    from src.data_sources.pubmed_scraper import PubMedScraper
except ImportError:
    PubMedScraper = None

logger = logging.getLogger(__name__)

# ── Cache TTLs (seconds) ─────────────────────────────────────────────────────
_TTL_SEARCH_RESULTS = 86_400  # 24 hours — search results
_TTL_AUTHOR_PROFILE = 86_400 * 7  # 7 days   — author citation profile
_TTL_CITATION_DATA = 86_400 * 3  # 3 days   — raw citation counts

# ── Institution classification keywords ──────────────────────────────────────
_ACADEMIC_KEYWORDS = [
    "university",
    "college",
    "institute",
    "school of",
    "faculty",
    "department of",
    "lab of",
    "laboratory of",
    "centre for",
    "center for",
    "academia",
    "polytechnic",
]
_PHARMA_KEYWORDS = [
    "pharma",
    "therapeutics",
    "biosciences",
    "biotechnology",
    "biotech",
    "biologics",
    "genomics",
    "proteomics",
    "diagnostics",
    "inc.",
    "inc,",
    " llc",
    "corp.",
    "corporation",
    "ltd.",
    "genentech",
    "pfizer",
    "novartis",
    "roche",
    "merck",
    "abbvie",
    "astrazeneca",
    "bayer",
    "sanofi",
    "johnson & johnson",
]
_HOSPITAL_KEYWORDS = [
    "hospital",
    "clinic",
    "medical center",
    "health system",
    "healthcare",
    "cancer center",
    "medical school",
]
_CRO_KEYWORDS = [
    "cro",
    "contract research",
    "covance",
    "labcorp",
    "pra health",
    "syneos",
    "parexel",
    "icon plc",
    "charles river",
]


class PubMedService:
    """
    Production-ready PubMed service.

    Provides two modes:
      1. Lead discovery  — search_leads() / search_multiple_queries()
      2. Lead enrichment — get_author_profile() [NEW in Phase 2.3]
    """

    def __init__(self) -> None:
        self.email = settings.PUBMED_EMAIL
        self.api_key = settings.PUBMED_API_KEY

        # Read server-wide defaults from config (set in .env)
        self.default_years_back = settings.PUBMED_DEFAULT_YEARS_BACK
        self.default_max_results = settings.PUBMED_MAX_RESULTS_PER_QUERY

        # Rate limits: 10 req/s with API key, 3 req/s without
        self._rps = 10 if self.api_key else 3
        self._request_delay = 1.0 / self._rps
        self._last_request = 0.0

        # Rate limits: 10 req/s with API key, 3 req/s without
        self._rps = 10 if self.api_key else 3
        self._request_delay = 1.0 / self._rps
        self._last_request = 0.0

        # Initialise Phase 1 scraper
        if PubMedScraper:
            self._scraper = PubMedScraper(
                email=self.email,
                api_key=self.api_key,
            )
        else:
            self._scraper = None
            logger.warning("PubMedScraper not available — check Biopython install")

    async def search_leads(
        self,
        query: str,
        max_results: int = 0,
        years_back: int = 0,
        use_cache: bool = True,
        journals: Optional[List[str]] = None,
        mesh_terms: Optional[List[str]] = None,
        study_type: Optional[str] = None,
        min_year: Optional[int] = None,
        max_year: Optional[int] = None,
    ) -> List[Dict]:
        """Search PubMed for corresponding authors matching a query."""
        if not self._scraper:
            raise RuntimeError("PubMedScraper unavailable — check Biopython install")

        # Resolve config-level defaults
        if max_results <= 0:
            max_results = self.default_max_results
        if years_back <= 0:
            years_back = self.default_years_back

        enriched_query = self._build_query(
            base_query=query,
            journals=journals,
            mesh_terms=mesh_terms,
            study_type=study_type,
            min_year=min_year,
            max_year=max_year,
            years_back=years_back,
        )

        cache_key = self._build_cache_key("pubmed:results", enriched_query, str(max_results))

        if use_cache:
            cached = await Cache.get(cache_key)
            if cached:
                logger.debug("Cache HIT for query: %s", query[:60])
                return cached

        loop = asyncio.get_event_loop()
        leads = await loop.run_in_executor(
            None,
            self._search_sync,
            enriched_query,
            min(max_results, 200),
            years_back,
        )

        if leads:
            await Cache.set(cache_key, leads, ttl=_TTL_SEARCH_RESULTS)
            logger.info("PubMed search '%s' → %d leads (cached 24h)", query[:60], len(leads))

        return leads

    async def search_multiple_queries(
        self,
        queries: List[str],
        max_results_per_query: int = 20,
        years_back: int = 3,
        **filter_kwargs,
    ) -> List[Dict]:
        """Search multiple queries, deduplicate, and return combined results."""
        all_leads: List[Dict] = []
        seen_names: set = set()

        for query in queries:
            leads = await self.search_leads(
                query=query,
                max_results=max_results_per_query,
                years_back=years_back,
                **filter_kwargs,
            )
            for lead in leads:
                name = (lead.get("name") or "").strip()
                if name and name not in seen_names:
                    all_leads.append(lead)
                    seen_names.add(name)

        return all_leads

    async def get_author_profile(
        self,
        author_name: str,
        max_publications: int = 20,
        years_back: int = 5,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Build a full citation profile for a named researcher."""
        if not self._scraper:
            return {"error": "pubmed_scraper_unavailable"}

        if not author_name or author_name == "Unknown":
            return {"error": "invalid_author_name"}

        normalised = author_name.strip().lower()
        cache_key = self._build_cache_key("pubmed:profile", normalised)

        if use_cache:
            cached = await Cache.get(cache_key)
            if cached:
                logger.debug("Profile cache HIT for author: %s", author_name)
                return cached

        author_query = f'"{author_name}"[Author]'

        loop = asyncio.get_event_loop()
        articles = await loop.run_in_executor(
            None,
            self._fetch_author_articles,
            author_query,
            max_publications,
            years_back,
        )

        profile_prefix = CacheKey.pubmed_author_profile("hash").rsplit(":", 1)[0]
        cache_key = self._build_cache_key(profile_prefix, normalised)

        if use_cache:
            cached = await Cache.get(cache_key)
            if cached:
                logger.debug("Profile cache HIT for author: %s", author_name)
                return cached

        author_query = f'"{author_name}"[Author]'

        loop = asyncio.get_event_loop()
        articles = await loop.run_in_executor(
            None,
            self._fetch_author_articles,
            author_query,
            max_publications,
            years_back,
        )

        if not articles:
            last_name = author_name.split()[-1] if author_name.split() else author_name
            fallback_query = f'"{last_name}"[Author]'
            articles = await loop.run_in_executor(
                None,
                self._fetch_author_articles,
                fallback_query,
                max_publications,
                years_back,
            )

        if not articles:
            profile: Dict[str, Any] = {
                "publication_count": 0,
                "total_citations": 0,
                "h_index_approx": 0,
                "most_cited_paper": None,
                "publications": [],
                "recent_journals": [],
                "institution_type": "unknown",
                "publication_velocity": 0.0,
                "recency_score": 0.0,
                "cached_at": datetime.utcnow().isoformat(),
            }
            await Cache.set(cache_key, profile, ttl=_TTL_AUTHOR_PROFILE)
            return profile

        pmids = [str(a["pmid"]) for a in articles if a.get("pmid")]
        citation_key = self._build_cache_key("pubmed:citations", ",".join(sorted(pmids)))
        citation_prefix = CacheKey.pubmed_citation_batch("hash").rsplit(":", 1)[0]
        citation_key = self._build_cache_key(citation_prefix, ",".join(sorted(pmids)))
        citation_map = await Cache.get(citation_key) if use_cache else None

        if not citation_map:
            citation_map = await loop.run_in_executor(None, self._fetch_citation_counts, pmids)
            if citation_map:
                await Cache.set(citation_key, citation_map, ttl=_TTL_CITATION_DATA)

        for article in articles:
            pmid = article.get("pmid", "")
            article["citation_count"] = citation_map.get(str(pmid), 0)

        total_citations = sum(a["citation_count"] for a in articles)
        h_index = self._compute_h_index(articles)
        most_cited = max(articles, key=lambda a: a["citation_count"], default=None)

        recent_journals = list({a["journal"] for a in articles if a.get("journal")})[:5]
        affiliations = [a.get("affiliation", "") for a in articles if a.get("affiliation")]
        institution_type = self._classify_institution(affiliations[0] if affiliations else "")

        velocity = round(len(articles) / max(years_back, 1), 2)

        current_year = datetime.utcnow().year
        years_list = [a.get("year", current_year - years_back) for a in articles if a.get("year")]
        if years_list:
            most_recent = max(years_list)
            age = max(0, current_year - most_recent)
            recency = max(0.0, 1.0 - (age / max(years_back, 1)))
        else:
            recency = 0.0

        profile = {
            "publication_count": len(articles),
            "total_citations": total_citations,
            "h_index_approx": h_index,
            "most_cited_paper": (
                {
                    "title": most_cited.get("title", ""),
                    "year": most_cited.get("year"),
                    "journal": most_cited.get("journal", ""),
                    "citation_count": most_cited["citation_count"],
                    "pmid": most_cited.get("pmid", ""),
                }
                if most_cited
                else None
            ),
            "publications": [
                {
                    "pmid": a.get("pmid", ""),
                    "title": a.get("title", "")[:200],
                    "year": a.get("year"),
                    "journal": a.get("journal", ""),
                    "citation_count": a["citation_count"],
                }
                for a in articles[:max_publications]
            ],
            "recent_journals": recent_journals,
            "institution_type": institution_type,
            "publication_velocity": velocity,
            "recency_score": round(recency, 3),
            "cached_at": datetime.utcnow().isoformat(),
        }

        await Cache.set(cache_key, profile, ttl=_TTL_AUTHOR_PROFILE)
        logger.info(
            "Author profile built: %s → pubs=%d, cit=%d, h=%d (cached 7d)",
            author_name,
            profile["publication_count"],
            profile["total_citations"],
            profile["h_index_approx"],
        )
        return profile

    def _search_sync(self, query: str, max_results: int, years_back: int) -> List[Dict]:
        """Synchronous wrapper around Phase 1 scraper for thread pool use."""
        try:
            return self._scraper.search_authors(
                query=query,
                max_results=max_results,
                years_back=years_back,
            )
        except Exception as exc:
            logger.error("PubMed search error: %s", exc, exc_info=True)
            return []

    def _fetch_author_articles(
        self,
        author_query: str,
        max_results: int,
        years_back: int,
    ) -> List[Dict]:
        """Fetch articles for a specific author query."""
        self._throttle()
        try:
            pmids = self._search_with_retry(
                self._scraper.search_pubmed,
                query=author_query,
                max_results=max_results,
                years_back=years_back,
            )
            if not pmids:
                return []

            self._throttle()
            articles = self._search_with_retry(self._scraper.fetch_article_details, pmids)

            result = []
            for article in articles:
                authors = article.get("authors", [])
                affiliation = ""
                if authors:
                    affiliation = authors[-1].get("affiliation", "")

                result.append(
                    {
                        "pmid": article.get("pmid", ""),
                        "title": article.get("title", ""),
                        "year": self._safe_year(article.get("year")),
                        "journal": article.get("journal", ""),
                        "affiliation": affiliation,
                        "citation_count": 0,
                    }
                )

            return result

        except Exception as exc:
            logger.error("_fetch_author_articles error: %s", exc, exc_info=True)
            return []

    def _fetch_citation_counts(self, pmids: List[str]) -> Dict[str, int]:
        """Use NCBI elink to get citation counts for a list of PMIDs."""
        if not pmids:
            return {}

        citation_map: Dict[str, int] = {}

        try:
            from Bio import Entrez  # type: ignore

            Entrez.email = self.email
            if self.api_key:
                Entrez.api_key = self.api_key

            batch_size = 10
            for i in range(0, len(pmids), batch_size):
                batch = pmids[i : i + batch_size]
                self._throttle()

                try:
                    handle = self._search_with_retry(
                        Entrez.elink,
                        dbfrom="pubmed",
                        db="pubmed",
                        id=",".join(batch),
                        linkname="pubmed_pubmed_citedin",
                    )
                    records = Entrez.read(handle)
                    handle.close()

                    for record in records:
                        source_pmid = record.get("IdList", [None])[0]
                        if not source_pmid:
                            continue

                        links = record.get("LinkSetDb", [])
                        count = 0
                        for link_set in links:
                            if link_set.get("LinkName") == "pubmed_pubmed_citedin":
                                count = len(link_set.get("Link", []))
                                break

                        citation_map[str(source_pmid)] = count

                except Exception as batch_exc:
                    logger.warning("elink batch %d failed: %s", i // batch_size, batch_exc)
                    for pmid in batch:
                        citation_map.setdefault(str(pmid), 0)

                time.sleep(self._request_delay)

        except Exception as exc:
            logger.error("_fetch_citation_counts error: %s", exc, exc_info=True)

        return citation_map

    def _search_with_retry(self, fn, *args, retries: int = 3, **kwargs):
        """Run blocking NCBI calls with exponential backoff for transient failures."""
        last_error: Optional[Exception] = None
        for attempt in range(1, retries + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                last_error = exc
                if attempt >= retries:
                    raise
                sleep_s = min(2 ** (attempt - 1), 8)
                context: Tuple[int, int, int] = (attempt, retries, sleep_s)
                logger.warning(
                    "Transient PubMed error on attempt %d/%d. Retrying in %ss.",
                    *context,
                    exc_info=True,
                )
                time.sleep(sleep_s)
        if last_error:
            raise last_error
        for attempt in range(1, retries + 1):
            try:
                return fn(*args, **kwargs)
            except Exception:
                if attempt >= retries:
                    raise
                sleep_s = min(2 ** (attempt - 1), 8)
                logger.warning(
                    "Transient PubMed error on attempt %d/%d. Retrying in %ss.",
                    attempt,
                    retries,
                    sleep_s,
                    exc_info=True,
                )
                time.sleep(sleep_s)

    def _build_query(
        self,
        base_query: str,
        journals: Optional[List[str]],
        mesh_terms: Optional[List[str]],
        study_type: Optional[str],
        min_year: Optional[int],
        max_year: Optional[int],
        years_back: int,
    ) -> str:
        """Construct a fully-qualified NCBI query string from base query + filters."""
        parts = [base_query]

        if journals:
            journal_clause = " OR ".join(f'"{j}"[Journal]' for j in journals)
            parts.append(f"({journal_clause})")

        if mesh_terms:
            mesh_clause = " AND ".join(f'"{t}"[MeSH Terms]' for t in mesh_terms)
            parts.append(f"({mesh_clause})")

        if study_type:
            parts.append(f'"{study_type}"[pt]')

        if min_year or max_year:
            y_min = min_year or (datetime.utcnow().year - years_back)
            y_max = max_year or datetime.utcnow().year
            parts.append(f"{y_min}:{y_max}[pdat]")

        return " AND ".join(parts)

    @staticmethod
    def _compute_h_index(articles: List[Dict]) -> int:
        """Compute approximate h-index from a list of articles."""
        counts = sorted([a.get("citation_count", 0) for a in articles], reverse=True)
        h = 0
        for i, c in enumerate(counts, start=1):
            if c >= i:
                h = i
            else:
                break
        return h

    @staticmethod
    def _classify_institution(affiliation: str) -> str:
        """Classify an affiliation string into an institution category."""
        if not affiliation:
            return "unknown"

        text = affiliation.lower()

        for keyword in _ACADEMIC_KEYWORDS:
            if keyword in text:
                return "academic"

        for keyword in _HOSPITAL_KEYWORDS:
            if keyword in text:
                return "hospital"

        for keyword in _CRO_KEYWORDS:
            if keyword in text:
                return "cro"

        for keyword in _PHARMA_KEYWORDS:
            if keyword in text:
                return "pharma"

        return "unknown"

    def _throttle(self) -> None:
        """Enforce per-request delay to stay within NCBI rate limits."""
        now = time.monotonic()
        elapsed = now - self._last_request
        if elapsed < self._request_delay:
            time.sleep(self._request_delay - elapsed)
        self._last_request = time.monotonic()

    @staticmethod
    def _build_cache_key(*parts: str) -> str:
        """Build a Redis-safe cache key using SHA-256 hashing."""
        combined = ":".join(parts)
        digest = hashlib.sha256(combined.encode("utf-8")).hexdigest()
        prefix = parts[0] if parts else "pubmed"
        return f"{prefix}:{digest}"

    @staticmethod
    def _safe_year(raw: Any) -> Optional[int]:
        """Convert a year value of any type to int, or return None."""
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    def convert_to_lead_model(self, pubmed_lead: Dict, user_id: str) -> Lead:
        """Convert a PubMed search result dict to a Lead ORM instance."""
        lead = Lead(
            user_id=user_id,
            name=pubmed_lead.get("name", "Unknown"),
            title=pubmed_lead.get("title", "Principal Investigator"),
            company=pubmed_lead.get("company", "Unknown"),
            location=pubmed_lead.get("location", "Unknown"),
            company_hq=pubmed_lead.get("company_hq", "Unknown"),
            email=pubmed_lead.get("email") or None,
            linkedin_url=pubmed_lead.get("linkedin") or None,
            recent_publication=pubmed_lead.get("recent_publication", True),
            publication_year=pubmed_lead.get("publication_year"),
            publication_title=pubmed_lead.get("publication_title"),
            publication_count=1,
            company_funding=pubmed_lead.get("company_funding", "Unknown"),
            uses_3d_models=pubmed_lead.get("uses_3d_models", True),
            status="NEW",
        )
        lead.add_data_source("pubmed")
        lead.set_enrichment(
            "pubmed",
            {
                "pmid": pubmed_lead.get("pubmed_id"),
                "journal": pubmed_lead.get("journal"),
                "search_date": datetime.utcnow().isoformat(),
            },
        )
        return lead

    async def get_service_status(self) -> Dict:
        return {
            "service": "pubmed",
            "available": self._scraper is not None,
            "email": self.email,
            "has_api_key": bool(self.api_key),
            "rate_limit": f"{self._rps} req/sec",
            "cache_enabled": True,
            "features": [
                "search_leads",
                "search_multiple_queries",
                "get_author_profile",
                "citation_tracking",
                "advanced_filters",
                "institution_classifier",
            ],
        }


_pubmed_service: Optional[PubMedService] = None


def get_pubmed_service() -> PubMedService:
    global _pubmed_service
    if _pubmed_service is None:
        _pubmed_service = PubMedService()
    return _pubmed_service


__all__ = ["PubMedService", "get_pubmed_service"]
