import unittest
from datetime import date, datetime, time, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.core.exceptions import AuthorizationException
from app.database.models.appointment import AppointmentStatus, AppointmentType
from app.services.navigator.appointment_service import AppointmentService


class AppointmentServiceTests(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.service = AppointmentService(self.db)
        self.service.appointments = MagicMock()
        self.service.availability = MagicMock()
        self.service.patients = MagicMock()

    def test_available_slots_exclude_lunch_existing_bookings_and_past_times(self):
        requested_date = date.today() + timedelta(days=1)
        window = SimpleNamespace(
            staff_id=12,
            start_time=time(9, 0),
            end_time=time(12, 0),
            lunch_start_time=time(10, 0),
            lunch_end_time=time(10, 30),
        )
        busy_start = datetime.combine(requested_date, time(11, 0))
        self.service.patients.find_by_user_id.return_value = SimpleNamespace(patient_id=5)
        self.service.availability.find_active_for_date.return_value = [window]
        self.service.appointments.find_busy_ranges.return_value = [
            (12, busy_start, busy_start + timedelta(minutes=30)),
        ]

        slots = self.service.get_available_slots(7, requested_date, 30)

        self.assertEqual(
            [slot["start"][-8:] for slot in slots],
            ["09:00:00", "09:30:00", "10:30:00", "11:30:00"],
        )

    def test_booking_locks_least_loaded_nurse_and_saves_in_transaction(self):
        patient = SimpleNamespace(patient_id=5)
        nurse_one = SimpleNamespace(staff_id=21)
        nurse_two = SimpleNamespace(staff_id=22)
        self.service.patients.find_by_user_id.return_value = patient
        self.service.availability.find_matching_staff.return_value = [nurse_one, nurse_two]
        self.service.appointments.count_upcoming.side_effect = lambda staff_id, _: {21: 4, 22: 1}[staff_id]
        self.service.appointments.lock_staff_for_booking.return_value = nurse_two
        self.service.appointments.has_overlap.return_value = False

        def save(appointment):
            appointment.appointment_id = 100
            return appointment

        self.service.appointments.save.side_effect = save
        start = datetime.combine(date.today() + timedelta(days=1), time(9, 0))

        result = self.service.book_routine_appointment(
            patient_id=5,
            created_by_user_id=7,
            appointment_type=AppointmentType.NURSE_FOLLOWUP,
            appointment_datetime=start,
            end_datetime=start + timedelta(minutes=30),
            reason=None,
            location_or_channel="Phone call",
        )

        self.db.begin.assert_called_once_with()
        self.service.appointments.lock_staff_for_booking.assert_called_once_with(22)
        self.service.appointments.has_overlap.assert_called_once_with(
            22,
            start,
            start + timedelta(minutes=30),
        )
        self.assertEqual(result["staff_id"], 22)
        self.assertEqual(result["appointment_id"], 100)
        self.assertEqual(result["status"], "REQUESTED")

    def test_booking_rejects_patient_id_not_owned_by_session_user(self):
        self.service.patients.find_by_user_id.return_value = SimpleNamespace(patient_id=8)
        start = datetime.combine(date.today() + timedelta(days=1), time(9, 0))

        with self.assertRaises(AuthorizationException):
            self.service.book_routine_appointment(
                patient_id=5,
                created_by_user_id=7,
                appointment_type=AppointmentType.NURSE_FOLLOWUP,
                appointment_datetime=start,
                end_datetime=start + timedelta(minutes=30),
                reason=None,
                location_or_channel="Phone call",
            )

        self.service.appointments.save.assert_not_called()

    def test_assigned_nurse_can_confirm_requested_appointment(self):
        staff = SimpleNamespace(staff_id=22)
        appointment = SimpleNamespace(
            appointment_id=100,
            staff_id=22,
            status=AppointmentStatus.REQUESTED,
        )
        self.service.appointments.find_staff_profile_for_user.return_value = staff
        self.service.appointments.lock_appointment.return_value = appointment
        self.service.appointments.save.side_effect = lambda item: item

        result = self.service.update_nurse_appointment(
            user_id=7,
            appointment_id=100,
            new_status=AppointmentStatus.CONFIRMED,
            staff_id=None,
        )

        self.assertEqual(result, {
            "appointment_id": 100,
            "staff_id": 22,
            "status": "CONFIRMED",
        })

    def test_assigned_nurse_can_view_appointment_details(self):
        staff = SimpleNamespace(staff_id=22)
        appointment = {
            "appointment_id": 100,
            "staff_id": 22,
            "patient_id": 5,
            "external_fhir_patient_id": "9075",
        }
        self.service.appointments.find_staff_profile_for_user.return_value = staff
        self.service.appointments.find_details_by_id.return_value = appointment

        result = self.service.get_nurse_appointment_details(user_id=7, appointment_id=100)

        self.assertEqual(result, appointment)

    def test_unassigned_nurse_cannot_view_appointment_details(self):
        self.service.appointments.find_staff_profile_for_user.return_value = SimpleNamespace(staff_id=22)
        self.service.appointments.find_details_by_id.return_value = {
            "appointment_id": 100,
            "staff_id": 23,
        }

        with self.assertRaises(AuthorizationException):
            self.service.get_nurse_appointment_details(user_id=7, appointment_id=100)

    def test_assigned_nurse_can_complete_confirmed_appointment(self):
        staff = SimpleNamespace(staff_id=22)
        appointment = SimpleNamespace(
            appointment_id=100,
            staff_id=22,
            status=AppointmentStatus.CONFIRMED,
        )
        self.service.appointments.find_staff_profile_for_user.return_value = staff
        self.service.appointments.lock_appointment.return_value = appointment
        self.service.appointments.save.side_effect = lambda item: item

        result = self.service.update_nurse_appointment(
            user_id=7,
            appointment_id=100,
            new_status=AppointmentStatus.COMPLETED,
            staff_id=None,
        )

        self.assertEqual(result["status"], "COMPLETED")

    def test_assigned_nurse_can_schedule_with_available_nurse(self):
        current_staff = SimpleNamespace(staff_id=22)
        target_staff = SimpleNamespace(staff_id=23)
        start = datetime.combine(date.today() + timedelta(days=1), time(9, 0))
        appointment = SimpleNamespace(
            appointment_id=100,
            staff_id=22,
            status=AppointmentStatus.REQUESTED,
            appointment_datetime=start,
            end_datetime=start + timedelta(minutes=30),
        )
        self.service.appointments.find_staff_profile_for_user.return_value = current_staff
        self.service.appointments.lock_appointment.return_value = appointment
        self.service.appointments.find_active_staff_by_role_id.return_value = [
            {"staff_id": 23, "staff_name": "Assigned Nurse"},
        ]
        self.service.appointments.lock_staff_for_booking.return_value = target_staff
        self.service.appointments.save.side_effect = lambda item: item

        result = self.service.update_nurse_appointment(
            user_id=7,
            appointment_id=100,
            new_status=AppointmentStatus.SCHEDULED,
            staff_id=23,
        )

        self.assertEqual(result["staff_id"], 23)
        self.assertEqual(result["status"], "SCHEDULED")
        self.service.appointments.find_active_staff_by_role_id.assert_called_once_with(
            3,
            excluded_staff_id=22,
        )


if __name__ == "__main__":
    unittest.main()