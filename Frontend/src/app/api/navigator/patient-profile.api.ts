import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ApiSuccessResponse, PatientProfileRecord } from '../../shared/types/navigator/patient-profile';

@Injectable({ providedIn: 'root' })
export class PatientProfileApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/patient-profiles`;

  getPatientProfile(patientId: number): Observable<ApiSuccessResponse<PatientProfileRecord>> {
    return this.http.get<ApiSuccessResponse<PatientProfileRecord>>(`${this.baseUrl}/${patientId}`);
  }
}
