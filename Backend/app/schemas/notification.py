"""Notification API request contracts."""

from typing import Literal

from pydantic import BaseModel, Field


class NotificationCreateRequest(BaseModel):
    recipient_user_id: int = Field(gt=0)
    title: str | None = Field(default=None, max_length=255)
    message: str = Field(min_length=1)
    notification_type: Literal[
        "GENERAL",
        "ESCALATION",
        "APPOINTMENT_REMINDER",
        "OUTREACH_UPDATE",
        "FOLLOW_UP",
        "SYSTEM_ALERT",
    ] = "GENERAL"
    priority: Literal["LOW", "NORMAL", "HIGH", "URGENT"] = "NORMAL"