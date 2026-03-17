from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, SmallInteger
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
