"""Business logic for outreach, check-ins, and follow-up work."""

import enum
from datetime import date, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.database.models.appointment_action import (
    AppointmentAction,
    AppointmentActionType,
    AppointmentOutcome,
    AppointmentResolutionStatus,
    ContactMethod,
)
from app.database.models.checkin_question import CheckinAnswerType, CheckinQuestion
from app.database.models.checkin_response import CheckinResponse, CheckinResponseSource
from app.database.models.checkin_session import CheckinSession, CheckinSessionStatus
from app.database.models.checkin_template import CheckinTemplate, CheckinTemplateStatus, CheckinTemplateType
from app.database.models.follow_up_task import FollowUpPriority, FollowUpTask, FollowUpTaskStatus, FollowUpTaskType
from app.database.models.outreach_campaign import CampaignStatus, CampaignType, OutreachCampaign
from app.database.models.outreach_event import (
    DeliveryStatus,
    OutreachEvent,
    OutreachEventChannel,
    OutreachEventStatus,
    OutreachEventType,
)
from app.database.models.outreach_workflow import OutreachChannel, OutreachWorkflow, TriggerAnchor, TriggerType
from app.database.repositories.navigator.outreach_repository import OutreachRepository


class OutreachService:
    CAMPAIGN_FIELDS = {
        "campaign_name", "campaign_type", "target_cohort_definition", "timezone",
        "start_at", "end_at", "status",
    }
    WORKFLOW_FIELDS = {
        "step_order", "step_name", "trigger_type", "trigger_anchor",
        "trigger_offset_hours", "channel", "template_text", "checkin_template_id",
        "escalation_on_no_response", "max_attempts", "retry_interval_minutes", "is_active",
    }
    EVENT_UPDATE_FIELDS = {
        "event_status", "delivery_status", "scheduled_at", "sent_at", "responded_at",
        "completed_at", "attempt_count", "last_error", "appointment_id",
    }

    def __init__(self, db: Session):
        self.db = db
        self.repository = OutreachRepository(db)

    def list_campaigns(self, organization_id: int | None = None) -> list[dict[str, Any]]:
        return self._serialize_many(self.repository.list_campaigns(organization_id))

    def create_campaign(self, data: dict[str, Any], user_id: int) -> dict[str, Any]:
        if not self.repository.organization_exists(data["organization_id"]):
            raise NotFoundException("Organization not found", "ORGANIZATION_NOT_FOUND")
        self._require_user(user_id)
        payload = dict(data)
        payload["campaign_type"] = self._enum(CampaignType, data["campaign_type"], "campaign type")
        payload["status"] = self._enum(CampaignStatus, data.get("status", "DRAFT"), "campaign status")
        campaign = OutreachCampaign(**payload, created_by_user_id=user_id)
        return self._save(campaign)

    def update_campaign(self, campaign_id: int, data: dict[str, Any], user_id: int) -> dict[str, Any]:
        campaign = self.repository.get_campaign(campaign_id)
        if not campaign:
            raise NotFoundException("Campaign not found", "CAMPAIGN_NOT_FOUND")
        self._require_user(user_id)
        updates = {key: value for key, value in data.items() if key in self.CAMPAIGN_FIELDS}
        if "campaign_type" in updates:
            updates["campaign_type"] = self._enum(CampaignType, updates["campaign_type"], "campaign type")
        if "status" in updates:
            updates["status"] = self._enum(CampaignStatus, updates["status"], "campaign status")
        self._apply(campaign, updates)
        campaign.updated_by_user_id = user_id
        return self._save(campaign)

    def list_workflows(self, campaign_id: int) -> list[dict[str, Any]]:
        self._require_campaign(campaign_id)
        return self._serialize_many(self.repository.list_workflows(campaign_id))

    def create_workflow(self, campaign_id: int, data: dict[str, Any]) -> dict[str, Any]:
        self._require_campaign(campaign_id)
        template_id = data.get("checkin_template_id")
        if template_id and not self.repository.get_approved_active_template(template_id):
            raise ValidationException("Only an approved active check-in template can be assigned", "TEMPLATE_NOT_APPROVED")
        payload = dict(data)
        payload["channel"] = self._enum(OutreachChannel, data["channel"], "outreach channel")
        payload["trigger_type"] = self._enum(TriggerType, data["trigger_type"], "trigger type")
        payload["trigger_anchor"] = self._enum(TriggerAnchor, data["trigger_anchor"], "trigger anchor")
        workflow = OutreachWorkflow(campaign_id=campaign_id, **payload)
        return self._save(workflow)

    def update_workflow(self, workflow_id: int, data: dict[str, Any]) -> dict[str, Any]:
        workflow = self.repository.get_workflow(workflow_id)
        if not workflow:
            raise NotFoundException("Workflow not found", "WORKFLOW_NOT_FOUND")
        updates = {key: value for key, value in data.items() if key in self.WORKFLOW_FIELDS}
        if updates.get("checkin_template_id") and not self.repository.get_approved_active_template(updates["checkin_template_id"]):
            raise ValidationException("Only an approved active check-in template can be assigned", "TEMPLATE_NOT_APPROVED")
        if "channel" in updates:
            updates["channel"] = self._enum(OutreachChannel, updates["channel"], "outreach channel")
        if "trigger_type" in updates:
            updates["trigger_type"] = self._enum(TriggerType, updates["trigger_type"], "trigger type")
        if "trigger_anchor" in updates:
            updates["trigger_anchor"] = self._enum(TriggerAnchor, updates["trigger_anchor"], "trigger anchor")
        self._apply(workflow, updates)
        return self._save(workflow)

    def list_templates(self, organization_id: int | None = None) -> list[dict[str, Any]]:
        return self._serialize_many(self.repository.list_templates(organization_id))

    def create_template(self, data: dict[str, Any], user_id: int) -> dict[str, Any]:
        if not self.repository.organization_exists(data["organization_id"]):
            raise NotFoundException("Organization not found", "ORGANIZATION_NOT_FOUND")
        self._require_user(user_id)
        payload = dict(data)
        payload["template_type"] = self._enum(CheckinTemplateType, data["template_type"], "template type")
        payload["status"] = CheckinTemplateStatus.DRAFT
        return self._save(CheckinTemplate(**payload, created_by_user_id=user_id))

    def list_questions(self, template_id: int) -> list[dict[str, Any]]:
        self._require_template(template_id)
        return self._serialize_many(self.repository.list_questions(template_id))

    def create_question(self, template_id: int, data: dict[str, Any]) -> dict[str, Any]:
        self._require_template(template_id)
        payload = dict(data)
        payload["answer_type"] = self._enum(CheckinAnswerType, data["answer_type"], "answer type")
        return self._save(CheckinQuestion(checkin_template_id=template_id, **payload))

    def list_events(
        self,
        campaign_id: int | None,
        patient_id: int | None,
        event_status: str | None,
    ) -> list[dict[str, Any]]:
        normalized_status = None
        if event_status:
            normalized_status = self._enum(OutreachEventStatus, event_status, "event status")
        return self._serialize_many(self.repository.list_events(campaign_id, patient_id, normalized_status))

    def create_event(self, data: dict[str, Any]) -> dict[str, Any]:
        campaign = self._require_campaign(data["campaign_id"])
        workflow = self.repository.get_workflow(data["workflow_id"])
        if not workflow or workflow.campaign_id != campaign.campaign_id:
            raise ValidationException("Workflow does not belong to the campaign", "INVALID_WORKFLOW_CAMPAIGN")
        payload = dict(data)
        payload["channel"] = self._enum(OutreachEventChannel, data["channel"], "event channel")
        payload["event_type"] = self._enum(OutreachEventType, data["event_type"], "event type")
        payload["event_status"] = self._enum(OutreachEventStatus, data.get("event_status", "PENDING"), "event status")
        payload["delivery_status"] = self._enum(DeliveryStatus, data.get("delivery_status", "PENDING"), "delivery status")
        event = OutreachEvent(**payload)
        return self._save(event)

    def update_event(self, event_id: int, data: dict[str, Any]) -> dict[str, Any]:
        event = self.repository.get_event(event_id)
        if not event:
            raise NotFoundException("Outreach event not found", "OUTREACH_EVENT_NOT_FOUND")
        updates = {key: value for key, value in data.items() if key in self.EVENT_UPDATE_FIELDS}
        if "event_status" in updates:
            updates["event_status"] = self._enum(OutreachEventStatus, updates["event_status"], "event status")
        if "delivery_status" in updates:
            updates["delivery_status"] = self._enum(DeliveryStatus, updates["delivery_status"], "delivery status")
        self._apply(event, updates)
        return self._save(event)

    def list_sessions(self, patient_id: int | None = None) -> list[dict[str, Any]]:
        sessions = self.repository.list_sessions(patient_id)
        results = []
        for session in sessions:
            item = self._serialize(session)
            item["responses"] = self._serialize_many(self.repository.list_responses(session.checkin_session_id))
            results.append(item)
        return results

    def create_session(self, data: dict[str, Any]) -> dict[str, Any]:
        event = self.repository.get_event(data["outreach_event_id"])
        if not event:
            raise NotFoundException("Outreach event not found", "OUTREACH_EVENT_NOT_FOUND")
        self._require_template(data["checkin_template_id"])
        if event.patient_id != data["patient_id"]:
            raise ValidationException("Session patient must match the outreach event", "INVALID_SESSION_PATIENT")
        payload = dict(data)
        payload["session_status"] = self._enum(CheckinSessionStatus, data.get("session_status", "PENDING"), "session status")
        return self._save(CheckinSession(**payload))

    def record_response(self, session_id: int, data: dict[str, Any], user_id: int | None) -> dict[str, Any]:
        session = self.repository.get_session(session_id)
        if not session:
            raise NotFoundException("Check-in session not found", "CHECKIN_SESSION_NOT_FOUND")
        question = self.repository.get_question(data["question_id"])
        if not question or question.checkin_template_id != session.checkin_template_id:
            raise ValidationException("Question does not belong to the session template", "INVALID_SESSION_QUESTION")
        if user_id is not None:
            self._require_user(user_id)
        payload = dict(data)
        payload["response_source"] = self._enum(CheckinResponseSource, data.get("response_source", "PATIENT_REPORTED"), "response source")
        response = CheckinResponse(checkin_session_id=session_id, recorded_by_user_id=user_id, **payload)
        return self._save(response)

    def list_appointment_actions(self, appointment_id: int) -> list[dict[str, Any]]:
        self._require_appointment(appointment_id)
        return self._serialize_many(self.repository.list_appointment_actions(appointment_id))

    def create_appointment_action(self, appointment_id: int, data: dict[str, Any], user_id: int) -> dict[str, Any]:
        appointment = self._require_appointment(appointment_id)
        self._require_user(user_id)
        if data.get("follow_up_required") and not data.get("follow_up_due_at"):
            raise ValidationException("A follow-up due date is required", "FOLLOW_UP_DUE_DATE_REQUIRED")

        try:
            payload = dict(data)
            if payload.get("contact_method"):
                payload["contact_method"] = self._enum(ContactMethod, payload["contact_method"], "contact method")
            payload["action_taken"] = self._enum(AppointmentActionType, payload["action_taken"], "action type")
            if payload.get("outcome"):
                payload["outcome"] = self._enum(AppointmentOutcome, payload["outcome"], "appointment outcome")
            payload["resolution_status"] = self._enum(
                AppointmentResolutionStatus,
                payload.get("resolution_status", "PENDING"),
                "resolution status",
            )
            action = self.repository.add(AppointmentAction(
                appointment_id=appointment_id,
                patient_id=appointment.patient_id,
                episode_id=appointment.episode_id,
                action_by_user_id=user_id,
                **payload,
            ))
            task = None
            if action.follow_up_required:
                task = self.repository.add(FollowUpTask(
                    patient_id=appointment.patient_id,
                    episode_id=appointment.episode_id,
                    appointment_id=appointment_id,
                    task_type=FollowUpTaskType.PATIENT_CONTACT,
                    title=f"Appointment follow-up #{appointment_id}",
                    description=action.follow_up_notes or action.action_notes,
                    created_by_user_id=user_id,
                    due_at=action.follow_up_due_at,
                    priority=(
                        FollowUpPriority.HIGH
                        if action.resolution_status == AppointmentResolutionStatus.UNABLE_TO_REACH
                        else FollowUpPriority.MEDIUM
                    ),
                ))
            self.db.commit()
            self.db.refresh(action)
            if task:
                self.db.refresh(task)
            result = self._serialize(action)
            result["follow_up_task"] = self._serialize(task) if task else None
            return result
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictException("Unable to save appointment action", "APPOINTMENT_ACTION_CONFLICT") from exc

    def list_tasks(self, assigned_to_staff_id: int | None, task_status: str | None) -> list[dict[str, Any]]:
        return self._serialize_many(self.repository.list_tasks(assigned_to_staff_id, task_status))

    def create_task(self, data: dict[str, Any], user_id: int) -> dict[str, Any]:
        self._require_user(user_id)
        payload = dict(data)
        payload["task_type"] = self._enum(FollowUpTaskType, data["task_type"], "task type")
        payload["priority"] = self._enum(FollowUpPriority, data.get("priority", "MEDIUM"), "task priority")
        payload["status"] = self._enum(FollowUpTaskStatus, data.get("status", "OPEN"), "task status")
        return self._save(FollowUpTask(**payload, created_by_user_id=user_id))

    def update_task(self, task_id: int, data: dict[str, Any], user_id: int) -> dict[str, Any]:
        task = self.repository.get_task(task_id)
        if not task:
            raise NotFoundException("Follow-up task not found", "FOLLOW_UP_TASK_NOT_FOUND")
        self._require_user(user_id)
        updates = {key: value for key, value in data.items() if value is not None}
        if "priority" in updates:
            updates["priority"] = self._enum(FollowUpPriority, updates["priority"], "task priority")
        if "status" in updates:
            updates["status"] = self._enum(FollowUpTaskStatus, updates["status"], "task status")
        self._apply(task, updates)
        if task.status == FollowUpTaskStatus.COMPLETED:
            task.completed_by_user_id = user_id
            task.completed_at = task.completed_at or datetime.utcnow()
        return self._save(task)

    def _save(self, entity) -> dict[str, Any]:
        try:
            self.repository.add(entity)
            self.db.commit()
            self.db.refresh(entity)
            return self._serialize(entity)
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictException("Record conflicts with existing data", "OUTREACH_DATA_CONFLICT") from exc

    def _require_campaign(self, campaign_id: int) -> OutreachCampaign:
        campaign = self.repository.get_campaign(campaign_id)
        if not campaign:
            raise NotFoundException("Campaign not found", "CAMPAIGN_NOT_FOUND")
        return campaign

    def _require_template(self, template_id: int) -> CheckinTemplate:
        template = self.repository.get_template(template_id)
        if not template:
            raise NotFoundException("Check-in template not found", "CHECKIN_TEMPLATE_NOT_FOUND")
        return template

    def _require_appointment(self, appointment_id: int):
        appointment = self.repository.get_appointment(appointment_id)
        if not appointment:
            raise NotFoundException("Appointment not found", "APPOINTMENT_NOT_FOUND")
        return appointment

    def _require_user(self, user_id: int) -> None:
        if not self.repository.user_exists(user_id):
            raise NotFoundException("User not found", "USER_NOT_FOUND")

    @staticmethod
    def _enum(enum_type, value, label: str):
        if isinstance(value, enum_type):
            return value
        try:
            return enum_type(value)
        except ValueError as exc:
            allowed = ", ".join(member.value for member in enum_type)
            raise ValidationException(f"Invalid {label}. Expected one of: {allowed}", "INVALID_ENUM_VALUE") from exc

    @staticmethod
    def _apply(entity, updates: dict[str, Any]) -> None:
        for key, value in updates.items():
            setattr(entity, key, value)

    @classmethod
    def _serialize_many(cls, entities) -> list[dict[str, Any]]:
        return [cls._serialize(entity) for entity in entities]

    @staticmethod
    def _serialize(entity) -> dict[str, Any] | None:
        if entity is None:
            return None
        result = {}
        for column in entity.__table__.columns:
            value = getattr(entity, column.name)
            if isinstance(value, enum.Enum):
                value = value.value
            elif isinstance(value, (datetime, date)):
                value = value.isoformat()
            result[column.name] = value
        return result