from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import Integer, distinct, func, select
from sqlalchemy.orm import Session

from db import get_db
from models.adverse_events import AeSummary, VaersReport, VaersVaccine

router = APIRouter(prefix="/adverse-events", tags=["adverse-events"])

DOSES_ADMINISTERED: dict[str, int] = {
    "FLU": 170_000_000,
    "COVID19": 270_000_000,
    "COVID": 270_000_000,
    "MMR": 8_000_000,
    "HPV": 14_000_000,
}
DEFAULT_DOSES = 10_000_000


def _doses_for(vax_type: str) -> int:
    return DOSES_ADMINISTERED.get(vax_type.upper(), DEFAULT_DOSES)


@router.get("/summary")
def get_summary(
    vax_type: str = "FLU",
    year: int = 2023,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    agg = db.execute(
        select(
            func.sum(AeSummary.report_count).label("total_reports"),
            func.sum(AeSummary.serious_count).label("serious_count"),
        ).where(
            AeSummary.vax_type == vax_type,
            AeSummary.data_year == year,
        )
    ).one()

    total_reports: int = int(agg.total_reports) if agg.total_reports else 0
    serious_count: int = int(agg.serious_count) if agg.serious_count else 0
    serious_pct = round(serious_count / total_reports * 100, 1) if total_reports > 0 else None

    doses = _doses_for(vax_type)
    rate_per_million = round(total_reports / doses * 1_000_000, 2) if total_reports > 0 else None

    top_signal_row = db.execute(
        select(AeSummary).where(
            AeSummary.vax_type == vax_type,
            AeSummary.data_year == year,
            AeSummary.prr > 2,
            AeSummary.chi_squared > 4,
        ).order_by(AeSummary.prr.desc()).limit(1)
    ).scalar_one_or_none()

    top_signal = None
    if top_signal_row:
        top_signal = {
            "symptom": top_signal_row.symptom,
            "prr": float(top_signal_row.prr) if top_signal_row.prr is not None else None,
            "chi_squared": float(top_signal_row.chi_squared) if top_signal_row.chi_squared is not None else None,
        }

    return {
        "vax_type": vax_type,
        "year": year,
        "total_reports": total_reports,
        "serious_count": serious_count,
        "serious_pct": serious_pct,
        "rate_per_million_doses": rate_per_million,
        "top_signal": top_signal,
    }


@router.get("/events")
def get_events(
    vax_type: str = "FLU",
    year: int = 2023,
    severity: str = "all",
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    stmt = select(AeSummary).where(
        AeSummary.vax_type == vax_type,
        AeSummary.data_year == year,
    )

    if severity == "serious":
        stmt = stmt.where(AeSummary.serious_count > 0)
    elif severity == "non-serious":
        stmt = stmt.where(
            (AeSummary.serious_count == 0) | (AeSummary.serious_count.is_(None))
        )

    stmt = stmt.order_by(AeSummary.report_count.desc()).limit(limit)
    rows = db.execute(stmt).scalars().all()

    doses = _doses_for(vax_type)

    return [
        {
            "symptom": r.symptom,
            "report_count": r.report_count,
            "serious_count": r.serious_count,
            "rate_per_million": round(int(r.report_count) / doses * 1_000_000, 2) if r.report_count else None,
            "prr": float(r.prr) if r.prr is not None else None,
            "chi_squared": float(r.chi_squared) if r.chi_squared is not None else None,
            "signal_flag": bool(
                r.prr is not None
                and r.chi_squared is not None
                and float(r.prr) > 2
                and float(r.chi_squared) > 4
            ),
        }
        for r in rows
    ]


@router.get("/onset")
def get_onset(
    vax_type: str = "FLU",
    year: int = 2023,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    stmt = (
        select(
            VaersReport.onset_days.label("onset_day"),
            func.count(VaersReport.vaers_id).label("count"),
            func.sum(
                func.cast(VaersReport.serious, Integer)
            ).label("serious_count"),
        )
        .join(VaersVaccine, VaersVaccine.vaers_id == VaersReport.vaers_id)
        .where(
            VaersVaccine.vax_type == vax_type,
            VaersReport.data_year == year,
            VaersReport.onset_days >= 0,
            VaersReport.onset_days <= 30,
        )
        .group_by(VaersReport.onset_days)
        .order_by(VaersReport.onset_days)
    )

    rows = db.execute(stmt).all()

    # Build a full 0-30 day grid, filling missing days with zeros
    data: dict[int, dict[str, Any]] = {
        d: {"onset_day": d, "count": 0, "serious_count": 0} for d in range(31)
    }
    for row in rows:
        day = int(row.onset_day)
        if 0 <= day <= 30:
            data[day]["count"] = int(row.count)
            data[day]["serious_count"] = int(row.serious_count) if row.serious_count else 0

    return list(data.values())


@router.get("/vaccines")
def get_vaccines(db: Session = Depends(get_db)) -> list[str]:
    rows = db.execute(
        select(distinct(AeSummary.vax_type)).order_by(AeSummary.vax_type)
    ).scalars().all()
    return [r for r in rows if r is not None]


@router.get("/years")
def get_years(db: Session = Depends(get_db)) -> list[int]:
    rows = db.execute(
        select(distinct(AeSummary.data_year)).order_by(AeSummary.data_year)
    ).scalars().all()
    return [r for r in rows if r is not None]
