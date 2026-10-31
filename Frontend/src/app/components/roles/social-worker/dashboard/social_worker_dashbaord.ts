import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { finalize } from 'rxjs';

import { StaffDashboardApi } from '../../../../api/navigator/staff-dashboard.api';
import { getSessionUser } from '../../../../api/tokenstore';
import {
  StaffDashboardAnalytics,
  StaffDashboardPeriod,
} from '../../../../shared/types/navigator/staff-dashboard';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

@Component({
  selector: 'app-social-worker-dashbaord',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './social_worker_dashbaord.html',
  styleUrl: './social_worker_dashbaord.scss',
})
export class SocialWorkerDashbaord {
  private readonly api = inject(StaffDashboardApi);
  private readonly toast = inject(ToastState);
  private readonly sessionUser = getSessionUser();

  readonly period = signal<StaffDashboardPeriod>('TODAY');
  readonly selectedPeriod = signal<StaffDashboardPeriod>('TODAY');
  readonly fromDate = signal(this.firstDayOfMonthValue(new Date()));
  readonly toDate = signal(this.localDateValue(new Date()));
  readonly appliedFromDate = signal<string | undefined>(undefined);
  readonly appliedToDate = signal<string | undefined>(undefined);
  readonly analytics = signal<StaffDashboardAnalytics | null>(null);
  readonly loading = signal(false);
  readonly error = signal('');
  readonly metrics = computed(() => {
    const data = this.analytics();
    if (!data) {
      return [];
    }
    return [
      { label: 'Patients escalated', value: data.patients_escalated, tone: 'default' },
      { label: 'Emergency escalations', value: data.emergency_escalations, tone: 'critical' },
      { label: 'Routine escalations', value: data.routine_escalations, tone: 'default' },
      {
        label: 'Check-in emergency escalations',
        value: data.checkin_emergency_escalations,
        tone: 'critical',
      },
      {
        label: 'Check-in routine escalations',
        value: data.checkin_routine_escalations,
        tone: 'default',
      },
      { label: 'My appointments', value: data.appointments_count, tone: 'positive' },
    ];
  });

  constructor() {
    this.loadAnalytics();
  }

  selectPeriod(period: StaffDashboardPeriod): void {
    this.selectedPeriod.set(period);
    if (period === 'THIS_MONTH') {
      return;
    }
    this.period.set(period);
    this.appliedFromDate.set(undefined);
    this.appliedToDate.set(undefined);
    this.loadAnalytics();
  }

  updateFromDate(event: Event): void {
    this.fromDate.set((event.target as HTMLInputElement).value);
  }

  updateToDate(event: Event): void {
    this.toDate.set((event.target as HTMLInputElement).value);
  }

  applyDateRange(): void {
    if (!this.fromDate() || !this.toDate()) {
      this.toast.warning('Select both a from date and a to date.');
      return;
    }
    if (this.fromDate() > this.toDate()) {
      this.toast.warning('From date must be on or before to date.');
      return;
    }
    this.period.set('THIS_MONTH');
    this.appliedFromDate.set(this.fromDate());
    this.appliedToDate.set(this.toDate());
    this.loadAnalytics();
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
      .getAnalytics(
        userId,
        this.period(),
        this.appliedFromDate(),
        this.appliedToDate(),
      )
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (response) => this.analytics.set(response.data),
        error: (error: { error?: { message?: string } }) => {
          const message = error.error?.message ?? 'Unable to load your dashboard analytics.';
          this.error.set(message);
          this.toast.error(message);
        },
      });
  }

  displayLabel(value: string): string {
    return value.toLowerCase().replaceAll('_', ' ').replace(/\b\w/g, (character) => character.toUpperCase());
  }

  private localDateValue(value: Date): string {
    const year = value.getFullYear();
    const month = String(value.getMonth() + 1).padStart(2, '0');
    const day = String(value.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  private firstDayOfMonthValue(value: Date): string {
    return this.localDateValue(new Date(value.getFullYear(), value.getMonth(), 1));
  }
}
