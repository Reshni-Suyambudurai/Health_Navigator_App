import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { ConversationHistoryData, SendConversationMessageData } from '../../shared/types/navigator/conversation';

interface ApiSuccessResponse<TData> {
  status: string;
  message: string;
  data: TData;
}

@Injectable({ providedIn: 'root' })
export class ConversationApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/conversations`;

  getHistory(userId: number): Observable<ApiSuccessResponse<ConversationHistoryData>> {
    return this.http.get<ApiSuccessResponse<ConversationHistoryData>>(`${this.baseUrl}/users/${userId}/messages`);
  }

  sendMessage(userId: number, message: string): Observable<ApiSuccessResponse<SendConversationMessageData>> {
    return this.http.post<ApiSuccessResponse<SendConversationMessageData>>(`${this.baseUrl}/messages`, {
      user_id: userId,
      message,
    });
  }
}