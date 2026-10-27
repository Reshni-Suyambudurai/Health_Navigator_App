import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { SafetyRulesResponse, ScenarioTestResponse } from '../../shared/types/navigator/safety-rules';
import { ApiSuccessResponse } from '../../shared/types/navigator/user';

@Injectable({ providedIn: 'root' })
export class SafetyRulesApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/clinical-governance/safety-rules`;

  getOverview(userId: number): Observable<SafetyRulesResponse> {
    return this.http.get<SafetyRulesResponse>(this.baseUrl, { params: this.userParams(userId) });
  }

  approveRule(userId: number, ruleId: number, note: string): Observable<ApiSuccessResponse<{ rule_id: number }>> {
    return this.http.post<ApiSuccessResponse<{ rule_id: number }>>(`${this.baseUrl}/${ruleId}/approve`, { note }, { params: this.userParams(userId) });
  }

  testScenario(userId: number, text: string, ruleId: number | null): Observable<ScenarioTestResponse> {
    return this.http.post<ScenarioTestResponse>(`${this.baseUrl}/scenario-test`, { text, rule_id: ruleId }, { params: this.userParams(userId) });
  }

  private userParams(userId: number): HttpParams { return new HttpParams().set('user_id', userId); }
}
