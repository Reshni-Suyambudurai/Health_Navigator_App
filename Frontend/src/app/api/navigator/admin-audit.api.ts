import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AdminAuditAction, AdminAuditListResponse } from '../../shared/types/navigator/audit-trail';

@Injectable({ providedIn: 'root' })
export class AdminAuditApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/admin/audit-trail`;

  list(
    userId: number,
    skip = 0,
    limit = 25,
    action: AdminAuditAction | '' = '',
  ): Observable<AdminAuditListResponse> {
    let params = new HttpParams()
      .set('user_id', userId)
      .set('skip', skip)
      .set('limit', limit);
    if (action) params = params.set('action', action);
    return this.http.get<AdminAuditListResponse>(this.baseUrl, { params });
  }
}