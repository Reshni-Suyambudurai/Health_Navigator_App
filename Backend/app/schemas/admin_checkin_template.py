"""Contracts for check-in template administration and clinical review."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class AdminCheckinTemplateCreateRequest(BaseModel):
    template_name: str = Field(min_length=1, max_length=255)
    template_type: Literal["POST_DISCHARGE", "CHRONIC_CARE", "MEDICATION_FOLLOWUP"]
    description: str | None = Field(default=None, max_length=2000)


class AdminCheckinTemplateUpdateRequest(BaseModel):
    template_name: str | None = Field(default=None, min_length=1, max_length=255)
    template_type: Literal["POST_DISCHARGE", "CHRONIC_CARE", "MEDICATION_FOLLOWUP"] | None = None
    description: str | None = Field(default=None, max_length=2000)


class AdminCheckinQuestionRequest(BaseModel):
    question_key: str = Field(min_length=1, max_length=100)
    question_text: str = Field(min_length=1, max_length=2000)
    answer_type: Literal["YES_NO", "TEXT", "NUMBER", "SINGLE_CHOICE", "MULTIPLE_CHOICE"]
    options: list[Any] | None = None
    display_order: int = Field(gt=0)
    is_required: bool = True
    is_active: bool = True


class AdminCheckinQuestionUpdateRequest(BaseModel):
    question_key: str | None = Field(default=None, min_length=1, max_length=100)
    question_text: str | None = Field(default=None, min_length=1, max_length=2000)
    answer_type: Literal["YES_NO", "TEXT", "NUMBER", "SINGLE_CHOICE", "MULTIPLE_CHOICE"] | None = None
    options: list[Any] | None = None
    display_order: int | None = Field(default=None, gt=0)
    is_required: bool | None = None
    is_active: bool | None = None


class AdminQuestionReorderRequest(BaseModel):
    question_ids: list[int] = Field(min_length=1)


class TemplateReviewSubmissionRequest(BaseModel):
    submission_note: str | None = Field(default=None, max_length=1000)


class TemplateReviewDecisionRequest(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    review_notes: str = Field(min_length=1, max_length=4000)