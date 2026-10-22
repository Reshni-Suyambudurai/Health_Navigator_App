import unittest
from datetime import date, datetime, time, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.core.exceptions import AuthorizationException
from app.database.models.appointment import AppointmentType
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


if __name__ == "__main__":
    unittest.main()