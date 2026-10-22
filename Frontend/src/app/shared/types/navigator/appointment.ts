import { ApiSuccessResponse } from './user';

export type AppointmentType = 'POST_DISCHARGE' | 'NURSE_FOLLOWUP' | 'CARE_MANAGER_CALL';
export type AppointmentStatus =
	| 'REQUESTED'
	| 'SCHEDULED'
	| 'CONFIRMED'
	| 'COMPLETED'
	| 'CANCELLED'
	| 'NO_SHOW'
	| 'RESCHEDULED';
export type DayOfWeek =
	| 'MONDAY'
	| 'TUESDAY'
	| 'WEDNESDAY'
	| 'THURSDAY'
	| 'FRIDAY'
	| 'SATURDAY'
	| 'SUNDAY';

export interface AppointmentRecord {
	appointment_id: number;
	patient_id: number;
	patient_name: string;
	appointment_type: AppointmentType;
	appointment_datetime: string;
	end_datetime: string;
	status: AppointmentStatus;
	booking_method: string;
	location_or_channel: string | null;
	reason: string | null;
	staff_id: number;
}

export interface AppointmentListData {
	appointments: AppointmentRecord[];
	count: number;
}

export interface PatientAppointmentRecord {
	appointment_id: number;
	patient_id: number;
	staff_id: number | null;
	staff_name: string;
	appointment_type: AppointmentType;
	appointment_datetime: string;
	end_datetime: string;
	status: AppointmentStatus;
	booking_method: string;
	location_or_channel: string | null;
	reason: string | null;
}

export interface PatientAppointmentListData {
	appointments: PatientAppointmentRecord[];
	count: number;
}

export interface AvailabilityRecord {
	availability_id: number;
	staff_id: number;
	day_of_week: DayOfWeek;
	start_time: string;
	end_time: string;
	lunch_start_time: string | null;
	lunch_end_time: string | null;
	effective_from: string;
	effective_until: string | null;
	is_active: boolean;
}

export interface AvailabilityListData {
	availability: AvailabilityRecord[];
	count: number;
}

export interface AvailabilityRequest {
	day_of_week: DayOfWeek;
	start_time: string;
	end_time: string;
	lunch_start_time: string | null;
	lunch_end_time: string | null;
	effective_from: string;
	effective_until: string | null;
	is_active: boolean;
}

export interface RoutineAppointmentRequest {
	patient_id: number;
	appointment_type: AppointmentType;
	appointment_datetime: string;
	end_datetime: string;
	reason?: string | null;
	location_or_channel?: string | null;
}

export interface AvailableAppointmentSlot {
	start: string;
	end: string;
}

export interface AvailableSlotsData {
	appointment_date: string;
	duration_minutes: number;
	slots: AvailableAppointmentSlot[];
	count: number;
}

export type AppointmentListResponse = ApiSuccessResponse<AppointmentListData>;
export type PatientAppointmentListResponse = ApiSuccessResponse<PatientAppointmentListData>;
export type AvailabilityListResponse = ApiSuccessResponse<AvailabilityListData>;
export type AvailableSlotsResponse = ApiSuccessResponse<AvailableSlotsData>;
