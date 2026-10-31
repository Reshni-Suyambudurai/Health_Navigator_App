import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  AdminCheckinQuestionListResponse,
  AdminCheckinQuestionRequest,
  AdminCheckinQuestionResponse,
  AdminCheckinTemplateListResponse,
  AdminCheckinTemplateRequest,
  AdminCheckinTemplateResponse,
  CheckinTemplateReviewListResponse,
  CheckinTemplateReviewResponse,
} from '../../shared/types/navigator/admin-checkin-template';
import { ApiSuccessResponse } from '../../shared/types/navigator/user';

@Injectable({ providedIn: 'root' })
export class AdminCheckinTemplateApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/admin/checkin-templates`;

  list(userId: number): Observable<AdminCheckinTemplateListResponse> {
    return this.http.get<AdminCheckinTemplateListResponse>(this.baseUrl, { params: this.actor(userId) });
  }

  get(userId: number, templateId: number): Observable<AdminCheckinTemplateResponse> {
    return this.http.get<AdminCheckinTemplateResponse>(`${this.baseUrl}/${templateId}`, {
      params: this.actor(userId),
    });
  }

  create(userId: number, payload: AdminCheckinTemplateRequest): Observable<AdminCheckinTemplateResponse> {
    return this.http.post<AdminCheckinTemplateResponse>(this.baseUrl, payload, { params: this.actor(userId) });
  }

  update(
    userId: number,
    templateId: number,
    payload: AdminCheckinTemplateRequest,
  ): Observable<AdminCheckinTemplateResponse> {
    return this.http.put<AdminCheckinTemplateResponse>(`${this.baseUrl}/${templateId}`, payload, {
      params: this.actor(userId),
    });
  }

  delete(userId: number, templateId: number): Observable<ApiSuccessResponse<null>> {
    return this.http.delete<ApiSuccessResponse<null>>(`${this.baseUrl}/${templateId}`, {
      params: this.actor(userId),
    });
  }

  createQuestion(
    userId: number,
    templateId: number,
    payload: AdminCheckinQuestionRequest,
  ): Observable<AdminCheckinQuestionResponse> {
    return this.http.post<AdminCheckinQuestionResponse>(`${this.baseUrl}/${templateId}/questions`, payload, {
      params: this.actor(userId),
    });
  }

  updateQuestion(
    userId: number,
    questionId: number,
    payload: AdminCheckinQuestionRequest,
  ): Observable<AdminCheckinQuestionResponse> {
    return this.http.put<AdminCheckinQuestionResponse>(`${this.baseUrl}/questions/${questionId}`, payload, {
      params: this.actor(userId),
    });
  }

  deleteQuestion(userId: number, questionId: number): Observable<ApiSuccessResponse<null>> {
    return this.http.delete<ApiSuccessResponse<null>>(`${this.baseUrl}/questions/${questionId}`, {
      params: this.actor(userId),
    });
  }

  reorder(
    userId: number,
    templateId: number,
    questionIds: number[],
  ): Observable<AdminCheckinQuestionListResponse> {
    return this.http.put<AdminCheckinQuestionListResponse>(
      `${this.baseUrl}/${templateId}/questions/reorder`,
      { question_ids: questionIds },
      { params: this.actor(userId) },
    );
  }

  submitReview(
    userId: number,
    templateId: number,
    submissionNote: string | null,
  ): Observable<CheckinTemplateReviewResponse> {
    return this.http.post<CheckinTemplateReviewResponse>(
      `${this.baseUrl}/${templateId}/submit-review`,
      { submission_note: submissionNote },
      { params: this.actor(userId) },
    );
  }

  createVersion(userId: number, templateId: number): Observable<AdminCheckinTemplateResponse> {
    return this.http.post<AdminCheckinTemplateResponse>(
      `${this.baseUrl}/${templateId}/versions`,
      {},
      { params: this.actor(userId) },
    );
  }

  private actor(userId: number): HttpParams {
    return new HttpParams().set('user_id', userId);
  }
}

@Injectable({ providedIn: 'root' })
export class ClinicalCheckinTemplateReviewApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/clinical-governance/checkin-template-reviews`;

  list(userId: number, reviewStatus = 'PENDING', organizationId?: number | null): Observable<CheckinTemplateReviewListResponse> {
    let params = this.actor(userId).set('review_status', reviewStatus);
    if (organizationId) params = params.set('organization_id', organizationId);
    return this.http.get<CheckinTemplateReviewListResponse>(this.baseUrl, {
      params,
    });
  }

  get(userId: number, reviewId: number): Observable<CheckinTemplateReviewResponse> {
    return this.http.get<CheckinTemplateReviewResponse>(`${this.baseUrl}/${reviewId}`, {
      params: this.actor(userId),
    });
  }

  decide(
    userId: number,
    reviewId: number,
    decision: 'APPROVED' | 'REJECTED',
    reviewNotes: string,
  ): Observable<CheckinTemplateReviewResponse> {
    return this.http.post<CheckinTemplateReviewResponse>(
      `${this.baseUrl}/${reviewId}/decision`,
      { decision, review_notes: reviewNotes },
      { params: this.actor(userId) },
    );
  }

  private actor(userId: number): HttpParams {
    return new HttpParams().set('user_id', userId);
  }
}