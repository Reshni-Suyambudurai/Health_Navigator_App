"""Create due outreach occurrences for campaigns with automation enabled."""

from datetime import datetime, timedelta
import logging
from typing import Any
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.models.outreach_event import (
    DeliveryStatus,
    OutreachEventChannel,
    OutreachEventStatus,
    OutreachEventType,
)
from app.database.repositories.navigator.admin_outreach_campaign_repository import AdminOutreachCampaignRepository
from app.services.navigator.admin_outreach_campaign_service import AdminOutreachCampaignService
from app.utils.audit_logger import AuditAction, AuditLogger


logger = logging.getLogger(__name__)


class AutomaticOutreachService:
    """Evaluate live cohorts and create only workflow occurrences that are due."""

    def __init__(self, db: Session):
        self.repository = AdminOutreachCampaignRepository(db)
        self.campaign_service = AdminOutreachCampaignService(db)
        self.campaign_service.repository = self.repository

    def run_due_outreach(self, now: datetime | None = None) -> dict[str, int]:
        evaluated_at = now or datetime.utcnow()
        result = {"campaigns_scanned": 0, "campaigns_failed": 0, "created_occurrences": 0}
        for campaign in self.repository.list_auto_outreach_campaigns():
            result["campaigns_scanned"] += 1
            try:
                result["created_occurrences"] += self._process_campaign(campaign, evaluated_at)
            except SQLAlchemyError:
                self.repository.rollback()
                result["campaigns_failed"] += 1
                logger.exception("Automatic outreach failed for campaign %s", campaign.campaign_id)
        return result

    def _process_campaign(self, campaign, now: datetime) -> int:
        if campaign.start_at and campaign.start_at > now:
            return 0
        if campaign.end_at and campaign.end_at < now:
            return 0
        criteria = self.campaign_service._validate_cohort(
            self.campaign_service._metadata(campaign).get("criteria") or {}
        )
        workflows = self.campaign_service._manual_outreach_workflows(campaign)
        if not workflows:
            return 0
        rows = self.repository.list_all_eligible_patients(campaign.organization_id, criteria)
        workflow_ids = [workflow.workflow_id for workflow in workflows]
        events = self.repository.list_eligible_outreach_events(
            campaign.organization_id,
            criteria,
            campaign.campaign_id,
            workflow_ids,
        )
        existing = {
            (event.patient_id, event.episode_id, event.workflow_id)
            for event in events
        }
        values = []
        for row in rows:
            patient_id = row[0].patient_id
            episode_id = row[2]
            discharge_at = row[9]
            for workflow in workflows:
                occurrence = (patient_id, episode_id, workflow.workflow_id)
                scheduled_at = discharge_at + timedelta(hours=workflow.trigger_offset_hours)
                if occurrence in existing or scheduled_at > now:
                    continue
                values.append({
                    "patient_id": patient_id,
                    "episode_id": episode_id,
                    "campaign_id": campaign.campaign_id,
                    "workflow_id": workflow.workflow_id,
                    "channel": OutreachEventChannel(workflow.channel.value),
                    "event_type": OutreachEventType.CHECK_IN,
                    "event_status": OutreachEventStatus.PENDING,
                    "delivery_status": DeliveryStatus.PENDING,
                    "scheduled_at": scheduled_at,
                    "attempt_count": 0,
                    "idempotency_key": self.campaign_service._outreach_idempotency_key(
                        campaign.campaign_id,
                        workflow.workflow_id,
                        patient_id,
                        episode_id,
                    ),
                })
        inserted = self.repository.stage_outreach_events(values)
        if not inserted:
            return 0
        audit_entry = AuditLogger.create_entry(
            action=AuditAction.AUTO_CREATE_OUTREACH_EVENTS,
            resource_type="OUTREACH_CAMPAIGN",
            resource_id=campaign.campaign_id,
            details={
                "workflow_ids": workflow_ids,
                "eligible_patients": len(rows),
                "created_occurrences": len(inserted),
                "evaluated_at": now,
            },
            correlation_id=f"auto-outreach-{uuid4()}",
        )
        self.repository.commit_with_audit(audit_entry)
        return len(inserted)