from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy import distinct, select
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import AdherenceRate

router = APIRouter(prefix="/api/adherence", tags=["adherence"])

@router.get("/series")
def get_series(series: str = "DTaP", year: int = 2023, state: str = "US",
               db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.execute(select(AdherenceRate).where(
        AdherenceRate.vaccine_series == series, AdherenceRate.year == year,
        AdherenceRate.state_abbr == state, AdherenceRate.demographic_category == "overall",
    ).order_by(AdherenceRate.dose_number)).scalars().all()
    return [{"dose_number": r.dose_number,
             "completion_rate": float(r.completion_rate) if r.completion_rate is not None else None,
             "on_time_rate": float(r.on_time_rate) if r.on_time_rate is not None else None} for r in rows]

@router.get("/demographics")
def get_demographics(series: str = "DTaP", year: int = 2023, category: str = "insurance_type",
                     db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.execute(select(AdherenceRate).where(
        AdherenceRate.vaccine_series == series, AdherenceRate.year == year,
        AdherenceRate.demographic_category == category,
    ).order_by(AdherenceRate.demographic_value)).scalars().all()
    return [{"demographic_value": r.demographic_value,
             "completion_rate": float(r.completion_rate) if r.completion_rate is not None else None,
             "on_time_rate": float(r.on_time_rate) if r.on_time_rate is not None else None} for r in rows]

@router.get("/series-list")
def get_series_list(db: Session = Depends(get_db)) -> list[str]:
    return [r for r in db.execute(select(distinct(AdherenceRate.vaccine_series)).order_by(AdherenceRate.vaccine_series)).scalars().all() if r]

@router.get("/years")
def get_years(db: Session = Depends(get_db)) -> list[int]:
    return [r for r in db.execute(select(distinct(AdherenceRate.year)).order_by(AdherenceRate.year)).scalars().all() if r]
