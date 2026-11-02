import { CommonModule } from '@angular/common';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';
import { Subject, catchError, finalize, of, switchMap, tap } from 'rxjs';

import { CareManagerDashboardApi } from '../../../../api/navigator/care-manager-dashboard.api';
import { getSessionUser } from '../../../../api/tokenstore';
import { TcmTrackerApi } from '../../../../api/navigator/tcm-tracker.api';
import { TcmPatientDetailDrawer } from '../../../../shared/components/tcm-tracker/tcm-patient-detail-drawer';
import {
  CareManagerAnalytics,
  CareManagerRow,
  CareManagerSectionKey,
} from '../../../../shared/types/navigator/care-manager-dashboard';
import { TcmPatientDetail } from '../../../../shared/types/navigator/tcm-tracker';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

interface PageColumn {
  key: string;
  label: string;
}

interface PageDefinition {
  title: string;
  description: string;
  columns: PageColumn[];
}

interface DashboardDetailDefinition {
  key: string;
  title: string;
  emptyMessage: string;
  columns: PageColumn[];
}

const DASHBOARD_DETAIL_DEFINITIONS: DashboardDetailDefinition[] = [
  {
    key: 'active_care_episodes',
    title: 'Active care episodes',
    emptyMessage: 'No active care episodes are assigned to you.',
    columns: [
      { key: 'patient', label: 'Patient' },
      { key: 'risk_tier', label: 'Risk tier' },
      { key: 'enrollment_status', label: 'Enrollment' },
      { key: 'episode_type', label: 'Episode type' },
      { key: 'episode_status', label: 'Episode status' },
      { key: 'opened_at', label: 'Opened' },
      { key: 'duration', label: 'Duration' },
    ],
  },
  {
    key: 'high_risk_patients',
    title: 'High-risk patients',
    emptyMessage: 'No high-risk patients have active assigned episodes.',
    columns: [
      { key: 'patient', label: 'Patient' },
      { key: 'risk_tier', label: 'Risk tier' },
      { key: 'enrollment_status', label: 'Enrollment' },
      { key: 'episode_type', label: 'Episode type' },
      { key: 'episode_status', label: 'Episode status' },
      { key: 'duration', label: 'Duration' },
    ],
  },
  {
    key: 'open_escalations',
    title: 'Open escalations',
    emptyMessage: 'No open escalations are available.',
    columns: [
      { key: 'patient', label: 'Patient' },
      { key: 'type', label: 'Type' },
      { key: 'priority', label: 'Priority' },
      { key: 'status', label: 'Status' },
      { key: 'assigned', label: 'Assigned' },
      { key: 'guardrail_urgency', label: 'Guardrail urgency' },
      { key: 'created_at', label: 'Created' },
    ],
  },
  {
    key: 'overdue_follow_ups',
    title: 'Overdue follow-ups',
    emptyMessage: 'No overdue follow-up tasks are assigned to you.',
    columns: [
      { key: 'patient', label: 'Patient' },
      { key: 'title', label: 'Task' },
      { key: 'task_type', label: 'Type' },
      { key: 'priority', label: 'Priority' },
      { key: 'status', label: 'Status' },
      { key: 'due_at', label: 'Due' },
      { key: 'linked_case', label: 'Linked case' },
    ],
  },
];

