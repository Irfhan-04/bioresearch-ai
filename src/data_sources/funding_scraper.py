"""
NIH RePORTER Funding Scraper — Phase 2.3 Step 4
================================================

Queries the NIH RePORTER REST API (free, no auth) to find:
  1. PIs with active grants matching a keyword  (search mode)
  2. Grant history for a specific PI name       (enrichment mode)

NIH RePORTER API:
  POST https://api.reporter.nih.gov/v2/projects/search
  No API key. No registration. Updated weekly by NIH.

Free tools used:
  - urllib.request (stdlib) — zero extra dependencies for HTTP
  - json, re, datetime (stdlib)
"""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── API constants ─────────────────────────────────────────────────────────────
_API_URL       = "https://api.reporter.nih.gov/v2/projects/search"
_HTTP_TIMEOUT  = 15          # seconds
_REQUEST_DELAY = 0.35        # seconds between calls (~3 req/sec)
_MAX_RESULTS   = 500         # hard cap per query (NIH allows up to 500)

# ── Fields to request from API ───────────────────────────────────────────────
_FIELDS = [
    "ProjectNum", "ContactPiName", "PiNames",
    "Organization", "ProjectTitle", "FiscalYear",
    "AwardAmount", "Terms", "AbstractText",
    "ProjectStartDate", "ProjectEndDate",
    "AgencyIcFundings", "ContactPiEmail",
]

# ── Grant mechanism → funding stage label ────────────────────────────────────
_MECHANISM_TO_STAGE: Dict[str, str] = {
    "R01": "NIH R01",   # Investigator-initiated — most common, $300k-600k/yr
    "R21": "NIH R21",   # Exploratory/developmental — $275k/2yr
    "R03": "NIH R03",   # Small grant — $50k/yr
    "U01": "NIH U01",   # Cooperative agreement — often >$1M/yr
    "P01": "NIH P01",   # Program project grant — multiple PIs
    "P30": "NIH P30",   # Core center grant
    "P50": "NIH P50",   # Specialized center
    "K99": "NIH K99",   # Career transition (pre-independence)
    "R00": "NIH R00",   # Career transition (post-independence)
    "DP2": "NIH DP2",   # NIH Director's New Innovator Award
    "RM1": "NIH RM1",   # Research project (multi-year)
    "UG3": "NIH UG3",   # Exploratory clinical trial
}

# ── Relevance keywords for biotech/DILI domain ───────────────────────────────
_DOMAIN_KEYWORDS = [
    "liver", "hepat", "dili", "toxicol", "toxicity", "drug",
    "3d", "organoid", "spheroid", "organ-on-chip", "in vitro",
    "safety", "pharmacol", "adme", "biomarker", "preclinical",
    "cell culture", "microphysiological", "new approach",
]


