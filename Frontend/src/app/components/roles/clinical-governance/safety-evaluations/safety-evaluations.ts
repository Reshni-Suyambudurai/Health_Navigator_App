import { CommonModule } from '@angular/common';
import { Component,inject,signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NgIcon,provideIcons } from '@ng-icons/core';
import { heroArrowPath,heroBeaker,heroCheckCircle,heroClipboardDocumentCheck,heroClock,heroExclamationTriangle,heroShieldCheck,heroXCircle } from '@ng-icons/heroicons/outline';
import { finalize } from 'rxjs/operators';
import { SafetyEvaluationsApi } from '../../../../api/navigator/safety-evaluations.api';
import { getSessionUser } from '../../../../api/tokenstore';
import { SafetyDecision,SafetyEvaluationOverview,SafetyEvaluationResult } from '../../../../shared/types/navigator/safety-evaluations';
import { ToastState } from '../../../../shared/ui/toast/toast-state';
type EvaluationView='RUN'|'ISSUES'|'HISTORY';
@Component({selector:'app-safety-evaluations',standalone:true,imports:[CommonModule,FormsModule,NgIcon],providers:[provideIcons({heroArrowPath,heroBeaker,heroCheckCircle,heroClipboardDocumentCheck,heroClock,heroExclamationTriangle,heroShieldCheck,heroXCircle})],templateUrl:'./safety-evaluations.html',styleUrl:'./safety-evaluations.scss'})
export class SafetyEvaluations{
 private readonly api=inject(SafetyEvaluationsApi);private readonly toast=inject(ToastState);private readonly sessionUser=getSessionUser();
 readonly overview=signal<SafetyEvaluationOverview|null>(null);readonly loading=signal(false);readonly saving=signal(false);readonly error=signal<string|null>(null);readonly view=signal<EvaluationView>('RUN');readonly selectedResultKey=signal<string|null>(null);decision='REMEDIATION_REQUIRED';decisionNotes='';
 ngOnInit():void{this.load();}
 load(organizationId:number|null=this.overview()?.selected_organization_id??null):void{const userId=this.userId();if(!userId){this.error.set('Your session has expired.');return;}this.loading.set(true);this.error.set(null);this.api.getOverview(userId,organizationId).pipe(finalize(()=>this.loading.set(false))).subscribe({next:r=>{this.overview.set(r.data);if(!this.selectedResultKey()||!r.data.results.some(i=>i.result_key===this.selectedResultKey()))this.selectedResultKey.set(r.data.results[0]?.result_key??null);},error:e=>this.error.set((e as {error?:{message?:string}}).error?.message??'Unable to load safety evaluations.')});}
 changeOrganization(value:number|string):void{this.selectedResultKey.set(null);this.load(Number(value));}
 selectView(view:EvaluationView):void{this.view.set(view);if(view!=='HISTORY')this.selectedResultKey.set(this.visibleResults[0]?.result_key??null);}
 get visibleResults():SafetyEvaluationResult[]{const results=this.overview()?.results??[];return this.view()==='ISSUES'?results.filter(r=>r.status==='FAIL'):results;}
 get selectedResult():SafetyEvaluationResult|null{return this.overview()?.results.find(r=>r.result_key===this.selectedResultKey())??null;}
 get userOrganizations(){const userOrgId=this.sessionUser?.organization_id;return this.overview()?.organizations.filter(o=>o.organization_id===userOrgId)??[];}
 get passRate():number{const run=this.overview()?.run;return run?.total_checks?Math.round(run.passed/run.total_checks*100):0;}
 recordDecision():void{const userId=this.userId(),org=this.overview()?.selected_organization_id,result=this.selectedResult;if(!userId||!org||!result||!this.decisionNotes.trim()){this.error.set('Decision notes are required.');return;}this.saving.set(true);this.api.recordDecision(userId,org,result.result_key,this.decision,this.decisionNotes).pipe(finalize(()=>this.saving.set(false))).subscribe({next:r=>{this.toast.success(r.message);this.decisionNotes='';this.load(org);},error:e=>this.error.set((e as {error?:{message?:string}}).error?.message??'Unable to record the decision.')});}
 label(value:string):string{return value.replaceAll('_',' ').toLowerCase().replace(/\b\w/g,l=>l.toUpperCase());}formatDate(value:string):string{return new Date(value).toLocaleString(undefined,{month:'short',day:'numeric',year:'numeric',hour:'numeric',minute:'2-digit'});}decisionNote(item:SafetyDecision):string{return item.details.notes||'No supporting note recorded.';}private userId():number{return Number(this.sessionUser?.user_id??this.sessionUser?.userId??0);}
}
