"""APScheduler adapter for portal outreach delivery."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import text

from app.config import settings
from app.database.connection import SessionLocal, engine
from app.services.navigator.outreach_delivery_service import OutreachDeliveryService


logger = logging.getLogger(__name__)
OUTREACH_DELIVERY_ADVISORY_LOCK_ID = 74012027


class OutreachDeliveryScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone="UTC")

    def start(self) -> None:
        if not settings.AUTO_OUTREACH_SCHEDULER_ENABLED:
            logger.info("Outreach delivery scheduler is disabled")
            return
        self.scheduler.add_job(
            self.run_once,
            trigger="interval",
            seconds=max(settings.AUTO_OUTREACH_INTERVAL_SECONDS, 10),
            id="outreach-delivery",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        self.scheduler.start()
        logger.info("Outreach delivery scheduler started")

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    @staticmethod
    def run_once() -> None:
        with engine.connect() as lock_connection:
            acquired = bool(lock_connection.execute(
                text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": OUTREACH_DELIVERY_ADVISORY_LOCK_ID},
            ).scalar())
            if not acquired:
                return
            db = SessionLocal()
            try:
                service = OutreachDeliveryService(db)
                delivery_result = service.process_due_events()
                expiry_result = service.expire_sessions()
                logger.info(
                    "Outreach delivery scan completed: delivery=%s expiry=%s",
                    delivery_result,
                    expiry_result,
                )
            except Exception:
                db.rollback()
                logger.exception("Outreach delivery scan failed")
            finally:
                db.close()
                lock_connection.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"),
                    {"lock_id": OUTREACH_DELIVERY_ADVISORY_LOCK_ID},
                )
