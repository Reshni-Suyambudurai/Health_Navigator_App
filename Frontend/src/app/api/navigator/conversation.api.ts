import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { CareTeamRequestStatus, ConversationHistoryData, SendConversationMessageData } from '../../shared/types/navigator/conversation';

interface ApiSuccessResponse<TData> {
  status: string;
  message: string;
  data: TData;
}

@Injectable({ providedIn: 'root' })
export class ConversationApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/conversations`;

  getHistory(userId: number, threadId?: number): Observable<ApiSuccessResponse<ConversationHistoryData>> {
    let params = new HttpParams();
    if (threadId !== undefined) {
      params = params.set('thread_id', threadId);
    }
    return this.http.get<ApiSuccessResponse<ConversationHistoryData>>(`${this.baseUrl}/users/${userId}/messages`, { params });
  }

  getCareTeamRequests(userId: number): Observable<ApiSuccessResponse<{ requests: CareTeamRequestStatus[] }>> {
    return this.http.get<ApiSuccessResponse<{ requests: CareTeamRequestStatus[] }>>(`${this.baseUrl}/users/${userId}/care-team-requests`);
  }

  sendMessage(userId: number, message: string, newSession = false): Observable<ApiSuccessResponse<SendConversationMessageData>> {
    return this.http.post<ApiSuccessResponse<SendConversationMessageData>>(`${this.baseUrl}/messages`, {
      user_id: userId,
      message,
      new_session: newSession,
    });
  }

  requestCareTeamFollowUp(userId: number, message?: string): Observable<ApiSuccessResponse<{ escalation_id: number; status: string }>> {
    return this.http.post<ApiSuccessResponse<{ escalation_id: number; status: string }>>(`${this.baseUrl}/care-team-requests`, {
      user_id: userId,
      message: message || null,
    });
  }
}