from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from garminconnect.models.base import Base


class HeartRateReading(Base):
    __tablename__ = "heart_rate"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    heart_rate: Mapped[int] = mapped_column(SmallInteger)


class StressReading(Base):
    __tablename__ = "stress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    stress_level: Mapped[int] = mapped_column(SmallInteger)


class BodyBatteryReading(Base):
    __tablename__ = "body_battery"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    level: Mapped[int] = mapped_column(SmallInteger)
    status: Mapped[str | None] = mapped_column(default=None)


class SpO2Reading(Base):
    __tablename__ = "spo2"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    spo2: Mapped[float] = mapped_column(Float)


class RespirationReading(Base):
    __tablename__ = "respiration"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    respiration_rate: Mapped[float] = mapped_column(Float)
