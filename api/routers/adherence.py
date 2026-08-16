from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import distinct, select
from sqlalchemy.orm import Session

from db import get_db
from models.adherence import AdherenceRate

router = APIRouter(prefix="/adherence", tags=["adherence"])

MAX_DOSES: dict[str, int] = {
    "DTaP": 5,
    "HepB": 3,
    "HPV": 2,
    "PCV": 4,
    "MMR": 2,
    "Varicella": 2,
    "Flu": 1,
}


@router.get("/series")
def get_series(
    series: str = "DTaP",
    year: int = 2023,
    state: str = "US",
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    max_dose = MAX_DOSES.get(series, 5)

    rows = db.execute(
        select(AdherenceRate).where(
            AdherenceRate.vaccine_series == series,
            AdherenceRate.year == year,
            AdherenceRate.state_abbr == state,
            AdherenceRate.demographic_category == "overall",
            AdherenceRate.dose_number <= max_dose,
        ).order_by(AdherenceRate.dose_number)
    ).scalars().all()

    return [
        {
            "dose_number": r.dose_number,
            "completion_rate": float(r.completion_rate) if r.completion_rate is not None else None,
            "on_time_rate": float(r.on_time_rate) if r.on_time_rate is not None else None,
        }
        for r in rows
    ]


@router.get("/demographics")
def get_demographics(
    series: str = "DTaP",
    year: int = 2023,
    category: str = "insurance_type",
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = db.execute(
        select(AdherenceRate).where(
            AdherenceRate.vaccine_series == series,
            AdherenceRate.year == year,
            AdherenceRate.demographic_category == category,
        ).order_by(AdherenceRate.demographic_value)
    ).scalars().all()

    return [
        {
            "demographic_value": r.demographic_value,
            "completion_rate": float(r.completion_rate) if r.completion_rate is not None else None,
            "on_time_rate": float(r.on_time_rate) if r.on_time_rate is not None else None,
        }
        for r in rows
    ]


@router.get("/series-list")
def get_series_list(db: Session = Depends(get_db)) -> list[str]:
    rows = db.execute(
        select(distinct(AdherenceRate.vaccine_series)).order_by(AdherenceRate.vaccine_series)
    ).scalars().all()
    return [r for r in rows if r is not None]


@router.get("/years")
def get_years(db: Session = Depends(get_db)) -> list[int]:
    rows = db.execute(
        select(distinct(AdherenceRate.year)).order_by(AdherenceRate.year)
    ).scalars().all()
    return [r for r in rows if r is not None]
