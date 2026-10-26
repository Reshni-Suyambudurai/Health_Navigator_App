import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { OutreachEventApi, OutreachEventRole } from '../../../api/navigator/outreach-event.api';
import { getSessionUser } from '../../../api/tokenstore';
import {
  DeliveryStatus,
  EventStatus,
  OutreachEventDetail,
  OutreachEventFilterOptions,
  OutreachEventFilters,
  OutreachEventSummary,
} from '../../types/navigator/outreach';
import { Pagination } from '../../ui/pagination/pagination';
import { RefreshButton } from '../../ui/refresh-button/refresh-button';
import { ToastState } from '../../ui/toast/toast-state';

@Component({
  selector: 'app-outreach-event-browser',
  standalone: true,
  imports: [CommonModule, FormsModule, Pagination, RefreshButton],
  templateUrl: './outreach-event-browser.html',
  styleUrl: './outreach-event-browser.scss',
})
export class OutreachEventBrowser implements OnInit {
  readonly role = input.required<OutreachEventRole>();
  private readonly api = inject(OutreachEventApi);
  private readonly toast = inject(ToastState);
  private readonly sessionUser = getSessionUser();

  readonly events = signal<OutreachEventSummary[]>([]);
  readonly selected = signal<OutreachEventDetail | null>(null);
  readonly count = signal(0);
  readonly hasMore = signal(false);
  readonly loading = signal(false);
  readonly detailLoading = signal(false);
  readonly filterOptions = signal<OutreachEventFilterOptions>({ campaigns: [], workflows: [] });
  readonly error = signal<string | null>(null);
  readonly page = signal(0);
  readonly pageSize = 25;
  readonly eventStatuses: EventStatus[] = ['PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED'];
  readonly deliveryStatuses: DeliveryStatus[] = ['PENDING', 'SENT', 'DELIVERED', 'FAILED', 'RESPONDED'];
  filters: OutreachEventFilters = { limit: this.pageSize };

  get pageStart(): number {
    return this.count() ? this.page() * this.pageSize + 1 : 0;
  }

  get pageEnd(): number {
    return Math.min((this.page() + 1) * this.pageSize, this.count());
  }

  ngOnInit(): void {
    this.loadFilterOptions();
    this.load();
  }

  loadFilterOptions(campaignId?: number): void {
    this.api.options(this.role(), this.sessionUser?.organization_id, campaignId).subscribe({
      next: (response) => this.filterOptions.set(response.data),
      error: () => this.toast.error('Unable to load campaign filters.'),
    });
  }

  onCampaignChange(): void {
    this.filters.workflow_id = undefined;
    this.loadFilterOptions(this.filters.campaign_id);
  }

  load(): void {
    if (!this.sessionUser) {
      this.error.set('Your session has expired. Sign in again to view outreach events.');
      return;
    }
    this.loading.set(true);
    this.error.set(null);
    this.api.list(this.role(), { ...this.filters, skip: this.page() * this.pageSize, limit: this.pageSize })
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (response) => {
          this.events.set(response.data.events);
          this.count.set(response.data.count);
          this.hasMore.set(response.data.has_more);
        },
        error: () => this.error.set('Unable to load outreach events. Try again.'),
      });
  }

  applyFilters(): void {
    this.page.set(0);
    this.selected.set(null);
    this.load();
  }

  clearFilters(): void {
    this.filters = { limit: this.pageSize };
    this.loadFilterOptions();
    this.applyFilters();
  }

  selectEvent(event: OutreachEventSummary): void {
    this.selected.set(null);
    this.detailLoading.set(true);
    this.api.get(this.role(), event.outreach_event_id)
      .pipe(finalize(() => this.detailLoading.set(false)))
      .subscribe({
        next: (response) => this.selected.set(response.data),
        error: () => this.toast.error('Unable to load event details.'),
      });
  }

  closeDetails(): void {
    this.selected.set(null);
  }

  previousPage(): void {
    if (this.page() > 0) {
      this.page.update((value) => value - 1);
      this.load();
    }
  }

  nextPage(): void {
    if (this.hasMore()) {
      this.page.update((value) => value + 1);
      this.load();
    }
  }

  formatDate(value: string | null): string {
    return value ? new Date(value).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : 'Not recorded';
  }

  formatLabel(value: string): string {
    return value.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  statusClass(value: string): string {
    if (['COMPLETED', 'DELIVERED', 'RESPONDED'].includes(value)) return 'positive';
    if (['FAILED', 'CANCELLED'].includes(value)) return 'critical';
    if (['PROCESSING', 'IN_PROGRESS'].includes(value)) return 'warning';
    return 'neutral';
  }
}