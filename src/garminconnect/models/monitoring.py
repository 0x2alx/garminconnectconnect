from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from garminconnect.models.base import Base


class HeartRateReading(Base):
    __tablename__ = "heart_rate"

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    heart_rate: Mapped[int] = mapped_column(SmallInteger)


class StressReading(Base):
    __tablename__ = "stress"

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    stress_level: Mapped[int] = mapped_column(SmallInteger)


class BodyBatteryReading(Base):
    __tablename__ = "body_battery"

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    level: Mapped[int] = mapped_column(SmallInteger)
    status: Mapped[str | None] = mapped_column(default=None)


class SpO2Reading(Base):
    __tablename__ = "spo2"

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    spo2: Mapped[float] = mapped_column(Float)


class RespirationReading(Base):
    __tablename__ = "respiration"

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    respiration_rate: Mapped[float] = mapped_column(Float)


class BodyBatteryEvent(Base):
    __tablename__ = "body_battery_events"

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    event_type: Mapped[str | None] = mapped_column(String(30), default=None)
    body_battery_impact: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    duration_minutes: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    feedback_type: Mapped[str | None] = mapped_column(String(50), default=None)


class IntensityMinutesReading(Base):
    __tablename__ = "intensity_minutes"

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    moderate_minutes: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    vigorous_minutes: Mapped[int | None] = mapped_column(SmallInteger, default=None)


class FloorsReading(Base):
    __tablename__ = "floors"

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    floors_ascended: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    floors_descended: Mapped[int | None] = mapped_column(SmallInteger, default=None)


class BloodPressureReading(Base):
    __tablename__ = "blood_pressure"

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    systolic: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    diastolic: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    pulse: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    notes: Mapped[str | None] = mapped_column(String(200), default=None)
