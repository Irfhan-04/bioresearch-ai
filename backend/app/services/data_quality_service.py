"""Data Quality Service — Phase 2.3 Step 6."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.models.lead import Lead

logger = logging.getLogger(__name__)

_MIN_COMPLETENESS_TO_SAVE = 0.25
_MIN_SCORE_TO_SAVE = 5
_MIN_NAME_LENGTH = 3

_LINKEDIN_URL_RE = re.compile(r"^https?://(www\.)?linkedin\.com/in/[a-zA-Z0-9\-_%]+/?$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class LeadQualityResult:
    passes: bool
    completeness: float
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    field_scores: Dict[str, bool] = field(default_factory=dict)


@dataclass
class PipelineQualityReport:
    total_candidates: int
    passed: int
    rejected: int
    rejection_reasons: Dict[str, int] = field(default_factory=dict)
    avg_completeness: float = 0.0


class DataQualityService:
    """Validates leads before database insertion."""

    _KEY_FIELDS = (
        "name",
        "title",
        "company",
        "email",
        "linkedin_url",
        "location",
        "propensity_score",
    )

    def validate_lead(self, lead: Dict[str, Any]) -> LeadQualityResult:
        issues: List[str] = []
        warnings: List[str] = []
        field_scores: Dict[str, bool] = {}

        name = (lead.get("name") or "").strip()
        if not name or len(name) < _MIN_NAME_LENGTH:
            issues.append("missing_or_invalid_name")
            field_scores["name"] = False
        else:
            field_scores["name"] = True

        score = lead.get("propensity_score") or 0
        try:
            score = int(score)
        except (TypeError, ValueError):
            score = 0

        if score < _MIN_SCORE_TO_SAVE:
            issues.append(f"score_too_low:{score}")
            field_scores["propensity_score"] = False
        elif score > 100:
            warnings.append(f"score_exceeds_100:{score}")
            field_scores["propensity_score"] = True
        else:
            field_scores["propensity_score"] = True

        email = (lead.get("email") or "").strip()
        if email:
            if not _EMAIL_RE.match(email):
                issues.append(f"invalid_email_format:{email[:30]}")
                field_scores["email"] = False
            else:
                field_scores["email"] = True
        else:
            field_scores["email"] = False

        linkedin = (lead.get("linkedin_url") or "").strip()
        if linkedin:
            if not _LINKEDIN_URL_RE.match(linkedin):
                warnings.append(f"suspicious_linkedin_url:{linkedin[:60]}")
                field_scores["linkedin_url"] = False
            else:
                field_scores["linkedin_url"] = True
        else:
            field_scores["linkedin_url"] = False

        company = (lead.get("company") or "").strip()
        field_scores["company"] = bool(company)
        if not company:
            warnings.append("missing_company")

        title = (lead.get("title") or "").strip()
        field_scores["title"] = bool(title)

        location = (lead.get("location") or "").strip()
        field_scores["location"] = bool(location)

        present = sum(1 for value in field_scores.values() if value)
        completeness = present / len(self._KEY_FIELDS)

        if completeness < _MIN_COMPLETENESS_TO_SAVE:
            issues.append(f"completeness_too_low:{completeness:.0%}")

        return LeadQualityResult(
            passes=not issues,
            completeness=completeness,
            issues=issues,
            warnings=warnings,
            field_scores=field_scores,
        )

    def validate_batch(
        self,
        leads: List[Dict[str, Any]],
        deduplicate: bool = True,
    ) -> Tuple[List[Dict[str, Any]], PipelineQualityReport]:
        seen_names = set()
        passing: List[Dict[str, Any]] = []
        rejection_counts: Dict[str, int] = {}
        completeness_sum = 0.0

        for lead in leads:
            norm_name = _normalise_name(lead.get("name") or "")
            if deduplicate and norm_name and norm_name in seen_names:
                _increment(rejection_counts, "duplicate_name")
                continue

            result = self.validate_lead(lead)
            completeness_sum += result.completeness

            if result.passes:
                passing.append(lead)
                if norm_name:
                    seen_names.add(norm_name)
            else:
                for issue in result.issues:
                    _increment(rejection_counts, issue.split(":")[0])

        total = len(leads)
        passed = len(passing)
        report = PipelineQualityReport(
            total_candidates=total,
            passed=passed,
            rejected=total - passed,
            rejection_reasons=rejection_counts,
            avg_completeness=round((completeness_sum / total) if total else 0.0, 3),
        )

        logger.info(
            "DataQuality: %d/%d leads passed (%.0f%% completeness avg)",
            passed,
            total,
            (completeness_sum / total) * 100 if total else 0,
        )
        return passing, report

    def check_existing_lead(self, lead: Lead) -> LeadQualityResult:
        lead_dict = {
            "name": lead.name,
            "title": lead.title,
            "company": lead.company,
            "email": lead.email,
            "linkedin_url": lead.linkedin_url,
            "location": lead.location,
            "propensity_score": lead.propensity_score,
        }
        return self.validate_lead(lead_dict)


def _normalise_name(name: str) -> str:
    name = name.lower()
    for prefix in ("dr.", "dr ", "prof.", "prof ", "mr.", "mrs.", "ms."):
        if name.startswith(prefix):
            name = name[len(prefix) :]
    return re.sub(r"\s+", " ", name).strip()


def _increment(values: Dict[str, int], key: str) -> None:
    values[key] = values.get(key, 0) + 1


_dq_service: Optional[DataQualityService] = None


def get_data_quality_service() -> DataQualityService:
    global _dq_service
    if _dq_service is None:
        _dq_service = DataQualityService()
    return _dq_service


__all__ = [
    "DataQualityService",
    "LeadQualityResult",
    "PipelineQualityReport",
    "get_data_quality_service",
]
