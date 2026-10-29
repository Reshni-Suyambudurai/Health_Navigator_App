import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  ClinicalGovernanceAnalyticsResponse,
  GovernancePeriod,
} from '../../shared/types/navigator/clinical-governance-dashboard';

@Injectable({ providedIn: 'root' })
export class ClinicalGovernanceDashboardApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/clinical-governance/dashboard`;

  getAnalytics(
    userId: number,
    period: GovernancePeriod,
    startDate?: string,
    endDate?: string,
  ): Observable<ClinicalGovernanceAnalyticsResponse> {
    let params = new HttpParams().set('period', period);
    if (period === 'custom' && startDate && endDate) {
      params = params.set('start_date', startDate).set('end_date', endDate);
    }
    return this.http.get<ClinicalGovernanceAnalyticsResponse>(
      `${this.baseUrl}/users/${userId}/analytics`,
      { params },
    );
  }
}