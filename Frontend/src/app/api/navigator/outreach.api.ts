import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  AppointmentAction,
  AppointmentActionListResponse,
  AppointmentActionRequest,
  CampaignListResponse,
  CampaignRequest,
  CheckinQuestion,
  CheckinQuestionRequest,
  CheckinTemplate,
  CheckinTemplateRequest,
  EventListResponse,
  EventStatus,
  FollowUpStatus,
  FollowUpTask,
  FollowUpTaskListResponse,
  OutreachCampaign,
  OutreachEvent,
  OutreachWorkflow,
  QuestionListResponse,
  SessionListResponse,
  TemplateListResponse,
  WorkflowListResponse,
  WorkflowRequest,
} from '../../shared/types/navigator/outreach';
import { ApiSuccessResponse } from '../../shared/types/navigator/user';

@Injectable({ providedIn: 'root' })
export class OutreachApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/outreach`;

  listCampaigns(): Observable<CampaignListResponse> {
    return this.http.get<CampaignListResponse>(`${this.baseUrl}/campaigns`);
  }

  createCampaign(userId: number, payload: CampaignRequest): Observable<ApiSuccessResponse<OutreachCampaign>> {
    return this.http.post<ApiSuccessResponse<OutreachCampaign>>(`${this.baseUrl}/campaigns`, payload, {
      params: this.userParams(userId),
    });
  }

  listWorkflows(campaignId: number): Observable<WorkflowListResponse> {
    return this.http.get<WorkflowListResponse>(`${this.baseUrl}/campaigns/${campaignId}/workflows`);
  }

  createWorkflow(campaignId: number, payload: WorkflowRequest): Observable<ApiSuccessResponse<OutreachWorkflow>> {
    return this.http.post<ApiSuccessResponse<OutreachWorkflow>>(
      `${this.baseUrl}/campaigns/${campaignId}/workflows`,
      payload,
    );
  }

  listTemplates(): Observable<TemplateListResponse> {
    return this.http.get<TemplateListResponse>(`${this.baseUrl}/checkin-templates`);
  }

  createTemplate(userId: number, payload: CheckinTemplateRequest): Observable<ApiSuccessResponse<CheckinTemplate>> {
    return this.http.post<ApiSuccessResponse<CheckinTemplate>>(`${this.baseUrl}/checkin-templates`, payload, {
      params: this.userParams(userId),
    });
  }

  listQuestions(templateId: number): Observable<QuestionListResponse> {
    return this.http.get<QuestionListResponse>(`${this.baseUrl}/checkin-templates/${templateId}/questions`);
  }

  createQuestion(templateId: number, payload: CheckinQuestionRequest): Observable<ApiSuccessResponse<CheckinQuestion>> {
    return this.http.post<ApiSuccessResponse<CheckinQuestion>>(
      `${this.baseUrl}/checkin-templates/${templateId}/questions`,
      payload,
    );
  }

  listEvents(): Observable<EventListResponse> {
    return this.http.get<EventListResponse>(`${this.baseUrl}/events`);
  }

  updateEvent(eventId: number, eventStatus: EventStatus): Observable<ApiSuccessResponse<OutreachEvent>> {
    return this.http.put<ApiSuccessResponse<OutreachEvent>>(`${this.baseUrl}/events/${eventId}`, {
      event_status: eventStatus,
    });
  }

  listSessions(): Observable<SessionListResponse> {
    return this.http.get<SessionListResponse>(`${this.baseUrl}/checkin-sessions`);
  }

  listAppointmentActions(appointmentId: number): Observable<AppointmentActionListResponse> {
    return this.http.get<AppointmentActionListResponse>(`${this.baseUrl}/appointments/${appointmentId}/actions`);
  }

  createAppointmentAction(
    userId: number,
    appointmentId: number,
    payload: AppointmentActionRequest,
  ): Observable<ApiSuccessResponse<AppointmentAction>> {
    return this.http.post<ApiSuccessResponse<AppointmentAction>>(
      `${this.baseUrl}/appointments/${appointmentId}/actions`,
      payload,
      { params: this.userParams(userId) },
    );
  }

  listTasks(): Observable<FollowUpTaskListResponse> {
    return this.http.get<FollowUpTaskListResponse>(`${this.baseUrl}/follow-up-tasks`);
  }

  updateTask(
    userId: number,
    taskId: number,
    taskStatus: FollowUpStatus,
  ): Observable<ApiSuccessResponse<FollowUpTask>> {
    return this.http.put<ApiSuccessResponse<FollowUpTask>>(
      `${this.baseUrl}/follow-up-tasks/${taskId}`,
      { status: taskStatus },
      { params: this.userParams(userId) },
    );
  }

  private userParams(userId: number): HttpParams {
    return new HttpParams().set('user_id', userId);
  }
}