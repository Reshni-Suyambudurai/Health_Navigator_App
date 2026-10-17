import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
	ApiSuccessResponse,
	CareTeamData,
	LoginData,
	LoginRequest,
	UserCreateData,
	UserCreateRequest,
	UserDeleteData,
	UserListData,
	PatientConsentRequest,
	PatientOnboardingState,
	PatientProfileUpdateRequest,
	UserRecord,
} from '../../shared/types/navigator/user';

@Injectable({ providedIn: 'root' })
export class UserApi {
	private readonly http = inject(HttpClient);
	private readonly baseUrl = `${environment.apiBaseUrl}/users`;

	login(payload: LoginRequest): Observable<ApiSuccessResponse<LoginData>> {
		return this.http.post<ApiSuccessResponse<LoginData>>(`${this.baseUrl}/login`, payload);
	}

	getUserById(userId: number): Observable<ApiSuccessResponse<UserRecord>> {
		return this.http.get<ApiSuccessResponse<UserRecord>>(`${this.baseUrl}/${userId}`);
	}

	getAllUsers(
		options: { skip?: number; limit?: number } = {}
	): Observable<ApiSuccessResponse<UserListData>> {
		const params = this.buildPaginationParams(options);
		return this.http.get<ApiSuccessResponse<UserListData>>(this.baseUrl, { params });
	}

	createUser(payload: UserCreateRequest): Observable<ApiSuccessResponse<UserCreateData>> {
		return this.http.post<ApiSuccessResponse<UserCreateData>>(this.baseUrl, payload);
	}

	deleteUser(userId: number): Observable<ApiSuccessResponse<UserDeleteData | null>> {
		return this.http.delete<ApiSuccessResponse<UserDeleteData | null>>(`${this.baseUrl}/${userId}`);
	}

	getActiveUsers(): Observable<ApiSuccessResponse<UserListData>> {
		return this.http.get<ApiSuccessResponse<UserListData>>(`${this.baseUrl}/status/active`);
	}

	getActiveUsersByRole(roleName: string): Observable<ApiSuccessResponse<CareTeamData>> {
		return this.http.get<ApiSuccessResponse<CareTeamData>>(
			`${this.baseUrl}/by-role/${encodeURIComponent(roleName)}`
		);
	}

	getPatientOnboarding(userId: number): Observable<ApiSuccessResponse<PatientOnboardingState>> {
		return this.http.get<ApiSuccessResponse<PatientOnboardingState>>(
			`${environment.apiBaseUrl}/patient-onboarding/users/${userId}`
		);
	}

	updatePatientProfile(
		userId: number,
		payload: PatientProfileUpdateRequest
	): Observable<ApiSuccessResponse<PatientOnboardingState>> {
		return this.http.put<ApiSuccessResponse<PatientOnboardingState>>(
			`${environment.apiBaseUrl}/patient-onboarding/users/${userId}/profile`,
			payload
		);
	}

	submitPatientConsent(
		userId: number,
		payload: PatientConsentRequest
	): Observable<ApiSuccessResponse<PatientOnboardingState>> {
		return this.http.post<ApiSuccessResponse<PatientOnboardingState>>(
			`${environment.apiBaseUrl}/patient-onboarding/users/${userId}/consent`,
			payload
		);
	}

	private buildPaginationParams(options: { skip?: number; limit?: number }): HttpParams {
		let params = new HttpParams();

		if (options.skip !== undefined) {
			params = params.set('skip', options.skip);
		}

		if (options.limit !== undefined) {
			params = params.set('limit', options.limit);
		}

		return params;
	}
}

