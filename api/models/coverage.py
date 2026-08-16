from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base


class CoverageRate(Base):
    __tablename__ = "coverage_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    state_abbr: Mapped[str | None] = mapped_column(String(2))
    state_fips: Mapped[str | None] = mapped_column(String(2))
    vaccine_code: Mapped[str | None] = mapped_column(String(20))
    year: Mapped[int | None] = mapped_column(Integer)
    demographic_category: Mapped[str | None] = mapped_column(String(50))
    demographic_value: Mapped[str | None] = mapped_column(String(100))
    coverage_rate: Mapped[float | None] = mapped_column(Numeric(5, 1))
    ci_lower: Mapped[float | None] = mapped_column(Numeric(5, 1))
    ci_upper: Mapped[float | None] = mapped_column(Numeric(5, 1))
    sample_size: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str | None] = mapped_column(String(50))
    loaded_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
