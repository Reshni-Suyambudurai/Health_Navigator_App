"""Business rules for check-in template authoring and clinical review."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AuthorizationException, ConflictException, NotFoundException, ValidationException
from app.database.models.checkin_question import CheckinAnswerType, CheckinQuestion
from app.database.models.checkin_template import CheckinTemplate, CheckinTemplateStatus, CheckinTemplateType
from app.database.models.checkin_template_review import CheckinTemplateReview, CheckinTemplateReviewStatus
from app.database.models.notification import NotificationPriority, NotificationType
from app.database.models.role import RoleName
from app.database.repositories.navigator.admin_checkin_template_repository import AdminCheckinTemplateRepository
from app.services.notification_service import NotificationService


class AdminCheckinTemplateService:
    CHOICE_TYPES = {CheckinAnswerType.SINGLE_CHOICE, CheckinAnswerType.MULTIPLE_CHOICE}

    def __init__(self, db: Session):
        self.repository = AdminCheckinTemplateRepository(db)
        self.notifications = NotificationService(db)

    def list_templates(self, actor_user_id: int) -> dict[str, Any]:
        admin = self._require_role(actor_user_id, RoleName.SYSTEM_ADMIN)
        templates = self.repository.list_templates(admin.organization_id)
        return {"templates": [self._serialize_template(item) for item in templates]}

    def get_template(self, actor_user_id: int, template_id: int) -> dict[str, Any]:
        admin = self._require_role(actor_user_id, RoleName.SYSTEM_ADMIN)
        template = self._require_template(template_id, admin.organization_id)
        return self._serialize_template(template, include_questions=True)

    def create_template(self, actor_user_id: int, data: dict[str, Any]) -> dict[str, Any]:
        admin = self._require_role(actor_user_id, RoleName.SYSTEM_ADMIN)
        name = self._required_text(data["template_name"], "Template name")
        if self.repository.template_version_exists(admin.organization_id, name, 1):
            raise ConflictException("Template version 1 already exists", "TEMPLATE_VERSION_EXISTS")
        template = CheckinTemplate(
            organization_id=admin.organization_id,
            template_name=name,
            template_type=self._enum(CheckinTemplateType, data["template_type"], "template type"),
            description=self._optional_text(data.get("description")),
            version=1,
            status=CheckinTemplateStatus.DRAFT,
            created_by_user_id=admin.user_id,
        )
        self._save(template)
        return self._serialize_template(template, include_questions=True)

    def update_template(self, actor_user_id: int, template_id: int, data: dict[str, Any]) -> dict[str, Any]:
        admin = self._require_role(actor_user_id, RoleName.SYSTEM_ADMIN)
        template = self._require_template(template_id, admin.organization_id)
        self._require_editable(template)
        if "template_name" in data:
            name = self._required_text(data["template_name"], "Template name")
            if self.repository.template_version_exists(
                admin.organization_id, name, template.version, template.checkin_template_id
            ):
                raise ConflictException("Template version already exists", "TEMPLATE_VERSION_EXISTS")
            template.template_name = name
        if "template_type" in data:
            template.template_type = self._enum(CheckinTemplateType, data["template_type"], "template type")
        if "description" in data:
            template.description = self._optional_text(data["description"])
        self._save(template)
        return self._serialize_template(template, include_questions=True)

    def delete_template(self, actor_user_id: int, template_id: int) -> None:
        admin = self._require_role(actor_user_id, RoleName.SYSTEM_ADMIN)
        template = self._require_template(template_id, admin.organization_id)
        self._require_editable(template)
        if self.repository.latest_review(template_id) is not None:
            raise ConflictException("A template with review history cannot be deleted", "TEMPLATE_HAS_REVIEW_HISTORY")
        self.repository.delete(template)

    def create_question(self, actor_user_id: int, template_id: int, data: dict[str, Any]) -> dict[str, Any]:
        admin = self._require_role(actor_user_id, RoleName.SYSTEM_ADMIN)
        template = self._require_template(template_id, admin.organization_id)
        self._require_editable(template)
        key = self._required_text(data["question_key"], "Question key")
        if self.repository.question_key_exists(template_id, key):
            raise ConflictException("Question key already exists", "QUESTION_KEY_EXISTS")
        if self.repository.question_order_exists(template_id, data["display_order"]):
            raise ConflictException("Question display order already exists", "QUESTION_ORDER_EXISTS")
        answer_type = self._enum(CheckinAnswerType, data["answer_type"], "answer type")
        options = self._validate_options(answer_type, data.get("options"))
        question = CheckinQuestion(
            checkin_template_id=template_id,
            question_key=key,
            question_text=self._required_text(data["question_text"], "Question text"),
            answer_type=answer_type,
            options=options,
            display_order=data["display_order"],
            is_required=data.get("is_required", True),
            is_active=data.get("is_active", True),
        )
        self._save(question)
        return self._serialize_question(question)

    def update_question(self, actor_user_id: int, question_id: int, data: dict[str, Any]) -> dict[str, Any]:
        admin = self._require_role(actor_user_id, RoleName.SYSTEM_ADMIN)
        result = self.repository.find_question(question_id, admin.organization_id)
        if result is None:
            raise NotFoundException("Question not found", "QUESTION_NOT_FOUND")
        question, template = result
        self._require_editable(template)
        if "question_key" in data:
            key = self._required_text(data["question_key"], "Question key")
            if self.repository.question_key_exists(template.checkin_template_id, key, question_id):
                raise ConflictException("Question key already exists", "QUESTION_KEY_EXISTS")
            question.question_key = key
        if "display_order" in data and self.repository.question_order_exists(
            template.checkin_template_id, data["display_order"], question_id
        ):
            raise ConflictException("Question display order already exists", "QUESTION_ORDER_EXISTS")
        answer_type = (
            self._enum(CheckinAnswerType, data["answer_type"], "answer type")
            if "answer_type" in data else question.answer_type
        )
        options = data.get("options", question.options)
        question.answer_type = answer_type
        question.options = self._validate_options(answer_type, options)
        if "question_text" in data:
            question.question_text = self._required_text(data["question_text"], "Question text")
        if "display_order" in data:
            question.display_order = data["display_order"]
        if "is_required" in data:
            question.is_required = data["is_required"]
        if "is_active" in data:
            question.is_active = data["is_active"]
        self._save(question)
        return self._serialize_question(question)

    def delete_question(self, actor_user_id: int, question_id: int) -> None:
        admin = self._require_role(actor_user_id, RoleName.SYSTEM_ADMIN)
        result = self.repository.find_question(question_id, admin.organization_id)
        if result is None:
            raise NotFoundException("Question not found", "QUESTION_NOT_FOUND")
        question, template = result
        self._require_editable(template)
        self.repository.delete(question)

    def reorder_questions(self, actor_user_id: int, template_id: int, question_ids: list[int]) -> list[dict[str, Any]]:
        admin = self._require_role(actor_user_id, RoleName.SYSTEM_ADMIN)
        template = self._require_template(template_id, admin.organization_id)
        self._require_editable(template)
        questions = self.repository.list_questions(template_id)
        existing_ids = [question.question_id for question in questions]
        if len(question_ids) != len(set(question_ids)) or set(question_ids) != set(existing_ids):
            raise ValidationException("Question order must contain every question exactly once", "INVALID_QUESTION_ORDER")
        self.repository.reorder_questions(questions, question_ids)
        return [self._serialize_question(question) for question in self.repository.list_questions(template_id)]

    def submit_review(self, actor_user_id: int, template_id: int, submission_note: str | None) -> dict[str, Any]:
        admin = self._require_role(actor_user_id, RoleName.SYSTEM_ADMIN)
        template = self._require_template(template_id, admin.organization_id)
        self._require_editable(template)
        questions = self.repository.list_questions(template_id)
        self._validate_template_questions(questions)
        review = CheckinTemplateReview(
            checkin_template_id=template_id,
            submitted_by_user_id=admin.user_id,
            status=CheckinTemplateReviewStatus.PENDING,
            submission_note=self._optional_text(submission_note),
        )
        notifications = self.notifications.prepare_for_role(
            sender_user_id=admin.user_id,
            organization_id=admin.organization_id,
            role_name=RoleName.CLINICAL_GOVERNANCE,
            title="Check-in template review requested",
            message=f"{template.template_name} v{template.version} was submitted for clinical review.",
            notification_type=NotificationType.FOLLOW_UP,
            priority=NotificationPriority.HIGH,
        )
        if not notifications:
            raise ValidationException(
                "No active Clinical Governance reviewer is available for this organization",
                "CLINICAL_REVIEWER_REQUIRED",
            )
        try:
            self.repository.save_all([review, *notifications])
        except SQLAlchemyError as exc:
            raise ConflictException(
                "Template review and notifications could not be submitted",
                "TEMPLATE_REVIEW_SUBMISSION_FAILED",
            ) from exc
        return self._serialize_review(review, template)

    def clone_version(self, actor_user_id: int, template_id: int) -> dict[str, Any]:
        admin = self._require_role(actor_user_id, RoleName.SYSTEM_ADMIN)
        source = self._require_template(template_id, admin.organization_id)
        latest_review = self.repository.latest_review(template_id)
        if (
            source.status != CheckinTemplateStatus.ACTIVE
            or latest_review is None
            or latest_review.status != CheckinTemplateReviewStatus.APPROVED
        ):
            raise ValidationException("Only an approved active template can be versioned", "TEMPLATE_NOT_APPROVED")
        version = self.repository.next_version(admin.organization_id, source.template_name)
        target = CheckinTemplate(
            organization_id=admin.organization_id,
            template_name=source.template_name,
            template_type=source.template_type,
            description=source.description,
            version=version,
            status=CheckinTemplateStatus.DRAFT,
            created_by_user_id=admin.user_id,
        )
        try:
            target = self.repository.clone_version(source, target, self.repository.list_questions(template_id))
        except SQLAlchemyError as exc:
            raise ConflictException("Template version could not be created", "TEMPLATE_VERSION_CONFLICT") from exc
        return self._serialize_template(target, include_questions=True)

    def list_pending_reviews(self, actor_user_id: int) -> dict[str, Any]:
        reviewer = self._require_role(actor_user_id, RoleName.CLINICAL_GOVERNANCE)
        items = self.repository.list_pending_reviews(reviewer.organization_id)
        return {"reviews": [self._serialize_review(review, template, True) for review, template in items]}

    def list_reviews(self, actor_user_id: int, status: str | None = None, organization_id: int | None = None) -> dict[str, Any]:
        reviewer_user = self._require_role(actor_user_id, RoleName.CLINICAL_GOVERNANCE)
        selected_organization_id = organization_id or reviewer_user.organization_id
        if not self.repository.organization_exists(selected_organization_id):
            raise NotFoundException("Organization not found", "ORGANIZATION_NOT_FOUND")
        review_status = None if not status or status == "ALL" else self._enum(CheckinTemplateReviewStatus, status, "review status")
        items = self.repository.list_reviews(selected_organization_id, review_status)
        reviews = []
        for review, template, submitter_first, submitter_last, reviewer_first, reviewer_last in items:
            item = self._serialize_review(review, template, True)
            item["submitted_by_name"] = f"{submitter_first} {submitter_last}"
            item["reviewed_by_name"] = f"{reviewer_first} {reviewer_last}" if reviewer_first else None
            reviews.append(item)
        organizations = [
            {"organization_id": organization.organization_id, "organization_name": organization.organization_name}
            for organization in self.repository.list_active_organizations()
        ]
        return {"reviews": reviews, "organizations": organizations, "selected_organization_id": selected_organization_id}

    def get_review(self, actor_user_id: int, review_id: int) -> dict[str, Any]:
        reviewer = self._require_role(actor_user_id, RoleName.CLINICAL_GOVERNANCE)
        result = self.repository.find_review(review_id)
        if result is None:
            raise NotFoundException("Template review not found", "TEMPLATE_REVIEW_NOT_FOUND")
        review, template = result
        return self._serialize_review(review, template, True)

    def decide_review(
        self,
        actor_user_id: int,
        review_id: int,
        decision: str,
        review_notes: str,
    ) -> dict[str, Any]:
        reviewer = self._require_role(actor_user_id, RoleName.CLINICAL_GOVERNANCE)
        result = self.repository.find_review(review_id)
        if result is None:
            raise NotFoundException("Template review not found", "TEMPLATE_REVIEW_NOT_FOUND")
        review, template = result
        if review.status != CheckinTemplateReviewStatus.PENDING:
            raise ConflictException("This review has already been decided", "REVIEW_ALREADY_DECIDED")
        approved = decision == CheckinTemplateReviewStatus.APPROVED.value
        if approved:
            self._validate_template_questions(self.repository.list_questions(template.checkin_template_id))
        clean_notes = self._required_text(review_notes, "Review notes")
        decision_label = "approved" if approved else "changes requested"
        notifications = self.notifications.prepare_for_role(
            sender_user_id=reviewer.user_id,
            organization_id=template.organization_id,
            role_name=RoleName.SYSTEM_ADMIN,
            title=f"Check-in template {decision_label}",
            message=(
                f"{template.template_name} v{template.version}: {decision_label}. "
                f"Review notes: {clean_notes}"
            ),
            notification_type=NotificationType.FOLLOW_UP,
            priority=NotificationPriority.NORMAL if approved else NotificationPriority.HIGH,
        )
        if not notifications:
            raise ValidationException(
                "No active System Administrator is available for this organization",
                "SYSTEM_ADMIN_RECIPIENT_REQUIRED",
            )
        review.status = CheckinTemplateReviewStatus.APPROVED if approved else CheckinTemplateReviewStatus.REJECTED
        review.reviewed_by_user_id = reviewer.user_id
        review.review_notes = clean_notes
        review.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.repository.decide_review(review, template, approved, notifications)
        return self._serialize_review(review, template, True)

    def _require_role(self, user_id: int, role_name: RoleName):
        user = self.repository.find_active_user_with_role(user_id, role_name)
        if user is None:
            raise AuthorizationException(f"Active {role_name.value.replace('_', ' ').title()} access is required")
        return user

    def _require_template(self, template_id: int, organization_id: int) -> CheckinTemplate:
        template = self.repository.find_template(template_id, organization_id)
        if template is None:
            raise NotFoundException("Check-in template not found", "CHECKIN_TEMPLATE_NOT_FOUND")
        return template

    def _require_editable(self, template: CheckinTemplate) -> None:
        if template.status != CheckinTemplateStatus.DRAFT:
            raise ConflictException("Approved template versions are immutable", "TEMPLATE_IMMUTABLE")
        pending = self.repository.find_pending_review(template.checkin_template_id)
        if pending is not None:
            raise ConflictException("Template cannot be changed while clinical review is pending", "REVIEW_PENDING")

    def _validate_template_questions(self, questions: list[CheckinQuestion]) -> None:
        active = [question for question in questions if question.is_active]
        if not active:
            raise ValidationException("At least one active question is required", "TEMPLATE_QUESTIONS_REQUIRED")
        for question in active:
            self._required_text(question.question_text, "Question text")
            self._validate_options(question.answer_type, question.options)

    def _validate_options(self, answer_type: CheckinAnswerType, options: Any) -> list[str] | None:
        if answer_type not in self.CHOICE_TYPES:
            if options not in (None, []):
                raise ValidationException("Options are only allowed for choice questions", "OPTIONS_NOT_ALLOWED")
            return None
        if not isinstance(options, list):
            raise ValidationException("Choice questions require options", "OPTIONS_REQUIRED")
        cleaned = [str(option).strip() for option in options if str(option).strip()]
        if len(cleaned) < 2 or len({option.casefold() for option in cleaned}) != len(cleaned):
            raise ValidationException("Provide at least two unique nonblank options", "INVALID_OPTIONS")
        return cleaned

    def _save(self, entity) -> None:
        try:
            self.repository.save(entity)
        except SQLAlchemyError as exc:
            raise ConflictException("Template data conflicts with existing data", "TEMPLATE_DATA_CONFLICT") from exc

    @staticmethod
    def _enum(enum_type, value: str, label: str):
        try:
            return enum_type(value)
        except ValueError as exc:
            raise ValidationException(f"Invalid {label}") from exc

    @staticmethod
    def _required_text(value: Any, label: str) -> str:
        text = str(value).strip() if value is not None else ""
        if not text:
            raise ValidationException(f"{label} is required")
        return text

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value is None:
            return None
        return str(value).strip() or None

    def _serialize_template(self, template: CheckinTemplate, include_questions: bool = False) -> dict[str, Any]:
        latest_review = self.repository.latest_review(template.checkin_template_id)
        result = {
            "checkin_template_id": template.checkin_template_id,
            "template_name": template.template_name,
            "template_type": template.template_type.value,
            "description": template.description,
            "version": template.version,
            "status": template.status.value,
            "review_status": latest_review.status.value if latest_review else None,
            "review_id": latest_review.review_id if latest_review else None,
            "review_notes": latest_review.review_notes if latest_review else None,
            "is_editable": template.status == CheckinTemplateStatus.DRAFT and (
                latest_review is None or latest_review.status != CheckinTemplateReviewStatus.PENDING
            ),
            "created_at": template.created_at.isoformat() if template.created_at else None,
            "updated_at": template.updated_at.isoformat() if template.updated_at else None,
        }
        if include_questions:
            result["questions"] = [
                self._serialize_question(question) for question in self.repository.list_questions(template.checkin_template_id)
            ]
        return result

    @staticmethod
    def _serialize_question(question: CheckinQuestion) -> dict[str, Any]:
        return {
            "question_id": question.question_id,
            "question_key": question.question_key,
            "question_text": question.question_text,
            "answer_type": question.answer_type.value,
            "options": question.options,
            "display_order": question.display_order,
            "is_required": question.is_required,
            "is_active": question.is_active,
        }

    def _serialize_review(
        self,
        review: CheckinTemplateReview,
        template: CheckinTemplate,
        include_questions: bool = False,
    ) -> dict[str, Any]:
        result = {
            "review_id": review.review_id,
            "status": review.status.value,
            "submission_note": review.submission_note,
            "review_notes": review.review_notes,
            "submitted_by_user_id": review.submitted_by_user_id,
            "reviewed_by_user_id": review.reviewed_by_user_id,
            "submitted_at": review.submitted_at.isoformat() if review.submitted_at else None,
            "reviewed_at": review.reviewed_at.isoformat() if review.reviewed_at else None,
            "template": self._serialize_template(template, include_questions),
        }
        return result