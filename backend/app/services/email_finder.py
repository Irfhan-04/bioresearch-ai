"""
Email Finder Service — Phase 2.3 Step 5
=========================================

Four-layer email discovery waterfall. All layers free.
"""

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
from app.models.lead import Lead

if TYPE_CHECKING:
    from app.services.quota_manager import QuotaManager

logger = logging.getLogger(__name__)

_TTL_EMAIL_RESULT = 86_400 * 30
_TTL_DOMAIN_RESULTS = 86_400 * 7

_CONF_STORE_ON_LEAD = 0.65
_CONF_NIH_DIRECT = 0.98
_CONF_HUNTER_MATCH = 0.88
_CONF_ACADEMIC_BASE = 0.72
_CONF_PATTERN_ONLY = 0.40

_HUNTER_DOMAIN_SEARCH = "https://api.hunter.io/v2/domain-search"

_UNIVERSITY_DOMAINS: Dict[str, str] = {
    "harvard": "harvard.edu",
    "mit": "mit.edu",
    "stanford": "stanford.edu",
    "johns hopkins": "jhu.edu",
    "yale": "yale.edu",
    "columbia": "columbia.edu",
    "penn": "upenn.edu",
    "duke": "duke.edu",
    "michigan": "umich.edu",
    "ucsf": "ucsf.edu",
    "uc san francisco": "ucsf.edu",
    "ucsd": "ucsd.edu",
    "uc san diego": "ucsd.edu",
    "ucla": "ucla.edu",
    "uc davis": "ucdavis.edu",
    "texas": "utexas.edu",
    "ut austin": "utexas.edu",
    "boston university": "bu.edu",
    "northeastern": "northeastern.edu",
    "tufts": "tufts.edu",
    "emory": "emory.edu",
    "vanderbilt": "vanderbilt.edu",
    "mayo": "mayo.edu",
    "mayo clinic": "mayo.edu",
    "nih": "nih.gov",
    "fda": "fda.hhs.gov",
    "epa": "epa.gov",
    "oxford": "ox.ac.uk",
    "cambridge": "cam.ac.uk",
    "imperial": "imperial.ac.uk",
    "ucl": "ucl.ac.uk",
}


