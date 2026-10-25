"""APScheduler adapter for automatic outreach processing."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import text

from app.config import settings
from app.database.connection import SessionLocal, engine
from app.services.navigator.automatic_outreach_service import AutomaticOutreachService


logger = logging.getLogger(__name__)
AUTO_OUTREACH_ADVISORY_LOCK_ID = 74012026


class AutomaticOutreachScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone="UTC")

    def start(self) -> None:
        if not settings.AUTO_OUTREACH_SCHEDULER_ENABLED:
            logger.info("Automatic outreach scheduler is disabled")
            return
        interval = max(settings.AUTO_OUTREACH_INTERVAL_SECONDS, 10)
        self.scheduler.add_job(
            self.run_once,
            trigger="interval",
            seconds=interval,
            id="automatic-outreach",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        self.scheduler.start()
        logger.info("Automatic outreach scheduler started with a %s second interval", interval)

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Automatic outreach scheduler stopped")

    @staticmethod
    def run_once() -> None:
        with engine.connect() as lock_connection:
            acquired = bool(lock_connection.execute(
                text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": AUTO_OUTREACH_ADVISORY_LOCK_ID},
            ).scalar())
            if not acquired:
                logger.info("Automatic outreach scan skipped because another instance holds the lock")
                return
            db = SessionLocal()
            try:
                result = AutomaticOutreachService(db).run_due_outreach()
                logger.info("Automatic outreach scan completed: %s", result)
            except Exception:
                db.rollback()
                logger.exception("Automatic outreach scan failed")
            finally:
                db.close()
                lock_connection.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"),
                    {"lock_id": AUTO_OUTREACH_ADVISORY_LOCK_ID},
                )