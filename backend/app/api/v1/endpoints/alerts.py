"""Smart alert rules API."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.models.alert import AlertRule
from app.models.user import User
from app.schemas.alert import AlertRuleCreate, AlertRuleResponse, AlertRuleUpdate

router = APIRouter()


@router.get("", response_model=List[AlertRuleResponse], summary="List alert rules")
async def list_alert_rules(current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AlertRule).where(AlertRule.user_id == current_user.id).order_by(AlertRule.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=AlertRuleResponse, status_code=201, summary="Create alert rule")
async def create_alert_rule(payload: AlertRuleCreate, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    rule = AlertRule(user_id=current_user.id, **payload.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.get("/{rule_id}", response_model=AlertRuleResponse, summary="Get alert rule")
async def get_alert_rule(rule_id: UUID, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id, AlertRule.user_id == current_user.id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Alert rule not found")
    return rule


@router.patch("/{rule_id}", response_model=AlertRuleResponse, summary="Update alert rule")
async def update_alert_rule(rule_id: UUID, payload: AlertRuleUpdate, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id, AlertRule.user_id == current_user.id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Alert rule not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(rule, field, value)
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=204, summary="Delete alert rule")
async def delete_alert_rule(rule_id: UUID, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id, AlertRule.user_id == current_user.id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Alert rule not found")
    await db.delete(rule)
    await db.commit()


@router.post("/{rule_id}/test", response_model=dict, summary="Test alert rule")
async def test_alert_rule(rule_id: UUID, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id, AlertRule.user_id == current_user.id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Alert rule not found")
    from app.services.smart_alert_service import get_smart_alert_service
    fired = await get_smart_alert_service()._evaluate_rule(rule, current_user, db, {})
    return {"fired": fired, "message": "Alert triggered" if fired else "No matching conditions"}
