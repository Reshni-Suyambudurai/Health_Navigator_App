"""Database operations for System Admin outreach campaign configuration."""

from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.models.care_navigation_episode import CareNavigationEpisode, EpisodeStatus, EpisodeType, TriggerType as EpisodeTriggerType
from app.database.models.checkin_template import CheckinTemplate, CheckinTemplateStatus
from app.database.models.checkin_template_review import CheckinTemplateReview, CheckinTemplateReviewStatus
from app.database.models.outreach_campaign import CampaignStatus, CampaignType, OutreachCampaign
from app.database.models.outreach_workflow import OutreachWorkflow
from app.database.models.patient_enrollment import EnrollmentProgram, EnrollmentStatus, PatientEnrollment
from app.database.models.patient_profile import PatientProfile
from app.database.models.role import Role, RoleName
from app.database.models.user import User, UserStatus


class AdminOutreachCampaignRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_admin_user(self, user_id: int) -> User | None:
        return (
            self.db.query(User)
            .join(Role, User.role_id == Role.role_id)
            .filter(
                User.user_id == user_id,
                User.status == UserStatus.ACTIVE,
                Role.role_name == RoleName.SYSTEM_ADMIN,
            )
            .one_or_none()
        )

    def find_user(self, user_id: int | None) -> User | None:
        if user_id is None:
            return None
        return self.db.query(User).filter(User.user_id == user_id).one_or_none()

    def list_campaigns(
        self,
        organization_id: int,
        skip: int,
        limit: int,
        campaign_status: CampaignStatus | None = None,
        campaign_type: CampaignType | None = None,
    ) -> tuple[list[OutreachCampaign], int]:
        query = self.db.query(OutreachCampaign).filter(
            OutreachCampaign.organization_id == organization_id
        )
        if campaign_status:
            query = query.filter(OutreachCampaign.status == campaign_status)
        if campaign_type:
            query = query.filter(OutreachCampaign.campaign_type == campaign_type)
        total = query.count()
        campaigns = query.order_by(OutreachCampaign.updated_at.desc()).offset(skip).limit(limit).all()
        return campaigns, total

    def find_campaign(self, campaign_id: int, organization_id: int) -> OutreachCampaign | None:
        return (
            self.db.query(OutreachCampaign)
            .filter(
                OutreachCampaign.campaign_id == campaign_id,
                OutreachCampaign.organization_id == organization_id,
            )
            .one_or_none()
        )

    def campaign_name_exists(
        self,
        organization_id: int,
        campaign_name: str,
        excluded_campaign_id: int | None = None,
    ) -> bool:
        query = self.db.query(OutreachCampaign.campaign_id).filter(
            OutreachCampaign.organization_id == organization_id,
            func.lower(OutreachCampaign.campaign_name) == campaign_name.lower(),
        )
        if excluded_campaign_id is not None:
            query = query.filter(OutreachCampaign.campaign_id != excluded_campaign_id)
        return query.first() is not None

    def list_workflows(self, campaign_id: int) -> list[OutreachWorkflow]:
        return (
            self.db.query(OutreachWorkflow)
            .filter(OutreachWorkflow.campaign_id == campaign_id)
            .order_by(OutreachWorkflow.step_order.asc())
            .all()
        )

    def find_workflow(
        self,
        workflow_id: int,
        organization_id: int,
    ) -> tuple[OutreachWorkflow, OutreachCampaign] | None:
        return (
            self.db.query(OutreachWorkflow, OutreachCampaign)
            .join(OutreachCampaign, OutreachCampaign.campaign_id == OutreachWorkflow.campaign_id)
            .filter(
                OutreachWorkflow.workflow_id == workflow_id,
                OutreachCampaign.organization_id == organization_id,
            )
            .one_or_none()
        )

    def workflow_step_exists(
        self,
        campaign_id: int,
        step_order: int,
        excluded_workflow_id: int | None = None,
    ) -> bool:
        query = self.db.query(OutreachWorkflow.workflow_id).filter(
            OutreachWorkflow.campaign_id == campaign_id,
            OutreachWorkflow.step_order == step_order,
        )
        if excluded_workflow_id is not None:
            query = query.filter(OutreachWorkflow.workflow_id != excluded_workflow_id)
        return query.first() is not None

    def list_active_templates(self, organization_id: int) -> list[CheckinTemplate]:
        return (
            self.db.query(CheckinTemplate)
            .join(
                CheckinTemplateReview,
                CheckinTemplateReview.checkin_template_id == CheckinTemplate.checkin_template_id,
            )
            .filter(
                CheckinTemplate.organization_id == organization_id,
                CheckinTemplate.status == CheckinTemplateStatus.ACTIVE,
                CheckinTemplateReview.status == CheckinTemplateReviewStatus.APPROVED,
            )
            .distinct()
            .order_by(CheckinTemplate.template_name.asc(), CheckinTemplate.version.desc())
            .all()
        )

    def find_active_template(self, template_id: int, organization_id: int) -> CheckinTemplate | None:
        return (
            self.db.query(CheckinTemplate)
            .join(
                CheckinTemplateReview,
                CheckinTemplateReview.checkin_template_id == CheckinTemplate.checkin_template_id,
            )
            .filter(
                CheckinTemplate.checkin_template_id == template_id,
                CheckinTemplate.organization_id == organization_id,
                CheckinTemplate.status == CheckinTemplateStatus.ACTIVE,
                CheckinTemplateReview.status == CheckinTemplateReviewStatus.APPROVED,
            )
            .one_or_none()
        )

    def count_eligible_patients(self, organization_id: int, criteria: dict) -> int:
        query = self._eligible_patient_query(organization_id, criteria).with_entities(
            func.count(func.distinct(PatientEnrollment.patient_id))
        )
        return query.scalar() or 0

    def list_eligible_patients(
        self,
        organization_id: int,
        criteria: dict,
        skip: int,
        limit: int,
    ) -> tuple[list, int]:
        ranked = self._eligible_patient_query(organization_id, criteria).with_entities(
            PatientEnrollment.patient_id.label("patient_id"),
            PatientEnrollment.enrollment_program.label("enrollment_program"),
            PatientEnrollment.enrollment_status.label("enrollment_status"),
            PatientEnrollment.enrollment_date.label("enrollment_date"),
            CareNavigationEpisode.episode_type.label("episode_type"),
            CareNavigationEpisode.status.label("episode_status"),
            CareNavigationEpisode.trigger_type.label("trigger_type"),
            CareNavigationEpisode.opened_at.label("episode_opened_at"),
            CareNavigationEpisode.created_at.label("episode_created_at"),
            func.row_number().over(
                partition_by=PatientEnrollment.patient_id,
                order_by=(CareNavigationEpisode.opened_at.desc(), CareNavigationEpisode.episode_id.desc()),
            ).label("patient_rank"),
        ).subquery()
        query = (
            self.db.query(
                PatientProfile,
                User,
                ranked.c.enrollment_program,
                ranked.c.enrollment_status,
                ranked.c.enrollment_date,
                ranked.c.episode_type,
                ranked.c.episode_status,
                ranked.c.trigger_type,
                ranked.c.episode_opened_at,
                ranked.c.episode_created_at,
            )
            .join(PatientProfile, PatientProfile.patient_id == ranked.c.patient_id)
            .join(User, User.user_id == PatientProfile.user_id)
            .filter(
                ranked.c.patient_rank == 1,
                User.organization_id == organization_id,
            )
        )
        total = query.count()
        patients = (
            query.order_by(User.last_name.asc(), User.first_name.asc(), PatientProfile.patient_id.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return patients, total

    def _eligible_patient_query(self, organization_id: int, criteria: dict):
        query = (
            self.db.query(PatientEnrollment)
            .join(
                CareNavigationEpisode,
                CareNavigationEpisode.enrollment_id == PatientEnrollment.enrollment_id,
            )
            .join(PatientProfile, PatientProfile.patient_id == PatientEnrollment.patient_id)
            .join(User, User.user_id == PatientProfile.user_id)
            .filter(
                PatientEnrollment.organization_id == organization_id,
                User.organization_id == organization_id,
            )
        )
        enrollment_statuses = criteria.get("enrollment_statuses") or []
        enrollment_programs = criteria.get("enrollment_programs") or []
        episode_types = criteria.get("episode_types") or []
        episode_statuses = criteria.get("episode_statuses") or []
        if enrollment_statuses:
            query = query.filter(PatientEnrollment.enrollment_status.in_(
                [EnrollmentStatus(value) for value in enrollment_statuses]
            ))
        if enrollment_programs:
            query = query.filter(PatientEnrollment.enrollment_program.in_(
                [EnrollmentProgram(value) for value in enrollment_programs]
            ))
        if episode_types:
            query = query.filter(CareNavigationEpisode.episode_type.in_(
                [EpisodeType(value) for value in episode_types]
            ))
        if episode_statuses:
            query = query.filter(CareNavigationEpisode.status.in_(
                [EpisodeStatus(value) for value in episode_statuses]
            ))
        discharged_within_days = criteria.get("discharged_within_days")
        if discharged_within_days:
            query = query.filter(
                CareNavigationEpisode.trigger_type == EpisodeTriggerType.DISCHARGE,
                CareNavigationEpisode.opened_at >= datetime.utcnow() - timedelta(days=discharged_within_days),
            )
        return query

    def save(self, entity):
        try:
            self.db.add(entity)
            self.db.commit()
            self.db.refresh(entity)
            return entity
        except Exception:
            self.db.rollback()
            raise