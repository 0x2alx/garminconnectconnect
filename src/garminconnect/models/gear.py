from __future__ import annotations
from datetime import date
from sqlalchemy import Date, Float, String
from sqlalchemy.orm import Mapped, mapped_column
from garminconnect.models.base import Base


class Gear(Base):
    __tablename__ = "gear"
    gear_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    make: Mapped[str | None] = mapped_column(String(100), default=None)
    model: Mapped[str | None] = mapped_column(String(100), default=None)
    gear_type: Mapped[str | None] = mapped_column(String(50), default=None)
    status: Mapped[str | None] = mapped_column(String(20), default=None)
    display_name: Mapped[str | None] = mapped_column(String(200), default=None)
    date_begin: Mapped[date | None] = mapped_column(Date, default=None)
    max_meters: Mapped[float | None] = mapped_column(Float, default=None)
    running_meters: Mapped[float | None] = mapped_column(Float, default=None)
