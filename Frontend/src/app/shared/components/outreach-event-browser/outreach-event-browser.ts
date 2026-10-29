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
import { CheckboxFilter, CheckboxFilterGroup } from '../../ui/checkbox-filter/checkbox-filter';

@Component({
  selector: 'app-outreach-event-browser',
  standalone: true,
  imports: [CommonModule, FormsModule, Pagination, RefreshButton, CheckboxFilter],
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
  readonly filterOptions = signal<OutreachEventFilterOptions>({ campaigns: [], workflows: [], patients: [] });
  readonly error = signal<string | null>(null);
  readonly page = signal(0);
  readonly pageSize = 8;
  readonly eventStatuses: EventStatus[] = ['PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED'];
  readonly deliveryStatuses: DeliveryStatus[] = ['PENDING', 'SENT', 'DELIVERED', 'FAILED', 'RESPONDED'];
  filters: OutreachEventFilters = { limit: this.pageSize };

  get pageStart(): number {
    return this.count() ? this.page() * this.pageSize + 1 : 0;
  }

  get pageEnd(): number {
    return Math.min((this.page() + 1) * this.pageSize, this.count());
  }

  get campaignWorkflowGroups(): CheckboxFilterGroup[] {
    const options = this.filterOptions();
    const campaignNames = new Map(options.campaigns.map((campaign) => [campaign.campaign_id, campaign.campaign_name]));
    return [
      {
        label: 'Campaigns',
        options: options.campaigns.map((campaign) => ({
          value: `campaign:${campaign.campaign_id}`,
          label: campaign.campaign_name,
        })),
      },
      {
        label: 'Workflows',
        options: options.workflows.map((workflow) => ({
          value: `workflow:${workflow.workflow_id}`,
          label: workflow.workflow_name,
          description: campaignNames.get(workflow.campaign_id),
        })),
      },
    ];
  }

  get selectedCampaignWorkflowValues(): string[] {
    return [
      ...(this.filters.campaign_id ?? []).map((id) => `campaign:${id}`),
      ...(this.filters.workflow_id ?? []).map((id) => `workflow:${id}`),
    ];
  }

  get patientGroups(): CheckboxFilterGroup[] {
    return [{
      label: '',
      options: this.filterOptions().patients.map((patient) => ({
        value: String(patient.patient_id),
        label: patient.patient_name,
        description: `Patient #${patient.patient_id}`,
      })),
    }];
  }

  get selectedPatientValues(): string[] {
    return (this.filters.patient_id ?? []).map(String);
  }

  get statusGroups(): CheckboxFilterGroup[] {
    return [
      {
        label: 'Delivery status',
        options: this.deliveryStatuses.map((status) => ({ value: `delivery:${status}`, label: this.formatLabel(status) })),
      },
      {
        label: 'Event status',
        options: this.eventStatuses.map((status) => ({ value: `event:${status}`, label: this.formatLabel(status) })),
      },
    ];
  }

  get selectedStatusValues(): string[] {
    return [
      ...(this.filters.delivery_status ?? []).map((status) => `delivery:${status}`),
      ...(this.filters.event_status ?? []).map((status) => `event:${status}`),
    ];
  }

  ngOnInit(): void {
    this.loadFilterOptions();
    this.load();
  }

  loadFilterOptions(): void {
    this.api.options(this.role(), this.sessionUser?.organization_id).subscribe({
      next: (response) => this.filterOptions.set(response.data),
      error: () => this.toast.error('Unable to load campaign filters.'),
    });
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

  applyCampaignWorkflowFilters(values: string[]): void {
    this.filters.campaign_id = this.numericValues(values, 'campaign:');
    this.filters.workflow_id = this.numericValues(values, 'workflow:');
    this.applyFilters();
  }

  applyPatientFilters(values: string[]): void {
    const patientIds = values.map(Number).filter((value) => Number.isInteger(value) && value > 0);
    this.filters.patient_id = patientIds.length ? patientIds : undefined;
    this.applyFilters();
  }

  applyStatusFilters(values: string[]): void {
    const deliveryStatuses = values
      .filter((value) => value.startsWith('delivery:'))
      .map((value) => value.slice('delivery:'.length) as DeliveryStatus);
    const eventStatuses = values
      .filter((value) => value.startsWith('event:'))
      .map((value) => value.slice('event:'.length) as EventStatus);
    this.filters.delivery_status = deliveryStatuses.length ? deliveryStatuses : undefined;
    this.filters.event_status = eventStatuses.length ? eventStatuses : undefined;
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

  triggerTiming(value: string, eventStatus: EventStatus): string {
    const scheduledAt = new Date(value).getTime();
    if (Number.isNaN(scheduledAt)) return 'Trigger time unavailable';
    if (eventStatus !== 'PENDING') return 'Trigger processed';

    const differenceMinutes = Math.round((scheduledAt - Date.now()) / 60000);
    if (differenceMinutes <= 0) return 'Due now';
    if (differenceMinutes < 60) return `Due in ${differenceMinutes} ${differenceMinutes === 1 ? 'minute' : 'minutes'}`;

    const differenceHours = Math.round(differenceMinutes / 60);
    if (differenceHours < 24) return `Due in ${differenceHours} ${differenceHours === 1 ? 'hour' : 'hours'}`;

    const differenceDays = Math.round(differenceHours / 24);
    return `Due in ${differenceDays} ${differenceDays === 1 ? 'day' : 'days'}`;
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

  private numericValues(values: string[], prefix: string): number[] | undefined {
    const result = values
      .filter((value) => value.startsWith(prefix))
      .map((value) => Number(value.slice(prefix.length)))
      .filter((value) => Number.isInteger(value) && value > 0);
    return result.length ? result : undefined;
  }
}