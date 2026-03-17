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
        self.pipeline.sync_date(yesterday)
        self.pipeline.sync_date(today, force=True)
        self.pipeline.sync_activities(limit=10)
        logger.info("sync_cycle_complete")

    def start(self) -> None:
        logger.info("scheduler_starting", interval_minutes=self.interval_minutes)
        self.run_once()
        scheduler = BlockingScheduler()
        scheduler.add_job(self.run_once, "interval", minutes=self.interval_minutes, id="garmin_sync")
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("scheduler_stopped")
