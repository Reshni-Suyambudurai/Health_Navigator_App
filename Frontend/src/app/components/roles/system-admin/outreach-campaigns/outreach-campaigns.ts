import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { finalize } from 'rxjs';
import { AdminOutreachApi } from '../../../../api/navigator/admin-outreach.api';
import { getSessionUser } from '../../../../api/tokenstore';
import {
  AdminCampaignRecord,
  AdminCampaignRequest,
  AdminCampaignStatus,
  AdminCampaignType,
  AdminCohortCriteria,
  EnrollmentProgram,
  EnrollmentStatus,
  EpisodeStatus,
  EpisodeType,
} from '../../../../shared/types/navigator/admin-outreach';
import { Breadcrumb, BreadcrumbItem } from '../../../../shared/ui/breadcrumb/breadcrumb';
import { ToastState } from '../../../../shared/ui/toast/toast-state';
import { CohortOutreachPanel } from './cohort-outreach-panel/cohort-outreach-panel';

interface CampaignDraft {
  campaign_name: string;
  description: string;
  campaign_type: AdminCampaignType;
  timezone: string;
  start_at: string;
  end_at: string;
  cohort: AdminCohortCriteria;
}

interface PendingTransition {
  campaign: AdminCampaignRecord;
  status: Extract<AdminCampaignStatus, 'ACTIVE' | 'PAUSED' | 'COMPLETED'>;
}

interface PendingAutoOutreach {
  campaign: AdminCampaignRecord;
  enabled: boolean;
}

@Component({
  selector: 'app-system-admin-outreach-campaigns',
  standalone: true,
  imports: [CommonModule, FormsModule, Breadcrumb, CohortOutreachPanel],
  templateUrl: './outreach-campaigns.html',
  styleUrl: './outreach-campaigns.scss',
})
export class SystemAdminOutreachCampaigns implements OnInit {
  private readonly api = inject(AdminOutreachApi);
  private readonly router = inject(Router);
  private readonly toast = inject(ToastState);
  private readonly sessionUser = getSessionUser();
  private readonly pageSize = 15;

  readonly campaigns = signal<AdminCampaignRecord[]>([]);
  readonly total = signal(0);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  readonly dialogMode = signal<'create' | 'edit' | null>(null);
  readonly selectedCampaign = signal<AdminCampaignRecord | null>(null);
  readonly pendingTransition = signal<PendingTransition | null>(null);
  readonly pendingAutoOutreach = signal<PendingAutoOutreach | null>(null);
  readonly cohortCampaign = signal<AdminCampaignRecord | null>(null);
  readonly visibleCampaigns = computed(() => {
    const term = this.search.trim().toLowerCase();
    return term
      ? this.campaigns().filter((campaign) =>
          campaign.campaign_name.toLowerCase().includes(term)
          || (campaign.description ?? '').toLowerCase().includes(term),
        )
      : this.campaigns();
  });
  readonly campaignTypes: AdminCampaignType[] = ['POST_DISCHARGE', 'MEDICATION_ADHERENCE', 'APPOINTMENT_REMINDER'];
  readonly statuses: AdminCampaignStatus[] = ['DRAFT', 'ACTIVE', 'PAUSED', 'COMPLETED', 'ARCHIVED'];
  readonly enrollmentStatuses: EnrollmentStatus[] = ['ACTIVE', 'INACTIVE', 'COMPLETED', 'WITHDRAWN', 'CLOSED', 'PAUSED'];
  readonly enrollmentPrograms: EnrollmentProgram[] = ['TCM', 'APCM', 'RPM', 'CHRONIC_CARE', 'CARE_NAVIGATION', 'TRANSITIONAL_CARE'];
  readonly episodeTypes: EpisodeType[] = ['POST_DISCHARGE_30_DAY', 'MEDICATION_SUPPORT', 'CHRONIC_CARE_FOLLOWUP', 'APPOINTMENT_FOLLOWUP', 'GENERAL_NAVIGATION', 'POST_DISCHARGE', 'CHRONIC_CARE'];
  readonly episodeStatuses: EpisodeStatus[] = ['OPEN', 'IN_PROGRESS', 'ON_HOLD', 'COMPLETED', 'CLOSED'];
  readonly breadcrumbs: BreadcrumbItem[] = [
    { label: 'System administration', route: '/system-admin/dashboard' },
    { label: 'Outreach campaigns' },
  ];

  search = '';
  statusFilter: AdminCampaignStatus | '' = '';
  typeFilter: AdminCampaignType | '' = '';
  page = 0;
  draft: CampaignDraft = this.emptyDraft();

  ngOnInit(): void {
    this.loadCampaigns();
  }

  refresh(): void {
    this.loadCampaigns();
  }

  applyFilters(): void {
    this.page = 0;
    this.loadCampaigns();
  }