class NIHReporterScraper:
    """
    Queries the NIH RePORTER v2 REST API.

    Two query modes:
      search_by_keywords() — find grants by topic → extract PIs as leads
      search_by_pi_name()  — look up a specific PI's grant portfolio
    """

    def __init__(self) -> None:
        self._last_request = 0.0

    # =========================================================================
    # PUBLIC — Search mode (new lead discovery)
    # =========================================================================

    def search_by_keywords(
        self,
        keywords: List[str],
        fiscal_years: Optional[List[int]] = None,
        max_results: int = 50,
        mechanisms: Optional[List[str]] = None,
        active_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Find PIs with NIH grants matching a list of keywords.

        Searches the `terms`, `project_title`, and `abstract_text` fields.
        Returns one record per unique PI (deduplicated by contact_pi_name).
        """
        fiscal_years = fiscal_years or _default_fiscal_years()
        search_text  = " ".join(keywords)

        payload: Dict[str, Any] = {
            "criteria": {
                "fiscal_years":            fiscal_years,
                "include_active_projects": active_only,
                "advanced_text_search": {
                    "search_field": "terms,title,abstract",
                    "search_text":  search_text,
                },
            },
            "offset":     0,
            "limit":      min(max_results * 3, _MAX_RESULTS),
            "sort_field": "award_amount",
            "sort_order": "desc",
            "fields":     _FIELDS,
        }

        if mechanisms:
            payload["criteria"]["project_nums"] = mechanisms

        raw = self._post_query(payload)
        if not raw:
            return []

        projects = [self._parse_project(r) for r in raw if r]
        projects = [p for p in projects if p is not None]

        deduped = _deduplicate_by_pi(projects)

        logger.info(
            "NIH search '%s' → %d projects → %d unique PIs",
            search_text[:50], len(projects), len(deduped)
        )
        return deduped[:max_results]

    # =========================================================================
    # PUBLIC — Enrichment mode (look up a specific PI)
    # =========================================================================

    def search_by_pi_name(
        self,
        pi_name: str,
        fiscal_years: Optional[List[int]] = None,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Find all NIH grants for a specific PI name.

        Used by FundingService.get_grants_for_pi() → EnrichmentService._enrich_company().
        """
        first, last = _parse_name_to_parts(pi_name)
        if not last:
            logger.warning("NIH PI lookup: could not parse name '%s'", pi_name)
            return []

        fiscal_years = fiscal_years or _default_fiscal_years(years_back=5)

        payload: Dict[str, Any] = {
            "criteria": {
                "fiscal_years": fiscal_years,
                "pi_names":     [{"last_name": last, "first_name": first}],
                "include_active_projects": False,   # include historical too
            },
            "offset":     0,
            "limit":      min(max_results, 25),
            "sort_field": "fiscal_year",
            "sort_order": "desc",
            "fields":     _FIELDS,
        }

        raw = self._post_query(payload)
        if not raw:
            return []

        projects = [self._parse_project(r) for r in raw if r]
        projects = [p for p in projects if p is not None]

        logger.info("NIH PI lookup '%s' → %d grants found", pi_name, len(projects))
        return projects[:max_results]

    # =========================================================================
    # PRIVATE — HTTP helper
    # =========================================================================

    def _post_query(self, payload: Dict[str, Any]) -> Optional[List[Dict]]:
        """POST a search query to the NIH RePORTER API."""
        self._throttle()

        body = json.dumps(payload).encode("utf-8")
        req  = urllib.request.Request(
            _API_URL,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept":       "application/json",
                "User-Agent":   "BiotechLeadGenerator/2.0 (research tool)",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
                data    = json.loads(resp.read().decode("utf-8"))
                results = data.get("results", [])
                total   = data.get("meta", {}).get("total", 0)
                logger.debug("NIH API: %d total hits, %d returned", total, len(results))
                return results

        except urllib.error.HTTPError as e:
            logger.error("NIH API HTTP %d: %s", e.code, e.reason)
        except urllib.error.URLError as e:
            logger.error("NIH API network error: %s", e.reason)
        except json.JSONDecodeError as e:
            logger.error("NIH API JSON parse error: %s", e)
        except Exception as e:
            logger.error("NIH API unexpected error: %s", e, exc_info=True)

        return None

    # =========================================================================
    # PRIVATE — Response parser
    # =========================================================================

    def _parse_project(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalise a single NIH project record into our standard schema."""
        contact_pi_raw = raw.get("contact_pi_name", "")
        if not contact_pi_raw:
            return None

        pi_first, pi_last = _parse_nih_name(contact_pi_raw)
        if not pi_last:
            return None

        pi_full_name = f"{pi_first} {pi_last}".strip()

        org      = raw.get("organization") or {}
        city     = org.get("org_city", "")
        state    = org.get("org_state", "")
        country  = org.get("org_country", "UNITED STATES")
        location = ", ".join(filter(None, [city, state]))
        if country not in ("UNITED STATES", "US", "USA"):
            location = ", ".join(filter(None, [city, country]))

        org_name      = _title_case(org.get("org_name", "Unknown"))
        project_num   = raw.get("project_num", "")
        mechanism     = _extract_mechanism(project_num)
        funding_stage = _MECHANISM_TO_STAGE.get(
            mechanism, f"NIH {mechanism}" if mechanism else "NIH Grant"
        )

        award_amount = raw.get("award_amount") or 0
        award_str    = f"${award_amount:,.0f}/yr" if award_amount else "Unknown"

        terms    = raw.get("terms", "") or ""
        abstract = (raw.get("abstract_text", "") or "")[:500]

        start_raw  = raw.get("project_start_date", "")
        end_raw    = raw.get("project_end_date", "")
        end_date   = _parse_date(end_raw)
        is_active  = end_date is None or end_date >= datetime.now()

        ic_fundings = raw.get("agency_ic_fundings", []) or []
        ics = [
            f["ic_name"] for f in ic_fundings
            if isinstance(f, dict) and f.get("ic_name")
        ]

        return {
            # PI identity
            "name":             pi_full_name,
            "pi_first":         pi_first,
            "pi_last":          pi_last,
            "email":            raw.get("contact_pi_email") or None,
            # Institution
            "company":          org_name,
            "company_hq":       location,
            "location":         location,
            # Grant details
            "project_num":      project_num,
            "mechanism":        mechanism,
            "project_title":    raw.get("project_title", ""),
            "fiscal_year":      raw.get("fiscal_year"),
            "award_amount":     award_amount,
            "award_str":        award_str,
            "start_date":       start_raw,
            "end_date":         end_raw,
            "is_active":        is_active,
            "terms":            terms,
            "abstract":         abstract,
            "funding_ics":      ics,
            # Mapped to Lead model fields
            "company_funding":  funding_stage,
            "title":            "Principal Investigator",
            "institution_type": "academic",
            "data_sources":     ["funding"],
            # Scoring signals
            "recent_publication": False,
            "uses_3d_models":     _mentions_3d(terms + " " + abstract),
        }

    # =========================================================================
    # PRIVATE — Rate limiter
    # =========================================================================

    def _throttle(self) -> None:
        """Enforce inter-request delay to be a good API citizen."""
        elapsed = time.monotonic() - self._last_request
        if elapsed < _REQUEST_DELAY:
            time.sleep(_REQUEST_DELAY - elapsed)
        self._last_request = time.monotonic()


# =============================================================================
# Module-level helpers
# =============================================================================

def _parse_nih_name(contact_pi_name: str) -> Tuple[str, str]:
    """
    Parse NIH API name format "LASTNAME, FIRSTNAME MI" into (first, last).

    Examples:
      "SMITH, JOHN A"      → ("John", "Smith")
      "CHEN-WILSON, SARAH" → ("Sarah", "Chen-Wilson")
    """
    if not contact_pi_name:
        return "", ""
    if "," in contact_pi_name:
        parts     = contact_pi_name.split(",", 1)
        last_raw  = parts[0].strip()
        first_raw = parts[1].strip().split()[0] if parts[1].strip() else ""
    else:
        words     = contact_pi_name.split()
        last_raw  = words[-1] if words else ""
        first_raw = words[0]  if len(words) > 1 else ""
    return _title_case(first_raw), _title_case(last_raw)


def _parse_name_to_parts(name: str) -> Tuple[str, str]:
    """
    Parse a natural-language name into (first, last).

    Handles:
      "Sarah Chen"       → ("Sarah", "Chen")
      "Dr. Sarah E. Chen" → ("Sarah", "Chen")
      "Chen, Sarah"      → ("Sarah", "Chen")
    """
    if not name:
        return "", ""

    clean = re.sub(
        r"\b(dr|prof|mr|mrs|ms|phd|md|dvm|jr|sr|ii|iii)\b\.?",
        "", name.lower(),
    )
    clean = re.sub(r"[^a-z\s,\-]", "", clean).strip()

    if "," in clean:
        parts = [p.strip() for p in clean.split(",", 1)]
        last  = parts[0]
        first = parts[1].split()[0] if parts[1].strip() else ""
    else:
        words = [w for w in clean.split() if w]
        if not words:
            return "", ""
        first = words[0]
        last  = words[-1] if len(words) > 1 else ""

    return first.capitalize(), last.capitalize()


def _extract_mechanism(project_num: str) -> str:
    """Extract the grant mechanism code from a project number like '1R01DK123456-01'."""
    if not project_num:
        return ""
    m = re.match(r"^\d?([A-Z]\d{2})", project_num.upper())
    return m.group(1) if m else ""


def _title_case(s: str) -> str:
    """Convert ALL CAPS institution/name to Title Case, preserving hyphens."""
    if not s:
        return ""
    return " ".join(
        "-".join(p.capitalize() for p in word.split("-"))
        for word in s.lower().split()
    )


def _parse_date(date_str: str) -> Optional[datetime]:
    """Parse NIH date string '2024-09-01T00:00:00' to datetime."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", ""))
    except (ValueError, AttributeError):
        return None


def _mentions_3d(text: str) -> bool:
    """Check if grant text mentions 3D/organoid/organ-on-chip models."""
    text_lower = text.lower()
    return any(
        kw in text_lower
        for kw in ["3d ", "3-d ", "organoid", "spheroid", "organ-on-chip",
                   "microphysiological", "new approach method"]
    )


def _deduplicate_by_pi(projects: List[Dict]) -> List[Dict]:
    """Keep only the highest-award grant per PI (last_name, first_initial)."""
    best: Dict[str, Dict] = {}
    for p in projects:
        key   = (p.get("pi_last", "").lower(), p.get("pi_first", "")[:1].lower())
        award = p.get("award_amount", 0) or 0
        if key not in best or award > (best[key].get("award_amount", 0) or 0):
            best[key] = p
    return list(best.values())


def _default_fiscal_years(years_back: int = 3) -> List[int]:
    """Return [current-years_back, …, current]."""
    current = datetime.now().year
    return list(range(current - years_back, current + 1))


__all__ = ["NIHReporterScraper", "_parse_nih_name"]
