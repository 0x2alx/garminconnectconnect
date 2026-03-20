from __future__ import annotations
from datetime import date, timedelta
import structlog
from apscheduler.schedulers.blocking import BlockingScheduler
from garminconnect.sync.pipeline import SyncPipeline

logger = structlog.get_logger()


class GarminScheduler:
    def __init__(self, pipeline: SyncPipeline, interval_minutes: int = 10):
        self.pipeline = pipeline
        self.interval_minutes = interval_minutes

    def run_once(self) -> None:
        today = date.today()
        yesterday = today - timedelta(days=1)
        logger.info("sync_cycle_start")
        self.pipeline.sync_date(yesterday, force=True)
        self.pipeline.sync_date(today, force=True)
        self.pipeline.sync_activities(limit=10)
        self.pipeline.sync_body_composition(yesterday, today)
        self.pipeline.sync_running_tolerance()
        self.pipeline.sync_endurance_score()
        self.pipeline.sync_hill_score()
        self.pipeline.sync_workouts()
        self.pipeline.sync_personal_records()
        self.pipeline.sync_badges()
        self.pipeline.sync_training_plan()
        logger.info("sync_cycle_complete")

    def sync_calendar(self) -> None:
        """Sync scheduled workouts from Garmin calendar (±3 months)."""
        logger.info("calendar_sync_start")
        count = self.pipeline.sync_calendar()
        logger.info("calendar_sync_complete", count=count)

    def start(self) -> None:
        logger.info("scheduler_starting", interval_minutes=self.interval_minutes)
        self.run_once()
        self.sync_calendar()
        scheduler = BlockingScheduler()
        scheduler.add_job(self.run_once, "interval", minutes=self.interval_minutes, id="garmin_sync")
        scheduler.add_job(self.sync_calendar, "interval", hours=6, id="garmin_calendar_sync")
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("scheduler_stopped")
