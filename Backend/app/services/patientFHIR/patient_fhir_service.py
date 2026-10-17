"""
Service layer for read-only PatientFHIR operations.
"""

from datetime import date
from typing import Any, Dict, List
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException, PatientFHIRException
from app.database.repositories.patientFHIR.patient_fhir_repository import PatientFHIRRepository


class PatientFHIRService:
    """Business service for Monster PatientFHIR data retrieval."""

    def __init__(self, db: Session):
        self.repository = PatientFHIRRepository(db)

    def _repo_call(self, operation: str, repository_method, *args, **kwargs):
        """Execute repository call and normalize Monster data-source failures."""
        try:
            return repository_method(*args, **kwargs)
        except NotFoundException:
            raise
        except Exception as exc:
            raise PatientFHIRException(
                f"Failed to fetch PatientFHIR data during '{operation}'",
                error_code="PATIENT_FHIR_003",
            ) from exc

    @staticmethod
    def _patient_display_name(patient: Dict[str, Any]) -> str:
        name_parts = [
            patient.get("first_name"),
            patient.get("middle_name"),
            patient.get("last_name"),
        ]
        return " ".join(part for part in name_parts if part) or "Unknown"

    @staticmethod
    def _age_from_dob(date_of_birth: Any) -> int | None:
        if not isinstance(date_of_birth, date):
            return None
        today = date.today()
        return today.year - date_of_birth.year - (
            (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
        )

    def _ensure_patient_exists(self, patient_id: str) -> Dict[str, Any]:
        patient = self._repo_call("find_patient_by_id", self.repository.find_patient_by_id, patient_id)
        if not patient:
            raise NotFoundException(f"Patient not found for id={patient_id}")
        return patient

    def _resolve_patient_id_by_fhir(self, fhir_patient_id: str) -> str:
        patient = self._repo_call(
            "get_patient_by_fhir_id", self.repository.get_patient_by_fhir_id, fhir_patient_id
        )
        if not patient:
            raise NotFoundException(f"Patient not found for fhir_patient_id={fhir_patient_id}")
        return str(patient["id"])

    def get_patients(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        return self._repo_call("find_all_patients", self.repository.find_all_patients, skip=skip, limit=limit)

    def get_patient_by_id(self, patient_id: str) -> Dict[str, Any]:
        patient = self._repo_call("find_patient_by_id", self.repository.find_patient_by_id, patient_id)
        if not patient:
            raise NotFoundException(f"Patient not found for id={patient_id}")
        return patient

    def get_patient_by_fhir_id(self, fhir_patient_id: str) -> Dict[str, Any]:
        patient = self._repo_call(
            "get_patient_by_fhir_id", self.repository.get_patient_by_fhir_id, fhir_patient_id
        )
        if not patient:
            raise NotFoundException(f"Patient not found for fhir_patient_id={fhir_patient_id}")
        return patient

    def get_patient_record(self, fhir_patient_id: str) -> Dict[str, Any]:
        patient = self.get_patient_by_fhir_id(fhir_patient_id)
        patient_id = str(patient["id"])

        return {
            "patient": patient,
            "conditions": self._repo_call("get_conditions", self.repository.get_conditions, patient_id),
            "medications": self._repo_call("get_medications", self.repository.get_medications, patient_id),
            "care_plans": self._repo_call("get_care_plans", self.repository.get_care_plans, patient_id),
            "encounters": self._repo_call("get_encounters", self.repository.get_encounters, patient_id),
            "observations": self._repo_call("get_observations", self.repository.get_observations, patient_id),
            "appointments": self._repo_call("get_appointments", self.repository.get_appointments, patient_id),
        }

    def get_patient_context(self, patient_id: str) -> Dict[str, Any]:
        patient = self._ensure_patient_exists(patient_id)
        recent_encounters = self._repo_call(
            "get_recent_encounters", self.repository.get_recent_encounters, patient_id, limit=10
        )
        recent_observations = self._repo_call(
            "get_recent_observations", self.repository.get_recent_observations, patient_id, limit=20
        )
        upcoming_appointments = self._repo_call(
            "get_upcoming_appointments", self.repository.get_upcoming_appointments, patient_id
        )
        active_conditions = self._repo_call(
            "get_active_conditions", self.repository.get_active_conditions, patient_id
        )

        risk_flags: List[str] = []
        if len(active_conditions) >= 5:
            risk_flags.append("multiple-active-conditions")
        if self._repo_call("get_latest_hospitalization", self.repository.get_latest_hospitalization, patient_id):
            risk_flags.append("recent-hospitalization-history")

        return {
            "patient": {
                "id": patient["id"],
                "fhir_patient_id": patient["fhir_patient_id"],
                "name": self._patient_display_name(patient),
                "age": self._age_from_dob(patient.get("date_of_birth")),
                "gender": patient.get("gender"),
            },
            "conditions": active_conditions,
            "medications": self._repo_call(
                "get_active_medications", self.repository.get_active_medications, patient_id
            ),
            "care_plans": self._repo_call(
                "get_active_care_plans", self.repository.get_active_care_plans, patient_id
            ),
            "recent_encounters": recent_encounters,
            "recent_observations": recent_observations,
            "upcoming_appointments": upcoming_appointments,
            "recent_discharge": self._repo_call(
                "get_latest_hospitalization", self.repository.get_latest_hospitalization, patient_id
            ),
            "risk_flags": risk_flags,
        }

    def get_patient_context_summary(self, patient_id: str) -> Dict[str, Any]:
        context = self.get_patient_context(patient_id)
        return {
            "patient": context["patient"],
            "active_condition_count": len(context["conditions"]),
            "active_medication_count": len(context["medications"]),
            "active_care_plan_count": len(context["care_plans"]),
            "recent_encounter_count": len(context["recent_encounters"]),
            "recent_observation_count": len(context["recent_observations"]),
            "upcoming_appointment_count": len(context["upcoming_appointments"]),
            "risk_flags": context["risk_flags"],
        }

    def get_patient_conditions(self, patient_id: str) -> List[Dict[str, Any]]:
        self._ensure_patient_exists(patient_id)
        return self._repo_call("get_conditions", self.repository.get_conditions, patient_id)

    def get_patient_active_conditions(self, patient_id: str) -> List[Dict[str, Any]]:
        self._ensure_patient_exists(patient_id)
        return self._repo_call("get_active_conditions", self.repository.get_active_conditions, patient_id)

    def get_condition(self, condition_id: str) -> Dict[str, Any]:
        condition = self._repo_call("get_condition_by_id", self.repository.get_condition_by_id, condition_id)
        if not condition:
            raise NotFoundException(f"Condition not found for id={condition_id}")
        return condition

    def get_patient_medications(self, patient_id: str) -> List[Dict[str, Any]]:
        self._ensure_patient_exists(patient_id)
        return self._repo_call("get_medications", self.repository.get_medications, patient_id)

    def get_patient_active_medications(self, patient_id: str) -> List[Dict[str, Any]]:
        self._ensure_patient_exists(patient_id)
        return self._repo_call("get_active_medications", self.repository.get_active_medications, patient_id)

    def get_patient_medication_history(self, patient_id: str) -> List[Dict[str, Any]]:
        self._ensure_patient_exists(patient_id)
        return self._repo_call("get_medication_history", self.repository.get_medication_history, patient_id)

    def get_medication(self, medication_id: str) -> Dict[str, Any]:
        medication = self._repo_call("get_medication_by_id", self.repository.get_medication_by_id, medication_id)
        if not medication:
            raise NotFoundException(f"Medication not found for id={medication_id}")
        return medication

    def get_patient_care_plans(self, patient_id: str) -> List[Dict[str, Any]]:
        self._ensure_patient_exists(patient_id)
        return self._repo_call("get_care_plans", self.repository.get_care_plans, patient_id)

    def get_patient_active_care_plans(self, patient_id: str) -> List[Dict[str, Any]]:
        self._ensure_patient_exists(patient_id)
        return self._repo_call("get_active_care_plans", self.repository.get_active_care_plans, patient_id)

    def get_care_plan(self, care_plan_id: str) -> Dict[str, Any]:
        care_plan = self._repo_call("get_care_plan_by_id", self.repository.get_care_plan_by_id, care_plan_id)
        if not care_plan:
            raise NotFoundException(f"Care plan not found for id={care_plan_id}")
        return care_plan

    def get_patient_encounters(self, patient_id: str) -> List[Dict[str, Any]]:
        self._ensure_patient_exists(patient_id)
        return self._repo_call("get_encounters", self.repository.get_encounters, patient_id)

    def get_patient_recent_encounters(self, patient_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        self._ensure_patient_exists(patient_id)
        return self._repo_call("get_recent_encounters", self.repository.get_recent_encounters, patient_id, limit=limit)

    def get_patient_latest_hospitalization(self, patient_id: str) -> Dict[str, Any]:
        self._ensure_patient_exists(patient_id)
        hospitalization = self._repo_call(
            "get_latest_hospitalization", self.repository.get_latest_hospitalization, patient_id
        )
        if not hospitalization:
            raise NotFoundException(f"No hospitalization encounter found for patient id={patient_id}")
        return hospitalization

    def get_patient_observations(self, patient_id: str) -> List[Dict[str, Any]]:
        self._ensure_patient_exists(patient_id)
        return self._repo_call("get_observations", self.repository.get_observations, patient_id)

    def get_patient_recent_observations(self, patient_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        self._ensure_patient_exists(patient_id)
        return self._repo_call(
            "get_recent_observations", self.repository.get_recent_observations, patient_id, limit=limit
        )

    def get_patient_observations_by_code(self, patient_id: str, code: str) -> List[Dict[str, Any]]:
        self._ensure_patient_exists(patient_id)
        return self._repo_call("get_observations_by_code", self.repository.get_observations_by_code, patient_id, code)

    def get_patient_latest_observation_by_code(self, patient_id: str, code: str) -> Dict[str, Any]:
        self._ensure_patient_exists(patient_id)
        observation = self._repo_call(
            "get_latest_observation_by_code", self.repository.get_latest_observation_by_code, patient_id, code
        )
        if not observation:
            raise NotFoundException(f"No observation found for patient id={patient_id} and code={code}")
        return observation

    def get_patient_appointments(self, patient_id: str) -> List[Dict[str, Any]]:
        self._ensure_patient_exists(patient_id)
        return self._repo_call("get_appointments", self.repository.get_appointments, patient_id)

    def get_patient_upcoming_appointments(self, patient_id: str) -> List[Dict[str, Any]]:
        self._ensure_patient_exists(patient_id)
        return self._repo_call("get_upcoming_appointments", self.repository.get_upcoming_appointments, patient_id)

    def get_patient_next_appointment(self, patient_id: str) -> Dict[str, Any]:
        self._ensure_patient_exists(patient_id)
        appointment = self._repo_call("get_next_appointment", self.repository.get_next_appointment, patient_id)
        if not appointment:
            raise NotFoundException(f"No upcoming appointment found for patient id={patient_id}")
        return appointment

    def get_appointment(self, appointment_id: str) -> Dict[str, Any]:
        appointment = self._repo_call("get_appointment_by_id", self.repository.get_appointment_by_id, appointment_id)
        if not appointment:
            raise NotFoundException(f"Appointment not found for id={appointment_id}")
        return appointment

    def get_patient_fhir_resources(self, patient_id: str, resource_type: str | None = None) -> List[Dict[str, Any]]:
        self._ensure_patient_exists(patient_id)
        return self._repo_call(
            "get_fhir_resources", self.repository.get_fhir_resources, patient_id, resource_type=resource_type
        )

    def get_fhir_resource(self, resource_type: str, resource_id: str) -> Dict[str, Any]:
        resource = self._repo_call("get_fhir_resource", self.repository.get_fhir_resource, resource_type, resource_id)
        if not resource:
            raise NotFoundException(
                f"FHIR resource not found for type={resource_type} and resource_id={resource_id}"
            )
        return resource

    def refresh_patient_context(self, patient_id: str) -> Dict[str, Any]:
        # Current implementation is read-through from Monster DB, so refresh is immediate.
        self._ensure_patient_exists(patient_id)
        return {
            "patient_id": patient_id,
            "refreshed": True,
            "message": "Patient context refreshed from Monster database",
        }

    def get_patient_record_by_patient_id(self, patient_id: str) -> Dict[str, Any]:
        patient = self._ensure_patient_exists(patient_id)
        return {
            "patient": patient,
            "conditions": self._repo_call("get_conditions", self.repository.get_conditions, patient_id),
            "medications": self._repo_call("get_medications", self.repository.get_medications, patient_id),
            "care_plans": self._repo_call("get_care_plans", self.repository.get_care_plans, patient_id),
            "encounters": self._repo_call("get_encounters", self.repository.get_encounters, patient_id),
            "observations": self._repo_call("get_observations", self.repository.get_observations, patient_id),
            "appointments": self._repo_call("get_appointments", self.repository.get_appointments, patient_id),
        }

    def get_patient_record_by_fhir_patient_id(self, fhir_patient_id: str) -> Dict[str, Any]:
        patient_id = self._resolve_patient_id_by_fhir(fhir_patient_id)
        return self.get_patient_record_by_patient_id(patient_id)
