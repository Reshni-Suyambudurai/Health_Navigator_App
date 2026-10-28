import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  StaffDashboardAnalyticsResponse,
  StaffDashboardPeriod,
} from '../../shared/types/navigator/staff-dashboard';

@Injectable({ providedIn: 'root' })
export class StaffDashboardApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/staff-dashboard`;

  getAnalytics(
    userId: number,
    period: StaffDashboardPeriod,
    fromDate?: string,
    toDate?: string,
  ): Observable<StaffDashboardAnalyticsResponse> {
    let params = new HttpParams().set('period', period);
    if (period === 'THIS_MONTH' && fromDate && toDate) {
      params = params.set('from_date', fromDate).set('to_date', toDate);
    }
    return this.http.get<StaffDashboardAnalyticsResponse>(
      `${this.baseUrl}/users/${userId}/analytics`,
      { params },
    );
  }
}
