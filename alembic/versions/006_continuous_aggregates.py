"""Add continuous aggregates for daily HR and stress rollups."""
from alembic import op

revision = "006"
down_revision = "005"


def upgrade():
    op.execute("""
        CREATE MATERIALIZED VIEW daily_hr_summary
        WITH (timescaledb.continuous) AS
        SELECT time_bucket('1 day', timestamp) AS day,
               MIN(heart_rate) AS min_hr, MAX(heart_rate) AS max_hr,
               AVG(heart_rate)::int AS avg_hr, COUNT(*) AS readings
        FROM heart_rate GROUP BY day
        WITH NO DATA
    """)
    op.execute("SELECT add_continuous_aggregate_policy('daily_hr_summary', '3 days', '1 day', '1 hour')")

    op.execute("""
        CREATE MATERIALIZED VIEW daily_stress_summary
        WITH (timescaledb.continuous) AS
        SELECT time_bucket('1 day', timestamp) AS day,
               AVG(stress_level)::int AS avg_stress, MAX(stress_level) AS max_stress,
               COUNT(*) AS readings
        FROM stress GROUP BY day
        WITH NO DATA
    """)
    op.execute("SELECT add_continuous_aggregate_policy('daily_stress_summary', '3 days', '1 day', '1 hour')")


def downgrade():
    op.execute("DROP MATERIALIZED VIEW IF EXISTS daily_stress_summary CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS daily_hr_summary CASCADE")