const PAGE_DEFINITIONS: Record<CareManagerSectionKey, PageDefinition> = {
  dashboard: {
    title: 'Dashboard',
    description: 'Monitor active care episodes, patient risk, escalations, and overdue follow-ups.',
    columns: [],
  },
  caseload: {
    title: 'Patient Caseload',
    description: 'Review assigned patients and their current enrollment and episode status.',
    columns: [
      { key: 'patient', label: 'Patient' },
      { key: 'risk_tier', label: 'Risk tier' },
      { key: 'enrollment_status', label: 'Enrollment' },
      { key: 'episode_status', label: 'Episode status' },
      { key: 'episode_type', label: 'Episode type' },
      { key: 'duration', label: 'Duration' },
    ],
  },
  appointments: {
    title: 'Appointment Tracking',
    description: 'Track upcoming appointments, outcomes, and the latest recorded actions.',
    columns: [
      { key: 'patient', label: 'Patient' },
      { key: 'appointment_type', label: 'Type' },
      { key: 'date_time', label: 'Date and time' },
      { key: 'assigned_to', label: 'Assigned to' },
      { key: 'status', label: 'Status' },
      { key: 'channel', label: 'Location / channel' },
      { key: 'latest_resolution', label: 'Latest resolution' },
    ],
  },
  outreach: {
    title: 'Outreach & Check-ins',
    description: 'Monitor campaign delivery, patient responses, and check-in completion.',
    columns: [
      { key: 'patient', label: 'Patient' },
      { key: 'campaign', label: 'Campaign' },
      { key: 'workflow', label: 'Workflow' },
      { key: 'channel', label: 'Channel' },
      { key: 'delivery', label: 'Delivery' },
      { key: 'status', label: 'Status' },
      { key: 'assigned_to', label: 'Assigned to' },
      { key: 'scheduled_at', label: 'Scheduled' },
    ],
  },
  escalations: {
    title: 'Escalation Management',
    description: 'Review priority, ownership, guardrail context, and pending escalation work.',
    columns: [
      { key: 'patient', label: 'Patient' },
      { key: 'type', label: 'Type' },
      { key: 'priority', label: 'Priority' },
      { key: 'status', label: 'Status' },
      { key: 'assigned', label: 'Assigned' },
      { key: 'guardrail_urgency', label: 'Guardrail urgency' },
      { key: 'created_at', label: 'Created' },
    ],
  },
  follow_up: {
    title: 'Follow-up Management',
    description: 'Manage due, overdue, completed, and linked follow-up work.',
    columns: [
      { key: 'patient', label: 'Patient' },
      { key: 'title', label: 'Task' },
      { key: 'task_type', label: 'Type' },
      { key: 'priority', label: 'Priority' },
      { key: 'status', label: 'Status' },
      { key: 'due_at', label: 'Due' },
      { key: 'linked_case', label: 'Linked case' },
    ],
  },
  program_performance: {
    title: 'Program Performance',
    description: 'Measure enrollments, completed episodes, outreach response, and appointment completion.',
    columns: [],
  },
};

@Component({
  selector: 'app-care-manager-dashbaord',
  standalone: true,
  imports: [CommonModule, TcmPatientDetailDrawer],
  templateUrl: './care_manager_dashbaord.html',
  styleUrl: './care_manager_dashbaord.scss',
})
export class CareManagerDashbaord {
  private readonly api = inject(CareManagerDashboardApi);
  private readonly tcmApi = inject(TcmTrackerApi);
  private readonly route = inject(ActivatedRoute);
  private readonly toast = inject(ToastState);
  private readonly destroyRef = inject(DestroyRef);
  private readonly sessionUser = getSessionUser();
  private readonly patientDetailRequests = new Subject<number>();

  readonly sectionKey = signal<CareManagerSectionKey>('dashboard');
  readonly analytics = signal<CareManagerAnalytics | null>(null);
  readonly loading = signal(false);
  readonly error = signal('');
  readonly selectedEpisodeId = signal<number | null>(null);
  readonly patientDetail = signal<TcmPatientDetail | null>(null);
  readonly patientDetailLoading = signal(false);
  readonly patientDetailError = signal('');
  readonly page = computed(() => PAGE_DEFINITIONS[this.sectionKey()]);
  readonly section = computed(() => this.analytics()?.[this.sectionKey()] ?? null);
  readonly dashboardDetails = computed(() => {
    const groups = this.analytics()?.dashboard.detail_groups ?? {};
    return DASHBOARD_DETAIL_DEFINITIONS.map((definition) => ({
      ...definition,
      rows: groups[definition.key] ?? [],
    }));
  });

  constructor() {
    this.configurePatientDetailRequests();
    this.route.data.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((data) => {
      this.sectionKey.set((data['careManagerSection'] as CareManagerSectionKey | undefined) ?? 'dashboard');
    });
    this.loadAnalytics();
  }

