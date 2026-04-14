"""Dashboard stats endpoint used by the frontend dashboard page."""

import json
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.deps import get_optional_user
from app.core.deps import get_current_active_user, get_db, get_optional_user
from app.models.researcher import Researcher
from app.models.user import User

router = APIRouter()

@router.get('/stats', summary='Get dashboard summary statistics')
async def get_dashboard_stats(
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    accessible_researchers = True

    total = await db.scalar(select(func.count(Researcher.id)).where(accessible_researchers))
    high = await db.scalar(
        select(func.count(Researcher.id)).where(
            accessible_researchers,
            Researcher.relevance_tier == 'HIGH',
        )
    )

    area_rows = await db.execute(
        select(Researcher.research_area, func.count(Researcher.id))
        .where(accessible_researchers, Researcher.research_area.isnot(None))
        .group_by(Researcher.research_area)
    )
    area_breakdown = [{'area': row[0], 'count': row[1]} for row in area_rows.fetchall()]

    eval_path = Path(__file__).parents[4] / 'ml' / 'reports' / 'eval_v1.json'
    model_meta: dict = {}
    if eval_path.exists():
        with eval_path.open() as f:
            model_meta = json.load(f)

    return {
        'total_researchers': int(total or 0),
        'high_relevance': int(high or 0),
        'research_areas_covered': len(area_breakdown),
        'queries_today': 0,
        'area_breakdown': area_breakdown,
        'model_version': model_meta.get('model_type', 'XGBoost v1'),
        'model_trained_at': model_meta.get('trained_at'),
        'n_training_samples': model_meta.get('n_training_samples'),
        'macro_f1': model_meta.get('macro_f1'),
    }