  resetFilters(): void {
    this.search = '';
    this.statusFilter = '';
    this.typeFilter = '';
    this.applyFilters();
  }

  previousPage(): void {
    if (this.page === 0) return;
    this.page -= 1;
    this.loadCampaigns();
  }

  nextPage(): void {
    if ((this.page + 1) * this.pageSize >= this.total()) return;
    this.page += 1;
    this.loadCampaigns();
  }

  openCreate(): void {
    this.selectedCampaign.set(null);
    this.draft = this.emptyDraft();
    this.error.set(null);
    this.dialogMode.set('create');
  }

  openEdit(campaign: AdminCampaignRecord): void {
    this.selectedCampaign.set(campaign);
    this.draft = {
      campaign_name: campaign.campaign_name,
      description: campaign.description ?? '',
      campaign_type: campaign.campaign_type,
      timezone: campaign.timezone,
      start_at: this.localDateTime(campaign.start_at),
      end_at: this.localDateTime(campaign.end_at),
      cohort: {
        enrollment_statuses: [...campaign.cohort.enrollment_statuses],
        enrollment_programs: [...campaign.cohort.enrollment_programs],
        episode_types: [...campaign.cohort.episode_types],
        episode_statuses: [...campaign.cohort.episode_statuses],
        discharged_within_days: campaign.cohort.discharged_within_days,
      },
    };
    this.error.set(null);
    this.dialogMode.set('edit');
  }

  closeDialog(): void {
    if (!this.saving()) this.dialogMode.set(null);
  }

  toggleCohortValue<TKey extends keyof Omit<AdminCohortCriteria, 'discharged_within_days'>>(
    key: TKey,
    value: AdminCohortCriteria[TKey][number],
  ): void {
    const values = this.draft.cohort[key] as string[];
    if (values.length === 1 && values.includes(value)) return;
    this.draft.cohort[key] = (
      values.includes(value) ? values.filter((item) => item !== value) : [...values, value]
    ) as AdminCohortCriteria[TKey];
  }

  isOnlyCohortValue<TKey extends keyof Omit<AdminCohortCriteria, 'discharged_within_days'>>(
    key: TKey,
    value: AdminCohortCriteria[TKey][number],
  ): boolean {
    const values = this.draft.cohort[key] as string[];
    return values.length === 1 && values.includes(value);
  }

  saveCampaign(): void {
    const actorId = this.actorId();
    if (!actorId || !this.validDraft()) return;
    const payload = this.toRequest();
    const selected = this.selectedCampaign();
    const request = selected
      ? this.api.updateCampaign(actorId, selected.campaign_id, payload)
      : this.api.createCampaign(actorId, payload);
    this.saving.set(true);
    this.error.set(null);
    request.pipe(finalize(() => this.saving.set(false))).subscribe({
      next: (response) => {
        this.toast.success(response.message);
        this.dialogMode.set(null);
        this.loadCampaigns();
      },
      error: (error: unknown) => this.showError(this.errorMessage(error, 'Unable to save the campaign.')),
    });
  }

  configureWorkflows(campaign: AdminCampaignRecord): void {
    this.router.navigate(['/system-admin/outreach-campaigns', campaign.campaign_id, 'workflows']);
  }

  openCohort(campaign: AdminCampaignRecord): void {
    this.cohortCampaign.set(campaign);
  }

  closeCohort(): void {
    this.cohortCampaign.set(null);
  }

  handleOutreachCreated(): void {
    this.loadCampaigns();
  }

  requestTransition(campaign: AdminCampaignRecord, status: PendingTransition['status']): void {
    this.pendingTransition.set({ campaign, status });
  }

  cancelTransition(): void {
    if (!this.saving()) this.pendingTransition.set(null);
  }

  confirmTransition(): void {
    const actorId = this.actorId();
    const pending = this.pendingTransition();
    if (!actorId || !pending) return;
    this.saving.set(true);
    this.api.transitionCampaign(actorId, pending.campaign.campaign_id, pending.status)
      .pipe(finalize(() => this.saving.set(false)))
      .subscribe({
        next: (response) => {
          this.toast.success(response.message);
          this.pendingTransition.set(null);
          this.loadCampaigns();
        },
        error: (error: unknown) => {
          this.pendingTransition.set(null);
          this.showError(this.errorMessage(error, 'Unable to change campaign status.'));
        },
      });
  }

  requestAutoOutreach(campaign: AdminCampaignRecord): void {
    this.pendingAutoOutreach.set({
      campaign,
      enabled: !campaign.auto_outreach_enabled,
    });
  }

  cancelAutoOutreach(): void {
    if (!this.saving()) this.pendingAutoOutreach.set(null);
  }

