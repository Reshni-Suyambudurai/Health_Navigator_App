import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { getSessionUser } from '../tokenstore';
import {
  OutreachEventDetail,
  OutreachEventFilterOptions,
  OutreachEventFilters,
  ProtectedOutreachEventDetailResponse,
  ProtectedOutreachEventListResponse,
} from '../../shared/types/navigator/outreach';

export type OutreachEventRole = 'admin' | 'care-manager';

@Injectable({ providedIn: 'root' })
export class OutreachEventApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  list(role: OutreachEventRole, filters: OutreachEventFilters): Observable<ProtectedOutreachEventListResponse> {
    return this.http.get<ProtectedOutreachEventListResponse>(`${this.baseUrl}/${role}/outreach-events`, {
      params: this.params(filters),
    });
  }

  get(role: OutreachEventRole, eventId: number): Observable<ProtectedOutreachEventDetailResponse> {
    return this.http.get<ProtectedOutreachEventDetailResponse>(
      `${this.baseUrl}/${role}/outreach-events/${eventId}`,
      { params: this.params({}) },
    );
  }

  options(role: OutreachEventRole, organizationId?: number, campaignId?: number): Observable<{ data: OutreachEventFilterOptions }> {
    let params = this.params({}).set('organization_id', organizationId ?? 0);
    if (campaignId) params = params.set('campaign_id', campaignId);
    return this.http.get<{ data: OutreachEventFilterOptions }>(`${this.baseUrl}/${role}/outreach-events/options`, { params });
  }

  private params(filters: OutreachEventFilters): HttpParams {
    const session = getSessionUser();
    let params = new HttpParams()
      .set('user_id', session?.user_id ?? session?.userId ?? 0)
      .set('organization_id', session?.organization_id ?? 0);
    const entries: [keyof OutreachEventFilters, string | number | undefined][] = [
      ['campaign_id', filters.campaign_id],
      ['workflow_id', filters.workflow_id],
      ['campaign_name', filters.campaign_name],
      ['workflow_name', filters.workflow_name],
      ['event_status', filters.event_status],
      ['delivery_status', filters.delivery_status],
      ['scheduled_from', filters.scheduled_from],
      ['scheduled_to', filters.scheduled_to],
      ['patient_search', filters.patient_search?.trim()],
      ['skip', filters.skip],
      ['limit', filters.limit],
    ];
    for (const [key, value] of entries) {
      if (value !== undefined && value !== '') params = params.set(key, value);
    }
    return params;
  }
}