from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column
from garminconnect.models.base import Base


class ActivityLap(Base):
    __tablename__ = "activity_laps"
    activity_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    lap_index: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    distance: Mapped[float | None] = mapped_column(Float, default=None)
    duration: Mapped[float | None] = mapped_column(Float, default=None)
    moving_duration: Mapped[float | None] = mapped_column(Float, default=None)
    avg_speed: Mapped[float | None] = mapped_column(Float, default=None)
    avg_heart_rate: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    max_heart_rate: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    calories: Mapped[int | None] = mapped_column(Integer, default=None)
    avg_cadence: Mapped[float | None] = mapped_column(Float, default=None)
    avg_power: Mapped[int | None] = mapped_column(Integer, default=None)
    elevation_gain: Mapped[float | None] = mapped_column(Float, default=None)
    elevation_loss: Mapped[float | None] = mapped_column(Float, default=None)
    ground_contact_time: Mapped[float | None] = mapped_column(Float, default=None)
    ground_contact_balance: Mapped[float | None] = mapped_column(Float, default=None)
    stride_length: Mapped[float | None] = mapped_column(Float, default=None)
    vertical_oscillation: Mapped[float | None] = mapped_column(Float, default=None)
    vertical_ratio: Mapped[float | None] = mapped_column(Float, default=None)
    start_latitude: Mapped[float | None] = mapped_column(Float, default=None)
    start_longitude: Mapped[float | None] = mapped_column(Float, default=None)
    intensity_type: Mapped[str | None] = mapped_column(String(20), default=None)
