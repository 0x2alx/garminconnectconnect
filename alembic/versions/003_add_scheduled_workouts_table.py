"""add scheduled_workouts table

Revision ID: 003
Revises: 002
Create Date: 2026-03-19
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scheduled_workouts",
        sa.Column("id", sa.String(30), primary_key=True),
        sa.Column("workout_id", sa.String(30), nullable=True),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("date", sa.Date, nullable=True),
        sa.Column("sport_type", sa.String(50), nullable=True),
        sa.Column("item_type", sa.String(30), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("scheduled_workouts")
