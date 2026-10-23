import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { EscalationDetail, EscalationQueueData } from '../../shared/types/navigator/escalation';

interface ApiSuccessResponse<TData> {
  status: string;
  message: string;
  data: TData;
}

@Injectable({ providedIn: 'root' })
export class EscalationApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/escalations`;

  list(nurseUserId: number, status?: string): Observable<ApiSuccessResponse<EscalationQueueData>> {
    let params = new HttpParams().set('nurse_user_id', nurseUserId);
    if (status) {
      params = params.set('status', status);
    }
    return this.http.get<ApiSuccessResponse<EscalationQueueData>>(this.baseUrl, { params });
  }

  detail(nurseUserId: number, escalationId: number): Observable<ApiSuccessResponse<EscalationDetail>> {
    return this.http.get<ApiSuccessResponse<EscalationDetail>>(`${this.baseUrl}/${escalationId}`, {
      params: { nurse_user_id: nurseUserId },
    });
  }

  claim(nurseUserId: number, escalationId: number): Observable<ApiSuccessResponse<EscalationDetail>> {
    return this.http.post<ApiSuccessResponse<EscalationDetail>>(`${this.baseUrl}/${escalationId}/claim`, null, {
      params: { nurse_user_id: nurseUserId },
    });
  }

  addAction(nurseUserId: number, escalationId: number, actionType: string, notes: string): Observable<ApiSuccessResponse<EscalationDetail>> {
    return this.http.post<ApiSuccessResponse<EscalationDetail>>(`${this.baseUrl}/${escalationId}/actions`, {
      nurse_user_id: nurseUserId,
      action_type: actionType,
      notes: notes || null,
    });
  }

  resolve(nurseUserId: number, escalationId: number, notes: string): Observable<ApiSuccessResponse<EscalationDetail>> {
    return this.http.post<ApiSuccessResponse<EscalationDetail>>(`${this.baseUrl}/${escalationId}/resolve`, {
      nurse_user_id: nurseUserId,
      notes: notes || null,
    });
  }
}