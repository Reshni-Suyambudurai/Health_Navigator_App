import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { finalize, forkJoin } from 'rxjs';
import { AdminOutreachApi } from '../../../../api/navigator/admin-outreach.api';
import { getSessionUser } from '../../../../api/tokenstore';
import {
  AdminCampaignRecord,
  AdminTemplateOption,
  AdminWorkflowRecord,
  AdminWorkflowRequest,
  WorkflowChannel,
  WorkflowTriggerAnchor,
  WorkflowTriggerType,
} from '../../../../shared/types/navigator/admin-outreach';
import { Breadcrumb, BreadcrumbItem } from '../../../../shared/ui/breadcrumb/breadcrumb';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

@Component({
  selector: 'app-system-admin-outreach-workflows',
  standalone: true,
  imports: [CommonModule, FormsModule, Breadcrumb],
  templateUrl: './outreach-workflows.html',
  styleUrl: './outreach-workflows.scss',
})
export class SystemAdminOutreachWorkflows implements OnInit {
  private readonly api = inject(AdminOutreachApi);
  private readonly route = inject(ActivatedRoute);
  private readonly toast = inject(ToastState);
  private readonly sessionUser = getSessionUser();

  readonly campaign = signal<AdminCampaignRecord | null>(null);
  readonly workflows = signal<AdminWorkflowRecord[]>([]);
  readonly templates = signal<AdminTemplateOption[]>([]);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  readonly dialogMode = signal<'create' | 'edit' | null>(null);
  readonly selectedWorkflow = signal<AdminWorkflowRecord | null>(null);
  readonly triggerTypes: WorkflowTriggerType[] = ['AFTER_DISCHARGE', 'BEFORE_APPOINTMENT', 'AFTER_EVENT'];
  readonly channels: WorkflowChannel[] = ['SMS', 'CALL', 'PHONE', 'EMAIL', 'PORTAL'];
  readonly breadcrumbs: BreadcrumbItem[] = [
    { label: 'System administration', route: '/system-admin/dashboard' },
    { label: 'Outreach campaigns', route: '/system-admin/outreach-campaigns' },
    { label: 'Workflow configuration' },
  ];

  campaignId = 0;
  draft: AdminWorkflowRequest = this.emptyDraft();

  ngOnInit(): void {
    this.campaignId = Number(this.route.snapshot.paramMap.get('campaignId'));
    if (!Number.isInteger(this.campaignId) || this.campaignId < 1) {
      this.showError('Campaign reference is invalid.');
      return;
    }
    this.loadConfiguration();
  }

  refresh(): void {
    this.loadConfiguration();
  }

  openCreate(): void {
    const firstTemplate = this.templates()[0];
    this.selectedWorkflow.set(null);
    this.draft = {
      ...this.emptyDraft(),
      step_order: Math.max(0, ...this.workflows().map((item) => item.step_order)) + 1,
      checkin_template_id: firstTemplate?.checkin_template_id ?? 0,
    };
    this.error.set(null);
    this.dialogMode.set('create');
  }

  openEdit(workflow: AdminWorkflowRecord): void {
    this.selectedWorkflow.set(workflow);
    this.draft = {
      step_order: workflow.step_order,
      step_name: workflow.step_name,
      trigger_type: workflow.trigger_type,
      trigger_anchor: workflow.trigger_anchor,
      trigger_offset_hours: workflow.trigger_offset_hours,
      channel: workflow.channel,
      template_text: workflow.template_text,
      checkin_template_id: workflow.checkin_template_id ?? 0,
      escalation_on_no_response: workflow.escalation_on_no_response,
      max_attempts: workflow.max_attempts,
      retry_interval_minutes: workflow.retry_interval_minutes,
      is_active: workflow.is_active,
    };
    this.error.set(null);
    this.dialogMode.set('edit');
  }

  closeDialog(): void {
    if (!this.saving()) this.dialogMode.set(null);
  }

  setTriggerType(triggerType: WorkflowTriggerType): void {
    this.draft.trigger_type = triggerType;
    this.draft.trigger_anchor = this.anchorFor(triggerType);
  }

