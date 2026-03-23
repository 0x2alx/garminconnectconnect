"""add biometrics, hydration, gear, and activity laps tables; weather columns on activities

Revision ID: 005
Revises: 004
Create Date: 2026-03-23
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lactate_threshold",
        sa.Column("date", sa.Date, primary_key=True),
        sa.Column("sport", sa.String(50), primary_key=True, server_default="DEFAULT"),
        sa.Column("speed", sa.Float, nullable=True),
        sa.Column("heart_rate", sa.SmallInteger, nullable=True),
    )
    op.create_table(
        "cycling_ftp",
        sa.Column("date", sa.Date, primary_key=True),
        sa.Column("ftp", sa.SmallInteger, nullable=True),
        sa.Column("source", sa.String(50), nullable=True),
    )
    op.create_table(
        "hydration",
        sa.Column("date", sa.Date, primary_key=True),
        sa.Column("intake_ml", sa.Float, nullable=True),
        sa.Column("goal_ml", sa.Float, nullable=True),
        sa.Column("daily_average_ml", sa.Float, nullable=True),
        sa.Column("sweat_loss_ml", sa.Float, nullable=True),
        sa.Column("activity_intake_ml", sa.Float, nullable=True),
    )
    op.create_table(
        "gear",
        sa.Column("gear_id", sa.String(50), primary_key=True),
        sa.Column("make", sa.String(100), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("gear_type", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("display_name", sa.String(200), nullable=True),
        sa.Column("date_begin", sa.Date, nullable=True),
        sa.Column("max_meters", sa.Float, nullable=True),
        sa.Column("running_meters", sa.Float, nullable=True),
    )
    op.create_table(
        "activity_laps",
        sa.Column("activity_id", sa.String(50), primary_key=True),
        sa.Column("lap_index", sa.SmallInteger, primary_key=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("distance", sa.Float, nullable=True),
        sa.Column("duration", sa.Float, nullable=True),
        sa.Column("moving_duration", sa.Float, nullable=True),
        sa.Column("avg_speed", sa.Float, nullable=True),
        sa.Column("avg_heart_rate", sa.SmallInteger, nullable=True),
        sa.Column("max_heart_rate", sa.SmallInteger, nullable=True),
        sa.Column("calories", sa.Integer, nullable=True),
        sa.Column("avg_cadence", sa.Float, nullable=True),
        sa.Column("avg_power", sa.Integer, nullable=True),
        sa.Column("elevation_gain", sa.Float, nullable=True),
        sa.Column("elevation_loss", sa.Float, nullable=True),
        sa.Column("ground_contact_time", sa.Float, nullable=True),
        sa.Column("ground_contact_balance", sa.Float, nullable=True),
        sa.Column("stride_length", sa.Float, nullable=True),
        sa.Column("vertical_oscillation", sa.Float, nullable=True),
        sa.Column("vertical_ratio", sa.Float, nullable=True),
        sa.Column("start_latitude", sa.Float, nullable=True),
        sa.Column("start_longitude", sa.Float, nullable=True),
        sa.Column("intensity_type", sa.String(20), nullable=True),
    )
    # Weather columns on activities
    op.add_column("activities", sa.Column("weather_temp", sa.Float, nullable=True))
    op.add_column("activities", sa.Column("weather_feels_like", sa.Float, nullable=True))
    op.add_column("activities", sa.Column("weather_humidity", sa.SmallInteger, nullable=True))
    op.add_column("activities", sa.Column("weather_wind_speed", sa.Float, nullable=True))
    op.add_column("activities", sa.Column("weather_condition", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("activities", "weather_condition")
    op.drop_column("activities", "weather_wind_speed")
    op.drop_column("activities", "weather_humidity")
    op.drop_column("activities", "weather_feels_like")
    op.drop_column("activities", "weather_temp")
    op.drop_table("activity_laps")
    op.drop_table("gear")
    op.drop_table("hydration")
    op.drop_table("cycling_ftp")
    op.drop_table("lactate_threshold")
