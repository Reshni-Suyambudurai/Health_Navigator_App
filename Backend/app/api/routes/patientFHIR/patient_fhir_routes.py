"""
PatientFHIR API routes backed by Monster read-only database.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.response_models import SuccessResponse
from app.database.connection import get_monster_db
from app.services.patientFHIR.patient_fhir_service import PatientFHIRService


router = APIRouter(
    prefix="/patientFHIR",
    tags=["PatientFHIR"]
)


@router.get("/patients", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patients(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_monster_db)
):
    """Get all patients from patients table (Monster DB)."""
    service = PatientFHIRService(db)
    data = service.get_patients(skip=skip, limit=limit)

    return SuccessResponse(
        status="success",
        message="Patients retrieved successfully",
        data={"patients": data, "count": len(data)}
    )


@router.get("/patients/{patient_id}", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patient_by_id(
    patient_id: str,
    db: Session = Depends(get_monster_db)
):
    """Get one patient by UUID from patients table."""
    service = PatientFHIRService(db)
    data = service.get_patient_by_id(patient_id)

    return SuccessResponse(
        status="success",
        message="Patient retrieved successfully",
        data=data
    )


@router.get("/patients/fhir/{fhir_patient_id}", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patient_by_fhir_id(
    fhir_patient_id: str,
    db: Session = Depends(get_monster_db)
):
    """Get one patient by FHIR identifier from patients table."""
    service = PatientFHIRService(db)
    data = service.get_patient_by_fhir_id(fhir_patient_id)

    return SuccessResponse(
        status="success",
        message="Patient retrieved successfully",
        data=data
    )


@router.get("/patients/{patient_id}/context", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patient_context(
    patient_id: str,
    db: Session = Depends(get_monster_db)
):
    """Get assembled patient context from patients + conditions + medications + care_plans + encounters + observations + appointments tables."""
    service = PatientFHIRService(db)
    data = service.get_patient_context(patient_id)

    return SuccessResponse(
        status="success",
        message="Patient context retrieved successfully",
        data=data
    )


@router.post("/patients/{patient_id}/context/refresh", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def refresh_patient_context(
    patient_id: str,
    db: Session = Depends(get_monster_db)
):
    """Refresh patient context read-through from patients + conditions + medications + care_plans + encounters + observations + appointments tables."""
    service = PatientFHIRService(db)
    data = service.refresh_patient_context(patient_id)

    return SuccessResponse(
        status="success",
        message="Patient context refreshed successfully",
        data=data
    )


@router.get("/patients/{patient_id}/context/summary", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patient_context_summary(
    patient_id: str,
    db: Session = Depends(get_monster_db)
):
    """Get compact context summary from patients + conditions + medications + care_plans + encounters + observations + appointments tables."""
    service = PatientFHIRService(db)
    data = service.get_patient_context_summary(patient_id)

    return SuccessResponse(
        status="success",
        message="Patient context summary retrieved successfully",
        data=data
    )


@router.get("/patients/{patient_id}/conditions", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patient_conditions(
    patient_id: str,
    db: Session = Depends(get_monster_db)
):
    """Get patient conditions from conditions table."""
    service = PatientFHIRService(db)
    data = service.get_patient_conditions(patient_id)

    return SuccessResponse(
        status="success",
        message="Conditions retrieved successfully",
        data={"conditions": data, "count": len(data)}
    )


@router.get("/patients/{patient_id}/conditions/active", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patient_active_conditions(
    patient_id: str,
    db: Session = Depends(get_monster_db)
):
    """Get active patient conditions from conditions table."""
    service = PatientFHIRService(db)
    data = service.get_patient_active_conditions(patient_id)

    return SuccessResponse(
        status="success",
        message="Active conditions retrieved successfully",
        data={"conditions": data, "count": len(data)}
    )


@router.get("/conditions/{condition_id}", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_condition(
    condition_id: str,
    db: Session = Depends(get_monster_db)
):
    """Get one condition by id from conditions table."""
    service = PatientFHIRService(db)
    data = service.get_condition(condition_id)

    return SuccessResponse(
        status="success",
        message="Condition retrieved successfully",
        data=data
    )


@router.get("/patients/{patient_id}/medications", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patient_medications(
    patient_id: str,
    db: Session = Depends(get_monster_db)
):
    """Get patient medications from medications table."""
    service = PatientFHIRService(db)
    data = service.get_patient_medications(patient_id)

    return SuccessResponse(
        status="success",
        message="Medications retrieved successfully",
        data={"medications": data, "count": len(data)}
    )


@router.get("/patients/{patient_id}/medications/active", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patient_active_medications(
    patient_id: str,
    db: Session = Depends(get_monster_db)
):
    """Get active medications from medications table."""
    service = PatientFHIRService(db)
    data = service.get_patient_active_medications(patient_id)

    return SuccessResponse(
        status="success",
        message="Active medications retrieved successfully",
        data={"medications": data, "count": len(data)}
    )


@router.get("/patients/{patient_id}/medications/history", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patient_medication_history(
    patient_id: str,
    db: Session = Depends(get_monster_db)
):
    """Get medication history from medications table."""
    service = PatientFHIRService(db)
    data = service.get_patient_medication_history(patient_id)

    return SuccessResponse(
        status="success",
        message="Medication history retrieved successfully",
        data={"medications": data, "count": len(data)}
    )


@router.get("/medications/{medication_id}", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_medication(
    medication_id: str,
    db: Session = Depends(get_monster_db)
):
    """Get one medication by id from medications table."""
    service = PatientFHIRService(db)
    data = service.get_medication(medication_id)

    return SuccessResponse(
        status="success",
        message="Medication retrieved successfully",
        data=data
    )


@router.get("/patients/{patient_id}/care-plans", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patient_care_plans(
    patient_id: str,
    db: Session = Depends(get_monster_db)
):
    """Get patient care plans from care_plans table."""
    service = PatientFHIRService(db)
    data = service.get_patient_care_plans(patient_id)

    return SuccessResponse(
        status="success",
        message="Care plans retrieved successfully",
        data={"care_plans": data, "count": len(data)}
    )


@router.get("/patients/{patient_id}/care-plans/active", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patient_active_care_plans(
    patient_id: str,
    db: Session = Depends(get_monster_db)
):
    """Get active care plans from care_plans table."""
    service = PatientFHIRService(db)
    data = service.get_patient_active_care_plans(patient_id)

    return SuccessResponse(
        status="success",
        message="Active care plans retrieved successfully",
        data={"care_plans": data, "count": len(data)}
    )


@router.get("/care-plans/{care_plan_id}", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_care_plan(
    care_plan_id: str,
    db: Session = Depends(get_monster_db)
):
    """Get one care plan by id from care_plans table."""
    service = PatientFHIRService(db)
    data = service.get_care_plan(care_plan_id)

    return SuccessResponse(
        status="success",
        message="Care plan retrieved successfully",
        data=data
    )


@router.get("/patients/{patient_id}/encounters", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patient_encounters(
    patient_id: str,
    db: Session = Depends(get_monster_db)
):
    """Get patient encounters from encounters table."""
    service = PatientFHIRService(db)
    data = service.get_patient_encounters(patient_id)

    return SuccessResponse(
        status="success",
        message="Encounters retrieved successfully",
        data={"encounters": data, "count": len(data)}
    )


@router.get("/patients/{patient_id}/encounters/recent", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patient_recent_encounters(
    patient_id: str,
    limit: int = 10,
    db: Session = Depends(get_monster_db)
):
    """Get recent patient encounters from encounters table."""
    service = PatientFHIRService(db)
    data = service.get_patient_recent_encounters(patient_id, limit=limit)

    return SuccessResponse(
        status="success",
        message="Recent encounters retrieved successfully",
        data={"encounters": data, "count": len(data)}
    )


@router.get("/patients/{patient_id}/encounters/latest-hospitalization", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patient_latest_hospitalization(
    patient_id: str,
    db: Session = Depends(get_monster_db)
):
    """Get latest hospitalization encounter from encounters table."""
    service = PatientFHIRService(db)
    data = service.get_patient_latest_hospitalization(patient_id)

    return SuccessResponse(
        status="success",
        message="Latest hospitalization retrieved successfully",
        data=data
    )


@router.get("/patients/{patient_id}/observations", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patient_observations(
    patient_id: str,
    db: Session = Depends(get_monster_db)
):
    """Get patient observations from observations table."""
    service = PatientFHIRService(db)
    data = service.get_patient_observations(patient_id)

    return SuccessResponse(
        status="success",
        message="Observations retrieved successfully",
        data={"observations": data, "count": len(data)}
    )


@router.get("/patients/{patient_id}/observations/recent", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patient_recent_observations(
    patient_id: str,
    limit: int = 20,
    db: Session = Depends(get_monster_db)
):
    """Get recent observations from observations table."""
    service = PatientFHIRService(db)
    data = service.get_patient_recent_observations(patient_id, limit=limit)

    return SuccessResponse(
        status="success",
        message="Recent observations retrieved successfully",
        data={"observations": data, "count": len(data)}
    )


@router.get("/patients/{patient_id}/observations/{code}", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patient_observations_by_code(
    patient_id: str,
    code: str,
    db: Session = Depends(get_monster_db)
):
    """Get observations by code from observations table."""
    service = PatientFHIRService(db)
    data = service.get_patient_observations_by_code(patient_id, code)

    return SuccessResponse(
        status="success",
        message="Observations by code retrieved successfully",
        data={"observations": data, "count": len(data)}
    )


@router.get("/patients/{patient_id}/observations/{code}/latest", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patient_latest_observation_by_code(
    patient_id: str,
    code: str,
    db: Session = Depends(get_monster_db)
):
    """Get latest observation by code from observations table."""
    service = PatientFHIRService(db)
    data = service.get_patient_latest_observation_by_code(patient_id, code)

    return SuccessResponse(
        status="success",
        message="Latest observation retrieved successfully",
        data=data
    )


@router.get("/patients/{patient_id}/appointments", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patient_appointments(
    patient_id: str,
    db: Session = Depends(get_monster_db)
):
    """Get patient appointments from appointments table."""
    service = PatientFHIRService(db)
    data = service.get_patient_appointments(patient_id)

    return SuccessResponse(
        status="success",
        message="Appointments retrieved successfully",
        data={"appointments": data, "count": len(data)}
    )


@router.get("/patients/{patient_id}/appointments/upcoming", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patient_upcoming_appointments(
    patient_id: str,
    db: Session = Depends(get_monster_db)
):
    """Get upcoming appointments from appointments table."""
    service = PatientFHIRService(db)
    data = service.get_patient_upcoming_appointments(patient_id)

    return SuccessResponse(
        status="success",
        message="Upcoming appointments retrieved successfully",
        data={"appointments": data, "count": len(data)}
    )


@router.get("/patients/{patient_id}/appointments/next", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patient_next_appointment(
    patient_id: str,
    db: Session = Depends(get_monster_db)
):
    """Get next appointment from appointments table."""
    service = PatientFHIRService(db)
    data = service.get_patient_next_appointment(patient_id)

    return SuccessResponse(
        status="success",
        message="Next appointment retrieved successfully",
        data=data
    )


@router.get("/appointments/{appointment_id}", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_appointment(
    appointment_id: str,
    db: Session = Depends(get_monster_db)
):
    """Get one appointment by id from appointments table."""
    service = PatientFHIRService(db)
    data = service.get_appointment(appointment_id)

    return SuccessResponse(
        status="success",
        message="Appointment retrieved successfully",
        data=data
    )


@router.get("/fhir/patients/{patient_id}/resources", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patient_fhir_resources(
    patient_id: str,
    db: Session = Depends(get_monster_db)
):
    """Get patient FHIR resources from fhir_resources table."""
    service = PatientFHIRService(db)
    data = service.get_patient_fhir_resources(patient_id)

    return SuccessResponse(
        status="success",
        message="FHIR resources retrieved successfully",
        data={"resources": data, "count": len(data)}
    )


@router.get("/fhir/patients/{patient_id}/resources/{resource_type}", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patient_fhir_resources_by_type(
    patient_id: str,
    resource_type: str,
    db: Session = Depends(get_monster_db)
):
    """Get patient FHIR resources by type from fhir_resources table."""
    service = PatientFHIRService(db)
    data = service.get_patient_fhir_resources(patient_id, resource_type=resource_type)

    return SuccessResponse(
        status="success",
        message="FHIR resources by type retrieved successfully",
        data={"resources": data, "count": len(data)}
    )


@router.get("/fhir/resources/{resource_type}/{resource_id}", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_fhir_resource(
    resource_type: str,
    resource_id: str,
    db: Session = Depends(get_monster_db)
):
    """Get one FHIR resource from fhir_resources table."""
    service = PatientFHIRService(db)
    data = service.get_fhir_resource(resource_type, resource_id)

    return SuccessResponse(
        status="success",
        message="FHIR resource retrieved successfully",
        data=data
    )


@router.get("/records/fhir/{fhir_patient_id}", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patient_health_record_by_fhir_id(
    fhir_patient_id: str,
    db: Session = Depends(get_monster_db)
):
    """Get full patient health record from patients + conditions + medications + care_plans + encounters + observations + appointments tables using FHIR id."""
    service = PatientFHIRService(db)
    data = service.get_patient_record_by_fhir_patient_id(fhir_patient_id)

    return SuccessResponse(
        status="success",
        message="Patient health record retrieved successfully",
        data=data
    )


@router.get("/records/patients/{patient_id}", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_patient_health_record_by_patient_id(
    patient_id: str,
    db: Session = Depends(get_monster_db)
):
    """Get full patient health record from patients + conditions + medications + care_plans + encounters + observations + appointments tables using patient id."""
    service = PatientFHIRService(db)
    data = service.get_patient_record_by_patient_id(patient_id)

    return SuccessResponse(
        status="success",
        message="Patient health record retrieved successfully",
        data=data
    )
