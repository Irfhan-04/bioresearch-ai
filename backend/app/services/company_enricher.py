"""Company Enricher Service — Phase 2.3 Step 5."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import TYPE_CHECKING, Any, Dict, Optional

from app.core.cache import Cache
from app.core.config import settings
from app.models.lead import Lead

if TYPE_CHECKING:
    from app.services.quota_manager import QuotaManager

logger = logging.getLogger(__name__)

_TTL_COMPANY_DATA = 86_400 * 30
_CLEARBIT_URL = "https://company.clearbit.com/v2/companies/find"

_EMPLOYEE_SIZE_MAP = [
    (10, "1-10 employees"),
    (50, "11-50 employees"),
    (200, "51-200 employees"),
    (500, "201-500 employees"),
    (1000, "501-1000 employees"),
    (5000, "1001-5000 employees"),
    (float("inf"), "5000+ employees"),
]

_FUNDING_TYPE_MAP = {
    "seed": "Seed",
    "angel": "Seed",
    "series_a": "Series A",
    "series_b": "Series B",
    "series_c": "Series C",
    "series_d": "Series D",
    "series_e": "Series E",
    "private_equity": "Private Equity",
    "public": "Public",
    "acquired": "Acquired",
}


class CompanyEnricher:
    def __init__(self) -> None:
        self._clearbit_key = settings.CLEARBIT_API_KEY

    async def enrich_company(
        self,
        company_name: str,
        lead: Optional[Lead] = None,
        quota_manager: Optional["QuotaManager"] = None,
    ) -> Dict[str, Any]:
        if lead:
            nih_result = self._try_nih_company_data(lead)
            if nih_result:
                return nih_result

        if self._clearbit_key and quota_manager and lead:
            if await self._should_call_clearbit(lead, quota_manager):
                domain = _extract_domain_from_company(company_name)
                if domain:
                    clearbit = await self._call_clearbit(domain, quota_manager)
                    if clearbit:
                        return clearbit

        return self._structural_mock(company_name)

    @staticmethod
    def _try_nih_company_data(lead: Lead) -> Optional[Dict[str, Any]]:
        grants = (lead.enrichment_data or {}).get("nih_grants", {}).get("grants", [])
        if not grants:
            return None
        best = max(grants, key=lambda g: (g.get("is_active", False), g.get("award_amount", 0) or 0))
        return {
            "name": best.get("company", lead.company or ""),
            "domain": "",
            "industry": "Academic/Research",
            "size": None,
            "location": best.get("location", ""),
            "funding": {
                "stage": best.get("company_funding", "NIH Grant"),
                "mechanism": best.get("mechanism", ""),
                "award_amount": best.get("award_str", ""),
                "project_title": best.get("project_title", ""),
                "is_active": best.get("is_active", False),
                "fiscal_year": best.get("fiscal_year"),
            },
            "source": "nih_reporter",
        }

    async def _should_call_clearbit(self, lead: Lead, quota_manager: "QuotaManager") -> bool:
        from app.services.contact_service import _get_institution_type

        if _get_institution_type(lead) == "academic":
            return False
        current_funding = lead.company_funding or "Unknown"
        if current_funding not in ("Unknown", "", None):
            return False
        score = lead.propensity_score or 0
        if score < settings.CLEARBIT_MIN_SCORE_FOR_API:
            return False
        return await quota_manager.can_use_clearbit(score)

    async def _call_clearbit(self, domain: str, quota_manager: "QuotaManager") -> Optional[Dict[str, Any]]:
        cache_key = f"clearbit:company:{hashlib.sha256(domain.encode()).hexdigest()}"
        cached = await Cache.get(cache_key)
        if cached is not None:
            return None if cached.get("source") == "clearbit_not_found" else cached

        req = urllib.request.Request(
            f"{_CLEARBIT_URL}?domain={urllib.parse.quote(domain)}",
            headers={"Authorization": f"Bearer {self._clearbit_key}", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                raw = json.loads(resp.read().decode())
            result = self._parse_clearbit_response(raw)
            await Cache.set(cache_key, result, ttl=_TTL_COMPANY_DATA)
            await quota_manager.record_clearbit_use()
            return result
        except urllib.error.HTTPError as e:
            if e.code == 404:
                await Cache.set(cache_key, {"source": "clearbit_not_found"}, ttl=86_400 * 7)
            elif e.code == 429:
                await quota_manager.mark_clearbit_exhausted()
            return None
        except Exception:
            return None

    @staticmethod
    def _parse_clearbit_response(raw: Dict[str, Any]) -> Dict[str, Any]:
        metrics = raw.get("metrics", {}) or {}
        geo = raw.get("geo", {}) or {}
        category = raw.get("category", {}) or {}
        employees = metrics.get("employees") or 0

        size_label = "Unknown"
        for threshold, label in _EMPLOYEE_SIZE_MAP:
            if employees <= threshold:
                size_label = label
                break

        funding_stage = "Unknown"
        for tag in raw.get("tags") or []:
            normalized = tag.lower().replace(" ", "_")
            if normalized in _FUNDING_TYPE_MAP:
                funding_stage = _FUNDING_TYPE_MAP[normalized]
                break

        location = ", ".join(filter(None, [geo.get("city", ""), geo.get("stateCode", ""), geo.get("country", "")]))
        return {
            "name": raw.get("name", ""),
            "domain": raw.get("domain", ""),
            "industry": category.get("industry", ""),
            "sub_industry": category.get("subIndustry", ""),
            "size": size_label,
            "employees": employees,
            "location": location,
            "founded": raw.get("foundedYear"),
            "description": (raw.get("description", "") or "")[:300],
            "funding": {"stage": funding_stage, "total_raised": ""},
            "social": {
                "linkedin": (raw.get("linkedin") or {}).get("handle", ""),
                "twitter": (raw.get("twitter") or {}).get("handle", ""),
            },
            "source": "clearbit",
        }

    @staticmethod
    def _structural_mock(company_name: str) -> Dict[str, Any]:
        return {
            "name": company_name,
            "domain": _extract_domain_from_company(company_name) or "",
            "industry": "Biotechnology",
            "size": None,
            "location": "",
            "funding": {"stage": "Unknown"},
            "source": "structural_mock",
        }


def _extract_domain_from_company(company: str) -> str:
    if not company:
        return ""
    text = company.lower()
    text = re.sub(r"\b(inc|llc|corp|ltd|co|gmbh|bv|plc|sa|university|college|institute)\b\.?", "", text)
    text = re.sub(r"[^a-z0-9]", "", text).strip()
    return f"{text}.com" if text and len(text) >= 3 else ""


_company_enricher: Optional[CompanyEnricher] = None


def get_company_enricher() -> CompanyEnricher:
    global _company_enricher
    if _company_enricher is None:
        _company_enricher = CompanyEnricher()
    return _company_enricher


__all__ = ["CompanyEnricher", "get_company_enricher"]
