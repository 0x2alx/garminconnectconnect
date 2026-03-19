from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from garminconnect.models.base import Base


class Workout(Base):
    __tablename__ = "workouts"

    workout_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(200), default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    sport_type: Mapped[str | None] = mapped_column(String(50), default=None)
    created_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    updated_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    estimated_duration_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    estimated_distance_meters: Mapped[float | None] = mapped_column(Float, default=None)
    num_steps: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    scheduled_date: Mapped[date | None] = mapped_column(Date, default=None)


class Badge(Base):
    __tablename__ = "badges"

    badge_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(200), default=None)
    category: Mapped[str | None] = mapped_column(String(100), default=None)
    earned_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    earned_number: Mapped[int | None] = mapped_column(SmallInteger, default=None)


class ScheduledWorkout(Base):
    __tablename__ = "scheduled_workouts"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    workout_id: Mapped[str | None] = mapped_column(String(30), default=None)
    title: Mapped[str | None] = mapped_column(String(200), default=None)
    date: Mapped[date | None] = mapped_column(Date, default=None)
    sport_type: Mapped[str | None] = mapped_column(String(50), default=None)
    item_type: Mapped[str | None] = mapped_column(String(30), default=None)


class TrainingPlan(Base):
    __tablename__ = "training_plans"

    plan_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(200), default=None)
    sport_type: Mapped[str | None] = mapped_column(String(50), default=None)
    start_date: Mapped[date | None] = mapped_column(Date, default=None)
    end_date: Mapped[date | None] = mapped_column(Date, default=None)
    goal: Mapped[str | None] = mapped_column(String(200), default=None)
    status: Mapped[str | None] = mapped_column(String(30), default=None)
