"""
LinkedIn Profile Service — Phase 2.3 Step 2
============================================

Finds LinkedIn profile URLs for leads using a free three-layer strategy:

"""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import Cache
from app.core.cache import Cache, CacheKey
from app.core.config import settings
from app.models.lead import Lead

logger = logging.getLogger(__name__)

# ── Confidence thresholds ─────────────────────────────────────────────────────
_CONF_STORE_VERIFIED = 0.75  # store on lead.linkedin_url + tag "linkedin-verified"
_CONF_STORE_CANDIDATE = 0.50  # store in enrichment_data only
_CONF_DISCARD = 0.50  # below this: do not store

# ── Cache TTL ─────────────────────────────────────────────────────────────────
_TTL_LINKEDIN_PROFILE = 86_400 * 7  # 7 days — preserves Google CSE daily quota

# ── Google CSE endpoint ───────────────────────────────────────────────────────
_GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"

# ── DuckDuckGo HTML endpoint ──────────────────────────────────────────────────
_DDG_URL = "https://html.duckduckgo.com/html/"

# ── LinkedIn URL validation pattern ──────────────────────────────────────────
_LINKEDIN_URL_RE = re.compile(
    r"https?://(?:www\.)?linkedin\.com/in/([\w\-]{3,100})/?",
    re.IGNORECASE,
)

# ── HTTP client settings ──────────────────────────────────────────────────────
_CONF_STORE_VERIFIED = 0.75
_CONF_STORE_CANDIDATE = 0.50
_CONF_DISCARD = 0.50

_TTL_LINKEDIN_PROFILE = 86_400 * 7

_GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"
_DDG_URL = "https://html.duckduckgo.com/html/"

_LINKEDIN_URL_RE = re.compile(
    r"https?://(?:[a-z]{2,3}\.)?(?:www\.)?linkedin\.com/in/([\w\-]{3,100})/?",
    re.IGNORECASE,
)
_HTTP_TIMEOUT = 8.0
_HTTP_USER_AGENT = (
    "Mozilla/5.0 (compatible; BiotechLeadGen/2.0; "
    "+https://github.com/your-org/biotech-lead-generator)"
)


