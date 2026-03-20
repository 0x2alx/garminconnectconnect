from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from garminconnect.models.base import Base


class HRVSummary(Base):
    __tablename__ = "hrv"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    weekly_avg: Mapped[float | None] = mapped_column(Float, default=None)
    last_night_avg: Mapped[float | None] = mapped_column(Float, default=None)
    last_night_5min_high: Mapped[float | None] = mapped_column(Float, default=None)
    baseline_low: Mapped[float | None] = mapped_column(Float, default=None)
    baseline_high: Mapped[float | None] = mapped_column(Float, default=None)
    status: Mapped[str | None] = mapped_column(String(30), default=None)


class TrainingReadiness(Base):
    __tablename__ = "training_readiness"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    score: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    level: Mapped[str | None] = mapped_column(String(30), default=None)
    sleep_score: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    recovery_score: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    hrv_score: Mapped[int | None] = mapped_column(SmallInteger, default=None)


class TrainingStatus(Base):
    __tablename__ = "training_status"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    training_status: Mapped[str | None] = mapped_column(String(50), default=None)
    weekly_load: Mapped[float | None] = mapped_column(Float, default=None)
    load_focus: Mapped[str | None] = mapped_column(String(50), default=None)
    vo2max_running: Mapped[float | None] = mapped_column(Float, default=None)
    vo2max_cycling: Mapped[float | None] = mapped_column(Float, default=None)
    fitness_age: Mapped[int | None] = mapped_column(SmallInteger, default=None)


class RacePrediction(Base):
    __tablename__ = "race_predictions"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    time_5k_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    time_10k_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    time_half_marathon_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    time_marathon_seconds: Mapped[int | None] = mapped_column(Integer, default=None)


class RunningTolerance(Base):
    __tablename__ = "running_tolerance"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    heat_acclimation: Mapped[float | None] = mapped_column(Float, default=None)
    altitude_acclimation: Mapped[float | None] = mapped_column(Float, default=None)
    heat_acclimation_status: Mapped[str | None] = mapped_column(String(30), default=None)
    altitude_acclimation_status: Mapped[str | None] = mapped_column(String(30), default=None)


class PersonalRecord(Base):
    __tablename__ = "personal_records"

    record_type: Mapped[str] = mapped_column(String(100), primary_key=True)
    activity_type: Mapped[str | None] = mapped_column(String(50), default=None)
    value: Mapped[float | None] = mapped_column(Float, default=None)
    activity_id: Mapped[str | None] = mapped_column(String(30), default=None)
    pr_date: Mapped[date | None] = mapped_column(Date, default=None)


class EnduranceScore(Base):
    __tablename__ = "endurance_score"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    overall_score: Mapped[int | None] = mapped_column(Integer, default=None)
    classification: Mapped[int | None] = mapped_column(SmallInteger, default=None)


class HillScore(Base):
    __tablename__ = "hill_score"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    overall_score: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    strength_score: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    endurance_score: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    vo2max: Mapped[float | None] = mapped_column(Float, default=None)
