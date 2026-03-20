"""complete data extraction

Revision ID: 004
Revises: 003
Create Date: 2026-03-20
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- New columns on activities table ---

    # Running dynamics
    op.add_column("activities", sa.Column("avg_ground_contact_time", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("avg_ground_contact_balance", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("avg_vertical_oscillation", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("avg_stride_length", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("avg_vertical_ratio", sa.Float(), nullable=True))

    # Performance
    op.add_column("activities", sa.Column("training_load", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("norm_power", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("max_power", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("avg_respiration_rate", sa.Float(), nullable=True))

    # Pacing
    op.add_column("activities", sa.Column("moving_duration_seconds", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("fastest_split_1k_seconds", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("fastest_split_mile_seconds", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("fastest_split_5k_seconds", sa.Float(), nullable=True))

    # HR zones
    op.add_column("activities", sa.Column("hr_zone_1_seconds", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("hr_zone_2_seconds", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("hr_zone_3_seconds", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("hr_zone_4_seconds", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("hr_zone_5_seconds", sa.Float(), nullable=True))

    # Metadata
    op.add_column("activities", sa.Column("location_name", sa.String(200), nullable=True))
    op.add_column("activities", sa.Column("lap_count", sa.SmallInteger(), nullable=True))
    op.add_column("activities", sa.Column("steps", sa.Integer(), nullable=True))
    op.add_column("activities", sa.Column("water_estimated_ml", sa.Integer(), nullable=True))
    op.add_column("activities", sa.Column("body_battery_impact", sa.SmallInteger(), nullable=True))
    op.add_column("activities", sa.Column("training_effect_label", sa.String(50), nullable=True))
    op.add_column("activities", sa.Column("moderate_intensity_minutes", sa.SmallInteger(), nullable=True))
    op.add_column("activities", sa.Column("vigorous_intensity_minutes", sa.SmallInteger(), nullable=True))

    # GPS start/end
    op.add_column("activities", sa.Column("start_latitude", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("start_longitude", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("end_latitude", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("end_longitude", sa.Float(), nullable=True))

    # --- New tables ---

    op.create_table(
        "endurance_score",
        sa.Column("date", sa.Date(), primary_key=True),
        sa.Column("overall_score", sa.Integer(), nullable=True),
        sa.Column("classification", sa.SmallInteger(), nullable=True),
    )

    op.create_table(
        "hill_score",
        sa.Column("date", sa.Date(), primary_key=True),
        sa.Column("overall_score", sa.SmallInteger(), nullable=True),
        sa.Column("strength_score", sa.SmallInteger(), nullable=True),
        sa.Column("endurance_score", sa.SmallInteger(), nullable=True),
        sa.Column("vo2max", sa.Float(), nullable=True),
    )

    op.create_table(
        "activity_trackpoints",
        sa.Column("activity_id", sa.String(50), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("altitude", sa.Float(), nullable=True),
        sa.Column("heart_rate", sa.SmallInteger(), nullable=True),
        sa.Column("cadence", sa.SmallInteger(), nullable=True),
        sa.Column("speed", sa.Float(), nullable=True),
        sa.Column("power", sa.Float(), nullable=True),
    )
    op.execute("SELECT create_hypertable('activity_trackpoints', 'timestamp', if_not_exists => TRUE)")

    op.create_table(
        "hrv_readings",
        sa.Column("timestamp", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("hrv_value", sa.SmallInteger(), nullable=True),
    )
    op.execute("SELECT create_hypertable('hrv_readings', 'timestamp', if_not_exists => TRUE)")


def downgrade() -> None:
    op.drop_table("hrv_readings")
    op.drop_table("activity_trackpoints")
    op.drop_table("hill_score")
    op.drop_table("endurance_score")

    # Remove activities columns
    op.drop_column("activities", "end_longitude")
    op.drop_column("activities", "end_latitude")
    op.drop_column("activities", "start_longitude")
    op.drop_column("activities", "start_latitude")
    op.drop_column("activities", "vigorous_intensity_minutes")
    op.drop_column("activities", "moderate_intensity_minutes")
    op.drop_column("activities", "training_effect_label")
    op.drop_column("activities", "body_battery_impact")
    op.drop_column("activities", "water_estimated_ml")
    op.drop_column("activities", "steps")
    op.drop_column("activities", "lap_count")
    op.drop_column("activities", "location_name")
    op.drop_column("activities", "hr_zone_5_seconds")
    op.drop_column("activities", "hr_zone_4_seconds")
    op.drop_column("activities", "hr_zone_3_seconds")
    op.drop_column("activities", "hr_zone_2_seconds")
    op.drop_column("activities", "hr_zone_1_seconds")
    op.drop_column("activities", "fastest_split_5k_seconds")
    op.drop_column("activities", "fastest_split_mile_seconds")
    op.drop_column("activities", "fastest_split_1k_seconds")
    op.drop_column("activities", "moving_duration_seconds")
    op.drop_column("activities", "avg_respiration_rate")
    op.drop_column("activities", "max_power")
    op.drop_column("activities", "norm_power")
    op.drop_column("activities", "training_load")
    op.drop_column("activities", "avg_vertical_ratio")
    op.drop_column("activities", "avg_stride_length")
    op.drop_column("activities", "avg_vertical_oscillation")
    op.drop_column("activities", "avg_ground_contact_balance")
    op.drop_column("activities", "avg_ground_contact_time")
