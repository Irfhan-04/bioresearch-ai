"""Smart alert evaluation service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import AlertChannel, AlertRule, AlertTrigger
from app.models.lead import Lead
from app.models.user import User
from app.services.email_service import get_email_service
from app.services.webhook_service import get_webhook_service

_DEFAULT_HIGH_VALUE_THRESHOLD = 70
_DEFAULT_SCORE_DELTA = 15


class SmartAlertService:
    def __init__(self):
        self._email_svc = get_email_service()
        self._webhook_svc = get_webhook_service()

    async def evaluate_all_rules(
        self,
        user: User,
        db: AsyncSession,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, int]:
        result = await db.execute(
            select(AlertRule).where(AlertRule.user_id == user.id, AlertRule.is_active == True)
        )
        rules = result.scalars().all()
        stats = {"rules_evaluated": 0, "alerts_fired": 0, "alerts_throttled": 0}

        for rule in rules:
            stats["rules_evaluated"] += 1
            if rule.is_throttled():
                stats["alerts_throttled"] += 1
                continue
            fired = await self._evaluate_rule(rule, user, db, context or {})
            if fired:
                stats["alerts_fired"] += 1
                rule.last_triggered_at = datetime.now(timezone.utc)
                rule.trigger_count += 1
                db.add(rule)

        await db.commit()
        return stats

    async def _evaluate_rule(self, rule: AlertRule, user: User, db: AsyncSession, context: Dict[str, Any]) -> bool:
        if rule.trigger == AlertTrigger.HIGH_VALUE_LEAD:
            return await self._check_high_value_leads(rule, user, db, context)
        if rule.trigger == AlertTrigger.NEW_NIH_GRANT:
            return await self._check_nih_grant_alerts(rule, user, db, context)
        if rule.trigger == AlertTrigger.CONFERENCE_MATCH:
            return await self._check_conference_match(rule, user, db, context)
        if rule.trigger == AlertTrigger.SCORE_INCREASE:
            return await self._check_score_increase(rule, user, db, context)
        return False

    async def _check_high_value_leads(self, rule: AlertRule, user: User, db: AsyncSession, context: Dict[str, Any]) -> bool:
        from datetime import timedelta

        min_score = rule.conditions.get("min_score", _DEFAULT_HIGH_VALUE_THRESHOLD)
        sources = rule.conditions.get("sources", [])
        since = datetime.now(timezone.utc) - timedelta(hours=rule.conditions.get("lookback_hours", 24))
        result = await db.execute(
            select(Lead).where(Lead.user_id == user.id, Lead.propensity_score >= min_score, Lead.created_at >= since)
        )
        leads = result.scalars().all()
        if sources:
            leads = [lead for lead in leads if any(source in (lead.data_sources or []) for source in sources)]
        if not leads:
            return False
        top = max(leads, key=lambda lead: lead.propensity_score or 0)
        await self._fire_alert(
            rule=rule,
            user=user,
            db=db,
            lead_id=str(top.id),
            lead_name=top.name,
            lead_company=top.company or "Unknown",
            score=top.propensity_score or 0,
            trigger_reason=self._build_trigger_reason(top),
        )
        return True

    async def _check_nih_grant_alerts(self, rule: AlertRule, user: User, db: AsyncSession, context: Dict[str, Any]) -> bool:
        from datetime import timedelta

        keywords = rule.conditions.get("keywords", [])
        since = datetime.now(timezone.utc) - timedelta(hours=rule.conditions.get("lookback_hours", 24))
        result = await db.execute(select(Lead).where(Lead.user_id == user.id, Lead.created_at >= since))
        leads = result.scalars().all()
        matching = []
        for lead in leads:
            nih = (lead.enrichment_data or {}).get("nih_grants", {})
            if not nih.get("active_grants", 0):
                continue
            if keywords:
                grant_text = " ".join(
                    f"{grant.get('terms', '')} {grant.get('project_title', '')}" for grant in nih.get("grants", [])
                ).lower()
                if not any(keyword.lower() in grant_text for keyword in keywords):
                    continue
            matching.append(lead)
        if not matching:
            return False
        top = max(matching, key=lambda lead: lead.propensity_score or 0)
        await self._fire_alert(
            rule=rule,
            user=user,
            db=db,
            lead_id=str(top.id),
            lead_name=top.name,
            lead_company=top.company or "Unknown",
            score=top.propensity_score or 0,
            trigger_reason=(
                f"Active NIH grant matching keywords: {', '.join(keywords[:3])}" if keywords else "Active NIH grant found"
            ),
        )
        return True

    async def _check_conference_match(self, rule: AlertRule, user: User, db: AsyncSession, context: Dict[str, Any]) -> bool:
        from datetime import timedelta

        since = datetime.now(timezone.utc) - timedelta(hours=rule.conditions.get("lookback_hours", 48))
        result = await db.execute(select(Lead).where(Lead.user_id == user.id, Lead.created_at >= since))
        leads = [lead for lead in result.scalars().all() if "conference" in (lead.data_sources or [])]
        if not leads:
            return False
        top = max(leads, key=lambda lead: lead.propensity_score or 0)
        conference_name = (top.enrichment_data or {}).get("conference", {}).get("conference_name", "Conference")
        await self._fire_alert(
            rule=rule,
            user=user,
            db=db,
            lead_id=str(top.id),
            lead_name=top.name,
            lead_company=top.company or "Unknown",
            score=top.propensity_score or 0,
            trigger_reason=f"Speaker at {conference_name}",
        )
        return True

    async def _check_score_increase(self, rule: AlertRule, user: User, db: AsyncSession, context: Dict[str, Any]) -> bool:
        min_delta = rule.conditions.get("min_delta", _DEFAULT_SCORE_DELTA)
        result = await db.execute(select(Lead).where(Lead.user_id == user.id))
        for lead in result.scalars().all():
            history = (lead.enrichment_data or {}).get("score_history", [])
            if len(history) < 2:
                continue
            prev = history[-2].get("score", 0)
            curr = history[-1].get("score", 0)
            delta = curr - prev
            if delta >= min_delta:
                await self._fire_alert(
                    rule=rule,
                    user=user,
                    db=db,
                    lead_id=str(lead.id),
                    lead_name=lead.name,
                    lead_company=lead.company or "Unknown",
                    score=curr,
                    trigger_reason=f"Score increased by {delta} points ({prev} → {curr})",
                )
                return True
        return False

    async def _fire_alert(
        self,
        rule: AlertRule,
        user: User,
        db: AsyncSession,
        lead_id: str,
        lead_name: str,
        lead_company: str,
        score: int,
        trigger_reason: str,
    ) -> None:
        if rule.channel in (AlertChannel.EMAIL, AlertChannel.BOTH) and user.email:
            await self._email_svc.send_high_value_lead_alert(
                to_email=user.email,
                user_name=user.full_name or user.email.split("@")[0],
                lead_name=lead_name,
                lead_company=lead_company,
                lead_score=score,
                lead_id=lead_id,
                trigger_reason=trigger_reason,
            )
        if rule.channel in (AlertChannel.WEBHOOK, AlertChannel.BOTH):
            await self._webhook_svc.notify_high_value_lead(
                user_id=str(user.id),
                lead_id=lead_id,
                lead_name=lead_name,
                lead_company=lead_company,
                score=score,
                trigger_reason=trigger_reason,
                db=db,
            )

    @staticmethod
    def _build_trigger_reason(lead: Lead) -> str:
        reasons = []
        nih = (lead.enrichment_data or {}).get("nih_grants", {})
        if nih.get("active_grants", 0):
            max_award = nih.get("max_award", 0)
            reasons.append(f"Active NIH grant (${max_award:,.0f}/yr)" if max_award else "Active NIH grant")
        if lead.recent_publication:
            pub_count = lead.publication_count or 0
            h_index = (lead.enrichment_data or {}).get("pubmed", {}).get("h_index_approx", 0)
            reasons.append(f"{pub_count} publications (h-index {h_index})" if h_index else f"{pub_count} publications")
        if "conference" in (lead.data_sources or []):
            reasons.append("Conference speaker")
        if not reasons:
            reasons.append(f"Score {lead.propensity_score}")
        return " · ".join(reasons)


_smart_alert_service: Optional[SmartAlertService] = None


def get_smart_alert_service() -> SmartAlertService:
    global _smart_alert_service
    if _smart_alert_service is None:
        _smart_alert_service = SmartAlertService()
    return _smart_alert_service


__all__ = ["SmartAlertService", "get_smart_alert_service"]
