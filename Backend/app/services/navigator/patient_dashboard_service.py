"""Business logic for patient-safe dashboard summary data."""

from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.database.repositories.navigator.patient_dashboard_repository import PatientDashboardRepository


class PatientDashboardService:
    def __init__(self, db: Session):
        self.repository = PatientDashboardRepository(db)

    def get_care_snapshot(self, user_id: int) -> dict[str, Any]:
        patient = self.repository.find_patient_by_user_id(user_id)
        if not patient:
            raise NotFoundException("Patient profile not found for this user.", "DASHBOARD_PATIENT_NOT_FOUND")

        episode = self.repository.find_active_episode(patient.patient_id)
        care_team = []
        if episode and episode.owner_staff_id:
            owner = self.repository.find_staff_user(episode.owner_staff_id)
            if owner:
                care_team.append(self._care_team_member(owner))
        elif episode:
            care_team = [self._care_team_member(user) for user in self.repository.list_clinical_queue_users(episode.enrollment_id)]

        return {
            "risk_tier": patient.risk_tier.value if patient.risk_tier else None,
            "episode_status": episode.status.value if episode else None,
            "care_team": care_team,
        }

    @staticmethod
    def _care_team_member(user) -> dict[str, Any]:
        return {
            "user_id": user.user_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "role_name": "TRANSITIONAL_CARE_NURSE",
        }