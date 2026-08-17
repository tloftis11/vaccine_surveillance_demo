from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

class CoverageRate(Base):
    __tablename__ = "coverage_rates"
    id:                 Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    state_abbr:         Mapped[str | None]    = mapped_column(String(2), index=True)
    state_fips:         Mapped[str | None]    = mapped_column(String(2))
    vaccine_code:       Mapped[str | None]    = mapped_column(String(20), index=True)
    year:               Mapped[int | None]    = mapped_column(Integer, index=True)
    demographic_category: Mapped[str | None]  = mapped_column(String(50))
    demographic_value:  Mapped[str | None]    = mapped_column(String(100))
    coverage_rate:      Mapped[float | None]  = mapped_column(Numeric(5, 2))
    ci_lower:           Mapped[float | None]  = mapped_column(Numeric(5, 2))
    ci_upper:           Mapped[float | None]  = mapped_column(Numeric(5, 2))
    sample_size:        Mapped[int | None]    = mapped_column(Integer)
    source:             Mapped[str | None]    = mapped_column(String(50))
    loaded_at:          Mapped[datetime]      = mapped_column(DateTime, default=datetime.utcnow)

class AeSummary(Base):
    __tablename__ = "ae_summary"
    id:             Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    data_year:      Mapped[int | None]    = mapped_column(Integer, index=True)
    vax_type:       Mapped[str | None]    = mapped_column(String(50), index=True)
    symptom:        Mapped[str | None]    = mapped_column(String(200))
    report_count:   Mapped[int | None]    = mapped_column(Integer)
    serious_count:  Mapped[int | None]    = mapped_column(Integer)
    prr:            Mapped[float | None]  = mapped_column(Numeric(8, 4))
    chi_squared:    Mapped[float | None]  = mapped_column(Numeric(8, 4))
    calculated_at:  Mapped[datetime]      = mapped_column(DateTime, default=datetime.utcnow)

class AdherenceRate(Base):
    __tablename__ = "adherence_rates"
    id:                  Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    vaccine_series:      Mapped[str | None]    = mapped_column(String(50), index=True)
    dose_number:         Mapped[int | None]    = mapped_column(Integer)
    year:                Mapped[int | None]    = mapped_column(Integer, index=True)
    state_abbr:          Mapped[str | None]    = mapped_column(String(2))
    demographic_category: Mapped[str | None]  = mapped_column(String(50))
    demographic_value:   Mapped[str | None]   = mapped_column(String(100))
    completion_rate:     Mapped[float | None]  = mapped_column(Numeric(5, 2))
    on_time_rate:        Mapped[float | None]  = mapped_column(Numeric(5, 2))
    source:              Mapped[str | None]    = mapped_column(String(50))
    loaded_at:           Mapped[datetime]      = mapped_column(DateTime, default=datetime.utcnow)
