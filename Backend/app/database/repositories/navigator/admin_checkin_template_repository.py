"""Database operations for authorized check-in template management."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.models.checkin_question import CheckinQuestion
from app.database.models.checkin_template import CheckinTemplate, CheckinTemplateStatus
from app.database.models.checkin_template_review import CheckinTemplateReview, CheckinTemplateReviewStatus
from app.database.models.role import Role, RoleName
from app.database.models.user import User, UserStatus


class AdminCheckinTemplateRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_active_user_with_role(self, user_id: int, role_name: RoleName) -> User | None:
        return (
            self.db.query(User)
            .join(Role, User.role_id == Role.role_id)
            .filter(
                User.user_id == user_id,
                User.status == UserStatus.ACTIVE,
                Role.role_name == role_name,
            )
            .one_or_none()
        )

    def list_templates(self, organization_id: int) -> list[CheckinTemplate]:
        return (
            self.db.query(CheckinTemplate)
            .filter(CheckinTemplate.organization_id == organization_id)
            .order_by(CheckinTemplate.template_name.asc(), CheckinTemplate.version.desc())
            .all()
        )

    def find_template(self, template_id: int, organization_id: int) -> CheckinTemplate | None:
        return (
            self.db.query(CheckinTemplate)
            .filter(
                CheckinTemplate.checkin_template_id == template_id,
                CheckinTemplate.organization_id == organization_id,
            )
            .one_or_none()
        )

    def template_version_exists(
        self,
        organization_id: int,
        template_name: str,
        version: int,
        excluded_template_id: int | None = None,
    ) -> bool:
        query = self.db.query(CheckinTemplate.checkin_template_id).filter(
            CheckinTemplate.organization_id == organization_id,
            func.lower(CheckinTemplate.template_name) == template_name.lower(),
            CheckinTemplate.version == version,
        )
        if excluded_template_id is not None:
            query = query.filter(CheckinTemplate.checkin_template_id != excluded_template_id)
        return query.first() is not None

    def next_version(self, organization_id: int, template_name: str) -> int:
        latest = (
            self.db.query(func.max(CheckinTemplate.version))
            .filter(
                CheckinTemplate.organization_id == organization_id,
                func.lower(CheckinTemplate.template_name) == template_name.lower(),
            )
            .scalar()
        )
        return (latest or 0) + 1

    def list_questions(self, template_id: int) -> list[CheckinQuestion]:
        return (
            self.db.query(CheckinQuestion)
            .filter(CheckinQuestion.checkin_template_id == template_id)
            .order_by(CheckinQuestion.display_order.asc())
            .all()
        )

    def find_question(self, question_id: int, organization_id: int):
        return (
            self.db.query(CheckinQuestion, CheckinTemplate)
            .join(CheckinTemplate, CheckinTemplate.checkin_template_id == CheckinQuestion.checkin_template_id)
            .filter(
                CheckinQuestion.question_id == question_id,
                CheckinTemplate.organization_id == organization_id,
            )
            .one_or_none()
        )

    def question_key_exists(
        self,
        template_id: int,
        question_key: str,
        excluded_question_id: int | None = None,
    ) -> bool:
        query = self.db.query(CheckinQuestion.question_id).filter(
            CheckinQuestion.checkin_template_id == template_id,
            func.lower(CheckinQuestion.question_key) == question_key.lower(),
        )
        if excluded_question_id is not None:
            query = query.filter(CheckinQuestion.question_id != excluded_question_id)
        return query.first() is not None

    def question_order_exists(
        self,
        template_id: int,
        display_order: int,
        excluded_question_id: int | None = None,
    ) -> bool:
        query = self.db.query(CheckinQuestion.question_id).filter(
            CheckinQuestion.checkin_template_id == template_id,
            CheckinQuestion.display_order == display_order,
        )
        if excluded_question_id is not None:
            query = query.filter(CheckinQuestion.question_id != excluded_question_id)
        return query.first() is not None

    def latest_review(self, template_id: int) -> CheckinTemplateReview | None:
        return (
            self.db.query(CheckinTemplateReview)
            .filter(CheckinTemplateReview.checkin_template_id == template_id)
            .order_by(CheckinTemplateReview.created_at.desc(), CheckinTemplateReview.review_id.desc())
            .first()
        )

    def find_pending_review(self, template_id: int) -> CheckinTemplateReview | None:
        return (
            self.db.query(CheckinTemplateReview)
            .filter(
                CheckinTemplateReview.checkin_template_id == template_id,
                CheckinTemplateReview.status == CheckinTemplateReviewStatus.PENDING,
            )
            .one_or_none()
        )

    def list_pending_reviews(self, organization_id: int) -> list[tuple[CheckinTemplateReview, CheckinTemplate]]:
        return (
            self.db.query(CheckinTemplateReview, CheckinTemplate)
            .join(CheckinTemplate, CheckinTemplate.checkin_template_id == CheckinTemplateReview.checkin_template_id)
            .filter(
                CheckinTemplate.organization_id == organization_id,
                CheckinTemplateReview.status == CheckinTemplateReviewStatus.PENDING,
            )
            .order_by(CheckinTemplateReview.submitted_at.asc())
            .all()
        )

    def find_review(self, review_id: int, organization_id: int):
        return (
            self.db.query(CheckinTemplateReview, CheckinTemplate)
            .join(CheckinTemplate, CheckinTemplate.checkin_template_id == CheckinTemplateReview.checkin_template_id)
            .filter(
                CheckinTemplateReview.review_id == review_id,
                CheckinTemplate.organization_id == organization_id,
            )
            .one_or_none()
        )

    def save(self, entity):
        try:
            self.db.add(entity)
            self.db.commit()
            self.db.refresh(entity)
            return entity
        except Exception:
            self.db.rollback()
            raise

    def save_all(self, entities: list) -> None:
        try:
            self.db.add_all(entities)
            self.db.commit()
            for entity in entities:
                self.db.refresh(entity)
        except Exception:
            self.db.rollback()
            raise

    def delete(self, entity) -> None:
        try:
            self.db.delete(entity)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def reorder_questions(self, questions: list[CheckinQuestion], ordered_ids: list[int]) -> None:
        try:
            offset = max(question.display_order for question in questions) + len(questions)
            for temporary_order, question in enumerate(questions, start=1):
                question.display_order = offset + temporary_order
            self.db.flush()
            lookup = {question.question_id: question for question in questions}
            for order, question_id in enumerate(ordered_ids, start=1):
                lookup[question_id].display_order = order
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def clone_version(
        self,
        source: CheckinTemplate,
        target: CheckinTemplate,
        questions: list[CheckinQuestion],
    ) -> CheckinTemplate:
        try:
            self.db.add(target)
            self.db.flush()
            for question in questions:
                self.db.add(CheckinQuestion(
                    checkin_template_id=target.checkin_template_id,
                    question_key=question.question_key,
                    question_text=question.question_text,
                    answer_type=question.answer_type,
                    options=question.options,
                    display_order=question.display_order,
                    is_required=question.is_required,
                    is_active=question.is_active,
                ))
            self.db.commit()
            self.db.refresh(target)
            return target
        except Exception:
            self.db.rollback()
            raise

    def decide_review(
        self,
        review: CheckinTemplateReview,
        template: CheckinTemplate,
        approve: bool,
        notifications: list,
    ) -> None:
        try:
            if approve:
                active_versions = self.db.query(CheckinTemplate).filter(
                    CheckinTemplate.organization_id == template.organization_id,
                    func.lower(CheckinTemplate.template_name) == template.template_name.lower(),
                    CheckinTemplate.status == CheckinTemplateStatus.ACTIVE,
                    CheckinTemplate.checkin_template_id != template.checkin_template_id,
                ).all()
                for active in active_versions:
                    active.status = CheckinTemplateStatus.INACTIVE
                template.status = CheckinTemplateStatus.ACTIVE
            self.db.add_all(notifications)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise