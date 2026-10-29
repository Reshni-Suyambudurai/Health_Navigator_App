from datetime import date, datetime, time

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.response_models import SuccessResponse
from app.database.connection import get_db
from app.database.models.appointment import AppointmentStatus, AppointmentType
from app.database.models.staff_availability import DayOfWeek
from app.services.navigator.appointment_service import AppointmentService
from app.services.navigator.staff_availability_service import StaffAvailabilityService


router = APIRouter(prefix="/appointments", tags=["Appointments"])


class RoutineAppointmentRequest(BaseModel):
    patient_id: int
    appointment_type: AppointmentType
    checkin_session_id: int | None = None
    appointment_datetime: datetime
    end_datetime: datetime
    reason: str | None = None
    location_or_channel: str | None = None


class AvailabilityRequest(BaseModel):
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    lunch_start_time: time | None = None
    lunch_end_time: time | None = None
    effective_from: date
    effective_until: date | None = None
    is_active: bool = True


class NurseAppointmentUpdateRequest(BaseModel):
    status: AppointmentStatus
    staff_id: int | None = None


@router.get("/available-slots", response_model=SuccessResponse)
def get_available_appointment_slots(
    appointment_date: date,
    duration_minutes: int = Query(..., ge=1),
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    slots = service.get_available_slots(
        user_id=user_id,
        requested_date=appointment_date,
        duration_minutes=duration_minutes,
    )
    return SuccessResponse(
        message="Available appointment slots retrieved successfully",
        data={
            "appointment_date": appointment_date.isoformat(),
            "duration_minutes": duration_minutes,
            "slots": slots,
            "count": len(slots),
        },
    )


@router.get("/booking-permissions", response_model=SuccessResponse)
def get_booking_permissions(
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    permissions = AppointmentService(db).get_booking_permissions(user_id)
    return SuccessResponse(
        message="Appointment booking permissions retrieved successfully",
        data=permissions,
    )


@router.get("/nurse/upcoming", response_model=SuccessResponse)
def get_nurse_upcoming_appointments(
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    appointments = service.get_nurse_appointments(user_id, upcoming=True)
    return SuccessResponse(
        message="Upcoming appointments retrieved successfully",
        data={"appointments": appointments, "count": len(appointments)},
    )


@router.get("/patient/upcoming", response_model=SuccessResponse)
def get_patient_upcoming_appointments(
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    appointments = service.get_patient_appointments(user_id, upcoming=True)
    return SuccessResponse(
        message="Upcoming appointments retrieved successfully",
        data={"appointments": appointments, "count": len(appointments)},
    )


@router.get("/patient/history", response_model=SuccessResponse)
def get_patient_appointment_history(
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    appointments = service.get_patient_appointments(user_id, upcoming=False)
    return SuccessResponse(
        message="Appointment history retrieved successfully",
        data={"appointments": appointments, "count": len(appointments)},
    )


@router.get("/nurse/history", response_model=SuccessResponse)
def get_nurse_appointment_history(
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    appointments = service.get_nurse_appointments(user_id, upcoming=False)
    return SuccessResponse(
        message="Appointment history retrieved successfully",
        data={"appointments": appointments, "count": len(appointments)},
    )


@router.get("/nurse/{appointment_id}/details", response_model=SuccessResponse)
def get_nurse_appointment_details(
    appointment_id: int,
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    appointment = service.get_nurse_appointment_details(user_id, appointment_id)
    return SuccessResponse(
        message="Appointment details retrieved successfully",
        data=appointment,
    )


@router.get("/nurse/{appointment_id}/reassignment-options", response_model=SuccessResponse)
def get_nurse_reassignment_options(
    appointment_id: int,
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    staff = service.get_reassignment_options(user_id, appointment_id)
    return SuccessResponse(
        message="Available nurses retrieved successfully",
        data={"staff": staff, "count": len(staff)},
    )


@router.put("/nurse/{appointment_id}", response_model=SuccessResponse)
def update_nurse_appointment(
    appointment_id: int,
    request: NurseAppointmentUpdateRequest,
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    appointment = service.update_nurse_appointment(
        user_id=user_id,
        appointment_id=appointment_id,
        new_status=request.status,
        staff_id=request.staff_id,
    )
    return SuccessResponse(
        message="Appointment updated successfully",
        data=appointment,
    )


@router.get("/nurse/availability", response_model=SuccessResponse)
def get_nurse_availability(
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    service = StaffAvailabilityService(db)
    availability = service.list_for_user(user_id)
    return SuccessResponse(
        message="Availability retrieved successfully",
        data={"availability": availability, "count": len(availability)},
    )


@router.post("/nurse/availability", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
def create_nurse_availability(
    request: AvailabilityRequest,
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    service = StaffAvailabilityService(db)
    availability = service.create_for_user(
        user_id=user_id,
        day_of_week=request.day_of_week,
        start_time=request.start_time,
        end_time=request.end_time,
        lunch_start_time=request.lunch_start_time,
        lunch_end_time=request.lunch_end_time,
        effective_from=request.effective_from,
        effective_until=request.effective_until,
        is_active=request.is_active,
    )
    return SuccessResponse(message="Availability saved successfully", data=availability)


@router.put("/nurse/availability/{availability_id}", response_model=SuccessResponse)
def update_nurse_availability(
    availability_id: int,
    request: AvailabilityRequest,
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    service = StaffAvailabilityService(db)
    availability = service.update_for_user(
        user_id=user_id,
        availability_id=availability_id,
        day_of_week=request.day_of_week,
        start_time=request.start_time,
        end_time=request.end_time,
        lunch_start_time=request.lunch_start_time,
        lunch_end_time=request.lunch_end_time,
        effective_from=request.effective_from,
        effective_until=request.effective_until,
        is_active=request.is_active,
    )
    return SuccessResponse(message="Availability updated successfully", data=availability)


@router.post("/routine", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
def book_routine_appointment(
    request: RoutineAppointmentRequest,
    user_id: int = Query(..., gt=0, description="Authenticated session user ID"),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    appointment = service.book_routine_appointment(
        patient_id=request.patient_id,
        created_by_user_id=user_id,
        appointment_type=request.appointment_type,
        checkin_session_id=request.checkin_session_id,
        appointment_datetime=request.appointment_datetime,
        end_datetime=request.end_datetime,
        reason=request.reason,
        location_or_channel=request.location_or_channel,
    )
    return SuccessResponse(message="Appointment booked successfully", data=appointment)
