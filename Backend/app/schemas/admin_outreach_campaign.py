"""Request contracts for System Admin outreach campaign configuration."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CohortCriteriaRequest(BaseModel):
    enrollment_statuses: list[str] = Field(min_length=1)
    enrollment_programs: list[str] = Field(min_length=1)
    episode_types: list[str] = Field(min_length=1)
    episode_statuses: list[str] = Field(min_length=1)
    discharged_within_days: int = Field(ge=1, le=365)


class AdminCampaignCreateRequest(BaseModel):
    campaign_name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    campaign_type: Literal["POST_DISCHARGE", "MEDICATION_ADHERENCE", "APPOINTMENT_REMINDER"]
    timezone: str = Field(default="UTC", min_length=1, max_length=100)
    start_at: datetime | None = None
    end_at: datetime | None = None
    cohort: CohortCriteriaRequest


class AdminCampaignUpdateRequest(BaseModel):
    campaign_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    campaign_type: Literal["POST_DISCHARGE", "MEDICATION_ADHERENCE", "APPOINTMENT_REMINDER"] | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=100)
    start_at: datetime | None = None
    end_at: datetime | None = None
    cohort: CohortCriteriaRequest | None = None


class AdminCampaignStatusRequest(BaseModel):
    status: Literal["ACTIVE", "PAUSED", "COMPLETED"]


class AdminWorkflowRequest(BaseModel):
    step_order: int = Field(gt=0)
    step_name: str = Field(min_length=1, max_length=255)
    trigger_type: Literal["AFTER_DISCHARGE", "BEFORE_APPOINTMENT", "AFTER_EVENT"]
    trigger_anchor: Literal["DISCHARGE_DATETIME", "APPOINTMENT_DATETIME", "EVENT_DATETIME"]
    trigger_offset_hours: int = Field(default=0, ge=0)
    channel: Literal["SMS", "CALL", "PHONE", "EMAIL", "PORTAL"]
    template_text: str | None = None
    checkin_template_id: int = Field(gt=0)
    escalation_on_no_response: bool = False
    max_attempts: int = Field(default=3, gt=0)
    retry_interval_minutes: int = Field(default=30, ge=0)
    is_active: bool = True


class AdminWorkflowUpdateRequest(BaseModel):
    step_order: int | None = Field(default=None, gt=0)
    step_name: str | None = Field(default=None, min_length=1, max_length=255)
    trigger_type: Literal["AFTER_DISCHARGE", "BEFORE_APPOINTMENT", "AFTER_EVENT"] | None = None
    trigger_anchor: Literal["DISCHARGE_DATETIME", "APPOINTMENT_DATETIME", "EVENT_DATETIME"] | None = None
    trigger_offset_hours: int | None = Field(default=None, ge=0)
    channel: Literal["SMS", "CALL", "PHONE", "EMAIL", "PORTAL"] | None = None
    template_text: str | None = None
    checkin_template_id: int | None = Field(default=None, gt=0)
    escalation_on_no_response: bool | None = None
    max_attempts: int | None = Field(default=None, gt=0)
    retry_interval_minutes: int | None = Field(default=None, ge=0)
    is_active: bool | None = None