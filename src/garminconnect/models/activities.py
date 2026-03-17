from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from garminconnect.models.base import Base


class Activity(Base):
    __tablename__ = "activities"

    activity_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    activity_type: Mapped[str | None] = mapped_column(String(50), default=None)
    sport: Mapped[str | None] = mapped_column(String(50), default=None)
    name: Mapped[str | None] = mapped_column(String(200), default=None)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    elapsed_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    distance_meters: Mapped[float | None] = mapped_column(Float, default=None)
    calories: Mapped[int | None] = mapped_column(Integer, default=None)
    avg_heart_rate: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    max_heart_rate: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    avg_speed: Mapped[float | None] = mapped_column(Float, default=None)
    max_speed: Mapped[float | None] = mapped_column(Float, default=None)
    elevation_gain: Mapped[float | None] = mapped_column(Float, default=None)
    elevation_loss: Mapped[float | None] = mapped_column(Float, default=None)
    avg_cadence: Mapped[float | None] = mapped_column(Float, default=None)
    avg_power: Mapped[float | None] = mapped_column(Float, default=None)
    training_effect_aerobic: Mapped[float | None] = mapped_column(Float, default=None)
    training_effect_anaerobic: Mapped[float | None] = mapped_column(Float, default=None)
    vo2max: Mapped[float | None] = mapped_column(Float, default=None)


class ActivityTrackpoint(Base):
    __tablename__ = "activity_trackpoints"

    activity_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    latitude: Mapped[float | None] = mapped_column(Float, default=None)
    longitude: Mapped[float | None] = mapped_column(Float, default=None)
    altitude: Mapped[float | None] = mapped_column(Float, default=None)
    heart_rate: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    cadence: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    speed: Mapped[float | None] = mapped_column(Float, default=None)
    power: Mapped[float | None] = mapped_column(Float, default=None)