  confirmAutoOutreach(): void {
    const actorId = this.actorId();
    const pending = this.pendingAutoOutreach();
    if (!actorId || !pending) return;
    this.saving.set(true);
    this.api.setAutoOutreach(actorId, pending.campaign.campaign_id, pending.enabled)
      .pipe(finalize(() => this.saving.set(false)))
      .subscribe({
        next: (response) => {
          this.toast.success(response.message);
          this.pendingAutoOutreach.set(null);
          this.loadCampaigns();
        },
        error: (error: unknown) => {
          this.pendingAutoOutreach.set(null);
          this.showError(this.errorMessage(error, 'Unable to update automatic outreach.'));
        },
      });
  }

  autoOutreachDisabled(campaign: AdminCampaignRecord): boolean {
    return this.saving() || (
      !campaign.auto_outreach_enabled
      && (campaign.status !== 'ACTIVE' || !campaign.readiness.ready)
    );
  }

  canEdit(campaign: AdminCampaignRecord): boolean {
    return campaign.status === 'DRAFT' || campaign.status === 'PAUSED';
  }

  statusClass(status: AdminCampaignStatus): string {
    if (status === 'ACTIVE') return 'status-positive';
    if (status === 'COMPLETED') return 'status-positive';
    if (status === 'PAUSED') return 'status-warning';
    return status === 'ARCHIVED' ? 'status-critical' : 'status-negative';
  }

  readinessClass(campaign: AdminCampaignRecord): string {
    return campaign.readiness.ready ? 'status-positive' : 'status-warning';
  }

  formatLabel(value: string): string {
    return value.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  formatDate(value: string | null): string {
    return value ? new Date(value).toLocaleDateString([], { dateStyle: 'medium' }) : 'Not scheduled';
  }

  get pageStart(): number {
    return this.total() ? this.page * this.pageSize + 1 : 0;
  }

  get pageEnd(): number {
    return Math.min((this.page + 1) * this.pageSize, this.total());
  }

  private loadCampaigns(): void {
    const actorId = this.actorId();
    if (!actorId) return this.showError('Your session has expired. Please sign in again.');
    this.loading.set(true);
    this.error.set(null);
    this.api.listCampaigns(actorId, {
      skip: this.page * this.pageSize,
      limit: this.pageSize,
      status: this.statusFilter,
      campaign_type: this.typeFilter,
    }).pipe(finalize(() => this.loading.set(false))).subscribe({
      next: (response) => {
        this.campaigns.set(response.data.campaigns);
        this.total.set(response.data.count);
      },
      error: (error: unknown) => this.showError(this.errorMessage(error, 'Unable to load campaigns.')),
    });
  }

  private validDraft(): boolean {
    if (!this.draft.campaign_name.trim()) return this.showValidation('Campaign name is required.');
    if (!this.draft.timezone.trim()) return this.showValidation('Timezone is required.');
    const cohort = this.draft.cohort;
    if (!cohort.enrollment_statuses.length || !cohort.enrollment_programs.length
      || !cohort.episode_types.length || !cohort.episode_statuses.length) {
      return this.showValidation('Select at least one value in every cohort group.');
    }
    if (cohort.discharged_within_days < 1 || cohort.discharged_within_days > 365) {
      return this.showValidation('Discharge window must be between 1 and 365 days.');
    }
    if (this.draft.start_at && this.draft.end_at
      && new Date(this.draft.end_at) <= new Date(this.draft.start_at)) {
      return this.showValidation('Campaign end date must be after its start date.');
    }
    return true;
  }

  private showValidation(message: string): false {
    this.showError(message);
    return false;
  }

  private toRequest(): AdminCampaignRequest {
    return {
      campaign_name: this.draft.campaign_name.trim(),
      description: this.draft.description.trim() || null,
      campaign_type: this.draft.campaign_type,
      timezone: this.draft.timezone.trim(),
      start_at: this.isoDateTime(this.draft.start_at),
      end_at: this.isoDateTime(this.draft.end_at),
      cohort: { ...this.draft.cohort },
    };
  }

  private emptyDraft(): CampaignDraft {
    return {
      campaign_name: '',
      description: '',
      campaign_type: 'POST_DISCHARGE',
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
      start_at: '',
      end_at: '',
      cohort: {
        enrollment_statuses: ['ACTIVE'],
        enrollment_programs: ['TCM'],
        episode_types: ['POST_DISCHARGE_30_DAY'],
        episode_statuses: ['OPEN', 'IN_PROGRESS'],
        discharged_within_days: 30,
      },
    };
  }

  private localDateTime(value: string | null): string {
    if (!value) return '';
    const date = new Date(value);
    const offset = date.getTimezoneOffset() * 60000;
    return new Date(date.getTime() - offset).toISOString().slice(0, 16);
  }

  private isoDateTime(value: string): string | null {
    return value ? new Date(value).toISOString() : null;
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