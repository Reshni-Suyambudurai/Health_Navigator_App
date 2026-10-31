import { CommonModule } from '@angular/common';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';

import { ClinicalGovernanceDashboardApi } from '../../../../api/navigator/clinical-governance-dashboard.api';
import { getSessionUser } from '../../../../api/tokenstore';
import {
  ClinicalGovernanceAnalytics,
  GovernancePeriod,
} from '../../../../shared/types/navigator/clinical-governance-dashboard';
import { Pagination } from '../../../../shared/ui/pagination/pagination';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

type GovernanceTableKey = 'red_flags' | 'documentation' | 'rules' | 'audit';

@Component({
  selector: 'app-clinical-governance-dashbaord',
  standalone: true,
  imports: [CommonModule, FormsModule, Pagination],
  templateUrl: './clinical_governance_dashbaord.html',
  styleUrl: './clinical_governance_dashbaord.scss',
})
export class ClinicalGovernanceDashbaord {
  private readonly api = inject(ClinicalGovernanceDashboardApi);
  private readonly toast = inject(ToastState);
  private readonly destroyRef = inject(DestroyRef);
  private readonly sessionUser = getSessionUser();

  readonly pageSize = 8;
  readonly analytics = signal<ClinicalGovernanceAnalytics | null>(null);
  readonly loading = signal(false);
  readonly error = signal('');
  readonly period = signal<GovernancePeriod>('today');
  readonly customStartDate = signal(this.todayValue());
  readonly customEndDate = signal(this.todayValue());
  readonly pages = signal<Record<GovernanceTableKey, number>>({
    red_flags: 1,
    documentation: 1,
    rules: 1,
    audit: 1,
  });
  readonly periodLabel = computed(() => {
    const range = this.analytics()?.period;
    if (!range) {
      return '';
    }
    return range.start_date === range.end_date
      ? this.formatDate(range.start_date)
      : `${this.formatDate(range.start_date)} - ${this.formatDate(range.end_date)}`;
  });

  constructor() {
    this.loadAnalytics();
  }

  selectPeriod(period: GovernancePeriod): void {
    this.period.set(period);
    this.resetPages();
    if (period !== 'custom') {
      this.loadAnalytics();
    }
  }

  applyCustomRange(): void {
    if (!this.customStartDate() || !this.customEndDate()) {
      this.error.set('Choose both a start date and an end date.');
      return;
    }
    if (this.customStartDate() > this.customEndDate()) {
      this.error.set('Start date cannot be after end date.');
      return;
    }
    this.resetPages();
    this.loadAnalytics();
  }

  loadAnalytics(): void {
    const userId = this.sessionUser?.user_id;
    if (!userId) {
      this.error.set('Your session could not be identified. Please sign in again.');
      return;
    }

    const period = this.period();
    this.loading.set(true);
    this.error.set('');
    this.api
      .getAnalytics(
        userId,
        period,
        period === 'custom' ? this.customStartDate() : undefined,
        period === 'custom' ? this.customEndDate() : undefined,
      )
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.loading.set(false)),
      )
      .subscribe({
        next: (response) => this.analytics.set(response.data),
        error: (error: { error?: { message?: string } }) => {
          const message = error.error?.message ?? 'Unable to load clinical governance analytics.';
          this.error.set(message);
          this.toast.error(message);
        },
      });
  }

  pageRows<T>(key: GovernanceTableKey, rows: T[]): T[] {
    const start = (this.page(key) - 1) * this.pageSize;
    return rows.slice(start, start + this.pageSize);
  }

  page(key: GovernanceTableKey): number {
    return this.pages()[key];
  }

  pageStart(key: GovernanceTableKey, total: number): number {
    return total ? (this.page(key) - 1) * this.pageSize + 1 : 0;
  }

  pageEnd(key: GovernanceTableKey, total: number): number {
    return Math.min(this.page(key) * this.pageSize, total);
  }

  previousPage(key: GovernanceTableKey): void {
    this.pages.update((pages) => ({ ...pages, [key]: Math.max(pages[key] - 1, 1) }));
  }

  nextPage(key: GovernanceTableKey, total: number): void {
    const lastPage = Math.max(Math.ceil(total / this.pageSize), 1);
    this.pages.update((pages) => ({ ...pages, [key]: Math.min(pages[key] + 1, lastPage) }));
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

  private resetPages(): void {
    this.pages.set({ red_flags: 1, documentation: 1, rules: 1, audit: 1 });
  }

  private todayValue(): string {
    const today = new Date();
    const timezoneOffset = today.getTimezoneOffset() * 60_000;
    return new Date(today.getTime() - timezoneOffset).toISOString().slice(0, 10);
  }

  private formatDate(value: string): string {
    return new Date(`${value}T00:00:00`).toLocaleDateString();
  }
}
