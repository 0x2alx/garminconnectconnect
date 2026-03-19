"""add new endpoint tables

Revision ID: 002
Revises: None
Create Date: 2026-03-19
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "002"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Time-series tables (will become hypertables)
    op.create_table(
        "body_battery_events",
        sa.Column("timestamp", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("event_type", sa.String(30)),
        sa.Column("body_battery_impact", sa.SmallInteger),
        sa.Column("duration_minutes", sa.SmallInteger),
        sa.Column("feedback_type", sa.String(50)),
    )
    op.create_table(
        "intensity_minutes",
        sa.Column("timestamp", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("moderate_minutes", sa.SmallInteger),
        sa.Column("vigorous_minutes", sa.SmallInteger),
    )
    op.create_table(
        "floors",
        sa.Column("timestamp", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("floors_ascended", sa.SmallInteger),
        sa.Column("floors_descended", sa.SmallInteger),
    )
    op.create_table(
        "blood_pressure",
        sa.Column("timestamp", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("systolic", sa.SmallInteger),
        sa.Column("diastolic", sa.SmallInteger),
        sa.Column("pulse", sa.SmallInteger),
        sa.Column("notes", sa.String(200)),
    )

    # Daily/static tables
    op.create_table(
        "running_tolerance",
        sa.Column("date", sa.Date, primary_key=True),
        sa.Column("heat_acclimation", sa.Float),
        sa.Column("altitude_acclimation", sa.Float),
        sa.Column("heat_acclimation_status", sa.String(30)),
        sa.Column("altitude_acclimation_status", sa.String(30)),
    )
    op.create_table(
        "personal_records",
        sa.Column("record_type", sa.String(100), primary_key=True),
        sa.Column("activity_type", sa.String(50)),
        sa.Column("value", sa.Float),
        sa.Column("activity_id", sa.String(30)),
        sa.Column("pr_date", sa.Date),
    )
    op.create_table(
        "workouts",
        sa.Column("workout_id", sa.String(30), primary_key=True),
        sa.Column("name", sa.String(200)),
        sa.Column("description", sa.Text),
        sa.Column("sport_type", sa.String(50)),
        sa.Column("created_date", sa.DateTime(timezone=True)),
        sa.Column("updated_date", sa.DateTime(timezone=True)),
        sa.Column("estimated_duration_seconds", sa.Integer),
        sa.Column("estimated_distance_meters", sa.Float),
        sa.Column("num_steps", sa.SmallInteger),
        sa.Column("scheduled_date", sa.Date),
    )
    op.create_table(
        "badges",
        sa.Column("badge_id", sa.String(30), primary_key=True),
        sa.Column("name", sa.String(200)),
        sa.Column("category", sa.String(100)),
        sa.Column("earned_date", sa.DateTime(timezone=True)),
        sa.Column("earned_number", sa.SmallInteger),
    )
    op.create_table(
        "training_plans",
        sa.Column("plan_id", sa.String(30), primary_key=True),
        sa.Column("name", sa.String(200)),
        sa.Column("sport_type", sa.String(50)),
        sa.Column("start_date", sa.Date),
        sa.Column("end_date", sa.Date),
        sa.Column("goal", sa.String(200)),
        sa.Column("status", sa.String(30)),
    )

    # Create hypertables for time-series tables
    op.execute("SELECT create_hypertable('body_battery_events', 'timestamp', if_not_exists => TRUE)")
    op.execute("SELECT create_hypertable('intensity_minutes', 'timestamp', if_not_exists => TRUE)")
    op.execute("SELECT create_hypertable('floors', 'timestamp', if_not_exists => TRUE)")
    op.execute("SELECT create_hypertable('blood_pressure', 'timestamp', if_not_exists => TRUE)")


def downgrade() -> None:
    op.drop_table("training_plans")
    op.drop_table("badges")
    op.drop_table("workouts")
    op.drop_table("personal_records")
    op.drop_table("running_tolerance")
    op.drop_table("blood_pressure")
    op.drop_table("floors")
    op.drop_table("intensity_minutes")
    op.drop_table("body_battery_events")
