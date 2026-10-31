import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  TcmCampaignListResponse,
  TcmPatientCategory,
  TcmPatientDetailResponse,
  TcmPatientPageResponse,
  TcmSummaryResponse,
  TcmWorkflowProgressResponse,
} from '../../shared/types/navigator/tcm-tracker';

export interface TcmTrackerFilters {
  campaignId?: number;
  fromDate?: string;
  toDate?: string;
}

@Injectable({ providedIn: 'root' })
export class TcmTrackerApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/tcm-tracker/users`;

  getCampaigns(userId: number): Observable<TcmCampaignListResponse> {
    return this.http.get<TcmCampaignListResponse>(`${this.baseUrl}/${userId}/campaigns`);
  }

  getSummary(userId: number, filters: TcmTrackerFilters): Observable<TcmSummaryResponse> {
    return this.http.get<TcmSummaryResponse>(
      `${this.baseUrl}/${userId}/summary`,
      { params: this.filterParams(filters) },
    );
  }

  getWorkflowProgress(
    userId: number,
    filters: TcmTrackerFilters,
  ): Observable<TcmWorkflowProgressResponse> {
    return this.http.get<TcmWorkflowProgressResponse>(
      `${this.baseUrl}/${userId}/workflow-progress`,
      { params: this.filterParams(filters) },
    );
  }

  getPatients(
    userId: number,
    category: TcmPatientCategory,
    page: number,
    pageSize: number,
    filters: TcmTrackerFilters,
    search?: string,
  ): Observable<TcmPatientPageResponse> {
    let params = this.filterParams(filters)
      .set('category', category)
      .set('page', page)
      .set('page_size', pageSize);
    if (search?.trim()) {
      params = params.set('search', search.trim());
    }
    return this.http.get<TcmPatientPageResponse>(`${this.baseUrl}/${userId}/patients`, { params });
  }

  getPatientDetails(
    userId: number,
    campaignId: number,
    episodeId: number,
  ): Observable<TcmPatientDetailResponse> {
    return this.http.get<TcmPatientDetailResponse>(
      `${this.baseUrl}/${userId}/campaigns/${campaignId}/episodes/${episodeId}/details`,
    );
  }

  private filterParams(filters: TcmTrackerFilters): HttpParams {
    let params = new HttpParams();
    if (filters.campaignId) {
      params = params.set('campaign_id', filters.campaignId);
    }
    if (filters.fromDate) {
      params = params.set('from_date', filters.fromDate);
    }
    if (filters.toDate) {
      params = params.set('to_date', filters.toDate);
    }
    return params;
  }
}