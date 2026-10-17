import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  ApiSuccessResponse,
  PatientIntakeMetadata,
  PatientIntakeResult,
  PatientOnboardFromFhirRequest,
} from '../../shared/types/navigator/patient-intake';

@Injectable({ providedIn: 'root' })
export class PatientIntakeApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/patient-intake`;

  getMetadata(): Observable<ApiSuccessResponse<PatientIntakeMetadata>> {
    return this.http.get<ApiSuccessResponse<PatientIntakeMetadata>>(`${this.baseUrl}/metadata`);
  }

  onboardFromFhir(
    payload: PatientOnboardFromFhirRequest
  ): Observable<ApiSuccessResponse<PatientIntakeResult>> {
    return this.http.post<ApiSuccessResponse<PatientIntakeResult>>(`${this.baseUrl}/from-fhir`, payload);
  }
}
