"""Contact service for researcher contact discovery."""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from app.core.cache import Cache
from app.core.config import settings
from app.models.researcher import Researcher

if TYPE_CHECKING:
    from app.services.quota_manager import QuotaManager

logger = logging.getLogger(__name__)

_TTL_CONTACT_RESULT = 86_400 * 30
_TTL_DOMAIN_RESULTS = 86_400 * 7

_CONF_STORE = 0.65
_CONF_NIH_DIRECT = 0.98
_CONF_ACADEMIC_BASE = 0.72
_CONF_PATTERN_ONLY = 0.40

_HUNTER_DOMAIN_SEARCH = "https://api.hunter.io/v2/domain-search"


class ContactService:
    def __init__(self) -> None:
        self._hunter_key = settings.HUNTER_API_KEY

    async def find_email(
        self,
        researcher: Researcher,
        quota_manager: "QuotaManager",
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """Discover the professional contact information for a researcher."""
        if not researcher.name:
            return _not_found("no_name")

        cache_key = _contact_cache_key(researcher)
        if not force_refresh:
            cached = await Cache.get(cache_key)
            if cached:
                return {**cached, "cached": True}

        result = self._try_nih_contact(researcher)
        if result and result["confidence"] >= _CONF_STORE:
            return await self._cache_and_return(cache_key, result)

        if _get_institution_type(researcher) == "academic":
            academic = self._try_academic_pattern(researcher)
            if academic and academic["confidence"] >= _CONF_STORE:
                return await self._cache_and_return(cache_key, academic)
            if academic:
                result = academic

        if self._hunter_key and quota_manager is not None:
            domain = _extract_company_domain(researcher)
            if domain:
                hunter_result = await self._try_hunter_domain(researcher.name, domain, quota_manager)
                if hunter_result and hunter_result["confidence"] >= _CONF_STORE:
                    return await self._cache_and_return(cache_key, hunter_result)
                if hunter_result and (not result or hunter_result["confidence"] > result["confidence"]):
                    result = hunter_result

        fallback = self._pattern_fallback(researcher)
        if not result or (fallback and fallback["confidence"] > result["confidence"]):
            result = fallback

        if result:
            result["found_at"] = datetime.utcnow().isoformat()
            await Cache.set(cache_key, result, ttl=_TTL_CONTACT_RESULT)
        return result or _not_found("all_layers_failed")

    @staticmethod
    def _try_nih_contact(researcher: Researcher) -> Optional[Dict[str, Any]]:
        grants = (researcher.enrichment_data or {}).get("nih_grants", {}).get("grants", [])
        for grant in grants:
            email = grant.get("email")
            if email and _is_plausible_email(email):
                return {
                    "email": email,
                    "confidence": _CONF_NIH_DIRECT,
                    "source": "nih_grant_record",
                    "alternatives": [],
                }
        return None

    def _try_academic_pattern(self, researcher: Researcher) -> Optional[Dict[str, Any]]:
        first, last = _parse_name(researcher.name)
        if not first or not last:
            return None

        domain = _lookup_university_domain(researcher.company or "") or _company_to_academic_domain(researcher.company or "")
        if not domain:
            return None

        f = _ascii_slug(first)
        l = _ascii_slug(last)
        fi = f[0] if f else ""
        candidates = [f"{f}.{l}@{domain}", f"{fi}{l}@{domain}", f"{f}@{domain}", f"{f}_{l}@{domain}"]
        valid = [c for c in candidates if _is_plausible_email(c)]
        if not valid:
            return None

        return {
            "email": valid[0],
            "confidence": _CONF_ACADEMIC_BASE,
            "source": "academic_pattern",
            "alternatives": valid[1:3],
            "domain": domain,
        }

    async def _try_hunter_domain(self, name: str, domain: str, quota_manager: "QuotaManager") -> Optional[Dict[str, Any]]:
        domain_cache_key = f"hunter:domain:{hashlib.sha256(domain.encode()).hexdigest()}"
        domain_data = await Cache.get(domain_cache_key)

        if domain_data is None:
            params = urllib.parse.urlencode({"domain": domain, "api_key": self._hunter_key, "limit": 20})
            req = urllib.request.Request(f"{_HUNTER_DOMAIN_SEARCH}?{params}", headers={"Accept": "application/json"})
            try:
                import json
                with urllib.request.urlopen(req, timeout=8) as resp:
                    domain_data = json.loads(resp.read().decode())
                await Cache.set(domain_cache_key, domain_data, ttl=_TTL_DOMAIN_RESULTS)
                await quota_manager.record_hunter_use()
            except Exception:
                return None

        emails = (domain_data.get("data") or {}).get("emails", [])
        if not emails:
            return None
        best = emails[0].get("value")
        if not best:
            return None
        return {
            "email": best,
            "confidence": 0.85,
            "source": "hunter_domain_search",
            "alternatives": [e.get("value") for e in emails[1:3]],
        }

    @staticmethod
    def _pattern_fallback(researcher: Researcher) -> Optional[Dict[str, Any]]:
        first, last = _parse_name(researcher.name)
        if not first or not last:
            return None
        domain = _extract_company_domain(researcher) or _company_to_domain_guess(researcher.company or "")
        if not domain:
            return None
        f = _ascii_slug(first)
        l = _ascii_slug(last)
        guess = f"{f}.{l}@{domain}"
        if not _is_plausible_email(guess):
            return None
        return {"email": guess, "confidence": _CONF_PATTERN_ONLY, "source": "pattern_fallback"}

    @staticmethod
    async def _cache_and_return(cache_key: str, result: Dict[str, Any]) -> Dict[str, Any]:
        result["found_at"] = datetime.utcnow().isoformat()
        await Cache.set(cache_key, result, ttl=_TTL_CONTACT_RESULT)
        return result


def get_contact_confidence(contact_result: Optional[Dict[str, Any]]) -> float:
    if not contact_result:
        return 0.0
    return float(contact_result.get("confidence", 0.0) or 0.0)


async def find_researcher_contact(
    researcher: Researcher,
    quota_manager: "QuotaManager",
    force_refresh: bool = False,
) -> Dict[str, Any]:
    service = get_contact_service()
    return await service.find_email(researcher, quota_manager, force_refresh=force_refresh)


def _not_found(reason: str = "") -> Dict[str, Any]:
    return {"email": None, "confidence": 0.0, "source": "not_found", "reason": reason}


def _is_plausible_email(email: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", email))


def _parse_name(name: str) -> tuple[str, str]:
    clean = re.sub(r"\b(dr|prof|mr|mrs|ms|phd|md|dvm|jr|sr|ii|iii)\b\.?", "", (name or "").lower())
    clean = re.sub(r"[^a-z\s\-]", "", clean).strip()
    parts = [p for p in clean.split() if p]
    if not parts:
        return "", ""
    return parts[0], parts[-1] if len(parts) > 1 else ""


def _ascii_slug(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def _get_institution_type(researcher: Researcher) -> str:
    for key in ("pubmed", "conference"):
        data = (researcher.enrichment_data or {}).get(key, {})
        if isinstance(data, dict) and data.get("institution_type"):
            return data["institution_type"]
    return "unknown"


def _lookup_university_domain(company: str) -> str:
    mapping = {"harvard": "harvard.edu", "mit": "mit.edu", "stanford": "stanford.edu", "nih": "nih.gov"}
    text = company.lower()
    for fragment, domain in mapping.items():
        if fragment in text:
            return domain
    return ""


def _company_to_academic_domain(company: str) -> str:
    text = re.sub(r"[^a-z]", "", company.lower())
    return f"{text}.edu" if text else ""


def _extract_company_domain(researcher: Researcher) -> str:
    company_data = (researcher.enrichment_data or {}).get("company", {})
    domain = company_data.get("domain", "")
    if domain and "." in domain:
        return domain.lower().strip()
    return _lookup_university_domain(researcher.company or "")


def _company_to_domain_guess(company: str) -> str:
    text = re.sub(r"[^a-z0-9]", "", company.lower()).strip()
    return f"{text}.com" if text and len(text) >= 3 else ""


def _contact_cache_key(researcher: Researcher) -> str:
    raw = f"{researcher.id}:{(researcher.name or '').strip().lower()}"
    return f"contact:finder:{hashlib.sha256(raw.encode()).hexdigest()}"


_contact_service: Optional[ContactService] = None


def get_contact_service() -> ContactService:
    global _contact_service
    if _contact_service is None:
        _contact_service = ContactService()
    return _contact_service


__all__ = ["ContactService", "find_researcher_contact", "get_contact_confidence", "get_contact_service"]
