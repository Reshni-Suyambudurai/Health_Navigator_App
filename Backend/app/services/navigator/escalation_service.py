"""Business rules for the transitional-care nurse escalation queue."""

from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import AuthorizationException, ConflictException, NotFoundException, ValidationException
from app.database.models.escalation import Escalation, EscalationStatus
from app.database.models.escalation_action import EscalationAction, EscalationActionType
from app.database.models.escalation_assignment import EscalationAssignment
from app.database.models.role import RoleName
from app.database.repositories.navigator.escalation_repository import EscalationRepository


class EscalationService:
    """Coordinates queue access, case ownership, nurse actions, and resolution."""

    def __init__(self, db: Session):
        self.repository = EscalationRepository(db)

    def list_for_nurse(self, nurse_user_id: int, status: Optional[str] = None) -> list[dict]:
        nurse = self._nurse_context(nurse_user_id)
        escalation_status = self._parse_status(status) if status else None
        escalations = self.repository.list_escalations(nurse["staff_id"], escalation_status)
        return [self._serialize_summary(escalation) for escalation in escalations]

    def get_detail(self, nurse_user_id: int, escalation_id: int) -> dict:
        escalation = self._authorized_escalation(nurse_user_id, escalation_id)
        detail = self._serialize_summary(escalation)
        detail["patient_summary"] = escalation.patient_summary
        detail["actions"] = [self._serialize_action(action) for action in self.repository.list_actions(escalation_id)]
        return detail

    def claim(self, nurse_user_id: int, escalation_id: int) -> dict:
        nurse = self._nurse_context(nurse_user_id)
        escalation = self._authorized_escalation(nurse_user_id, escalation_id)
        if escalation.status in {EscalationStatus.RESOLVED, EscalationStatus.CLOSED}:
            raise ConflictException("Resolved escalations cannot be claimed.", "ESCALATION_ALREADY_RESOLVED")

        active_assignment = self.repository.find_active_assignment(escalation_id)
        if active_assignment and active_assignment.assigned_to_staff_id != nurse["staff_id"]:
            raise ConflictException("This escalation is already assigned to another staff member.", "ESCALATION_ALREADY_ASSIGNED")

        if not active_assignment:
            self.repository.add_assignment(
                EscalationAssignment(
                    escalation_id=escalation_id,
                    assigned_to_staff_id=nurse["staff_id"],
                    assigned_by_user_id=nurse_user_id,
                    assigned_at=self.repository.now(),
                    is_active=True,
                )
            )
            self._add_action(escalation_id, nurse_user_id, EscalationActionType.ASSIGN, "Escalation claimed by nurse.")

        escalation.status = EscalationStatus.IN_PROGRESS
        self._commit()
        return self.get_detail(nurse_user_id, escalation_id)

    def add_action(self, nurse_user_id: int, escalation_id: int, action_type: str, notes: Optional[str]) -> dict:
        self._authorized_escalation(nurse_user_id, escalation_id)
        try:
            parsed_action_type = EscalationActionType(action_type)
        except ValueError as exc:
            raise ValidationException("Unsupported escalation action type.", "INVALID_ESCALATION_ACTION") from exc

        if parsed_action_type in {EscalationActionType.ASSIGN, EscalationActionType.RESOLVED}:
            raise ValidationException("Use the claim or resolve endpoint for this action.", "INVALID_ESCALATION_ACTION")

        self._add_action(escalation_id, nurse_user_id, parsed_action_type, notes)
        self._commit()
        return self.get_detail(nurse_user_id, escalation_id)

    def resolve(self, nurse_user_id: int, escalation_id: int, notes: Optional[str]) -> dict:
        escalation = self._authorized_escalation(nurse_user_id, escalation_id)
        if escalation.status in {EscalationStatus.RESOLVED, EscalationStatus.CLOSED}:
            raise ConflictException("This escalation is already resolved.", "ESCALATION_ALREADY_RESOLVED")

        escalation.status = EscalationStatus.RESOLVED
        escalation.resolved_at = self.repository.now()
        self._add_action(escalation_id, nurse_user_id, EscalationActionType.RESOLVED, notes)
        self._commit()
        return self.get_detail(nurse_user_id, escalation_id)

    def _nurse_context(self, user_id: int) -> dict:
        user = self.repository.find_user_by_id(user_id)
        staff = self.repository.find_staff_by_user_id(user_id)
        if not user or not staff:
            raise AuthorizationException("A staff profile is required for the nurse queue.", "STAFF_PROFILE_REQUIRED")
        if not user.role or user.role.role_name != RoleName.TRANSITIONAL_CARE_NURSE:
            raise AuthorizationException("Only transitional-care nurses can work escalation queues.", "ESCALATION_NURSE_REQUIRED")
        return {"staff_id": staff.staff_id}

    def _authorized_escalation(self, user_id: int, escalation_id: int) -> Escalation:
        nurse = self._nurse_context(user_id)
        escalation = self.repository.find_escalation(escalation_id)
        if not escalation:
            raise NotFoundException("Escalation not found.", "ESCALATION_NOT_FOUND")
        if not self.repository.has_active_queue_membership(escalation.queue_id, nurse["staff_id"]):
            raise AuthorizationException("You do not have access to this escalation.", "ESCALATION_ACCESS_DENIED")
        return escalation

    def _serialize_summary(self, escalation: Escalation) -> dict:
        patient = self.repository.find_patient(escalation.patient_id)
        patient_user = self.repository.find_user_by_id(patient.user_id) if patient else None
        assignment = self.repository.find_active_assignment(escalation.escalation_id)
        assigned_staff = self.repository.find_staff_by_id(assignment.assigned_to_staff_id) if assignment else None
        assigned_user = self.repository.find_user_by_id(assigned_staff.user_id) if assigned_staff else None
        return {
            "escalation_id": escalation.escalation_id,
            "patient_id": escalation.patient_id,
            "patient_name": f"{patient_user.first_name} {patient_user.last_name}" if patient_user else "Unknown patient",
            "escalation_type": escalation.escalation_type.value,
            "priority": escalation.priority.value,
            "reason": escalation.reason or "Patient requested care-team support.",
            "status": escalation.status.value,
            "created_at": escalation.created_at.isoformat(),
            "resolved_at": escalation.resolved_at.isoformat() if escalation.resolved_at else None,
            "assigned_to": f"{assigned_user.first_name} {assigned_user.last_name}" if assigned_user else None,
        }

    @staticmethod
    def _serialize_action(action: EscalationAction) -> dict:
        return {"action_id": action.escalation_action_id, "action_type": action.action_type.value, "notes": action.action_notes, "action_at": action.action_at.isoformat()}

    def _add_action(self, escalation_id: int, user_id: int, action_type: EscalationActionType, notes: Optional[str]) -> None:
        self.repository.add_action(EscalationAction(escalation_id=escalation_id, action_by_user_id=user_id, action_type=action_type, action_notes=notes, action_at=self.repository.now()))

    def _commit(self) -> None:
        try:
            self.repository.commit()
        except Exception:
            self.repository.rollback()
            raise

    @staticmethod
    def _parse_status(status: str) -> EscalationStatus:
        try:
            return EscalationStatus(status.upper())
        except ValueError as exc:
            raise ValidationException("Unsupported escalation status.", "INVALID_ESCALATION_STATUS") from exc