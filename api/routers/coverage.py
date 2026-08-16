from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from db import get_db
from models.coverage import CoverageRate

router = APIRouter(prefix="/coverage", tags=["coverage"])

HP2030_TARGETS: dict[str, float] = {
    "MMR": 95.0,
    "DTaP": 90.0,
    "VAR": 90.0,
    "HepB": 90.0,
    "PCV": 90.0,
    "Hib": 90.0,
    "Flu": 70.0,
    "HPV": 80.0,
}


@router.get("/national")
def get_national(
    vaccine: str = "MMR",
    year: int = 2023,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    national_row = db.execute(
        select(CoverageRate).where(
            CoverageRate.vaccine_code == vaccine,
            CoverageRate.year == year,
            CoverageRate.state_abbr == "US",
            CoverageRate.demographic_category == "overall",
        )
    ).scalar_one_or_none()

    hp2030_target = HP2030_TARGETS.get(vaccine)

    states_result = db.execute(
        select(CoverageRate).where(
            CoverageRate.vaccine_code == vaccine,
            CoverageRate.year == year,
            CoverageRate.state_abbr != "US",
            CoverageRate.demographic_category == "overall",
        )
    ).scalars().all()

    total_states = len(states_result)
    states_below = 0
    if hp2030_target is not None:
        states_below = sum(
            1
            for r in states_result
            if r.coverage_rate is not None and float(r.coverage_rate) < hp2030_target
        )

    return {
        "vaccine": vaccine,
        "year": year,
        "national_rate": float(national_row.coverage_rate) if national_row and national_row.coverage_rate is not None else None,
        "ci_lower": float(national_row.ci_lower) if national_row and national_row.ci_lower is not None else None,
        "ci_upper": float(national_row.ci_upper) if national_row and national_row.ci_upper is not None else None,
        "hp2030_target": hp2030_target,
        "states_below_target": states_below,
        "total_states_with_data": total_states,
    }


@router.get("/states")
def get_states(
    vaccine: str = "MMR",
    year: int = 2023,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = db.execute(
        select(CoverageRate).where(
            CoverageRate.vaccine_code == vaccine,
            CoverageRate.year == year,
            CoverageRate.state_abbr != "US",
            CoverageRate.demographic_category == "overall",
        ).order_by(CoverageRate.state_abbr)
    ).scalars().all()

    return [
        {
            "state_abbr": r.state_abbr,
            "state_fips": r.state_fips,
            "coverage_rate": float(r.coverage_rate) if r.coverage_rate is not None else None,
            "ci_lower": float(r.ci_lower) if r.ci_lower is not None else None,
            "ci_upper": float(r.ci_upper) if r.ci_upper is not None else None,
        }
        for r in rows
    ]


@router.get("/trend")
def get_trend(
    vaccine: str = "MMR",
    state: str = "US",
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = db.execute(
        select(CoverageRate).where(
            CoverageRate.vaccine_code == vaccine,
            CoverageRate.state_abbr == state,
            CoverageRate.demographic_category == "overall",
        ).order_by(CoverageRate.year)
    ).scalars().all()

    return [
        {
            "year": r.year,
            "coverage_rate": float(r.coverage_rate) if r.coverage_rate is not None else None,
            "ci_lower": float(r.ci_lower) if r.ci_lower is not None else None,
            "ci_upper": float(r.ci_upper) if r.ci_upper is not None else None,
        }
        for r in rows
    ]


@router.get("/demographics")
def get_demographics(
    vaccine: str = "MMR",
    year: int = 2023,
    category: str = "race_ethnicity",
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = db.execute(
        select(CoverageRate).where(
            CoverageRate.vaccine_code == vaccine,
            CoverageRate.year == year,
            CoverageRate.demographic_category == category,
        ).order_by(CoverageRate.demographic_value)
    ).scalars().all()

    return [
        {
            "demographic_value": r.demographic_value,
            "coverage_rate": float(r.coverage_rate) if r.coverage_rate is not None else None,
            "ci_lower": float(r.ci_lower) if r.ci_lower is not None else None,
            "ci_upper": float(r.ci_upper) if r.ci_upper is not None else None,
        }
        for r in rows
    ]


@router.get("/vaccines")
def get_vaccines(db: Session = Depends(get_db)) -> list[str]:
    rows = db.execute(
        select(distinct(CoverageRate.vaccine_code)).order_by(CoverageRate.vaccine_code)
    ).scalars().all()
    return [r for r in rows if r is not None]


@router.get("/years")
def get_years(db: Session = Depends(get_db)) -> list[int]:
    rows = db.execute(
        select(distinct(CoverageRate.year)).order_by(CoverageRate.year)
    ).scalars().all()
    return [r for r in rows if r is not None]
