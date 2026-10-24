import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  OrganizationResponse,
  OrganizationUpdateRequest,
} from '../../shared/types/navigator/organization';

@Injectable({ providedIn: 'root' })
export class OrganizationApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/organizations/current`;

  getCurrent(userId: number): Observable<OrganizationResponse> {
    return this.http.get<OrganizationResponse>(this.baseUrl, {
      params: this.userParams(userId),
    });
  }

  updateCurrent(userId: number, payload: OrganizationUpdateRequest): Observable<OrganizationResponse> {
    return this.http.put<OrganizationResponse>(this.baseUrl, payload, {
      params: this.userParams(userId),
    });
  }

  private userParams(userId: number): HttpParams {
    return new HttpParams().set('user_id', userId);
  }
}