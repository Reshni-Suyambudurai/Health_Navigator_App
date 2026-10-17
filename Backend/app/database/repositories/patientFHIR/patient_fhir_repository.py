"""
Repository for read-only PatientFHIR access from Monster database.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session


class PatientFHIRRepository:
    """Read-only repository over Monster PatientFHIR tables."""

    def __init__(self, db: Session):
        self.db = db

    def _fetch_one(self, query: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        result = self.db.execute(text(query), params).mappings().first()
        return dict(result) if result else None

    def _fetch_all(self, query: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [dict(row) for row in self.db.execute(text(query), params).mappings().all()]

    def find_all_patients(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT
                id,
                fhir_patient_id,
                first_name,
                middle_name,
                last_name,
                date_of_birth,
                gender,
                phone,
                email,
                address_line,
                city,
                state,
                postal_code,
                country,
                preferred_language,
                marital_status,
                created_at,
                updated_at
            FROM patients
            ORDER BY created_at DESC
            OFFSET :skip LIMIT :limit
            """,
            {"skip": skip, "limit": limit},
        )

    def find_patient_by_id(self, patient_id: str) -> Optional[Dict[str, Any]]:
        return self._fetch_one(
            """
            SELECT
                id,
                fhir_patient_id,
                first_name,
                middle_name,
                last_name,
                date_of_birth,
                gender,
                phone,
                email,
                address_line,
                city,
                state,
                postal_code,
                country,
                preferred_language,
                marital_status,
                created_at,
                updated_at
            FROM patients
            WHERE id = :patient_id
            LIMIT 1
            """,
            {"patient_id": patient_id},
        )

    def get_patient_by_fhir_id(self, fhir_patient_id: str) -> Optional[Dict[str, Any]]:
        return self._fetch_one(
            """
            SELECT
                id,
                fhir_patient_id,
                first_name,
                middle_name,
                last_name,
                date_of_birth,
                gender,
                phone,
                email,
                address_line,
                city,
                state,
                postal_code,
                country,
                preferred_language,
                marital_status,
                created_at,
                updated_at
            FROM patients
            WHERE fhir_patient_id = :fhir_patient_id
            LIMIT 1
            """,
            {"fhir_patient_id": fhir_patient_id},
        )

    def get_conditions(self, patient_id: str) -> List[Dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT
                id,
                patient_id,
                condition_code,
                code_system,
                condition_name,
                clinical_status,
                verification_status,
                onset_date,
                abatement_date,
                recorded_date,
                created_at,
                updated_at
            FROM conditions
            WHERE patient_id = :patient_id
            ORDER BY recorded_date DESC NULLS LAST, created_at DESC
            """,
            {"patient_id": patient_id},
        )

    def get_active_conditions(self, patient_id: str) -> List[Dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT
                id,
                patient_id,
                condition_code,
                code_system,
                condition_name,
                clinical_status,
                verification_status,
                onset_date,
                abatement_date,
                recorded_date,
                created_at,
                updated_at
            FROM conditions
            WHERE patient_id = :patient_id
              AND LOWER(COALESCE(clinical_status, '')) = 'active'
            ORDER BY recorded_date DESC NULLS LAST, created_at DESC
            """,
            {"patient_id": patient_id},
        )

    def get_condition_by_id(self, condition_id: str) -> Optional[Dict[str, Any]]:
        return self._fetch_one(
            """
            SELECT
                id,
                patient_id,
                condition_code,
                code_system,
                condition_name,
                clinical_status,
                verification_status,
                onset_date,
                abatement_date,
                recorded_date,
                created_at,
                updated_at
            FROM conditions
            WHERE id = :condition_id
            LIMIT 1
            """,
            {"condition_id": condition_id},
        )

    def get_medications(self, patient_id: str) -> List[Dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT
                id,
                patient_id,
                rxnorm_code,
                medication_name,
                status,
                intent,
                dosage_text,
                authored_on,
                start_date,
                end_date,
                reason,
                created_at,
                updated_at
            FROM medications
            WHERE patient_id = :patient_id
            ORDER BY authored_on DESC NULLS LAST, created_at DESC
            """,
            {"patient_id": patient_id},
        )

    def get_active_medications(self, patient_id: str) -> List[Dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT
                id,
                patient_id,
                rxnorm_code,
                medication_name,
                status,
                intent,
                dosage_text,
                authored_on,
                start_date,
                end_date,
                reason,
                created_at,
                updated_at
            FROM medications
            WHERE patient_id = :patient_id
              AND LOWER(COALESCE(status, '')) IN ('active', 'in-progress')
            ORDER BY authored_on DESC NULLS LAST, created_at DESC
            """,
            {"patient_id": patient_id},
        )

    def get_medication_by_id(self, medication_id: str) -> Optional[Dict[str, Any]]:
        return self._fetch_one(
            """
            SELECT
                id,
                patient_id,
                rxnorm_code,
                medication_name,
                status,
                intent,
                dosage_text,
                authored_on,
                start_date,
                end_date,
                reason,
                created_at,
                updated_at
            FROM medications
            WHERE id = :medication_id
            LIMIT 1
            """,
            {"medication_id": medication_id},
        )

    def get_medication_history(self, patient_id: str) -> List[Dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT
                id,
                patient_id,
                rxnorm_code,
                medication_name,
                status,
                intent,
                dosage_text,
                authored_on,
                start_date,
                end_date,
                reason,
                created_at,
                updated_at
            FROM medications
            WHERE patient_id = :patient_id
            ORDER BY COALESCE(start_date, authored_on, created_at) DESC
            """,
            {"patient_id": patient_id},
        )

    def get_care_plans(self, patient_id: str) -> List[Dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT
                id,
                patient_id,
                status,
                intent,
                category_code,
                category_name,
                title,
                description,
                start_date,
                end_date,
                created_at,
                updated_at
            FROM care_plans
            WHERE patient_id = :patient_id
            ORDER BY start_date DESC NULLS LAST, created_at DESC
            """,
            {"patient_id": patient_id},
        )

    def get_active_care_plans(self, patient_id: str) -> List[Dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT
                id,
                patient_id,
                status,
                intent,
                category_code,
                category_name,
                title,
                description,
                start_date,
                end_date,
                created_at,
                updated_at
            FROM care_plans
            WHERE patient_id = :patient_id
              AND LOWER(COALESCE(status, '')) IN ('active', 'in-progress')
            ORDER BY start_date DESC NULLS LAST, created_at DESC
            """,
            {"patient_id": patient_id},
        )

    def get_care_plan_by_id(self, care_plan_id: str) -> Optional[Dict[str, Any]]:
        return self._fetch_one(
            """
            SELECT
                id,
                patient_id,
                status,
                intent,
                category_code,
                category_name,
                title,
                description,
                start_date,
                end_date,
                created_at,
                updated_at
            FROM care_plans
            WHERE id = :care_plan_id
            LIMIT 1
            """,
            {"care_plan_id": care_plan_id},
        )

    def get_encounters(self, patient_id: str) -> List[Dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT
                id,
                patient_id,
                status,
                encounter_class,
                encounter_type_code,
                encounter_type_name,
                start_time,
                end_time,
                reason,
                discharge_disposition,
                created_at,
                updated_at
            FROM encounters
            WHERE patient_id = :patient_id
            ORDER BY start_time DESC NULLS LAST, created_at DESC
            """,
            {"patient_id": patient_id},
        )

    def get_recent_encounters(self, patient_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT
                id,
                patient_id,
                status,
                encounter_class,
                encounter_type_code,
                encounter_type_name,
                start_time,
                end_time,
                reason,
                discharge_disposition,
                created_at,
                updated_at
            FROM encounters
            WHERE patient_id = :patient_id
            ORDER BY start_time DESC NULLS LAST, created_at DESC
            LIMIT :limit
            """,
            {"patient_id": patient_id, "limit": limit},
        )

    def get_latest_hospitalization(self, patient_id: str) -> Optional[Dict[str, Any]]:
        return self._fetch_one(
            """
            SELECT
                id,
                patient_id,
                status,
                encounter_class,
                encounter_type_code,
                encounter_type_name,
                start_time,
                end_time,
                reason,
                discharge_disposition,
                created_at,
                updated_at
            FROM encounters
            WHERE patient_id = :patient_id
              AND LOWER(COALESCE(encounter_class, '')) IN ('inpatient', 'emergency', 'hospitalization')
            ORDER BY start_time DESC NULLS LAST, created_at DESC
            LIMIT 1
            """,
            {"patient_id": patient_id},
        )

    def get_observations(self, patient_id: str) -> List[Dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT
                id,
                patient_id,
                observation_code,
                code_system,
                observation_name,
                status,
                value_numeric,
                value_text,
                unit,
                effective_time,
                interpretation,
                created_at,
                updated_at
            FROM observations
            WHERE patient_id = :patient_id
            ORDER BY effective_time DESC NULLS LAST, created_at DESC
            """,
            {"patient_id": patient_id},
        )

    def get_recent_observations(self, patient_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT
                id,
                patient_id,
                observation_code,
                code_system,
                observation_name,
                status,
                value_numeric,
                value_text,
                unit,
                effective_time,
                interpretation,
                created_at,
                updated_at
            FROM observations
            WHERE patient_id = :patient_id
            ORDER BY effective_time DESC NULLS LAST, created_at DESC
            LIMIT :limit
            """,
            {"patient_id": patient_id, "limit": limit},
        )

    def get_observations_by_code(self, patient_id: str, code: str) -> List[Dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT
                id,
                patient_id,
                observation_code,
                code_system,
                observation_name,
                status,
                value_numeric,
                value_text,
                unit,
                effective_time,
                interpretation,
                created_at,
                updated_at
            FROM observations
            WHERE patient_id = :patient_id
              AND LOWER(COALESCE(observation_code, '')) = LOWER(:code)
            ORDER BY effective_time DESC NULLS LAST, created_at DESC
            """,
            {"patient_id": patient_id, "code": code},
        )

    def get_latest_observation_by_code(self, patient_id: str, code: str) -> Optional[Dict[str, Any]]:
        return self._fetch_one(
            """
            SELECT
                id,
                patient_id,
                observation_code,
                code_system,
                observation_name,
                status,
                value_numeric,
                value_text,
                unit,
                effective_time,
                interpretation,
                created_at,
                updated_at
            FROM observations
            WHERE patient_id = :patient_id
              AND LOWER(COALESCE(observation_code, '')) = LOWER(:code)
            ORDER BY effective_time DESC NULLS LAST, created_at DESC
            LIMIT 1
            """,
            {"patient_id": patient_id, "code": code},
        )

    def get_appointments(self, patient_id: str) -> List[Dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT
                id,
                patient_id,
                status,
                appointment_type,
                reason,
                start_time,
                end_time,
                location,
                practitioner_name,
                created_at,
                updated_at
            FROM appointments
            WHERE patient_id = :patient_id
            ORDER BY start_time DESC NULLS LAST, created_at DESC
            """,
            {"patient_id": patient_id},
        )

    def get_upcoming_appointments(self, patient_id: str) -> List[Dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT
                id,
                patient_id,
                status,
                appointment_type,
                reason,
                start_time,
                end_time,
                location,
                practitioner_name,
                created_at,
                updated_at
            FROM appointments
            WHERE patient_id = :patient_id
              AND start_time >= CURRENT_TIMESTAMP
            ORDER BY start_time ASC
            """,
            {"patient_id": patient_id},
        )

    def get_next_appointment(self, patient_id: str) -> Optional[Dict[str, Any]]:
        return self._fetch_one(
            """
            SELECT
                id,
                patient_id,
                status,
                appointment_type,
                reason,
                start_time,
                end_time,
                location,
                practitioner_name,
                created_at,
                updated_at
            FROM appointments
            WHERE patient_id = :patient_id
              AND start_time >= CURRENT_TIMESTAMP
            ORDER BY start_time ASC
            LIMIT 1
            """,
            {"patient_id": patient_id},
        )

    def get_appointment_by_id(self, appointment_id: str) -> Optional[Dict[str, Any]]:
        return self._fetch_one(
            """
            SELECT
                id,
                patient_id,
                status,
                appointment_type,
                reason,
                start_time,
                end_time,
                location,
                practitioner_name,
                created_at,
                updated_at
            FROM appointments
            WHERE id = :appointment_id
            LIMIT 1
            """,
            {"appointment_id": appointment_id},
        )

    def get_fhir_resources(self, patient_id: str, resource_type: Optional[str] = None) -> List[Dict[str, Any]]:
        if resource_type:
            return self._fetch_all(
                """
                SELECT
                    id,
                    patient_id,
                    resource_type,
                    fhir_resource_id,
                    version_id,
                    last_updated,
                    resource_json,
                    created_at,
                    updated_at
                FROM fhir_resources
                WHERE patient_id = :patient_id
                  AND LOWER(resource_type) = LOWER(:resource_type)
                ORDER BY last_updated DESC NULLS LAST, created_at DESC
                """,
                {"patient_id": patient_id, "resource_type": resource_type},
            )

        return self._fetch_all(
            """
            SELECT
                id,
                patient_id,
                resource_type,
                fhir_resource_id,
                version_id,
                last_updated,
                resource_json,
                created_at,
                updated_at
            FROM fhir_resources
            WHERE patient_id = :patient_id
            ORDER BY last_updated DESC NULLS LAST, created_at DESC
            """,
            {"patient_id": patient_id},
        )

    def get_fhir_resource(self, resource_type: str, resource_id: str) -> Optional[Dict[str, Any]]:
        return self._fetch_one(
            """
            SELECT
                id,
                patient_id,
                resource_type,
                fhir_resource_id,
                version_id,
                last_updated,
                resource_json,
                created_at,
                updated_at
            FROM fhir_resources
            WHERE LOWER(resource_type) = LOWER(:resource_type)
              AND fhir_resource_id = :resource_id
            LIMIT 1
            """,
            {"resource_type": resource_type, "resource_id": resource_id},
        )
