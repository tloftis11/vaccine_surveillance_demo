from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db import Base


class VaersReport(Base):
    __tablename__ = "vaers_reports"

    vaers_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    received_date: Mapped[date | None] = mapped_column()
    state_abbr: Mapped[str | None] = mapped_column(String(2))
    age_years: Mapped[float | None] = mapped_column(Numeric(5, 1))
    sex: Mapped[str | None] = mapped_column(String(1))
    died: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    life_threatening: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hospitalized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hospital_days: Mapped[int | None] = mapped_column(Integer)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recovered: Mapped[bool | None] = mapped_column(Boolean)
    vax_date: Mapped[date | None] = mapped_column()
    onset_date: Mapped[date | None] = mapped_column()
    onset_days: Mapped[int | None] = mapped_column(Integer)
    serious: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    data_year: Mapped[int | None] = mapped_column(Integer)
    loaded_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    vaccines: Mapped[list[VaersVaccine]] = relationship(
        "VaersVaccine", back_populates="report", cascade="all, delete-orphan"
    )
    symptoms: Mapped[list[VaersSymptom]] = relationship(
        "VaersSymptom", back_populates="report", cascade="all, delete-orphan"
    )


class VaersVaccine(Base):
    __tablename__ = "vaers_vaccines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vaers_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vaers_reports.vaers_id"), nullable=False
    )
    vax_type: Mapped[str | None] = mapped_column(String(50))
    vax_manufacturer: Mapped[str | None] = mapped_column(String(100))
    vax_dose_series: Mapped[str | None] = mapped_column(String(20))
    vax_route: Mapped[str | None] = mapped_column(String(20))
    vax_site: Mapped[str | None] = mapped_column(String(30))

    report: Mapped[VaersReport] = relationship("VaersReport", back_populates="vaccines")


class VaersSymptom(Base):
    __tablename__ = "vaers_symptoms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vaers_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vaers_reports.vaers_id"), nullable=False
    )
    symptom: Mapped[str | None] = mapped_column(String(200))
    meddra_version: Mapped[str | None] = mapped_column(String(20))

    report: Mapped[VaersReport] = relationship("VaersReport", back_populates="symptoms")


class AeSummary(Base):
    __tablename__ = "ae_summary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data_year: Mapped[int | None] = mapped_column(Integer)
    vax_type: Mapped[str | None] = mapped_column(String(50))
    symptom: Mapped[str | None] = mapped_column(String(200))
    report_count: Mapped[int | None] = mapped_column(Integer)
    serious_count: Mapped[int | None] = mapped_column(Integer)
    prr: Mapped[float | None] = mapped_column(Numeric(8, 4))
    chi_squared: Mapped[float | None] = mapped_column(Numeric(8, 4))
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