  openPatient(row: CareManagerRow): void {
    const episodeId = row['episode_id'];
    if (typeof episodeId !== 'number') {
      return;
    }
    this.selectedEpisodeId.set(episodeId);
    this.patientDetail.set(null);
    this.patientDetailRequests.next(episodeId);
  }

  closePatient(): void {
    this.selectedEpisodeId.set(null);
    this.patientDetail.set(null);
    this.patientDetailError.set('');
  }

  hasPatientDetails(row: CareManagerRow): boolean {
    return typeof row['episode_id'] === 'number';
  }

  supportsPatientDetails(): boolean {
    return ['caseload', 'appointments', 'outreach', 'escalations'].includes(this.sectionKey());
  }

  loadAnalytics(): void {
    const userId = this.sessionUser?.user_id;
    if (!userId) {
      this.error.set('Your session could not be identified. Please sign in again.');
      return;
    }

    this.loading.set(true);
    this.error.set('');
    this.api
      .getAnalytics(userId)
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (response) => this.analytics.set(response.data),
        error: (error: { error?: { message?: string } }) => {
          const message = error.error?.message ?? 'Unable to load care-manager analytics.';
          this.error.set(message);
          this.toast.error(message);
        },
      });
  }

  displayValue(value: string | number | null): string | number {
    if (value === null || value === '') {
      return 'Not available';
    }
    if (typeof value === 'number') {
      return value;
    }
    if (/^\d{4}-\d{2}-\d{2}T/.test(value)) {
      return new Date(value).toLocaleString();
    }
    return value.toLowerCase().replaceAll('_', ' ').replace(/\b\w/g, (character) => character.toUpperCase());
  }

  episodeStatusClass(value: string | number | null): string {
    switch (value) {
      case 'COMPLETED':
      case 'CLOSED':
        return 'episode-status-positive';
      case 'OPEN':
      case 'ON_HOLD':
        return 'episode-status-warning';
      case 'IN_PROGRESS':
        return 'episode-status-neutral';
      default:
        return 'episode-status-neutral';
    }
  }

  escalationStatusClass(value: string | number | null): string {
    switch (value) {
      case 'OPEN':
        return 'escalation-status-critical';
      case 'ASSIGNED':
        return 'episode-status-neutral';
      case 'IN_PROGRESS':
        return 'escalation-status-warning';
      case 'RESOLVED':
      case 'CLOSED':
        return 'escalation-status-positive';
      default:
        return 'escalation-status-neutral';
    }
  }

  outreachStatusClass(value: string | number | null): string {
    switch (value) {
      case 'PENDING':
        return 'outreach-status-warning';
      case 'PROCESSING':
        return 'outreach-status-neutral';
      case 'COMPLETED':
        return 'outreach-status-positive';
      case 'FAILED':
        return 'outreach-status-critical';
      case 'CANCELLED':
        return 'outreach-status-critical';
      default:
        return 'outreach-status-neutral';
    }
  }

  appointmentStatusClass(value: string | number | null): string {
    switch (value) {
      case 'CONFIRMED':
      case 'COMPLETED':
        return 'appointment-status-positive';
      case 'REQUESTED':
      case 'RESCHEDULED':
        return 'appointment-status-warning';
      case 'CANCELLED':
      case 'NO_SHOW':
        return 'appointment-status-critical';
      case 'SCHEDULED':
      default:
        return 'appointment-status-neutral';
    }
  }

  private configurePatientDetailRequests(): void {
    const userId = this.sessionUser?.user_id;
    if (!userId) {
      return;
    }
    this.patientDetailRequests.pipe(
      tap(() => {
        this.patientDetailLoading.set(true);
        this.patientDetailError.set('');
      }),
      switchMap((episodeId) => this.tcmApi.getEpisodeDetails(userId, episodeId).pipe(
        catchError((error: { error?: { message?: string } }) => {
          this.patientDetailError.set(error.error?.message ?? 'Unable to load patient details.');
          return of(null);
        }),
      )),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe((response) => {
      this.patientDetailLoading.set(false);
      if (response) {
        this.patientDetail.set(response.data);
      }
    });
  }
}
