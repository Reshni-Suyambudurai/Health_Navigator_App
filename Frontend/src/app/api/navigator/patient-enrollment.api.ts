import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  ApiSuccessResponse,
  PatientEnrollmentListData,
  PatientEnrollmentListParams,
} from '../../shared/types/navigator/patient-enrollment';

@Injectable({ providedIn: 'root' })
export class PatientEnrollmentApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/patient-enrollments`;

  getEnrollments(
    options: PatientEnrollmentListParams = {}
  ): Observable<ApiSuccessResponse<PatientEnrollmentListData>> {
    let params = new HttpParams();

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
}
