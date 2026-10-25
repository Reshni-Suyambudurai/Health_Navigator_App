import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { getSessionUser } from './tokenstore';
import {
  NotificationCreateRequest,
  NotificationListResponse,
  NotificationResponse,
  NotificationUnreadCountResponse,
} from '../shared/types/notification';

@Injectable({ providedIn: 'root' })
export class NotificationApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/notifications`;

  create(userId: number, payload: NotificationCreateRequest): Observable<NotificationResponse> {
    return this.http.post<NotificationResponse>(this.baseUrl, payload, { params: this.actor(userId) });
  }

  list(userId: number, limit = 50): Observable<NotificationListResponse> {
    return this.http.get<NotificationListResponse>(this.baseUrl, {
      params: this.actor(userId).set('skip', 0).set('limit', limit),
    });
  }

  unreadCount(userId: number): Observable<NotificationUnreadCountResponse> {
    return this.http.get<NotificationUnreadCountResponse>(`${this.baseUrl}/unread-count`, {
      params: this.actor(userId),
    });
  }

  get(userId: number, notificationId: number): Observable<NotificationResponse> {
    return this.http.get<NotificationResponse>(`${this.baseUrl}/${notificationId}`, {
      params: this.actor(userId),
    });
  }

  markRead(userId: number, notificationId: number): Observable<NotificationResponse> {
    return this.http.patch<NotificationResponse>(
      `${this.baseUrl}/${notificationId}/read`,
      {},
      { params: this.actor(userId) },
    );
  }

  private actor(userId: number): HttpParams {
    const session = getSessionUser();
    return new HttpParams().set('user_id', session?.user_id ?? session?.userId ?? userId);
  }
}