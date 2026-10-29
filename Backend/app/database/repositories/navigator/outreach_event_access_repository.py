"""Scoped read queries for staff outreach-event access."""

from datetime import datetime
from typing import Any

from sqlalchemy import String, cast, func, or_
from sqlalchemy.orm import Session

from app.database.models.appointment import Appointment
from app.database.models.care_navigation_episode import CareNavigationEpisode
from app.database.models.checkin_question import CheckinQuestion
from app.database.models.checkin_response import CheckinResponse
from app.database.models.checkin_session import CheckinSession
from app.database.models.follow_up_task import FollowUpTask
from app.database.models.outreach_campaign import OutreachCampaign
from app.database.models.outreach_event import OutreachEvent
from app.database.models.outreach_workflow import OutreachWorkflow
from app.database.models.patient_profile import PatientProfile
from app.database.models.role import Role
from app.database.models.staff_profile import StaffProfile
from app.database.models.user import User


class OutreachEventAccessRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_actor(self, user_id: int) -> User | None:
        return (
            self.db.query(User)
            .join(Role, Role.role_id == User.role_id)
            .filter(User.user_id == user_id, User.status == "ACTIVE")
            .one_or_none()
        )

    def find_staff_profile(self, user_id: int) -> StaffProfile | None:
        return (
            self.db.query(StaffProfile)
            .filter(StaffProfile.user_id == user_id)
            .one_or_none()
        )

    def list_events(
        self,
        organization_id: int,
        staff_id: int | None,
        *,
        campaign_id: list[int] | None,
        workflow_id: list[int] | None,
        campaign_name: str | None,
        workflow_name: str | None,
        event_status: list[str] | None,
        delivery_status: list[str] | None,
        scheduled_from: datetime | None,
        scheduled_to: datetime | None,
        patient_search: str | None,
        patient_id: list[int] | None,
        skip: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        query = self._scoped_query(organization_id, staff_id)
        query = self._apply_filters(
            query,
            campaign_id=campaign_id,
            workflow_id=workflow_id,
            campaign_name=campaign_name,
            workflow_name=workflow_name,
            event_status=event_status,
            delivery_status=delivery_status,
            scheduled_from=scheduled_from,
            scheduled_to=scheduled_to,
            patient_search=patient_search,
            patient_id=patient_id,
        )
        total = query.with_entities(func.count(OutreachEvent.outreach_event_id)).scalar() or 0
        rows = (
            query.order_by(OutreachEvent.scheduled_at.desc(), OutreachEvent.outreach_event_id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return [self._summary(row) for row in rows], total

    def list_filter_options(
        self,
        organization_id: int,
        staff_id: int | None,
        campaign_id: int | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        campaign_query = self.db.query(OutreachCampaign).filter(
            OutreachCampaign.organization_id == organization_id,
        )
        workflow_query = self.db.query(OutreachWorkflow).join(
            OutreachCampaign,
            OutreachCampaign.campaign_id == OutreachWorkflow.campaign_id,
        ).filter(OutreachCampaign.organization_id == organization_id)

        if campaign_id is not None:
            workflow_query = workflow_query.filter(OutreachWorkflow.campaign_id == campaign_id)

        campaigns = campaign_query.order_by(OutreachCampaign.campaign_name.asc()).all()
        workflows = workflow_query.order_by(OutreachWorkflow.step_order.asc(), OutreachWorkflow.step_name.asc()).all()
        patient_rows = self._scoped_query(organization_id, staff_id).with_entities(
            PatientProfile.patient_id,
            User.first_name,
            User.last_name,
        ).distinct().order_by(User.first_name.asc(), User.last_name.asc()).all()
        return {
            "campaigns": [
                {"campaign_id": campaign.campaign_id, "campaign_name": campaign.campaign_name}
                for campaign in campaigns
            ],
            "workflows": [
                {
                    "workflow_id": workflow.workflow_id,
                    "campaign_id": workflow.campaign_id,
                    "workflow_name": workflow.step_name,
                }
                for workflow in workflows
            ],
            "patients": [
                {
                    "patient_id": patient_id,
                    "patient_name": f"{first_name} {last_name}",
                }
                for patient_id, first_name, last_name in patient_rows
            ],
        }

    def get_event(self, event_id: int, organization_id: int, staff_id: int | None) -> dict[str, Any] | None:
        row = self._scoped_query(organization_id, staff_id).filter(
            OutreachEvent.outreach_event_id == event_id,
        ).one_or_none()
        if row is None:
            return None

        event, campaign, workflow, patient, patient_user, episode, appointment = row
        sessions = (
            self.db.query(CheckinSession)
            .filter(CheckinSession.outreach_event_id == event.outreach_event_id)
            .order_by(CheckinSession.created_at.desc())
            .all()
        )
        responses = []
        for session in sessions:
            response_rows = (
                self.db.query(CheckinResponse, CheckinQuestion)
                .join(CheckinQuestion, CheckinQuestion.question_id == CheckinResponse.question_id)
                .filter(CheckinResponse.checkin_session_id == session.checkin_session_id)
                .order_by(CheckinResponse.answered_at)
                .all()
            )
            responses.extend(self._response(response, question) for response, question in response_rows)

        task_filters = [FollowUpTask.patient_id == event.patient_id]
        if event.appointment_id is not None:
            task_filters.append(FollowUpTask.appointment_id == event.appointment_id)
        if event.episode_id is not None:
            task_filters.append(FollowUpTask.episode_id == event.episode_id)
        tasks = (
            self.db.query(FollowUpTask)
            .filter(or_(*task_filters))
            .order_by(FollowUpTask.due_at.asc().nullslast(), FollowUpTask.created_at.desc())
            .all()
        )
        return {
            **self._summary(row),
            "delivery": {
                "sent_at": event.sent_at.isoformat() if event.sent_at else None,
                "responded_at": event.responded_at.isoformat() if event.responded_at else None,
                "completed_at": event.completed_at.isoformat() if event.completed_at else None,
                "attempt_count": event.attempt_count,
                "last_error": event.last_error,
            },
            "checkin_responses": responses,
            "appointment": self._appointment(appointment),
            "follow_up_tasks": [self._task(task) for task in tasks],
        }

    def _scoped_query(self, organization_id: int, staff_id: int | None):
        query = (
            self.db.query(
                OutreachEvent,
                OutreachCampaign,
                OutreachWorkflow,
                PatientProfile,
                User,
                CareNavigationEpisode,
                Appointment,
            )
            .join(OutreachCampaign, OutreachCampaign.campaign_id == OutreachEvent.campaign_id)
            .join(OutreachWorkflow, OutreachWorkflow.workflow_id == OutreachEvent.workflow_id)
            .join(PatientProfile, PatientProfile.patient_id == OutreachEvent.patient_id)
            .join(User, User.user_id == PatientProfile.user_id)
            .outerjoin(CareNavigationEpisode, CareNavigationEpisode.episode_id == OutreachEvent.episode_id)
            .outerjoin(Appointment, Appointment.appointment_id == OutreachEvent.appointment_id)
            .filter(OutreachCampaign.organization_id == organization_id)
        )
        if staff_id is not None:
            query = query.filter(CareNavigationEpisode.owner_staff_id == staff_id)
        return query

    @staticmethod
    def _apply_filters(query, **filters):
        if filters["campaign_id"]:
            query = query.filter(OutreachEvent.campaign_id.in_(filters["campaign_id"]))
        if filters["workflow_id"]:
            query = query.filter(OutreachEvent.workflow_id.in_(filters["workflow_id"]))
        if filters["campaign_name"]:
            query = query.filter(OutreachCampaign.campaign_name.ilike(f"%{filters['campaign_name'].strip()}%"))
        if filters["workflow_name"]:
            query = query.filter(OutreachWorkflow.step_name.ilike(f"%{filters['workflow_name'].strip()}%"))
        if filters["event_status"]:
            query = query.filter(OutreachEvent.event_status.in_(filters["event_status"]))
        if filters["delivery_status"]:
            query = query.filter(OutreachEvent.delivery_status.in_(filters["delivery_status"]))
        if filters["scheduled_from"] is not None:
            query = query.filter(OutreachEvent.scheduled_at >= filters["scheduled_from"])
        if filters["scheduled_to"] is not None:
            query = query.filter(OutreachEvent.scheduled_at < filters["scheduled_to"])
        if filters["patient_search"]:
            search = f"%{filters['patient_search'].strip()}%"
            query = query.filter(
                or_(
                    User.first_name.ilike(search),
                    User.last_name.ilike(search),
                    User.email.ilike(search),
                    cast(PatientProfile.patient_id, String).ilike(search),
                ),
            )
        if filters["patient_id"]:
            query = query.filter(OutreachEvent.patient_id.in_(filters["patient_id"]))
        return query

    @classmethod
    def _summary(cls, row):
        event, campaign, workflow, patient, patient_user, episode, appointment = row
        return {
            "outreach_event_id": event.outreach_event_id,
            "patient_id": event.patient_id,
            "patient_name": f"{patient_user.first_name} {patient_user.last_name}",
            "campaign_id": event.campaign_id,
            "campaign_name": campaign.campaign_name,
            "workflow_id": event.workflow_id,
            "workflow_name": workflow.step_name,
            "episode_id": event.episode_id,
            "appointment_id": event.appointment_id,
            "channel": event.channel.value,
            "event_type": event.event_type.value,
            "event_status": event.event_status.value,
            "delivery_status": event.delivery_status.value,
            "scheduled_at": event.scheduled_at.isoformat(),
            "attempt_count": event.attempt_count,
            "last_activity_at": next(
                (value.isoformat() for value in (event.completed_at, event.responded_at, event.sent_at) if value),
                None,
            ),
        }

    @staticmethod
    def _response(response, question):
        return {
            "response_id": response.response_id,
            "question_id": response.question_id,
            "question_text": question.question_text,
            "answer_text": response.answer_text,
            "answer_value": response.answer_value,
            "response_source": response.response_source.value,
            "answered_at": response.answered_at.isoformat(),
        }

    @staticmethod
    def _appointment(appointment):
        if appointment is None:
            return None
        return {
            "appointment_id": appointment.appointment_id,
            "appointment_type": appointment.appointment_type,
            "appointment_datetime": appointment.appointment_datetime.isoformat(),
            "end_datetime": appointment.end_datetime.isoformat(),
            "status": appointment.status.value if hasattr(appointment.status, "value") else appointment.status,
            "location_or_channel": appointment.location_or_channel,
            "reason": appointment.reason,
        }

    @staticmethod
    def _task(task):
        return {
            "follow_up_task_id": task.follow_up_task_id,
            "task_type": task.task_type.value,
            "title": task.title,
            "description": task.description,
            "assigned_to_staff_id": task.assigned_to_staff_id,
            "due_at": task.due_at.isoformat() if task.due_at else None,
            "priority": task.priority.value,
            "status": task.status.value,
        }