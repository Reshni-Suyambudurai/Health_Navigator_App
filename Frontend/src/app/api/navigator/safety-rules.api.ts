import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  ClinicalGuardrailCreate,
  SafetyRulesResponse,
  SafetyRuleUpdate,
  ScenarioTestResponse,
} from '../../shared/types/navigator/safety-rules';
import { ApiSuccessResponse } from '../../shared/types/navigator/user';

@Injectable({ providedIn: 'root' })
export class SafetyRulesApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/clinical-guardrails`;
  private readonly scenarioUrl = `${environment.apiBaseUrl}/clinical-governance/safety-rules/scenario-test`;

  getOverview(userId: number): Observable<SafetyRulesResponse> {
    return this.http.get<SafetyRulesResponse>(this.baseUrl, { params: this.userParams(userId) });
  }

  createGuardrail(userId: number, request: ClinicalGuardrailCreate): Observable<ApiSuccessResponse<{ guardrail_id: number; rule_ids: number[] }>> {
    return this.http.post<ApiSuccessResponse<{ guardrail_id: number; rule_ids: number[] }>>(this.baseUrl, request, { params: this.userParams(userId) });
  }

  addRule(userId: number, guardrailId: number, request: SafetyRuleUpdate): Observable<ApiSuccessResponse<{ rule_id: number }>> {
    const { guardrail_name: _name, description: _description, ...rule } = request;
    return this.http.post<ApiSuccessResponse<{ rule_id: number }>>(`${this.baseUrl}/${guardrailId}/rules`, rule, { params: this.userParams(userId) });
  }

  updateDraftRule(userId: number, ruleId: number, request: SafetyRuleUpdate): Observable<ApiSuccessResponse<{ rule_id: number }>> {
    return this.http.put<ApiSuccessResponse<{ rule_id: number }>>(`${this.baseUrl}/rules/${ruleId}`, request, { params: this.userParams(userId) });
  }

  submitRules(userId: number, ruleIds: number[]): Observable<ApiSuccessResponse<{ rule_ids: number[]; notified_reviewers: number }>> {
    return this.http.post<ApiSuccessResponse<{ rule_ids: number[]; notified_reviewers: number }>>(`${this.baseUrl}/rules/submit`, { rule_ids: ruleIds }, { params: this.userParams(userId) });
  }

  approveRule(userId: number, ruleId: number, reason: string, effectiveFrom: string): Observable<ApiSuccessResponse<{ rule_id: number }>> {
    return this.http.post<ApiSuccessResponse<{ rule_id: number }>>(`${this.baseUrl}/rules/${ruleId}/approve`, { reason, effective_from: effectiveFrom }, { params: this.userParams(userId) });
  }

  rejectRule(userId: number, ruleId: number, reason: string): Observable<ApiSuccessResponse<{ rule_id: number }>> {
    return this.http.post<ApiSuccessResponse<{ rule_id: number }>>(`${this.baseUrl}/rules/${ruleId}/reject`, { reason }, { params: this.userParams(userId) });
  }

  deactivateRule(userId: number, ruleId: number, reason: string): Observable<ApiSuccessResponse<{ rule_id: number }>> {
    return this.http.post<ApiSuccessResponse<{ rule_id: number }>>(`${this.baseUrl}/rules/${ruleId}/deactivate`, { reason }, { params: this.userParams(userId) });
  }

  activateRule(userId: number, ruleId: number, request: SafetyRuleUpdate, changeReason: string, effectiveFrom: string): Observable<ApiSuccessResponse<{ rule_id: number }>> {
    return this.http.put<ApiSuccessResponse<{ rule_id: number }>>(`${this.baseUrl}/rules/${ruleId}/activate`, { ...request, change_reason: changeReason, effective_from: effectiveFrom }, { params: this.userParams(userId) });
  }

  testScenario(userId: number, text: string, ruleId: number | null): Observable<ScenarioTestResponse> {
    return this.http.post<ScenarioTestResponse>(this.scenarioUrl, { text, rule_id: ruleId }, { params: this.userParams(userId) });
  }

  private userParams(userId: number): HttpParams {
    return new HttpParams().set('user_id', userId);
  }
}
