import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
	AppointmentListResponse,
	AvailableSlotsResponse,
	AvailabilityRecord,
	AvailabilityListResponse,
	AvailabilityRequest,
	PatientAppointmentListResponse,
	RoutineAppointmentRequest,
} from '../../shared/types/navigator/appointment';
import { ApiSuccessResponse } from '../../shared/types/navigator/user';

@Injectable({ providedIn: 'root' })
export class AppointmentApi {
	private readonly http = inject(HttpClient);
	private readonly baseUrl = `${environment.apiBaseUrl}/appointments`;

	getNurseUpcoming(userId: number): Observable<AppointmentListResponse> {
		return this.http.get<AppointmentListResponse>(`${this.baseUrl}/nurse/upcoming`, {
			params: this.userParams(userId),
		});
	}

	getNurseHistory(userId: number): Observable<AppointmentListResponse> {
		return this.http.get<AppointmentListResponse>(`${this.baseUrl}/nurse/history`, {
			params: this.userParams(userId),
		});
	}

	getPatientUpcoming(userId: number): Observable<PatientAppointmentListResponse> {
		return this.http.get<PatientAppointmentListResponse>(`${this.baseUrl}/patient/upcoming`, {
			params: this.userParams(userId),
		});
	}

	getPatientHistory(userId: number): Observable<PatientAppointmentListResponse> {
		return this.http.get<PatientAppointmentListResponse>(`${this.baseUrl}/patient/history`, {
			params: this.userParams(userId),
		});
	}

	getNurseAvailability(userId: number): Observable<AvailabilityListResponse> {
		return this.http.get<AvailabilityListResponse>(`${this.baseUrl}/nurse/availability`, {
			params: this.userParams(userId),
		});
	}

	getAvailableSlots(
		userId: number,
		appointmentDate: string,
		durationMinutes: number,
	): Observable<AvailableSlotsResponse> {
		const params = this.userParams(userId)
			.set('appointment_date', appointmentDate)
			.set('duration_minutes', durationMinutes);
		return this.http.get<AvailableSlotsResponse>(`${this.baseUrl}/available-slots`, { params });
	}

	createNurseAvailability(
		userId: number,
		payload: AvailabilityRequest,
	): Observable<ApiSuccessResponse<AvailabilityRecord>> {
		return this.http.post<ApiSuccessResponse<AvailabilityRecord>>(
			`${this.baseUrl}/nurse/availability`,
			payload,
			{ params: this.userParams(userId) },
		);
	}

	updateNurseAvailability(
		userId: number,
		availabilityId: number,
		payload: AvailabilityRequest,
	): Observable<ApiSuccessResponse<AvailabilityRecord>> {
		return this.http.put<ApiSuccessResponse<AvailabilityRecord>>(
			`${this.baseUrl}/nurse/availability/${availabilityId}`,
			payload,
			{ params: this.userParams(userId) },
		);
	}

	bookRoutineAppointment(
		userId: number,
		payload: RoutineAppointmentRequest,
	): Observable<ApiSuccessResponse<unknown>> {
		return this.http.post<ApiSuccessResponse<unknown>>(`${this.baseUrl}/routine`, payload, {
			params: this.userParams(userId),
		});
	}

	private userParams(userId: number): HttpParams {
		return new HttpParams().set('user_id', userId);
	}
}
