from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from garminconnect.models.base import Base


class DailySummary(Base):
    __tablename__ = "daily_summary"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    total_steps: Mapped[int | None] = mapped_column(Integer, default=None)
    step_goal: Mapped[int | None] = mapped_column(Integer, default=None)
    total_calories: Mapped[int | None] = mapped_column(Integer, default=None)
    active_calories: Mapped[int | None] = mapped_column(Integer, default=None)
    bmr_calories: Mapped[int | None] = mapped_column(Integer, default=None)
    total_distance_meters: Mapped[float | None] = mapped_column(Float, default=None)
    floors_climbed: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    floors_goal: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    intensity_minutes: Mapped[int | None] = mapped_column(Integer, default=None)
    moderate_intensity_minutes: Mapped[int | None] = mapped_column(Integer, default=None)
    vigorous_intensity_minutes: Mapped[int | None] = mapped_column(Integer, default=None)
    resting_heart_rate: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    min_heart_rate: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    max_heart_rate: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    avg_stress: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    max_stress: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    body_battery_high: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    body_battery_low: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    avg_spo2: Mapped[float | None] = mapped_column(Float, default=None)
    lowest_spo2: Mapped[float | None] = mapped_column(Float, default=None)
    avg_respiration: Mapped[float | None] = mapped_column(Float, default=None)
    hydration_ml: Mapped[int | None] = mapped_column(Integer, default=None)
    sweat_loss_ml: Mapped[int | None] = mapped_column(Integer, default=None)


class BodyComposition(Base):
    __tablename__ = "body_composition"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, default=None)
    bmi: Mapped[float | None] = mapped_column(Float, default=None)
    body_fat_pct: Mapped[float | None] = mapped_column(Float, default=None)
    muscle_mass_kg: Mapped[float | None] = mapped_column(Float, default=None)
    bone_mass_kg: Mapped[float | None] = mapped_column(Float, default=None)
    body_water_pct: Mapped[float | None] = mapped_column(Float, default=None)
