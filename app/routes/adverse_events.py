from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import AeSummary

router = APIRouter(prefix="/api/adverse-events", tags=["adverse-events"])

DOSES = {"FLU":170_000_000,"COVID19":270_000_000,"MMR":8_000_000,"HPV":14_000_000}

@router.get("/summary")
def get_summary(vax_type: str = "FLU", year: int = 2023, db: Session = Depends(get_db)) -> dict[str, Any]:
    agg = db.execute(select(
        func.sum(AeSummary.report_count).label("total"),
        func.sum(AeSummary.serious_count).label("serious"),
    ).where(AeSummary.vax_type == vax_type, AeSummary.data_year == year)).one()
    total = int(agg.total) if agg.total else 0
    serious = int(agg.serious) if agg.serious else 0
    doses = DOSES.get(vax_type.upper(), 10_000_000)
    top = db.execute(select(AeSummary).where(
        AeSummary.vax_type == vax_type, AeSummary.data_year == year,
        AeSummary.prr > 2, AeSummary.chi_squared > 4,
    ).order_by(AeSummary.prr.desc()).limit(1)).scalar_one_or_none()
    return {
        "vax_type": vax_type, "year": year,
        "total_reports": total,
        "serious_count": serious,
        "serious_pct": round(serious / total * 100, 1) if total else None,
        "rate_per_million_doses": round(total / doses * 1_000_000, 2) if total else None,
        "top_signal": {"symptom": top.symptom, "prr": float(top.prr), "chi_squared": float(top.chi_squared)} if top else None,
    }

@router.get("/events")
def get_events(vax_type: str = "FLU", year: int = 2023, severity: str = "all",
               limit: int = 50, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    stmt = select(AeSummary).where(AeSummary.vax_type == vax_type, AeSummary.data_year == year)
    if severity == "serious":
        stmt = stmt.where(AeSummary.serious_count > 0)
    rows = db.execute(stmt.order_by(AeSummary.report_count.desc()).limit(limit)).scalars().all()
    doses = DOSES.get(vax_type.upper(), 10_000_000)
    return [{
        "symptom": r.symptom,
        "report_count": r.report_count,
        "serious_count": r.serious_count,
        "rate_per_million": round(int(r.report_count) / doses * 1_000_000, 2) if r.report_count else None,
        "prr": float(r.prr) if r.prr is not None else None,
        "chi_squared": float(r.chi_squared) if r.chi_squared is not None else None,
        "signal_flag": bool(r.prr and r.chi_squared and float(r.prr) > 2 and float(r.chi_squared) > 4),
    } for r in rows]

@router.get("/vaccines")
def get_vaccines(db: Session = Depends(get_db)) -> list[str]:
    return [r for r in db.execute(select(distinct(AeSummary.vax_type)).order_by(AeSummary.vax_type)).scalars().all() if r]

@router.get("/years")
def get_years(db: Session = Depends(get_db)) -> list[int]:
    return [r for r in db.execute(select(distinct(AeSummary.data_year)).order_by(AeSummary.data_year)).scalars().all() if r]