  saveWorkflow(): void {
    const actorId = this.actorId();
    if (!actorId || !this.validDraft()) return;
    const payload: AdminWorkflowRequest = {
      ...this.draft,
      step_name: this.draft.step_name.trim(),
      template_text: this.draft.template_text?.trim() || null,
    };
    const selected = this.selectedWorkflow();
    const request = selected
      ? this.api.updateWorkflow(actorId, selected.workflow_id, payload)
      : this.api.createWorkflow(actorId, this.campaignId, payload);
    this.saving.set(true);
    this.error.set(null);
    request.pipe(finalize(() => this.saving.set(false))).subscribe({
      next: (response) => {
        this.toast.success(response.message);
        this.dialogMode.set(null);
        this.loadConfiguration();
      },
      error: (error: unknown) => this.showError(this.errorMessage(error, 'Unable to save the workflow step.')),
    });
  }

  isEditable(): boolean {
    const status = this.campaign()?.status;
    return status === 'DRAFT' || status === 'PAUSED';
  }

  configurationClass(status: AdminWorkflowRecord['configuration_status']): string {
    if (status === 'READY') return 'status-positive';
    return status === 'INACTIVE' ? 'status-negative' : 'status-warning';
  }

  campaignStatusClass(): string {
    const status = this.campaign()?.status;
    if (status === 'ACTIVE' || status === 'COMPLETED') return 'status-positive';
    return status === 'PAUSED' ? 'status-warning' : 'status-negative';
  }

  formatLabel(value: string): string {
    return value.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  private loadConfiguration(): void {
    const actorId = this.actorId();
    if (!actorId) return this.showError('Your session has expired. Please sign in again.');
    this.loading.set(true);
    this.error.set(null);
    forkJoin({
      workflows: this.api.listWorkflows(actorId, this.campaignId),
      templates: this.api.listTemplates(actorId),
    }).pipe(finalize(() => this.loading.set(false))).subscribe({
      next: ({ workflows, templates }) => {
        this.campaign.set(workflows.data.campaign);
        this.workflows.set(workflows.data.workflows);
        this.templates.set(templates.data.templates);
      },
      error: (error: unknown) => this.showError(this.errorMessage(error, 'Unable to load workflow configuration.')),
    });
  }

  private validDraft(): boolean {
    if (!this.draft.step_name.trim()) return this.showValidation('Step name is required.');
    if (this.draft.step_order < 1) return this.showValidation('Step order must be at least 1.');
    if (!this.draft.checkin_template_id) return this.showValidation('Select an active check-in template.');
    if (this.draft.trigger_offset_hours < 0) return this.showValidation('Trigger offset cannot be negative.');
    if (this.draft.max_attempts < 1) return this.showValidation('Maximum attempts must be at least 1.');
    if (this.draft.retry_interval_minutes < 0) return this.showValidation('Retry interval cannot be negative.');
    return true;
  }

  private showValidation(message: string): false {
    this.showError(message);
    return false;
  }

  private emptyDraft(): AdminWorkflowRequest {
    return {
      step_order: 1,
      step_name: '',
      trigger_type: 'AFTER_DISCHARGE',
      trigger_anchor: 'DISCHARGE_DATETIME',
      trigger_offset_hours: 24,
      channel: 'SMS',
      template_text: null,
      checkin_template_id: 0,
      escalation_on_no_response: false,
      max_attempts: 3,
      retry_interval_minutes: 30,
      is_active: true,
    };
  }

  private anchorFor(triggerType: WorkflowTriggerType): WorkflowTriggerAnchor {
    if (triggerType === 'AFTER_DISCHARGE') return 'DISCHARGE_DATETIME';
    if (triggerType === 'BEFORE_APPOINTMENT') return 'APPOINTMENT_DATETIME';
    return 'EVENT_DATETIME';
  }

  private actorId(): number | null {
    return this.sessionUser?.user_id ?? this.sessionUser?.userId ?? null;
  }

  private showError(message: string): void {
    this.error.set(message);
    this.toast.error(message);
  }

  private errorMessage(error: unknown, fallback: string): string {
    return (error as { error?: { message?: string } })?.error?.message ?? fallback;
  }
}