class EmailFinder:
    def __init__(self) -> None:
        self._hunter_key = settings.HUNTER_API_KEY

    async def find_email(
        self,
        lead: Lead,
        quota_manager: "QuotaManager",
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        if not lead.name:
            return _not_found("no_name")

        cache_key = _email_cache_key(lead)
        if not force_refresh:
            cached = await Cache.get(cache_key)
            if cached:
                return {**cached, "cached": True}

        result: Optional[Dict[str, Any]] = None

        result = self._try_nih_email(lead)
        if result and result["confidence"] >= _CONF_STORE_ON_LEAD:
            return await self._cache_and_return(cache_key, result)

        if _get_institution_type(lead) == "academic":
            academic = self._try_academic_pattern(lead)
            if academic and academic["confidence"] >= _CONF_STORE_ON_LEAD:
                return await self._cache_and_return(cache_key, academic)
            if academic:
                result = academic

        score = lead.propensity_score or 0
        if self._hunter_key and await quota_manager.can_use_hunter(score):
            domain = _extract_company_domain(lead)
            if domain:
                hunter_result = await self._try_hunter_domain(lead.name, domain, quota_manager)
                if hunter_result and hunter_result["confidence"] >= _CONF_STORE_ON_LEAD:
                    return await self._cache_and_return(cache_key, hunter_result)
                if hunter_result and (not result or hunter_result["confidence"] > result["confidence"]):
                    result = hunter_result

        fallback = self._pattern_fallback(lead)
        if not result or (fallback and fallback["confidence"] > result["confidence"]):
            result = fallback

        if result:
            result["found_at"] = datetime.utcnow().isoformat()
            await Cache.set(cache_key, result, ttl=_TTL_EMAIL_RESULT)
        return result or _not_found("all_layers_failed")

    @staticmethod
    def _try_nih_email(lead: Lead) -> Optional[Dict[str, Any]]:
        grants = (lead.enrichment_data or {}).get("nih_grants", {}).get("grants", [])
        for grant in grants:
            email = grant.get("email")
            if email and _is_plausible_email(email):
                return {
                    "email": email,
                    "confidence": _CONF_NIH_DIRECT,
                    "source": "nih_grant_record",
                    "alternatives": [],
                    "note": "Directly from NIH grant contact record",
                }
        return None

    def _try_academic_pattern(self, lead: Lead) -> Optional[Dict[str, Any]]:
        first, last = _parse_name(lead.name)
        if not first or not last:
            return None

        domain = _lookup_university_domain(lead.company or "") or _company_to_academic_domain(lead.company or "")
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
            "note": "Institutional pattern — verify before outreach",
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
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    await quota_manager.mark_hunter_exhausted()
                return None
            except Exception:
                return None

        return self._match_hunter_result(name, domain_data)

    @staticmethod
    def _match_hunter_result(name: str, domain_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        emails = (domain_data.get("data") or {}).get("emails", [])
        if not emails:
            return None

        first, last = _parse_name(name)
        if not first or not last:
            return None

        f_slug = _ascii_slug(first)
        l_slug = _ascii_slug(last)
        best = None
        best_score = 0.0

        for entry in emails:
            addr = (entry.get("value") or "").lower()
            hunter_conf = (entry.get("confidence") or 0) / 100
            local = addr.split("@")[0] if "@" in addr else ""
            match_score = 0
            if l_slug in local:
                match_score += 3
            if f_slug in local or (f_slug and local.startswith(f_slug[0])):
                match_score += 2
            total = hunter_conf + match_score
            if total > best_score:
                best_score = total
                best = {
                    "email": entry.get("value"),
                    "confidence": min(0.70 + hunter_conf * 0.25 + match_score * 0.03, 0.97),
                    "source": "hunter_domain_search",
                    "alternatives": [e.get("value") for e in emails if e.get("value") != entry.get("value")][:2],
                    "hunter_confidence": entry.get("confidence"),
                }

        return best if best and best_score > 2 else None

    @staticmethod
    def _pattern_fallback(lead: Lead) -> Optional[Dict[str, Any]]:
        first, last = _parse_name(lead.name)
        if not first or not last:
            return None
        domain = _extract_company_domain(lead) or _company_to_domain_guess(lead.company or "")
        if not domain:
            return None
        f = _ascii_slug(first)
        l = _ascii_slug(last)
        fi = f[0] if f else ""
        patterns = [f"{f}.{l}@{domain}", f"{fi}{l}@{domain}", f"{f}@{domain}"]
        valid = [p for p in patterns if _is_plausible_email(p)]
        if not valid:
            return None
        return {
            "email": valid[0],
            "confidence": _CONF_PATTERN_ONLY,
            "source": "pattern_fallback",
            "alternatives": valid[1:],
            "note": "Pattern-generated — low confidence, verify before use",
        }

    @staticmethod
    async def _cache_and_return(cache_key: str, result: Dict[str, Any]) -> Dict[str, Any]:
        result["found_at"] = datetime.utcnow().isoformat()
        await Cache.set(cache_key, result, ttl=_TTL_EMAIL_RESULT)
        return result


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


def _get_institution_type(lead: Lead) -> str:
    for key in ("pubmed", "conference"):
        data = (lead.enrichment_data or {}).get(key, {})
        if isinstance(data, dict) and data.get("institution_type"):
            return data["institution_type"]
    return "unknown"


def _lookup_university_domain(company: str) -> str:
    text = company.lower()
    for fragment, domain in _UNIVERSITY_DOMAINS.items():
        if fragment in text:
            return domain
    return ""


def _company_to_academic_domain(company: str) -> str:
    text = company.lower()
    text = re.sub(r"\b(university of|the university|college of|school of|institute of)\b", "", text)
    text = re.sub(r"[^a-z\s]", "", text).strip()
    words = [w for w in text.split() if len(w) > 2]
    if not words:
        return ""
    return f"{''.join(words[:2])}.edu"


def _extract_company_domain(lead: Lead) -> str:
    company_data = (lead.enrichment_data or {}).get("company", {})
    domain = company_data.get("domain", "")
    if domain and "." in domain:
        return domain.lower().strip()
    if lead.company:
        domain = _lookup_university_domain(lead.company)
        if domain:
            return domain
    if _get_institution_type(lead) == "academic" and lead.company:
        return _company_to_academic_domain(lead.company)
    return ""


def _company_to_domain_guess(company: str) -> str:
    text = company.lower()
    text = re.sub(r"\b(inc|llc|corp|ltd|co|gmbh|bv|plc|sa)\b\.?", "", text)
    text = re.sub(r"[^a-z0-9]", "", text).strip()
    return f"{text}.com" if text and len(text) >= 3 else ""


def _email_cache_key(lead: Lead) -> str:
    raw = f"{lead.id}:{(lead.name or '').strip().lower()}"
    return f"email:finder:{hashlib.sha256(raw.encode()).hexdigest()}"


_email_finder: Optional[EmailFinder] = None


def get_email_finder() -> EmailFinder:
    global _email_finder
    if _email_finder is None:
        _email_finder = EmailFinder()
    return _email_finder


__all__ = ["EmailFinder", "get_email_finder"]
