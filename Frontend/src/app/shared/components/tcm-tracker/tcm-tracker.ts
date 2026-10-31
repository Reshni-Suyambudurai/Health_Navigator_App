import { CommonModule } from '@angular/common';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Subject, catchError, forkJoin, of, switchMap, tap } from 'rxjs';

import { getSessionUser } from '../../../api/tokenstore';
import { TcmTrackerApi, TcmTrackerFilters } from '../../../api/navigator/tcm-tracker.api';
import {
  TcmCampaign,
  TcmPatientCategory,
  TcmPatientDetail,
  TcmPatientPage,
  TcmPatientRow,
  TcmSummary,
  TcmTrackerScope,
  TcmWorkflowProgress,
} from '../../types/navigator/tcm-tracker';
import { Pagination } from '../../ui/pagination/pagination';
import { ToastState } from '../../ui/toast/toast-state';
import { TcmPatientDetailDrawer } from './tcm-patient-detail-drawer';

interface TrackerQuery {
  filters: TcmTrackerFilters;
  category: TcmPatientCategory;
  page: number;
  search: string;
}

@Component({
  selector: 'app-tcm-tracker',
  standalone: true,
  imports: [CommonModule, FormsModule, Pagination, TcmPatientDetailDrawer],
  templateUrl: './tcm-tracker.html',
  styleUrl: './tcm-tracker.scss',
})
export class TcmTracker {
  private readonly api = inject(TcmTrackerApi);
  private readonly toast = inject(ToastState);
  private readonly destroyRef = inject(DestroyRef);
  private readonly sessionUser = getSessionUser();
  private readonly dashboardRequests = new Subject<TcmTrackerFilters>();
  private readonly patientRequests = new Subject<TrackerQuery>();
  private readonly detailRequests = new Subject<TcmPatientRow>();

  readonly campaigns = signal<TcmCampaign[]>([]);
  readonly scope = signal<TcmTrackerScope>('ASSIGNED_PATIENTS');
  readonly selectedCampaign = signal<number | 'ALL'>('ALL');
  readonly fromDate = signal('');
  readonly toDate = signal('');
  readonly summary = signal<TcmSummary | null>(null);
  readonly workflows = signal<TcmWorkflowProgress[]>([]);
  readonly selectedCategory = signal<TcmPatientCategory>('ACTIVE');
  readonly patientPage = signal<TcmPatientPage | null>(null);
  readonly page = signal(1);
  readonly pageSize = 10;
  readonly search = signal('');
  readonly dashboardLoading = signal(false);
  readonly tableLoading = signal(false);
  readonly detailLoading = signal(false);
  readonly dashboardError = signal('');
  readonly tableError = signal('');
  readonly detailError = signal('');
  readonly selectedPatient = signal<TcmPatientRow | null>(null);
  readonly detail = signal<TcmPatientDetail | null>(null);

  readonly categories: { key: TcmPatientCategory; label: string }[] = [
    { key: 'ACTIVE', label: 'Active patients' },
    { key: 'NEEDS_ATTENTION', label: 'Needs attention' },
    { key: 'APPOINTMENT_ATTENTION', label: 'Appointment attention' },
    { key: 'REGULAR_APPOINTMENTS', label: 'Regular appointments' },
    { key: 'COMPLETE', label: 'Complete' },
  ];
  readonly paginationStart = computed(() => this.patientPage()?.total ? (this.page() - 1) * this.pageSize + 1 : 0);
  readonly paginationEnd = computed(() => Math.min(this.page() * this.pageSize, this.patientPage()?.total ?? 0));

  constructor() {
    this.configureRequests();
    this.loadCampaigns();
  }

  selectCampaign(value: string): void {
    this.selectedCampaign.set(value === 'ALL' ? 'ALL' : Number(value));
    this.resetAndReload();
  }

  updateFromDate(value: string): void { this.fromDate.set(value); }
  updateToDate(value: string): void { this.toDate.set(value); }

  applyFilters(): void {
    if (this.fromDate() && this.toDate() && this.fromDate() > this.toDate()) {
      this.toast.warning('From date must be on or before to date.');
      return;
    }
    this.resetAndReload();
  }

  selectCategory(category: TcmPatientCategory): void {
    this.selectedCategory.set(category);
    this.page.set(1);
    this.requestPatients();
  }

  applySearch(): void {
    this.page.set(1);
    this.requestPatients();
  }

  previousPage(): void {
    if (this.page() > 1) {
      this.page.update((value) => value - 1);
      this.requestPatients();
    }
  }

  nextPage(): void {
    if (this.paginationEnd() < (this.patientPage()?.total ?? 0)) {
      this.page.update((value) => value + 1);
      this.requestPatients();
    }
  }

  openPatient(patient: TcmPatientRow): void {
    this.selectedPatient.set(patient);
    this.detail.set(null);
    this.detailRequests.next(patient);
  }

