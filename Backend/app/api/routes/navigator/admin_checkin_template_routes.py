"""Role-scoped routes for check-in template authoring and clinical review."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.response_models import SuccessResponse
from app.database.connection import get_db
from app.schemas.admin_checkin_template import (
    AdminCheckinQuestionRequest,
    AdminCheckinQuestionUpdateRequest,
    AdminCheckinTemplateCreateRequest,
    AdminCheckinTemplateUpdateRequest,
    AdminQuestionReorderRequest,
    TemplateReviewDecisionRequest,
    TemplateReviewSubmissionRequest,
)
from app.services.navigator.admin_checkin_template_service import AdminCheckinTemplateService


admin_router = APIRouter(prefix="/admin/checkin-templates", tags=["System Admin Check-in Templates"])
review_router = APIRouter(
    prefix="/clinical-governance/checkin-template-reviews",
    tags=["Clinical Governance Check-in Template Reviews"],
)


@admin_router.get("", response_model=SuccessResponse)
def list_templates(user_id: int, db: Session = Depends(get_db)):
    data = AdminCheckinTemplateService(db).list_templates(user_id)
    return SuccessResponse(message="Check-in templates retrieved successfully", data=data)


@admin_router.post("", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: AdminCheckinTemplateCreateRequest,
    user_id: int,
    db: Session = Depends(get_db),
):
    data = AdminCheckinTemplateService(db).create_template(user_id, payload.model_dump())
    return SuccessResponse(message="Check-in template saved as draft", data=data)


@admin_router.get("/{template_id}", response_model=SuccessResponse)
def get_template(template_id: int, user_id: int, db: Session = Depends(get_db)):
    data = AdminCheckinTemplateService(db).get_template(user_id, template_id)
    return SuccessResponse(message="Check-in template retrieved successfully", data=data)


@admin_router.put("/{template_id}", response_model=SuccessResponse)
def update_template(
    template_id: int,
    payload: AdminCheckinTemplateUpdateRequest,
    user_id: int,
    db: Session = Depends(get_db),
):
    data = AdminCheckinTemplateService(db).update_template(
        user_id, template_id, payload.model_dump(exclude_unset=True)
    )
    return SuccessResponse(message="Check-in template updated successfully", data=data)


@admin_router.delete("/{template_id}", response_model=SuccessResponse)
def delete_template(template_id: int, user_id: int, db: Session = Depends(get_db)):
    AdminCheckinTemplateService(db).delete_template(user_id, template_id)
    return SuccessResponse(message="Draft check-in template deleted successfully", data=None)


@admin_router.post("/{template_id}/questions", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
def create_question(
    template_id: int,
    payload: AdminCheckinQuestionRequest,
    user_id: int,
    db: Session = Depends(get_db),
):
    data = AdminCheckinTemplateService(db).create_question(user_id, template_id, payload.model_dump())
    return SuccessResponse(message="Question added successfully", data=data)


@admin_router.put("/questions/{question_id}", response_model=SuccessResponse)
def update_question(
    question_id: int,
    payload: AdminCheckinQuestionUpdateRequest,
    user_id: int,
    db: Session = Depends(get_db),
):
    data = AdminCheckinTemplateService(db).update_question(
        user_id, question_id, payload.model_dump(exclude_unset=True)
    )
    return SuccessResponse(message="Question updated successfully", data=data)


@admin_router.delete("/questions/{question_id}", response_model=SuccessResponse)
def delete_question(question_id: int, user_id: int, db: Session = Depends(get_db)):
    AdminCheckinTemplateService(db).delete_question(user_id, question_id)
    return SuccessResponse(message="Question deleted successfully", data=None)


@admin_router.put("/{template_id}/questions/reorder", response_model=SuccessResponse)
def reorder_questions(
    template_id: int,
    payload: AdminQuestionReorderRequest,
    user_id: int,
    db: Session = Depends(get_db),
):
    questions = AdminCheckinTemplateService(db).reorder_questions(user_id, template_id, payload.question_ids)
    return SuccessResponse(message="Questions reordered successfully", data={"questions": questions})


@admin_router.post("/{template_id}/submit-review", response_model=SuccessResponse)
def submit_review(
    template_id: int,
    payload: TemplateReviewSubmissionRequest,
    user_id: int,
    db: Session = Depends(get_db),
):
    data = AdminCheckinTemplateService(db).submit_review(user_id, template_id, payload.submission_note)
    return SuccessResponse(message="Template submitted for clinical review", data=data)


@admin_router.post("/{template_id}/versions", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
def create_version(template_id: int, user_id: int, db: Session = Depends(get_db)):
    data = AdminCheckinTemplateService(db).clone_version(user_id, template_id)
    return SuccessResponse(message="New draft version created", data=data)


@review_router.get("", response_model=SuccessResponse)
def list_pending_reviews(user_id: int, db: Session = Depends(get_db)):
    data = AdminCheckinTemplateService(db).list_pending_reviews(user_id)
    return SuccessResponse(message="Pending template reviews retrieved successfully", data=data)


@review_router.get("/{review_id}", response_model=SuccessResponse)
def get_review(review_id: int, user_id: int, db: Session = Depends(get_db)):
    data = AdminCheckinTemplateService(db).get_review(user_id, review_id)
    return SuccessResponse(message="Template review retrieved successfully", data=data)


@review_router.post("/{review_id}/decision", response_model=SuccessResponse)
def decide_review(
    review_id: int,
    payload: TemplateReviewDecisionRequest,
    user_id: int,
    db: Session = Depends(get_db),
):
    data = AdminCheckinTemplateService(db).decide_review(
        user_id, review_id, payload.decision, payload.review_notes
    )
    return SuccessResponse(message=f"Template review {payload.decision.lower()}", data=data)