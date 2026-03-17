from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from garminconnect.models.base import Base


class SleepSummary(Base):
    __tablename__ = "sleep_summary"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    total_sleep_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    deep_sleep_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    light_sleep_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    rem_sleep_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    awake_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    sleep_score: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    sleep_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    sleep_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    avg_spo2: Mapped[float | None] = mapped_column(Float, default=None)
    avg_respiration: Mapped[float | None] = mapped_column(Float, default=None)
    avg_stress: Mapped[float | None] = mapped_column(Float, default=None)
    avg_hrv: Mapped[float | None] = mapped_column(Float, default=None)
    body_battery_change: Mapped[int | None] = mapped_column(SmallInteger, default=None)


class SleepStage(Base):
    __tablename__ = "sleep_stages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    stage: Mapped[str] = mapped_column(String(20))
    duration_seconds: Mapped[int] = mapped_column(Integer)
