"""Business logic for organization-scoped outreach campaign configuration."""

from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AuthorizationException, ConflictException, NotFoundException, ValidationException
from app.database.models.care_navigation_episode import EpisodeStatus, EpisodeType
from app.database.models.outreach_campaign import CampaignStatus, CampaignType, OutreachCampaign
from app.database.models.outreach_workflow import OutreachChannel, OutreachWorkflow, TriggerAnchor, TriggerType
from app.database.models.patient_enrollment import EnrollmentProgram, EnrollmentStatus
from app.database.repositories.navigator.admin_outreach_campaign_repository import AdminOutreachCampaignRepository


class AdminOutreachCampaignService:
    EDITABLE_STATUSES = (CampaignStatus.DRAFT, CampaignStatus.PAUSED)
    TRANSITIONS = {
        CampaignStatus.DRAFT: (CampaignStatus.ACTIVE,),
        CampaignStatus.ACTIVE: (CampaignStatus.PAUSED, CampaignStatus.COMPLETED),
        CampaignStatus.PAUSED: (CampaignStatus.ACTIVE, CampaignStatus.COMPLETED),
        CampaignStatus.COMPLETED: (),
        CampaignStatus.ARCHIVED: (),
    }
    CAMPAIGN_FIELDS = {"campaign_name", "campaign_type", "timezone", "start_at", "end_at"}
    WORKFLOW_FIELDS = {
        "step_order", "step_name", "trigger_type", "trigger_anchor", "trigger_offset_hours",
        "channel", "template_text", "checkin_template_id", "escalation_on_no_response",
        "max_attempts", "retry_interval_minutes", "is_active",
    }

    def __init__(self, db: Session):
        self.repository = AdminOutreachCampaignRepository(db)

    def list_campaigns(
        self,
        actor_user_id: int,
        skip: int = 0,
        limit: int = 25,
        status: str | None = None,
        campaign_type: str | None = None,
    ) -> dict[str, Any]:
        admin = self._require_admin(actor_user_id)
        status_value = self._enum(CampaignStatus, status, "campaign status") if status else None
        type_value = self._campaign_type(campaign_type) if campaign_type else None
        campaigns, total = self.repository.list_campaigns(
            admin.organization_id, skip, limit, status_value, type_value
        )
        return {"campaigns": [self._serialize_campaign(item) for item in campaigns], "count": total}

    def get_campaign(self, actor_user_id: int, campaign_id: int) -> dict[str, Any]:
        admin = self._require_admin(actor_user_id)
        campaign = self._require_campaign(campaign_id, admin.organization_id)
        return self._serialize_campaign(campaign, include_workflows=True)

    def create_campaign(
        self,
        actor_user_id: int,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        admin = self._require_admin(actor_user_id)
        campaign_name = self._required_text(data["campaign_name"], "Campaign name")
        if self.repository.campaign_name_exists(admin.organization_id, campaign_name):
            raise ConflictException("Campaign name already exists", "CAMPAIGN_NAME_EXISTS")
        criteria = self._validate_cohort(data["cohort"])
        self._validate_dates(data.get("start_at"), data.get("end_at"))
        campaign = OutreachCampaign(
            organization_id=admin.organization_id,
            campaign_name=campaign_name,
            campaign_type=self._campaign_type(data["campaign_type"]),
            target_cohort_definition={
                "description": self._optional_text(data.get("description")),
                "criteria": criteria,
            },
            timezone=self._required_text(data.get("timezone", "UTC"), "Timezone"),
            start_at=data.get("start_at"),
            end_at=data.get("end_at"),
            status=CampaignStatus.DRAFT,
            created_by_user_id=admin.user_id,
            updated_by_user_id=admin.user_id,
        )
        self._save(campaign)
        return self._serialize_campaign(campaign, include_workflows=True)

    def update_campaign(
        self,
        actor_user_id: int,
        campaign_id: int,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        admin = self._require_admin(actor_user_id)
        campaign = self._require_campaign(campaign_id, admin.organization_id)
        self._require_editable(campaign)
        before = self._snapshot(campaign)
        if "campaign_name" in data:
            name = self._required_text(data["campaign_name"], "Campaign name")
            if self.repository.campaign_name_exists(admin.organization_id, name, campaign_id):
                raise ConflictException("Campaign name already exists", "CAMPAIGN_NAME_EXISTS")
            campaign.campaign_name = name
        if "campaign_type" in data:
            campaign.campaign_type = self._campaign_type(data["campaign_type"])
        if "timezone" in data:
            campaign.timezone = self._required_text(data["timezone"], "Timezone")
        if "start_at" in data:
            campaign.start_at = data["start_at"]
        if "end_at" in data:
            campaign.end_at = data["end_at"]
        metadata = self._metadata(campaign)
        if "description" in data:
            metadata["description"] = self._optional_text(data["description"])
        if "cohort" in data and data["cohort"] is not None:
            metadata["criteria"] = self._validate_cohort(data["cohort"])
        campaign.target_cohort_definition = metadata
        self._validate_dates(campaign.start_at, campaign.end_at)
        campaign.updated_by_user_id = admin.user_id
        after = self._snapshot(campaign)
        changed = [field for field in before if before[field] != after[field]]
        if not changed:
            raise ValidationException("No campaign changes were provided", "NO_CAMPAIGN_CHANGES")
        self._save(campaign)
        return self._serialize_campaign(campaign, include_workflows=True)

    def preview_cohort(self, actor_user_id: int, campaign_id: int) -> dict[str, Any]:
        admin = self._require_admin(actor_user_id)
        campaign = self._require_campaign(campaign_id, admin.organization_id)
        criteria = self._validate_cohort(self._metadata(campaign).get("criteria") or {})
        count = self.repository.count_eligible_patients(admin.organization_id, criteria)
        return {"eligible_patient_count": count, "criteria": criteria, "discharge_date_source": "EPISODE_OPENED_AT"}

    def list_cohort_members(
        self,
        actor_user_id: int,
        campaign_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> dict[str, Any]:
        admin = self._require_admin(actor_user_id)
        campaign = self._require_campaign(campaign_id, admin.organization_id)
        criteria = self._validate_cohort(self._metadata(campaign).get("criteria") or {})
        rows, total = self.repository.list_eligible_patients(
            admin.organization_id,
            criteria,
            skip,
            limit,
        )
        return {
            "campaign_id": campaign.campaign_id,
            "campaign_name": campaign.campaign_name,
            "patients": [self._serialize_cohort_patient(row) for row in rows],
            "count": total,
            "skip": skip,
            "limit": limit,
            "has_more": skip + len(rows) < total,
        }

    def transition_status(
        self,
        actor_user_id: int,
        campaign_id: int,
        target_status: str,
    ) -> dict[str, Any]:
        admin = self._require_admin(actor_user_id)
        campaign = self._require_campaign(campaign_id, admin.organization_id)
        next_status = self._enum(CampaignStatus, target_status, "campaign status")
        if next_status not in self.TRANSITIONS.get(campaign.status, ()):
            raise ValidationException(
                f"Campaign cannot transition from {campaign.status.value} to {next_status.value}",
                "INVALID_CAMPAIGN_TRANSITION",
            )
        if next_status == CampaignStatus.ACTIVE:
            readiness = self._readiness(campaign)
            if not readiness["ready"]:
                raise ValidationException(
                    "Campaign is not ready: " + "; ".join(readiness["issues"]),
                    "CAMPAIGN_NOT_READY",
                )
        campaign.status = next_status
        campaign.updated_by_user_id = admin.user_id
        self._save(campaign)
        return self._serialize_campaign(campaign, include_workflows=True)

    def list_workflows(self, actor_user_id: int, campaign_id: int) -> dict[str, Any]:
        admin = self._require_admin(actor_user_id)
        campaign = self._require_campaign(campaign_id, admin.organization_id)
        workflows = self.repository.list_workflows(campaign_id)
        return {
            "campaign": self._serialize_campaign(campaign),
            "workflows": [self._serialize_workflow(item, admin.organization_id) for item in workflows],
            "count": len(workflows),
        }

    def list_templates(self, actor_user_id: int) -> list[dict[str, Any]]:
        admin = self._require_admin(actor_user_id)
        return [{
            "checkin_template_id": item.checkin_template_id,
            "template_name": item.template_name,
            "template_type": item.template_type.value,
            "version": item.version,
            "status": item.status.value,
        } for item in self.repository.list_active_templates(admin.organization_id)]

    def create_workflow(
        self,
        actor_user_id: int,
        campaign_id: int,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        admin = self._require_admin(actor_user_id)
        campaign = self._require_campaign(campaign_id, admin.organization_id)
        self._require_editable(campaign)
        if self.repository.workflow_step_exists(campaign_id, data["step_order"]):
            raise ConflictException("Workflow step order already exists", "WORKFLOW_STEP_EXISTS")
        self._require_template(data["checkin_template_id"], admin.organization_id)
        workflow = OutreachWorkflow(campaign_id=campaign_id, **self._workflow_payload(data))
        self._save(workflow)
        return self._serialize_workflow(workflow, admin.organization_id)

    def update_workflow(
        self,
        actor_user_id: int,
        workflow_id: int,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        admin = self._require_admin(actor_user_id)
        result = self.repository.find_workflow(workflow_id, admin.organization_id)
        if not result:
            raise NotFoundException("Workflow not found", "WORKFLOW_NOT_FOUND")
        workflow, campaign = result
        self._require_editable(campaign)
        before = self._workflow_snapshot(workflow)
        if "step_order" in data and self.repository.workflow_step_exists(
            campaign.campaign_id, data["step_order"], workflow.workflow_id
        ):
            raise ConflictException("Workflow step order already exists", "WORKFLOW_STEP_EXISTS")
        if data.get("checkin_template_id") is not None:
            self._require_template(data["checkin_template_id"], admin.organization_id)
        payload = self._workflow_payload(data, partial=True)
        for field, value in payload.items():
            setattr(workflow, field, value)
        after = self._workflow_snapshot(workflow)
        changed = [field for field in before if before[field] != after[field]]
        if not changed:
            raise ValidationException("No workflow changes were provided", "NO_WORKFLOW_CHANGES")
        self._save(workflow)
        return self._serialize_workflow(workflow, admin.organization_id)

    def _readiness(self, campaign: OutreachCampaign) -> dict[str, Any]:
        issues = []
        try:
            criteria = self._validate_cohort(self._metadata(campaign).get("criteria") or {})
        except ValidationException as exc:
            criteria = {}
            issues.append(exc.message)
        workflows = self.repository.list_workflows(campaign.campaign_id)
        active = [item for item in workflows if item.is_active]
        if not active:
            issues.append("At least one active workflow is required")
        for workflow in active:
            if not workflow.checkin_template_id or not self.repository.find_active_template(
                workflow.checkin_template_id, campaign.organization_id
            ):
                issues.append(f"Workflow step {workflow.step_order} requires an active check-in template")
        eligible_count = self.repository.count_eligible_patients(campaign.organization_id, criteria) if criteria else 0
        return {
            "ready": not issues,
            "issues": issues,
            "eligible_patient_count": eligible_count,
            "workflow_count": len(workflows),
            "active_workflow_count": len(active),
        }

    def _serialize_campaign(self, campaign: OutreachCampaign, include_workflows: bool = False) -> dict[str, Any]:
        metadata = self._metadata(campaign)
        creator = self.repository.find_user(campaign.created_by_user_id)
        updater = self.repository.find_user(campaign.updated_by_user_id)
        result = {
            "campaign_id": campaign.campaign_id,
            "organization_id": campaign.organization_id,
            "campaign_name": campaign.campaign_name,
            "description": metadata.get("description"),
            "campaign_type": campaign.campaign_type.value,
            "cohort": metadata.get("criteria", metadata if "criteria" not in metadata else {}),
            "timezone": campaign.timezone,
            "start_at": campaign.start_at.isoformat() if campaign.start_at else None,
            "end_at": campaign.end_at.isoformat() if campaign.end_at else None,
            "status": campaign.status.value,
            "created_by": self._user_name(creator),
            "updated_by": self._user_name(updater),
            "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
            "updated_at": campaign.updated_at.isoformat() if campaign.updated_at else None,
            "readiness": self._readiness(campaign),
        }
        if include_workflows:
            result["workflows"] = [
                self._serialize_workflow(item, campaign.organization_id)
                for item in self.repository.list_workflows(campaign.campaign_id)
            ]
        return result

    def _serialize_workflow(self, workflow: OutreachWorkflow, organization_id: int) -> dict[str, Any]:
        template = (
            self.repository.find_active_template(workflow.checkin_template_id, organization_id)
            if workflow.checkin_template_id else None
        )
        configured = bool(workflow.is_active and template)
        return {
            **self._workflow_snapshot(workflow),
            "workflow_id": workflow.workflow_id,
            "campaign_id": workflow.campaign_id,
            "template_name": template.template_name if template else None,
            "configuration_status": "INACTIVE" if not workflow.is_active else ("READY" if configured else "INCOMPLETE"),
        }

    @staticmethod
    def _serialize_cohort_patient(row) -> dict[str, Any]:
        (
            profile,
            user,
            enrollment_program,
            enrollment_status,
            enrollment_date,
            episode_type,
            episode_status,
            trigger_type,
            episode_opened_at,
            episode_created_at,
        ) = row
        return {
            "patient_id": profile.patient_id,
            "external_fhir_patient_id": profile.external_fhir_patient_id,
            "patient_name": f"{user.first_name} {user.last_name}".strip(),
            "enrollment_program": enrollment_program.value,
            "enrollment_status": enrollment_status.value,
            "enrollment_date": enrollment_date.isoformat() if enrollment_date else None,
            "episode_type": episode_type.value,
            "episode_status": episode_status.value,
            "discharge_date": (
                episode_opened_at.isoformat()
                if trigger_type.value == "DISCHARGE" and episode_opened_at else None
            ),
            "episode_created_at": episode_created_at.isoformat() if episode_created_at else None,
        }

    def _workflow_payload(self, data: dict[str, Any], partial: bool = False) -> dict[str, Any]:
        payload = {key: value for key, value in data.items() if key in self.WORKFLOW_FIELDS}
        if not partial or "step_name" in payload:
            payload["step_name"] = self._required_text(payload.get("step_name"), "Step name")
        if "trigger_type" in payload:
            payload["trigger_type"] = self._enum(TriggerType, payload["trigger_type"], "trigger type")
        if "trigger_anchor" in payload:
            payload["trigger_anchor"] = self._enum(TriggerAnchor, payload["trigger_anchor"], "trigger anchor")
        if "channel" in payload:
            payload["channel"] = self._enum(OutreachChannel, payload["channel"], "channel")
        return payload

    def _validate_cohort(self, cohort: dict[str, Any]) -> dict[str, Any]:
        if hasattr(cohort, "model_dump"):
            cohort = cohort.model_dump()
        result = {
            "enrollment_statuses": self._enum_list(EnrollmentStatus, cohort.get("enrollment_statuses"), "enrollment status"),
            "enrollment_programs": self._enum_list(EnrollmentProgram, cohort.get("enrollment_programs"), "enrollment program"),
            "episode_types": self._enum_list(EpisodeType, cohort.get("episode_types"), "episode type"),
            "episode_statuses": self._enum_list(EpisodeStatus, cohort.get("episode_statuses"), "episode status"),
            "discharged_within_days": cohort.get("discharged_within_days"),
        }
        days = result["discharged_within_days"]
        if not isinstance(days, int) or not 1 <= days <= 365:
            raise ValidationException("Discharge window must be between 1 and 365 days", "INVALID_DISCHARGE_WINDOW")
        return result

    @staticmethod
    def _enum_list(enum_type, values, label: str) -> list[str]:
        if not values:
            raise ValidationException(f"At least one {label} is required", "INVALID_COHORT")
        try:
            return [enum_type(value).value for value in values]
        except ValueError as exc:
            raise ValidationException(f"Invalid {label}", "INVALID_COHORT") from exc

    @staticmethod
    def _metadata(campaign: OutreachCampaign) -> dict[str, Any]:
        value = campaign.target_cohort_definition or {}
        if "criteria" in value or "description" in value:
            return dict(value)
        return {"description": None, "criteria": dict(value)}

    @staticmethod
    def _snapshot(campaign: OutreachCampaign) -> dict[str, Any]:
        return {
            "campaign_name": campaign.campaign_name,
            "campaign_type": campaign.campaign_type.value,
            "target_cohort_definition": campaign.target_cohort_definition,
            "timezone": campaign.timezone,
            "start_at": campaign.start_at,
            "end_at": campaign.end_at,
            "status": campaign.status.value,
        }

    @staticmethod
    def _workflow_snapshot(workflow: OutreachWorkflow) -> dict[str, Any]:
        return {
            "step_order": workflow.step_order,
            "step_name": workflow.step_name,
            "trigger_type": workflow.trigger_type.value,
            "trigger_anchor": workflow.trigger_anchor.value,
            "trigger_offset_hours": workflow.trigger_offset_hours,
            "channel": workflow.channel.value,
            "template_text": workflow.template_text,
            "checkin_template_id": workflow.checkin_template_id,
            "escalation_on_no_response": workflow.escalation_on_no_response,
            "max_attempts": workflow.max_attempts,
            "retry_interval_minutes": workflow.retry_interval_minutes,
            "is_active": workflow.is_active,
        }

    def _require_admin(self, user_id: int):
        admin = self.repository.find_admin_user(user_id)
        if not admin:
            raise AuthorizationException("Active System Administrator access is required", "SYSTEM_ADMIN_ACCESS_REQUIRED")
        return admin

    def _require_campaign(self, campaign_id: int, organization_id: int) -> OutreachCampaign:
        campaign = self.repository.find_campaign(campaign_id, organization_id)
        if not campaign:
            raise NotFoundException("Campaign not found", "CAMPAIGN_NOT_FOUND")
        return campaign

    @staticmethod
    def _require_editable(campaign: OutreachCampaign) -> None:
        if campaign.status not in AdminOutreachCampaignService.EDITABLE_STATUSES:
            raise ValidationException("Pause the campaign before editing it", "CAMPAIGN_NOT_EDITABLE")

    def _require_template(self, template_id: int, organization_id: int):
        template = self.repository.find_active_template(template_id, organization_id)
        if not template:
            raise ValidationException("Select an active check-in template from this organization", "INVALID_CHECKIN_TEMPLATE")
        return template

    @staticmethod
    def _validate_dates(start_at, end_at) -> None:
        if start_at and end_at and end_at <= start_at:
            raise ValidationException("Campaign end date must be after its start date", "INVALID_CAMPAIGN_DATES")

    @staticmethod
    def _campaign_type(value: str) -> CampaignType:
        allowed = (CampaignType.POST_DISCHARGE, CampaignType.MEDICATION_ADHERENCE, CampaignType.APPOINTMENT_REMINDER)
        campaign_type = AdminOutreachCampaignService._enum(CampaignType, value, "campaign type")
        if campaign_type not in allowed:
            raise ValidationException("Campaign type is not available in this MVP", "INVALID_CAMPAIGN_TYPE")
        return campaign_type

    @staticmethod
    def _enum(enum_type, value, label: str):
        try:
            return value if isinstance(value, enum_type) else enum_type(value)
        except ValueError as exc:
            raise ValidationException(f"Invalid {label}", "INVALID_ENUM_VALUE") from exc

    @staticmethod
    def _required_text(value: str | None, label: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValidationException(f"{label} is required", "REQUIRED_FIELD")
        return cleaned

    @staticmethod
    def _optional_text(value: str | None) -> str | None:
        cleaned = value.strip() if value else ""
        return cleaned or None

    @staticmethod
    def _user_name(user) -> str | None:
        return f"{user.first_name} {user.last_name}" if user else None

    def _save(self, entity) -> None:
        try:
            self.repository.save(entity)
        except SQLAlchemyError as exc:
            raise ConflictException("Campaign configuration conflicts with existing data", "CAMPAIGN_CONFLICT") from exc