import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  AdminRoleListResponse,
  AdminUserCreateRequest,
  AdminUserFilters,
  AdminUserListResponse,
  AdminUserResponse,
  AdminUserStatus,
  AdminUserUpdateRequest,
} from '../../shared/types/navigator/admin-user';

@Injectable({ providedIn: 'root' })
export class AdminUserApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/admin`;

  list(userId: number, filters: AdminUserFilters): Observable<AdminUserListResponse> {
    let params = this.actorParams(userId)
      .set('skip', filters.skip ?? 0)
      .set('limit', filters.limit ?? 25);
    if (filters.search) params = params.set('search', filters.search);
    if (filters.role_name) params = params.set('role_name', filters.role_name);
    if (filters.user_status) params = params.set('user_status', filters.user_status);
    return this.http.get<AdminUserListResponse>(`${this.baseUrl}/users`, { params });
  }

  listRoles(userId: number): Observable<AdminRoleListResponse> {
    return this.http.get<AdminRoleListResponse>(`${this.baseUrl}/roles`, {
      params: this.actorParams(userId),
    });
  }

  create(userId: number, payload: AdminUserCreateRequest): Observable<AdminUserResponse> {
    return this.http.post<AdminUserResponse>(`${this.baseUrl}/users`, payload, {
      params: this.actorParams(userId),
    });
  }

  update(
    userId: number,
    targetUserId: number,
    payload: AdminUserUpdateRequest,
  ): Observable<AdminUserResponse> {
    return this.http.put<AdminUserResponse>(`${this.baseUrl}/users/${targetUserId}`, payload, {
      params: this.actorParams(userId),
    });
  }

  updateStatus(
    userId: number,
    targetUserId: number,
    status: AdminUserStatus,
  ): Observable<AdminUserResponse> {
    return this.http.patch<AdminUserResponse>(
      `${this.baseUrl}/users/${targetUserId}/status`,
      { status },
      { params: this.actorParams(userId) },
    );
  }

  private actorParams(userId: number): HttpParams {
    return new HttpParams().set('user_id', userId);
  }
}