class LinkedInService:
    def __init__(self) -> None:
        self._google_api_key = getattr(settings, "GOOGLE_CSE_API_KEY", None)
        self._google_cse_id = getattr(settings, "GOOGLE_CSE_ID", None)
        self._has_google_cse = bool(self._google_api_key and self._google_cse_id)

        if self._has_google_cse:
            logger.info("LinkedInService: Google CSE configured (100 req/day free)")
        else:
            logger.warning(
                "LinkedInService: Google CSE not configured — "
                "using DuckDuckGo + pattern fallback only. "
                "Set GOOGLE_CSE_API_KEY + GOOGLE_CSE_ID for best results."
            )

    # ── PUBLIC: Main entry point ──────────────────────────────────────────────
    async def find_profile_url(
        self,
        lead: Lead,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        if not lead.name or lead.name == "Unknown":
            return _not_found_result("no_name")

        cache_key = self._build_cache_key(lead)
        if not force_refresh:
            cached = await Cache.get(cache_key)
            if cached:
                logger.debug("LinkedIn cache HIT for lead %s (%s)", lead.id, lead.name)
                return {**cached, "cached": True}

        # Layer 1 — always generate patterns first (no I/O, instant)
        patterns = self._generate_url_patterns(lead.name, lead.company or "")
        best_pattern = patterns[0] if patterns else None

        # Layer 2 — Google CSE (best quality, 100 req/day free)
        patterns = self._generate_url_patterns(lead.name, lead.company or "")
        best_pattern = patterns[0] if patterns else None

        result = None
        if self._has_google_cse:
            result = await self._try_google_cse(lead.name, lead.company or "")
        # Layer 3 — DuckDuckGo fallback
        if not result or result["confidence"] < _CONF_STORE_CANDIDATE:
            ddg_result = await self._try_duckduckgo(lead.name, lead.company or "")
            if ddg_result and (
                not result or ddg_result["confidence"] > result["confidence"]
            ):
                result = ddg_result

        # Merge pattern if nothing better found
        if not result or result["confidence"] < _CONF_STORE_CANDIDATE:
            if best_pattern:
                conf = self._compute_pattern_confidence(
                    best_pattern,
                    lead.name,
                    lead.company or "",
                )
                result = {
                    "url": best_pattern,
                    "confidence": conf,
                    "source": "pattern",
                    "slug": self._url_to_slug(best_pattern),
                }
            else:
                result = _not_found_result("no_pattern_generated")

        result["cached"] = False
        result["found_at"] = datetime.utcnow().isoformat()

        if result.get("confidence", 0) >= _CONF_DISCARD:
            await Cache.set(cache_key, result, ttl=_TTL_LINKEDIN_PROFILE)

        logger.info(
            "LinkedIn lookup for %s → %s (conf=%.2f, src=%s)",
            lead.name,
            result.get("url", "NOT_FOUND"),
            result.get("confidence", 0),
            result.get("source", "?"),
        )
        return result

    async def enrich_lead_linkedin(
        self,
        lead: Lead,
        db: AsyncSession,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        result = await self.find_profile_url(lead, force_refresh=force_refresh)
        confidence = result.get("confidence", 0.0)
        url = result.get("url")

        if url and confidence >= _CONF_STORE_VERIFIED:
            if not lead.linkedin_url:
                lead.linkedin_url = url
            lead.add_tag("linkedin-verified")

        lead.set_enrichment(
            "linkedin",
            {**result, "enriched_at": datetime.utcnow().isoformat()},
          {
                **result,
                "enriched_at": datetime.utcnow().isoformat(),
            },

        )
        lead.add_data_source("linkedin")

        db.add(lead)
        await db.commit()
        await db.refresh(lead)

        return {
            "status": "success" if url else "not_found",
            "lead_id": str(lead.id),
            "url": url,
            "confidence": confidence,
            "source": result.get("source", "unknown"),
            "verified": confidence >= _CONF_STORE_VERIFIED,
        }

    async def get_service_status(self) -> Dict[str, Any]:
        return {
            "service": "linkedin",
            "available": True,
            "strategy": "pattern + google_cse + duckduckgo",
            "google_cse": self._has_google_cse,
            "daily_cse_quota": 100 if self._has_google_cse else 0,
            "cost": "free",
            "cache_ttl_days": 7,
            "confidence_threshold_for_storage": _CONF_STORE_VERIFIED,
        }
                  
    # ── PRIVATE: Layer 1 — Pattern generation ────────────────────────────────
                  
    @staticmethod
    def _generate_url_patterns(name: str, company: str) -> List[str]:
        clean = _strip_accents(name)
        clean = re.sub(
            r"\b(dr|prof|mr|mrs|ms|phd|md|dvm|dds|jr|sr|ii|iii)\b\.?",
            "",
            clean.lower(),
        )
        clean = re.sub(r"[^a-z\s]", "", clean).strip()
        parts = clean.split()

        if not parts:
            return []

        first = parts[0]
        last = parts[-1] if len(parts) > 1 else parts[0]
        mid = parts[1] if len(parts) > 2 else ""

        patterns = []
        base = [
            f"{first}-{last}",
            f"{first[0]}{last}",
            f"{first}.{last}",
            f"{last}-{first}",
        ]
        if mid:
            base.insert(1, f"{first}-{mid[0]}-{last}")
            base.insert(2, f"{first}-{mid}-{last}")

        for slug in base:
            url = f"https://www.linkedin.com/in/{slug}"
            if url not in patterns:
                patterns.append(url)

        return patterns[:7]

    @staticmethod
    def _compute_pattern_confidence(url: str, name: str, company: str) -> float:
        conf = 0.50
        slug = _extract_slug(url)
        parts = _name_parts(name)

        if parts["first"] and parts["first"] in slug:
            conf += 0.05
        if parts["last"] and parts["last"] in slug:
            conf += 0.07

        return round(min(conf, 0.65), 3)

    # ── PRIVATE: Layer 2 — Google Custom Search API ───────────────────────────

    async def _try_google_cse(self, name: str, company: str) -> Optional[Dict[str, Any]]:
        query_parts = [f'site:linkedin.com/in "{name}"']
        if company:
            query_parts.append(f'"{company}"')
        query = " ".join(query_parts)

        params = {
            "key": self._google_api_key,
            "cx": self._google_cse_id,
            "q": query,
            "num": 3,
        }

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                resp = await client.get(_GOOGLE_CSE_URL, params=params)

            if resp.status_code == 429:
                logger.warning("Google CSE daily quota exhausted — falling back to DuckDuckGo")
                return None
                logger.warning("Google CSE daily quota exhausted — using DuckDuckGo")
                return None
            if resp.status_code != 200:
                logger.warning("Google CSE HTTP %d", resp.status_code)
                return None

            data = resp.json()
            items = data.get("items", [])

            for item in items:
                url = item.get("link", "")
                if not _is_valid_linkedin_url(url):
                    continue

                return {
                    "url": _normalise_linkedin_url(url),
                    "confidence": self._compute_cse_confidence(url, name, company),
                    "source": "google_cse",
                    "slug": _extract_slug(url),
                    "query": query,
                }

        except httpx.TimeoutException:
            logger.warning("Google CSE timeout for %s", name)
        except Exception as exc:
            logger.error("Google CSE error: %s", exc, exc_info=True)

        return None

    @staticmethod
    def _compute_cse_confidence(url: str, name: str, company: str) -> float:
        conf = 0.85
        slug = _extract_slug(url).lower()
        parts = _name_parts(name)

        if parts["first"] and parts["first"][:4] in slug:
            conf += 0.05
        if parts["last"] and parts["last"][:4] in slug:
            conf += 0.05

        return round(min(conf, 0.97), 3)
                  
    # ── PRIVATE: Layer 3 — DuckDuckGo HTML fallback ───────────────────────────

    async def _try_duckduckgo(self, name: str, company: str) -> Optional[Dict[str, Any]]:
        query_parts = [f'site:linkedin.com/in "{name}"']
        if company:
            query_parts.append(f'"{company}"')
        query = " ".join(query_parts)

        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT,
                follow_redirects=True,
                headers={"User-Agent": _HTTP_USER_AGENT},
            ) as client:
                resp = await client.post(
                    _DDG_URL,
                    data={"q": query, "b": "", "kl": "us-en"},
                )

            if resp.status_code != 200:
                return None
            slugs = _LINKEDIN_URL_RE.findall(resp.text)
            for slug in slugs:
                url = f"https://www.linkedin.com/in/{slug}"
                conf = self._compute_ddg_confidence(url, name, company)
                if conf >= _CONF_STORE_CANDIDATE:
                    return {
                        "url": url,
                        "confidence": conf,
                        "source": "duckduckgo",
                        "slug": slug,
                        "query": query,
                    }

        except httpx.TimeoutException:
            logger.warning("DuckDuckGo timeout for %s", name)
        except Exception as exc:
            logger.error("DuckDuckGo error: %s", exc, exc_info=True)

        return None

    @staticmethod
    def _compute_ddg_confidence(url: str, name: str, company: str) -> float:
        conf = 0.72
        slug = _extract_slug(url).lower()
        parts = _name_parts(name)

        if parts["first"] and parts["first"][:4] in slug:
            conf += 0.06
        if parts["last"] and parts["last"][:4] in slug:
            conf += 0.07

        return round(min(conf, 0.90), 3)

    # ── PRIVATE: Cache key builder ────────────────────────────────────────────

    @staticmethod
    def _build_cache_key(lead: Lead) -> str:
        raw = f"{lead.id}:{(lead.name or '').strip().lower()}"
        digest = hashlib.sha256(raw.encode()).hexdigest()
        return f"linkedin:profile:{digest}"
        return CacheKey.linkedin_profile(digest)

    @staticmethod
    def _url_to_slug(url: str) -> str:
        return _extract_slug(url)

# ── Module-level helpers ──────────────────────────────────────────────────────
def _not_found_result(reason: str) -> Dict[str, Any]:
    return {
        "url": None,
        "confidence": 0.0,
        "source": "not_found",
        "reason": reason,
        "cached": False,
    }


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _name_parts(name: str) -> Dict[str, str]:
    clean = _strip_accents(name).lower()
    clean = re.sub(r"\b(dr|prof|mr|mrs|ms|phd|md)\b\.?", "", clean).strip()
    clean = re.sub(r"[^a-z\s]", " ", clean)
    parts = [p for p in clean.split() if p]
    return {
        "first": parts[0] if parts else "",
        "last": parts[-1] if len(parts) > 1 else "",
    }


def _is_valid_linkedin_url(url: str) -> bool:
    return bool(_LINKEDIN_URL_RE.match(url))


def _extract_slug(url: str) -> str:
    m = _LINKEDIN_URL_RE.search(url)
    return m.group(1) if m else ""


def _normalise_linkedin_url(url: str) -> str:
    slug = _extract_slug(url)
    if not slug:
        return url
    return f"https://www.linkedin.com/in/{slug}"


# ── Singleton ─────────────────────────────────────────────────────────────────

_linkedin_service: Optional[LinkedInService] = None


def get_linkedin_service() -> LinkedInService:
    global _linkedin_service
    if _linkedin_service is None:
        _linkedin_service = LinkedInService()
    return _linkedin_service


__all__ = [
    "LinkedInService",
    "get_linkedin_service",
    "_name_parts",
    "_is_valid_linkedin_url",
    "_extract_slug",
    "_normalise_linkedin_url",
    "_not_found_result",
    "_strip_accents",
]
__all__ = ["LinkedInService", "get_linkedin_service"]
