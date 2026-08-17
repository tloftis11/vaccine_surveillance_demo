from __future__ import annotations
from statistics import mean
from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import CoverageRate

router = APIRouter(prefix="/api/coverage", tags=["coverage"])

HP2030 = {"MMR":95.0,"DTaP":90.0,"VAR":90.0,"HepB":90.0,"PCV":90.0,
           "Hib":90.0,"Flu":70.0,"HPV":80.0,"MenACWY":80.0,"Tdap":80.0}

@router.get("/national")
def get_national(vaccine: str = "MMR", year: int = 2023, db: Session = Depends(get_db)) -> dict[str, Any]:
    # Try exact US national row first (may have duplicates from NIS-Child + NIS-Teen)
    us_rows = db.execute(select(CoverageRate).where(
        CoverageRate.vaccine_code == vaccine, CoverageRate.year == year,
        CoverageRate.state_abbr == "US", CoverageRate.demographic_category == "overall",
    )).scalars().all()

    states = db.execute(select(CoverageRate).where(
        CoverageRate.vaccine_code == vaccine, CoverageRate.year == year,
        CoverageRate.state_abbr != "US", CoverageRate.demographic_category == "overall",
    )).scalars().all()

    target = HP2030.get(vaccine)

    # Compute national rate: prefer US row; fall back to mean of state rows
    national_rate = ci_lower = ci_upper = None
    if us_rows:
        rates = [float(r.coverage_rate) for r in us_rows if r.coverage_rate is not None]
        lowers = [float(r.ci_lower) for r in us_rows if r.ci_lower is not None]
        uppers = [float(r.ci_upper) for r in us_rows if r.ci_upper is not None]
        national_rate = round(mean(rates), 1) if rates else None
        ci_lower = round(mean(lowers), 1) if lowers else None
        ci_upper = round(mean(uppers), 1) if uppers else None
    elif states:
        rates = [float(s.coverage_rate) for s in states if s.coverage_rate is not None]
        national_rate = round(mean(rates), 1) if rates else None

    # Deduplicate states by state_abbr (take highest coverage_rate when multiple rows)
    seen: dict[str, float] = {}
    for s in states:
        if s.coverage_rate is not None:
            v = float(s.coverage_rate)
            if s.state_abbr not in seen or v > seen[s.state_abbr]:
                seen[s.state_abbr] = v
    unique_states = list(seen.values())

    below = sum(1 for v in unique_states if target and v < target)
    return {
        "vaccine": vaccine, "year": year,
        "national_rate": national_rate,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "hp2030_target": target,
        "states_below_target": below,
        "total_states_with_data": len(unique_states),
    }

@router.get("/states")
def get_states(vaccine: str = "MMR", year: int = 2023, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.execute(select(CoverageRate).where(
        CoverageRate.vaccine_code == vaccine, CoverageRate.year == year,
        CoverageRate.state_abbr != "US", CoverageRate.demographic_category == "overall",
    ).order_by(CoverageRate.state_abbr)).scalars().all()
    # Deduplicate by state_abbr (keep highest coverage when NIS-Child+NIS-Teen both report)
    seen: dict[str, dict] = {}
    for r in rows:
        key = r.state_abbr
        rate = float(r.coverage_rate) if r.coverage_rate is not None else None
        if key not in seen or (rate is not None and (seen[key]["coverage_rate"] or 0) < rate):
            seen[key] = {
                "state_abbr": r.state_abbr, "state_fips": r.state_fips,
                "coverage_rate": rate,
                "ci_lower": float(r.ci_lower) if r.ci_lower is not None else None,
                "ci_upper": float(r.ci_upper) if r.ci_upper is not None else None,
            }
    return sorted(seen.values(), key=lambda x: x["state_abbr"])

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
