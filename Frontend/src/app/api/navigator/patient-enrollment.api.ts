import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  ApiSuccessResponse,
  PatientEnrollmentListData,
  PatientEnrollmentListParams,
  PatientEnrollmentStatusUpdateData,
  PatientEnrollmentStatusUpdateRequest,
  PatientCareDetailsData,
  PatientCareDetailsUpsertRequest,
} from '../../shared/types/navigator/patient-enrollment';

@Injectable({ providedIn: 'root' })
export class PatientEnrollmentApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/patient-enrollments`;

  getEnrollments(
    options: PatientEnrollmentListParams = {}
  ): Observable<ApiSuccessResponse<PatientEnrollmentListData>> {
    let params = new HttpParams();

    if (options.patient_id !== undefined) {
      params = params.set('patient_id', options.patient_id);
    }

    if (options.organization_id !== undefined) {
      params = params.set('organization_id', options.organization_id);
    }

    if (options.status_filter !== undefined) {
      params = params.set('status_filter', options.status_filter);
    }

    if (options.skip !== undefined) {
      params = params.set('skip', options.skip);
    }

    if (options.limit !== undefined) {
      params = params.set('limit', options.limit);
    }

    return this.http.get<ApiSuccessResponse<PatientEnrollmentListData>>(this.baseUrl, { params });
  }

  updateStatus(
    enrollmentId: number,
    payload: PatientEnrollmentStatusUpdateRequest
  ): Observable<ApiSuccessResponse<PatientEnrollmentStatusUpdateData>> {
    return this.http.patch<ApiSuccessResponse<PatientEnrollmentStatusUpdateData>>(
      `${this.baseUrl}/${enrollmentId}/status`,
      payload
    );
  }

  getCareDetails(patientId: number): Observable<ApiSuccessResponse<PatientCareDetailsData>> {
    return this.http.get<ApiSuccessResponse<PatientCareDetailsData>>(
      `${this.baseUrl}/patient/${patientId}/care-details`
    );
  }

  upsertCareDetails(
    patientId: number,
    payload: PatientCareDetailsUpsertRequest
  ): Observable<ApiSuccessResponse<PatientCareDetailsData>> {
    return this.http.put<ApiSuccessResponse<PatientCareDetailsData>>(
      `${this.baseUrl}/patient/${patientId}/care-details`,
      payload
    );
  }
}
