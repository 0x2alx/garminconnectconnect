from __future__ import annotations
from datetime import date
from sqlalchemy import Date, Float, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column
from garminconnect.models.base import Base


class LactateThreshold(Base):
    __tablename__ = "lactate_threshold"
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    sport: Mapped[str] = mapped_column(String(50), primary_key=True, default="DEFAULT")
    speed: Mapped[float | None] = mapped_column(Float, default=None)
    heart_rate: Mapped[int | None] = mapped_column(SmallInteger, default=None)


class CyclingFTP(Base):
    __tablename__ = "cycling_ftp"
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    ftp: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    source: Mapped[str | None] = mapped_column(String(50), default=None)
