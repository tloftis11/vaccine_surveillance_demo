from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class AdherenceRate(Base):
    __tablename__ = "adherence_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vaccine_series: Mapped[str | None] = mapped_column(String(50))
    dose_number: Mapped[int | None] = mapped_column(Integer)
    year: Mapped[int | None] = mapped_column(Integer)
    state_abbr: Mapped[str | None] = mapped_column(String(2))
    demographic_category: Mapped[str | None] = mapped_column(String(50))
    demographic_value: Mapped[str | None] = mapped_column(String(100))
    completion_rate: Mapped[float | None] = mapped_column(Numeric(5, 1))
    on_time_rate: Mapped[float | None] = mapped_column(Numeric(5, 1))
    source: Mapped[str | None] = mapped_column(String(50))
    loaded_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
