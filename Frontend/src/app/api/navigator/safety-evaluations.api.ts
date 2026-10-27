import { HttpClient,HttpParams } from '@angular/common/http';
import { Injectable,inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { SafetyEvaluationResponse } from '../../shared/types/navigator/safety-evaluations';
import { ApiSuccessResponse } from '../../shared/types/navigator/user';
@Injectable({providedIn:'root'})
export class SafetyEvaluationsApi{
 private readonly http=inject(HttpClient); private readonly baseUrl=`${environment.apiBaseUrl}/clinical-governance/safety-evaluations`;
 getOverview(userId:number,organizationId?:number|null):Observable<SafetyEvaluationResponse>{let params=new HttpParams().set('user_id',userId);if(organizationId)params=params.set('organization_id',organizationId);return this.http.get<SafetyEvaluationResponse>(this.baseUrl,{params});}
 recordDecision(userId:number,organizationId:number,resultKey:string,decision:string,notes:string):Observable<ApiSuccessResponse<{result_key:string}>>{return this.http.post<ApiSuccessResponse<{result_key:string}>>(`${this.baseUrl}/decisions`,{organization_id:organizationId,result_key:resultKey,decision,notes},{params:new HttpParams().set('user_id',userId)});}
}
