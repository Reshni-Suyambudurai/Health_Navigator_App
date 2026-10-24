import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { forkJoin, finalize } from 'rxjs';
import { OutreachApi } from '../../../../api/navigator/outreach.api';
import { getSessionUser } from '../../../../api/tokenstore';
import {
  CampaignRequest,
  CheckinQuestion,
  CheckinQuestionRequest,
  CheckinSession,
  CheckinTemplate,
  CheckinTemplateRequest,
  EventStatus,
  FollowUpStatus,
  FollowUpTask,
  OutreachCampaign,
  OutreachEvent,
  OutreachWorkflow,
  WorkflowRequest,
} from '../../../../shared/types/navigator/outreach';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

type OutreachView = 'campaigns' | 'templates' | 'events' | 'checkins' | 'tasks';

@Component({
  selector: 'app-outreach-tracker',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './outreach-tracker.html',
  styleUrl: './outreach-tracker.scss',
})
export class OutreachTracker implements OnInit {
  private readonly api = inject(OutreachApi);
  private readonly toast = inject(ToastState);
  private readonly sessionUser = getSessionUser();

  readonly activeView = signal<OutreachView>('campaigns');
  readonly campaigns = signal<OutreachCampaign[]>([]);
  readonly workflows = signal<OutreachWorkflow[]>([]);
  readonly templates = signal<CheckinTemplate[]>([]);
  readonly questions = signal<CheckinQuestion[]>([]);
  readonly events = signal<OutreachEvent[]>([]);
  readonly sessions = signal<CheckinSession[]>([]);
  readonly tasks = signal<FollowUpTask[]>([]);
  readonly selectedCampaignId = signal<number | null>(null);
  readonly selectedTemplateId = signal<number | null>(null);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);

  readonly views: { value: OutreachView; label: string }[] = [
    { value: 'campaigns', label: 'Campaigns' },
    { value: 'templates', label: 'Check-in templates' },
    { value: 'events', label: 'Event monitor' },
    { value: 'checkins', label: 'Check-ins' },
    { value: 'tasks', label: 'Follow-up tasks' },
  ];
  readonly eventStatuses: EventStatus[] = ['PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED'];
  readonly taskStatuses: FollowUpStatus[] = ['OPEN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'];

  campaignDraft: CampaignRequest = {
    organization_id: 0,
    campaign_name: '',
    campaign_type: 'POST_DISCHARGE',
    timezone: 'UTC',
    status: 'DRAFT',
  };
  workflowDraft: WorkflowRequest = {
    step_order: 1,
    step_name: '',
    trigger_type: 'AFTER_DISCHARGE',
    trigger_anchor: 'DISCHARGE_DATETIME',
    trigger_offset_hours: 0,
    channel: 'SMS',
    template_text: null,
    checkin_template_id: null,
    escalation_on_no_response: false,
    max_attempts: 3,
    retry_interval_minutes: 30,
    is_active: true,
  };
  templateDraft: CheckinTemplateRequest = {
    organization_id: 0,
    template_name: '',
    template_type: 'POST_DISCHARGE',
    description: null,
    version: 1,
    status: 'DRAFT',
  };
  questionDraft: CheckinQuestionRequest = {
    question_key: '',
    question_text: '',
    answer_type: 'YES_NO',
    options: null,
    display_order: 1,
    is_required: true,
    is_active: true,
  };

  ngOnInit(): void {
    this.loadWorkspace();
  }

  setView(view: OutreachView): void {
    this.activeView.set(view);
  }

  selectCampaign(campaignId: number): void {
    this.selectedCampaignId.set(campaignId);
    this.api.listWorkflows(campaignId).subscribe({
      next: (response) => {
        this.workflows.set(response.data.workflows);
        this.workflowDraft.step_order = response.data.count + 1;
      },
      error: (error: unknown) => this.showError(error, 'Unable to load workflow steps.'),
    });
  }

  selectTemplate(templateId: number): void {
    this.selectedTemplateId.set(templateId);
    this.api.listQuestions(templateId).subscribe({
      next: (response) => {
        this.questions.set(response.data.questions);
        this.questionDraft.display_order = response.data.count + 1;
      },
      error: (error: unknown) => this.showError(error, 'Unable to load template questions.'),
    });
  }

  createCampaign(): void {
    const userId = this.userId();
    if (!userId || this.campaignDraft.organization_id <= 0 || !this.campaignDraft.campaign_name.trim()) {
      this.toast.warning('Enter an organization ID and campaign name.');
      return;
    }
    this.saving.set(true);
    this.api.createCampaign(userId, { ...this.campaignDraft, campaign_name: this.campaignDraft.campaign_name.trim() })
      .pipe(finalize(() => this.saving.set(false)))
      .subscribe({
        next: (response) => {
          this.campaigns.update((records) => [response.data, ...records]);
          this.campaignDraft.campaign_name = '';
          this.toast.success(response.message);
        },
        error: (error: unknown) => this.showError(error, 'Unable to create the campaign.'),
      });
  }

  createWorkflow(): void {
    const campaignId = this.selectedCampaignId();
    if (!campaignId || !this.workflowDraft.step_name.trim()) {
      this.toast.warning('Select a campaign and enter a step name.');
      return;
    }
    this.saving.set(true);
    this.api.createWorkflow(campaignId, { ...this.workflowDraft, step_name: this.workflowDraft.step_name.trim() })
      .pipe(finalize(() => this.saving.set(false)))
      .subscribe({
        next: (response) => {
          this.workflows.update((records) => [...records, response.data]);
          this.workflowDraft.step_name = '';
          this.workflowDraft.step_order += 1;
          this.toast.success(response.message);
        },
        error: (error: unknown) => this.showError(error, 'Unable to create the workflow step.'),
      });
  }

  createTemplate(): void {
    const userId = this.userId();
    if (!userId || this.templateDraft.organization_id <= 0 || !this.templateDraft.template_name.trim()) {
      this.toast.warning('Enter an organization ID and template name.');
      return;
    }
    this.saving.set(true);
    this.api.createTemplate(userId, { ...this.templateDraft, template_name: this.templateDraft.template_name.trim() })
      .pipe(finalize(() => this.saving.set(false)))
      .subscribe({
        next: (response) => {
          this.templates.update((records) => [response.data, ...records]);
          this.templateDraft.template_name = '';
          this.templateDraft.description = null;
          this.toast.success(response.message);
        },
        error: (error: unknown) => this.showError(error, 'Unable to create the template.'),
      });
  }

  createQuestion(): void {
    const templateId = this.selectedTemplateId();
    if (!templateId || !this.questionDraft.question_key.trim() || !this.questionDraft.question_text.trim()) {
      this.toast.warning('Select a template and complete the question fields.');
      return;
    }
    this.saving.set(true);
    this.api.createQuestion(templateId, {
      ...this.questionDraft,
      question_key: this.questionDraft.question_key.trim(),
      question_text: this.questionDraft.question_text.trim(),
    }).pipe(finalize(() => this.saving.set(false))).subscribe({
      next: (response) => {
        this.questions.update((records) => [...records, response.data]);
        this.questionDraft.question_key = '';
        this.questionDraft.question_text = '';
        this.questionDraft.display_order += 1;
        this.toast.success(response.message);
      },
      error: (error: unknown) => this.showError(error, 'Unable to create the question.'),
    });
  }

  updateEvent(event: OutreachEvent, status: string): void {
    const nextStatus = this.eventStatuses.find((item) => item === status);
    if (!nextStatus || nextStatus === event.event_status) {
      return;
    }
    this.api.updateEvent(event.outreach_event_id, nextStatus).subscribe({
      next: (response) => {
        this.events.update((records) => records.map((item) =>
          item.outreach_event_id === event.outreach_event_id ? response.data : item,
        ));
        this.toast.success(response.message);
      },
      error: (error: unknown) => this.showError(error, 'Unable to update the event.'),
    });
  }

  updateTask(task: FollowUpTask, status: string): void {
    const userId = this.userId();
    const nextStatus = this.taskStatuses.find((item) => item === status);
    if (!userId || !nextStatus || nextStatus === task.status) {
      return;
    }
    this.api.updateTask(userId, task.follow_up_task_id, nextStatus).subscribe({
      next: (response) => {
        this.tasks.update((records) => records.map((item) =>
          item.follow_up_task_id === task.follow_up_task_id ? response.data : item,
        ));
        this.toast.success(response.message);
      },
      error: (error: unknown) => this.showError(error, 'Unable to update the task.'),
    });
  }

  formatDate(value: string | null): string {
    return value ? new Date(value).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : 'Not set';
  }

  formatLabel(value: string): string {
    return value.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  statusClass(value: string): string {
    if (['ACTIVE', 'COMPLETED', 'DELIVERED', 'RESPONDED', 'RESOLVED'].includes(value)) return 'positive';
    if (['FAILED', 'CRITICAL', 'CANCELLED'].includes(value)) return 'critical';
    if (['PROCESSING', 'IN_PROGRESS', 'PAUSED'].includes(value)) return 'warning';
    return 'neutral';
  }

  private loadWorkspace(): void {
    this.loading.set(true);
    this.error.set(null);
    forkJoin({
      campaigns: this.api.listCampaigns(),
      templates: this.api.listTemplates(),
      events: this.api.listEvents(),
      sessions: this.api.listSessions(),
      tasks: this.api.listTasks(),
    }).pipe(finalize(() => this.loading.set(false))).subscribe({
      next: (response) => {
        this.campaigns.set(response.campaigns.data.campaigns);
        this.templates.set(response.templates.data.templates);
        this.events.set(response.events.data.events);
        this.sessions.set(response.sessions.data.sessions);
        this.tasks.set(response.tasks.data.tasks);
      },
      error: (error: unknown) => this.showError(error, 'Unable to load the outreach workspace.'),
    });
  }

  private userId(): number | null {
    return this.sessionUser?.user_id ?? this.sessionUser?.userId ?? null;
  }

  private showError(error: unknown, fallback: string): void {
    const message = (error as { error?: { message?: string } })?.error?.message ?? fallback;
    this.error.set(message);
    this.toast.error(message);
  }
}