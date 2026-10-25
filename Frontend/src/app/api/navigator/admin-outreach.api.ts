import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  AdminCampaignFilters,
  AdminCampaignListResponse,
  AdminCampaignRequest,
  AdminCampaignResponse,
  AdminCampaignStatus,
  AdminCohortMembersResponse,
  AdminCreateOutreachResponse,
  AdminOutreachSelection,
  AdminTemplateListResponse,
  AdminWorkflowListResponse,
  AdminWorkflowRequest,
  AdminWorkflowResponse,
} from '../../shared/types/navigator/admin-outreach';

@Injectable({ providedIn: 'root' })
export class AdminOutreachApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/admin/outreach-campaigns`;

  listCampaigns(userId: number, filters: AdminCampaignFilters): Observable<AdminCampaignListResponse> {
    let params = this.actorParams(userId)
      .set('skip', filters.skip ?? 0)
      .set('limit', filters.limit ?? 25);
    if (filters.status) params = params.set('campaign_status', filters.status);
    if (filters.campaign_type) params = params.set('campaign_type', filters.campaign_type);
    return this.http.get<AdminCampaignListResponse>(this.baseUrl, { params });
  }

  getCampaign(userId: number, campaignId: number): Observable<AdminCampaignResponse> {
    return this.http.get<AdminCampaignResponse>(`${this.baseUrl}/${campaignId}`, {
      params: this.actorParams(userId),
    });
  }

  listCohortMembers(
    userId: number,
    campaignId: number,
    skip = 0,
    limit = 20,
  ): Observable<AdminCohortMembersResponse> {
    const params = this.actorParams(userId).set('skip', skip).set('limit', limit);
    return this.http.get<AdminCohortMembersResponse>(
      `${this.baseUrl}/${campaignId}/cohort-members`,
      { params },
    );
  }

  createOutreachEvents(
    userId: number,
    campaignId: number,
    selections: AdminOutreachSelection[],
  ): Observable<AdminCreateOutreachResponse> {
    return this.http.post<AdminCreateOutreachResponse>(
      `${this.baseUrl}/${campaignId}/outreach-events`,
      { selections },
      { params: this.actorParams(userId) },
    );
  }

  createCampaign(userId: number, payload: AdminCampaignRequest): Observable<AdminCampaignResponse> {
    return this.http.post<AdminCampaignResponse>(this.baseUrl, payload, {
      params: this.actorParams(userId),
    });
  }

  updateCampaign(
    userId: number,
    campaignId: number,
    payload: AdminCampaignRequest,
  ): Observable<AdminCampaignResponse> {
    return this.http.put<AdminCampaignResponse>(`${this.baseUrl}/${campaignId}`, payload, {
      params: this.actorParams(userId),
    });
  }

  transitionCampaign(
    userId: number,
    campaignId: number,
    status: AdminCampaignStatus,
  ): Observable<AdminCampaignResponse> {
    return this.http.patch<AdminCampaignResponse>(
      `${this.baseUrl}/${campaignId}/status`,
      { status },
      { params: this.actorParams(userId) },
    );
  }

  setAutoOutreach(
    userId: number,
    campaignId: number,
    enabled: boolean,
  ): Observable<AdminCampaignResponse> {
    return this.http.patch<AdminCampaignResponse>(
      `${this.baseUrl}/${campaignId}/auto-outreach`,
      { enabled },
      { params: this.actorParams(userId) },
    );
  }

  listWorkflows(userId: number, campaignId: number): Observable<AdminWorkflowListResponse> {
    return this.http.get<AdminWorkflowListResponse>(`${this.baseUrl}/${campaignId}/workflows`, {
      params: this.actorParams(userId),
    });
  }

  createWorkflow(
    userId: number,
    campaignId: number,
    payload: AdminWorkflowRequest,
  ): Observable<AdminWorkflowResponse> {
    return this.http.post<AdminWorkflowResponse>(`${this.baseUrl}/${campaignId}/workflows`, payload, {
      params: this.actorParams(userId),
    });
  }

  updateWorkflow(
    userId: number,
    workflowId: number,
    payload: AdminWorkflowRequest,
  ): Observable<AdminWorkflowResponse> {
    return this.http.put<AdminWorkflowResponse>(`${this.baseUrl}/workflows/${workflowId}`, payload, {
      params: this.actorParams(userId),
    });
  }

  listTemplates(userId: number): Observable<AdminTemplateListResponse> {
    return this.http.get<AdminTemplateListResponse>(`${this.baseUrl}/templates`, {
      params: this.actorParams(userId),
    });
  }

  private actorParams(userId: number): HttpParams {
    return new HttpParams().set('user_id', userId);
  }
}