  closePatient(): void {
    this.selectedPatient.set(null);
    this.detail.set(null);
    this.detailError.set('');
  }

  categoryCount(category: TcmPatientCategory): number {
    const counts = this.summary()?.patient_categories;
    if (!counts) return 0;
    const keys: Record<TcmPatientCategory, keyof typeof counts> = {
      ACTIVE: 'active',
      NEEDS_ATTENTION: 'needs_attention',
      APPOINTMENT_ATTENTION: 'appointment_attention',
      REGULAR_APPOINTMENTS: 'regular_appointments',
      COMPLETE: 'complete',
    };
    return counts[keys[category]];
  }

  label(value: string | null | undefined): string {
    return value ? value.toLowerCase().replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()) : 'Not available';
  }

  statusClass(value: string | null | undefined): string {
    const status = value?.toUpperCase();
    if (['EMERGENCY', 'ESCALATED', 'OVERDUE', 'FAILED', 'CANCELLED', 'NO_SHOW', 'EXPIRED', 'ABANDONED'].includes(status ?? '')) {
      return 'status-critical';
    }
    if (['COMPLETED', 'COMPLETE', 'RESOLVED', 'CLOSED'].includes(status ?? '')) {
      return 'status-positive';
    }
    if (['OPEN', 'ASSIGNED', 'IN_PROGRESS', 'PENDING', 'REQUESTED', 'SCHEDULED', 'CONFIRMED', 'RESCHEDULED', 'SAME_DAY', 'ON_HOLD', 'NOT_YET_BOOKED'].includes(status ?? '')) {
      return 'status-warning';
    }
    return 'status-neutral';
  }

  private configureRequests(): void {
    const userId = this.sessionUser?.user_id;
    if (!userId) {
      this.dashboardError.set('Your session could not be identified. Please sign in again.');
      return;
    }
    this.dashboardRequests.pipe(
      tap(() => { this.dashboardLoading.set(true); this.dashboardError.set(''); }),
      switchMap((filters) => forkJoin({
        summary: this.api.getSummary(userId, filters),
        workflows: this.api.getWorkflowProgress(userId, filters),
      }).pipe(
        catchError((error) => {
          const message = error.error?.message ?? 'Unable to load the TCM tracker.';
          this.dashboardError.set(message);
          this.toast.error(message);
          return of(null);
        }),
      )),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe((response) => {
      this.dashboardLoading.set(false);
      if (response) {
        this.summary.set(response.summary.data);
        this.workflows.set(response.workflows.data.workflows);
      }
    });

    this.patientRequests.pipe(
      tap(() => { this.tableLoading.set(true); this.tableError.set(''); }),
      switchMap((request) => this.api.getPatients(
        userId, request.category, request.page, this.pageSize, request.filters, request.search,
      ).pipe(
        catchError((error) => {
          const message = error.error?.message ?? 'Unable to load patients.';
          this.tableError.set(message);
          return of(null);
        }),
      )),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe((response) => {
      this.tableLoading.set(false);
      if (response) this.patientPage.set(response.data);
    });

    this.detailRequests.pipe(
      tap(() => { this.detailLoading.set(true); this.detailError.set(''); }),
      switchMap((patient) => this.api.getPatientDetails(userId, patient.campaign_id, patient.episode_id).pipe(
        catchError((error) => {
          this.detailError.set(error.error?.message ?? 'Unable to load patient details.');
          return of(null);
        }),
      )),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe((response) => {
      this.detailLoading.set(false);
      if (response) this.detail.set(response.data);
    });
  }

  private loadCampaigns(): void {
    const userId = this.sessionUser?.user_id;
    if (!userId) return;
    this.api.getCampaigns(userId).subscribe({
      next: (response) => {
        this.campaigns.set(response.data.campaigns);
        this.scope.set(response.data.scope);
        this.reload();
      },
      error: (error) => {
        const message = error.error?.message ?? 'Unable to load TCM campaigns.';
        this.dashboardError.set(message);
        this.toast.error(message);
      },
    });
  }

  private resetAndReload(): void {
    this.page.set(1);
    this.selectedCategory.set('ACTIVE');
    this.closePatient();
    this.reload();
  }

  private reload(): void {
    const filters = this.filters();
    this.dashboardRequests.next(filters);
    this.patientRequests.next({ filters, category: this.selectedCategory(), page: this.page(), search: this.search() });
  }

  private requestPatients(): void {
    this.patientRequests.next({
      filters: this.filters(),
      category: this.selectedCategory(),
      page: this.page(),
      search: this.search(),
    });
  }

  private filters(): TcmTrackerFilters {
    return {
      campaignId: this.selectedCampaign() === 'ALL' ? undefined : this.selectedCampaign() as number,
      fromDate: this.fromDate() || undefined,
      toDate: this.toDate() || undefined,
    };
  }
}