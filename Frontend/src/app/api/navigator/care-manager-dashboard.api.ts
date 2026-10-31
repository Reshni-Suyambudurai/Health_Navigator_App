import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { CareManagerAnalyticsResponse } from '../../shared/types/navigator/care-manager-dashboard';

@Injectable({ providedIn: 'root' })
export class CareManagerDashboardApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/care-manager-dashboard`;

  getAnalytics(userId: number): Observable<CareManagerAnalyticsResponse> {
    return this.http.get<CareManagerAnalyticsResponse>(`${this.baseUrl}/users/${userId}/analytics`);
  }
}
