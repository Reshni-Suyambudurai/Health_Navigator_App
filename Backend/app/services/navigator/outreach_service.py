"""Business logic for outreach, check-ins, and follow-up work."""

import enum
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AuthorizationException, BaseAPIException, ConflictException, NotFoundException, ValidationException
from app.database.models.appointment_action import (
    AppointmentAction,
    AppointmentActionType,
    AppointmentOutcome,
    AppointmentResolutionStatus,
    ContactMethod,
)
from app.database.models.checkin_question import CheckinAnswerType, CheckinQuestion, CheckinRiskLevel
from app.database.models.checkin_escalation import CheckinEscalation, CheckinEscalationStatus, CheckinEscalationType
from app.database.models.checkin_escalation_response import CheckinEscalationResponse
from app.database.models.checkin_response import CheckinResponse, CheckinResponseSource
from app.database.models.checkin_session import CheckinSession, CheckinSessionStatus
from app.database.models.checkin_template import CheckinTemplate, CheckinTemplateStatus, CheckinTemplateType
from app.database.models.escalation_assignment import EscalationAssignment, EscalationAssignmentStatus
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
from app.database.models.notification import Notification, NotificationPriority, NotificationStatus, NotificationType
from app.database.models.role import RoleName
from app.database.repositories.navigator.outreach_repository import OutreachRepository
from app.database.repositories.navigator.patient_profile_repository import PatientProfileRepository
from app.services.navigator.checkin_session_expiry import calculate_session_expiry


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
        self.profile_repository = PatientProfileRepository(db)

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
        if template_id and not self.repository.get_template(template_id):
            raise NotFoundException("Check-in template not found", "CHECKIN_TEMPLATE_NOT_FOUND")
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
        if updates.get("checkin_template_id") and not self.repository.get_template(updates["checkin_template_id"]):
            raise NotFoundException("Check-in template not found", "CHECKIN_TEMPLATE_NOT_FOUND")
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
        payload["status"] = self._enum(CheckinTemplateStatus, data.get("status", "DRAFT"), "template status")
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

    def list_sessions(self, user_id: int | None = None) -> list[dict[str, Any]]:
        patient_id = None
        if user_id is not None:
            patient = self.profile_repository.find_by_user_id(user_id)
            if not patient:
                raise NotFoundException("Patient profile not found for user", "PATIENT_PROFILE_NOT_FOUND")
            patient_id = patient.patient_id
        sessions = self.repository.list_sessions(patient_id)
        results = []
        for session in sessions:
            item = self._serialize(session)
            item["responses"] = self._serialize_many(self.repository.list_responses(session.checkin_session_id))
            template = self.repository.get_template(session.checkin_template_id)
            item["template"] = {
                "checkin_template_id": template.checkin_template_id,
                "template_name": template.template_name,
                "description": template.description,
                "expiry_after_hours": template.expiry_after_hours,
            } if template else None
            appointment = self.repository.get_appointment(session.appointment_id) if session.appointment_id else None
            item["appointment_required"] = bool(template and template.appointment_required)
            item["appointment_id"] = session.appointment_id
            item["appointment_status"] = appointment.status.value if appointment else None
            item["appointment_datetime"] = (
                appointment.appointment_datetime.isoformat()
                if appointment
                else None
            )
            item["questions"] = [
                {
                    "question_id": question.question_id,
                    "question_key": question.question_key,
                    "question_text": question.question_text,
                    "answer_type": question.answer_type.value,
                    "options": question.options,
                    "display_order": question.display_order,
                    "is_required": question.is_required,
                    "is_active": question.is_active,
                }
                for question in self.repository.list_questions(session.checkin_template_id)
                if question.is_active
            ]
            self._add_escalation_projection(item, session.checkin_session_id)
            results.append(item)
        return results

    def create_session(self, data: dict[str, Any]) -> dict[str, Any]:
        event = self.repository.get_event(data["outreach_event_id"])
        if not event:
            raise NotFoundException("Outreach event not found", "OUTREACH_EVENT_NOT_FOUND")
        self._require_template(data["checkin_template_id"])
        if event.patient_id != data["patient_id"]:
            raise ValidationException("Session patient must match the outreach event", "INVALID_SESSION_PATIENT")
        template = self.repository.get_template(data["checkin_template_id"])
        payload = dict(data)
        payload["scheduled_at"] = event.scheduled_at
        payload["expires_at"] = calculate_session_expiry(event.scheduled_at, template.expiry_after_hours)
        payload["session_status"] = self._enum(CheckinSessionStatus, data.get("session_status", "PENDING"), "session status")
        now = datetime.utcnow()
        if payload["session_status"] in (
            CheckinSessionStatus.IN_PROGRESS,
            CheckinSessionStatus.COMPLETED,
            CheckinSessionStatus.ESCALATED,
        ) and payload.get("started_at") is None:
            payload["started_at"] = now
        if payload["session_status"] == CheckinSessionStatus.COMPLETED and payload.get("completed_at") is None:
            payload["completed_at"] = now
        return self._save(CheckinSession(**payload))

    def record_response(self, session_id: int, data: dict[str, Any], user_id: int | None) -> dict[str, Any]:
        session = self.repository.lock_session(session_id)
        if not session:
            raise NotFoundException("Check-in session not found", "CHECKIN_SESSION_NOT_FOUND")
        self._require_session_patient(session, user_id)
        self._require_editable_session(session)
        question = self.repository.get_question(data["question_id"])
        if not question or question.checkin_template_id != session.checkin_template_id or not question.is_active:
            raise ValidationException("Question does not belong to the session template", "INVALID_SESSION_QUESTION")
        self._validate_answer(question, data)
        response = self._upsert_response(session_id, question, data, user_id, datetime.utcnow())
        if session.session_status == CheckinSessionStatus.PENDING:
            session.session_status = CheckinSessionStatus.IN_PROGRESS
            session.started_at = datetime.utcnow()
        elif session.session_status == CheckinSessionStatus.IN_PROGRESS and session.started_at is None:
            session.started_at = datetime.utcnow()
        try:
            self.db.commit()
            self.db.refresh(response)
            return self._serialize(response)
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictException("Unable to save check-in response", "CHECKIN_RESPONSE_CONFLICT") from exc

    def submit_session(self, session_id: int, data: dict[str, Any], user_id: int | None) -> dict[str, Any]:
        try:
            return self._submit_session(session_id, data, user_id)
        except BaseAPIException:
            self.db.rollback()
            raise

    def _submit_session(self, session_id: int, data: dict[str, Any], user_id: int | None) -> dict[str, Any]:
        session = self.repository.lock_session(session_id)
        if not session:
            raise NotFoundException("Check-in session not found", "CHECKIN_SESSION_NOT_FOUND")
        self._require_session_patient(session, user_id)
        submitted_answers = data.get("responses", [])
        questions = [
            question
            for question in self.repository.list_questions(session.checkin_template_id)
            if question.is_active
        ]
        questions_by_id = {question.question_id: question for question in questions}

        if session.session_status in (CheckinSessionStatus.COMPLETED, CheckinSessionStatus.ESCALATED):
            if self._submission_matches(session_id, submitted_answers, questions_by_id):
                result = self._session_result(session)
                self.db.rollback()
                return result
            raise ConflictException("A finalized check-in cannot be changed", "CHECKIN_ALREADY_SUBMITTED")
        self._require_editable_session(session)

        submitted_by_id: dict[int, dict[str, Any]] = {}
        for answer in submitted_answers:
            question_id = answer["question_id"]
            if question_id in submitted_by_id:
                raise ValidationException("Each question may be submitted only once", "DUPLICATE_CHECKIN_ANSWER")
            question = questions_by_id.get(question_id)
            if question is None:
                raise ValidationException("Question does not belong to the session template", "INVALID_SESSION_QUESTION")
            self._validate_answer(question, answer)
            submitted_by_id[question_id] = answer

        existing_by_question = {
            response.question_id: response
            for response in self.repository.list_responses(session_id)
        }
        missing_required = [
            question.question_text
            for question in questions
            if question.is_required
            and question.question_id not in submitted_by_id
            and question.question_id not in existing_by_question
        ]
        if missing_required:
            raise ValidationException(
                "Answer all required questions before submitting",
                "REQUIRED_CHECKIN_ANSWERS_MISSING",
            )

        now = datetime.utcnow()
        responses_by_question = dict(existing_by_question)
        for question_id, answer in submitted_by_id.items():
            responses_by_question[question_id] = self._upsert_response(
                session_id,
                questions_by_id[question_id],
                answer,
                user_id,
                now,
            )
        self.db.flush()

        escalation = None
        for question in questions:
            response = responses_by_question.get(question.question_id)
            if response is None:
                continue
            critical = self._is_critical_response(question, {
                "answer_text": response.answer_text,
                "answer_value": response.answer_value,
            })
            response.evaluated_risk_level = question.risk_level if critical else CheckinRiskLevel.NORMAL
            response.risk_evaluation = None
            if critical:
                escalation = self._apply_checkin_risk(session, question, response)
            else:
                remaining = self._remove_checkin_risk(session, response)
                escalation = escalation or remaining

        session.started_at = session.started_at or now
        session.completed_at = now
        session.session_status = (
            CheckinSessionStatus.ESCALATED
            if escalation is not None
            else CheckinSessionStatus.COMPLETED
        )
        if escalation is not None:
            template = self.repository.get_template(session.checkin_template_id)
            self._assign_checkin_escalation(session, template, escalation, now)
        try:
            self.db.commit()
            return self._session_result(session)
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictException("Unable to submit check-in", "CHECKIN_SUBMISSION_CONFLICT") from exc

    def _upsert_response(
        self,
        session_id: int,
        question: CheckinQuestion,
        data: dict[str, Any],
        user_id: int,
        answered_at: datetime,
    ) -> CheckinResponse:
        payload = {
            "question_id": question.question_id,
            "message_id": data.get("message_id"),
            "answer_text": data.get("answer_text"),
            "answer_value": data.get("answer_value"),
            "response_source": CheckinResponseSource.PATIENT_REPORTED,
            "recorded_by_user_id": user_id,
            "answered_at": answered_at,
            "evaluated_risk_level": CheckinRiskLevel.NORMAL,
            "risk_evaluation": None,
        }
        response = self.repository.get_response(session_id, question.question_id)
        if response is None:
            response = self.repository.add(CheckinResponse(checkin_session_id=session_id, **payload))
        else:
            self._apply(response, payload)
        return response

    def _require_session_patient(self, session: CheckinSession, user_id: int | None) -> None:
        if user_id is None:
            raise ValidationException("Patient identity is required", "PATIENT_IDENTITY_REQUIRED")
        patient = self.profile_repository.find_by_user_id(user_id)
        if patient is None or patient.patient_id != session.patient_id:
            raise AuthorizationException("This check-in does not belong to the patient", "CHECKIN_PATIENT_MISMATCH")

    @staticmethod
    def _require_editable_session(session: CheckinSession) -> None:
        if session.session_status not in (CheckinSessionStatus.PENDING, CheckinSessionStatus.IN_PROGRESS):
            raise ConflictException("This check-in is no longer editable", "CHECKIN_NOT_EDITABLE")
        if session.expires_at and datetime.utcnow() >= session.expires_at:
            raise ValidationException("This check-in session has expired", "CHECKIN_SESSION_EXPIRED")

    @classmethod
    def _validate_answer(cls, question: CheckinQuestion, data: dict[str, Any]) -> None:
        value = data.get("answer_value") if data.get("answer_value") is not None else data.get("answer_text")
        if value is None or value == "" or value == []:
            raise ValidationException("An answer value is required", "CHECKIN_ANSWER_REQUIRED")
        if question.answer_type == CheckinAnswerType.TEXT:
            if not isinstance(value, str) or not value.strip():
                raise ValidationException("Enter a text answer", "INVALID_CHECKIN_TEXT_ANSWER")
            return
        if question.answer_type == CheckinAnswerType.NUMBER:
            try:
                float(value)
            except (TypeError, ValueError) as exc:
                raise ValidationException("Enter a numeric answer", "INVALID_CHECKIN_NUMBER_ANSWER") from exc
            return
        if question.answer_type == CheckinAnswerType.YES_NO:
            normalized = str(value).strip().lower()
            if normalized not in {"yes", "no", "true", "false"}:
                raise ValidationException("Select Yes or No", "INVALID_CHECKIN_YES_NO_ANSWER")
            return
        allowed = {str(item).strip().lower() for item in cls._option_values(question.options)}
        actual = value if isinstance(value, list) else [value]
        if question.answer_type == CheckinAnswerType.MULTIPLE_CHOICE and not isinstance(value, list):
            raise ValidationException("Select one or more options", "INVALID_CHECKIN_MULTIPLE_CHOICE_ANSWER")
        if not actual or any(str(item).strip().lower() not in allowed for item in actual):
            raise ValidationException("Select a configured option", "INVALID_CHECKIN_CHOICE_ANSWER")

    @staticmethod
    def _option_values(options: Any) -> list[Any]:
        if isinstance(options, dict):
            options = options.get("options", options.get("values", []))
        if not isinstance(options, list):
            return []
        return [
            item.get("value", item.get("label")) if isinstance(item, dict) else item
            for item in options
        ]

    def _submission_matches(
        self,
        session_id: int,
        submitted_answers: list[dict[str, Any]],
        questions_by_id: dict[int, CheckinQuestion],
    ) -> bool:
        submitted = {answer["question_id"]: answer for answer in submitted_answers}
        stored = {
            response.question_id: response
            for response in self.repository.list_responses(session_id)
            if response.question_id in questions_by_id
        }
        if set(submitted) != set(stored):
            return False
        return all(
            submitted[question_id].get("answer_text") == response.answer_text
            and submitted[question_id].get("answer_value") == response.answer_value
            for question_id, response in stored.items()
        )

    def _session_result(self, session: CheckinSession) -> dict[str, Any]:
        result = self._serialize(session)
        result["responses"] = self._serialize_many(
            self.repository.list_responses(session.checkin_session_id)
        )
        self._add_escalation_projection(result, session.checkin_session_id)
        return result

    def _assign_checkin_escalation(
        self,
        session: CheckinSession,
        template: CheckinTemplate,
        escalation: CheckinEscalation,
        assigned_at: datetime,
    ) -> EscalationAssignment | None:
        role_id = template.escalation_role_id if template else None
        escalation.target_role_id = role_id
        if role_id is None:
            return None
        role = self.repository.get_role(role_id)
        staff = None
        if role and role.role_name == RoleName.TRANSITIONAL_CARE_NURSE and session.episode_id:
            episode = self.repository.get_episode(session.episode_id)
            if episode and episode.owner_staff_id:
                staff = self.repository.get_eligible_staff(
                    episode.owner_staff_id,
                    template.organization_id,
                    role_id,
                )
        elif role and role.role_name in (RoleName.PHARMACIST, RoleName.SOCIAL_WORKER):
            staff = self.repository.find_least_loaded_staff(template.organization_id, role_id)
        if staff is None:
            return None

        assignment = self.repository.get_checkin_assignment(escalation.checkin_escalation_id)
        if assignment is None:
            assignment = self.repository.add(EscalationAssignment(
                checkin_escalation_id=escalation.checkin_escalation_id,
                assigned_to_staff_id=staff.staff_id,
                assigned_at=assigned_at,
                assignment_status=EscalationAssignmentStatus.ASSIGNED,
                is_active=True,
            ))
        escalation.assigned_to_staff_id = staff.staff_id
        escalation.assigned_at = assignment.assigned_at
        escalation.escalation_status = CheckinEscalationStatus.ASSIGNED
        return assignment

    def _add_escalation_projection(self, result: dict[str, Any], session_id: int) -> None:
        escalation = self.repository.get_checkin_escalation(session_id)
        result["escalation"] = self._serialize(escalation)
        result["assignment"] = None
        result["assignee"] = None
        if escalation is None:
            return
        assignment = self.repository.get_checkin_assignment(escalation.checkin_escalation_id)
        if assignment is not None:
            result["assignment"] = self._serialize(assignment)
        if escalation.assigned_to_staff_id is None:
            return
        identity = self.repository.get_staff_identity(escalation.assigned_to_staff_id)
        if identity is None:
            return
        staff, user, role = identity
        result["assignee"] = {
            "staff_id": staff.staff_id,
            "name": f"{user.first_name} {user.last_name}".strip(),
            "role": role.role_name.value,
        }

    def list_staff_checkins(self, user_id: int) -> list[dict[str, Any]]:
        staff, _, role = self._require_checkin_staff(user_id)
        assignments = self.repository.list_staff_checkin_assignments(staff.staff_id)
        return [self._staff_checkin_result(assignment, role.role_name) for assignment in assignments]

    def start_checkin_assignment(self, assignment_id: int, user_id: int) -> dict[str, Any]:
        assignment, escalation = self._require_owned_assignment(assignment_id, user_id)
        if assignment.assignment_status == EscalationAssignmentStatus.COMPLETED:
            raise ConflictException("Completed check-in work cannot be restarted", "CHECKIN_ASSIGNMENT_COMPLETED")
        assignment.assignment_status = EscalationAssignmentStatus.IN_PROGRESS
        escalation.escalation_status = CheckinEscalationStatus.IN_PROGRESS
        self.db.commit()
        _, _, role = self._require_checkin_staff(user_id)
        return self._staff_checkin_result(assignment, role.role_name)

    def resolve_checkin_assignment(
        self,
        assignment_id: int,
        data: dict[str, Any],
        user_id: int,
    ) -> dict[str, Any]:
        assignment, escalation = self._require_owned_assignment(assignment_id, user_id)
        if assignment.assignment_status == EscalationAssignmentStatus.COMPLETED:
            return self._staff_checkin_result(assignment, self._require_checkin_staff(user_id)[2].role_name)
        now = datetime.utcnow()
        assignment.assignment_status = EscalationAssignmentStatus.COMPLETED
        assignment.action_taken = data["action_taken"].strip()
        assignment.resolution_notes = data["resolution_notes"].strip()
        assignment.completed_at = now
        assignment.is_active = False
        escalation.escalation_status = CheckinEscalationStatus.RESOLVED
        escalation.action_taken = assignment.action_taken
        escalation.resolution_notes = assignment.resolution_notes
        escalation.resolved_at = now
        session = self.repository.get_session(escalation.checkin_session_id)
        if session is not None:
            session.session_status = CheckinSessionStatus.COMPLETED
            session.completed_at = session.completed_at or now
            patient_identity = self.repository.get_patient_identity(session.patient_id)
            _, sender_user, _ = self._require_checkin_staff(user_id)
            if patient_identity is not None:
                _, patient_user = patient_identity
                if patient_user.organization_id != sender_user.organization_id:
                    raise AuthorizationException(
                        "Patient and staff must belong to the same organization",
                        "CHECKIN_NOTIFICATION_ORGANIZATION_MISMATCH",
                    )
                template = self.repository.get_template(session.checkin_template_id)
                template_name = template.template_name if template else "your check-in"
                self.repository.add(Notification(
                    organization_id=patient_user.organization_id,
                    sender_user_id=sender_user.user_id,
                    recipient_user_id=patient_user.user_id,
                    title="Your check-in follow-up is complete",
                    message=(
                        f"Your care team has completed the follow-up for {template_name}. "
                        "View the response in Check-ins."
                    ),
                    notification_type=NotificationType.FOLLOW_UP,
                    priority=NotificationPriority.NORMAL,
                    status=NotificationStatus.UNREAD,
                ))
        self.db.commit()
        _, _, role = self._require_checkin_staff(user_id)
        return self._staff_checkin_result(assignment, role.role_name)

    def _require_checkin_staff(self, user_id: int):
        identity = self.repository.get_staff_identity_by_user(user_id)
        if identity is None:
            raise AuthorizationException("A staff profile is required", "CHECKIN_STAFF_REQUIRED")
        _, _, role = identity
        if role.role_name not in (
            RoleName.TRANSITIONAL_CARE_NURSE,
            RoleName.PHARMACIST,
            RoleName.SOCIAL_WORKER,
        ):
            raise AuthorizationException("This role cannot manage check-ins", "CHECKIN_STAFF_ROLE_REQUIRED")
        return identity

    def _require_owned_assignment(self, assignment_id: int, user_id: int):
        staff, _, _ = self._require_checkin_staff(user_id)
        assignment = self.repository.get_assignment(assignment_id)
        if assignment is None or assignment.checkin_escalation_id is None:
            raise NotFoundException("Check-in assignment not found", "CHECKIN_ASSIGNMENT_NOT_FOUND")
        if assignment.assigned_to_staff_id != staff.staff_id:
            raise AuthorizationException("This check-in is assigned to another staff member", "CHECKIN_ASSIGNMENT_FORBIDDEN")
        escalation = self.repository.get_checkin_escalation_by_id(assignment.checkin_escalation_id)
        if escalation is None:
            raise NotFoundException("Check-in escalation not found", "CHECKIN_ESCALATION_NOT_FOUND")
        return assignment, escalation

    def _staff_checkin_result(self, assignment: EscalationAssignment, role_name: RoleName) -> dict[str, Any]:
        escalation = self.repository.get_checkin_escalation_by_id(assignment.checkin_escalation_id)
        session = self.repository.get_session(escalation.checkin_session_id)
        template = self.repository.get_template(session.checkin_template_id)
        patient_identity = self.repository.get_patient_identity(session.patient_id)
        patient_name = "Patient"
        patient_phone = None
        if patient_identity:
            _, patient_user = patient_identity
            patient_name = f"{patient_user.first_name} {patient_user.last_name}".strip()
            patient_phone = patient_user.phone
        questions = {
            question.question_id: question
            for question in self.repository.list_questions(session.checkin_template_id)
            if question.is_active
        }
        triggering_ids = {
            response.response_id
            for response in self.repository.list_checkin_escalation_responses(escalation.checkin_escalation_id)
        }
        responses = []
        for response in self.repository.list_responses(session.checkin_session_id):
            question = questions.get(response.question_id)
            if question is None:
                continue
            item = self._serialize(response)
            item["question_text"] = question.question_text
            item["is_triggering"] = response.response_id in triggering_ids
            responses.append(item)
        return {
            "assignment": self._serialize(assignment),
            "escalation": self._serialize(escalation),
            "session": self._serialize(session),
            "patient": {
                "patient_id": session.patient_id,
                "name": patient_name,
                "contact_number": patient_phone,
            },
            "template_name": template.template_name if template else "Check-in",
            "staff_role": role_name.value,
            "responses": responses,
        }

    def _apply_checkin_risk(
        self,
        session: CheckinSession,
        question: CheckinQuestion,
        response: CheckinResponse,
    ) -> CheckinEscalation:
        session.session_status = CheckinSessionStatus.ESCALATED
        escalation = self.repository.get_checkin_escalation(session.checkin_session_id)
        escalation_type = (
            CheckinEscalationType.EMERGENCY
            if question.risk_level == CheckinRiskLevel.EMERGENCY
            else CheckinEscalationType.ROUTINE
        )
        if escalation is None:
            escalation = self.repository.add(CheckinEscalation(
                checkin_session_id=session.checkin_session_id,
                escalation_type=escalation_type,
                escalation_reason="One or more check-in responses require care-team review.",
                trigger_source="CHECKIN_RESPONSE",
                matched_rule_key=question.question_key,
                escalation_status=CheckinEscalationStatus.OPEN,
            ))
        elif escalation_type == CheckinEscalationType.EMERGENCY:
            escalation.escalation_type = CheckinEscalationType.EMERGENCY

        link = self.repository.get_checkin_escalation_response(
            escalation.checkin_escalation_id,
            response.response_id,
        )
        if link is None:
            self.repository.add(CheckinEscalationResponse(
                checkin_escalation_id=escalation.checkin_escalation_id,
                response_id=response.response_id,
            ))
        return escalation

    def _remove_checkin_risk(
        self,
        session: CheckinSession,
        response: CheckinResponse,
    ) -> CheckinEscalation | None:
        escalation = self.repository.get_checkin_escalation(session.checkin_session_id)
        if escalation is None:
            return None
        link = self.repository.get_checkin_escalation_response(
            escalation.checkin_escalation_id,
            response.response_id,
        )
        if link is not None:
            self.repository.delete(link)
            self.db.flush()

        triggering_responses = self.repository.list_checkin_escalation_responses(
            escalation.checkin_escalation_id,
        )
        if not triggering_responses:
            self.repository.delete(escalation)
            self.db.flush()
            return None
        escalation.escalation_type = (
            CheckinEscalationType.EMERGENCY
            if any(
                item.evaluated_risk_level == CheckinRiskLevel.EMERGENCY
                for item in triggering_responses
            )
            else CheckinEscalationType.ROUTINE
        )
        return escalation

    @staticmethod
    def _is_critical_response(question: CheckinQuestion, payload: dict[str, Any]) -> bool:
        rule = question.critical_response
        if rule is None:
            return False
        value = payload.get("answer_value") if payload.get("answer_value") is not None else payload.get("answer_text")
        if question.answer_type == CheckinAnswerType.NUMBER and isinstance(rule, dict):
            try:
                number = float(value)
            except (TypeError, ValueError):
                return False
            minimum_matches = "min" not in rule or (
                number >= float(rule["min"])
                if rule.get("min_inclusive", True)
                else number > float(rule["min"])
            )
            maximum_matches = "max" not in rule or (
                number <= float(rule["max"])
                if rule.get("max_inclusive", True)
                else number < float(rule["max"])
            )
            return minimum_matches and maximum_matches
        expected = rule.get("values", []) if isinstance(rule, dict) else rule
        expected_values = expected if isinstance(expected, list) else [expected]
        actual_values = value if isinstance(value, list) else [value]
        return any(str(actual).strip().lower() == str(item).strip().lower() for actual in actual_values for item in expected_values)

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