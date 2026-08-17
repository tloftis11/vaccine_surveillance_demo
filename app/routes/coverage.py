from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy import distinct, select
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import CoverageRate

router = APIRouter(prefix="/api/coverage", tags=["coverage"])

HP2030 = {"MMR":95.0,"DTaP":90.0,"VAR":90.0,"HepB":90.0,"PCV":90.0,
           "Hib":90.0,"Flu":70.0,"HPV":80.0,"MenACWY":80.0,"Tdap":80.0}

@router.get("/national")
def get_national(vaccine: str = "MMR", year: int = 2023, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = db.execute(select(CoverageRate).where(
        CoverageRate.vaccine_code == vaccine, CoverageRate.year == year,
        CoverageRate.state_abbr == "US", CoverageRate.demographic_category == "overall",
    )).scalar_one_or_none()
    states = db.execute(select(CoverageRate).where(
        CoverageRate.vaccine_code == vaccine, CoverageRate.year == year,
        CoverageRate.state_abbr != "US", CoverageRate.demographic_category == "overall",
    )).scalars().all()
    target = HP2030.get(vaccine)
    below = sum(1 for s in states if s.coverage_rate is not None and float(s.coverage_rate) < target) if target else 0
    return {
        "vaccine": vaccine, "year": year,
        "national_rate": float(row.coverage_rate) if row and row.coverage_rate is not None else None,
        "ci_lower": float(row.ci_lower) if row and row.ci_lower is not None else None,
        "ci_upper": float(row.ci_upper) if row and row.ci_upper is not None else None,
        "hp2030_target": target,
        "states_below_target": below,
        "total_states_with_data": len(states),
    }

@router.get("/states")
def get_states(vaccine: str = "MMR", year: int = 2023, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.execute(select(CoverageRate).where(
        CoverageRate.vaccine_code == vaccine, CoverageRate.year == year,
        CoverageRate.state_abbr != "US", CoverageRate.demographic_category == "overall",
    ).order_by(CoverageRate.state_abbr)).scalars().all()
    return [{"state_abbr": r.state_abbr, "state_fips": r.state_fips,
             "coverage_rate": float(r.coverage_rate) if r.coverage_rate is not None else None,
             "ci_lower": float(r.ci_lower) if r.ci_lower is not None else None,
             "ci_upper": float(r.ci_upper) if r.ci_upper is not None else None} for r in rows]

@router.get("/trend")
def get_trend(vaccine: str = "MMR", state: str = "US", db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.execute(select(CoverageRate).where(
        CoverageRate.vaccine_code == vaccine, CoverageRate.state_abbr == state,
        CoverageRate.demographic_category == "overall",
    ).order_by(CoverageRate.year)).scalars().all()
    return [{"year": r.year,
             "coverage_rate": float(r.coverage_rate) if r.coverage_rate is not None else None,
             "ci_lower": float(r.ci_lower) if r.ci_lower is not None else None,
             "ci_upper": float(r.ci_upper) if r.ci_upper is not None else None} for r in rows]

@router.get("/demographics")
def get_demographics(vaccine: str = "MMR", year: int = 2023, category: str = "race_ethnicity",
                     db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.execute(select(CoverageRate).where(
        CoverageRate.vaccine_code == vaccine, CoverageRate.year == year,
        CoverageRate.demographic_category == category,
    ).order_by(CoverageRate.demographic_value)).scalars().all()
    return [{"demographic_value": r.demographic_value,
             "coverage_rate": float(r.coverage_rate) if r.coverage_rate is not None else None} for r in rows]

@router.get("/vaccines")
def get_vaccines(db: Session = Depends(get_db)) -> list[str]:
    return [r for r in db.execute(select(distinct(CoverageRate.vaccine_code)).order_by(CoverageRate.vaccine_code)).scalars().all() if r]

@router.get("/years")
def get_years(db: Session = Depends(get_db)) -> list[int]:
    return [r for r in db.execute(select(distinct(CoverageRate.year)).order_by(CoverageRate.year)).scalars().all() if r]
