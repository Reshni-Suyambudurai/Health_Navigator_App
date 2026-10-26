import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, input, output, signal } from '@angular/core';
import { finalize } from 'rxjs';
import { AdminOutreachApi } from '../../../../../api/navigator/admin-outreach.api';
import { getSessionUser } from '../../../../../api/tokenstore';
import {
  AdminCampaignRecord,
  AdminCohortPatient,
  AdminOutreachSelection,
  AdminOutreachSummary,
} from '../../../../../shared/types/navigator/admin-outreach';
import { ToastState } from '../../../../../shared/ui/toast/toast-state';
import { RefreshButton } from '../../../../../shared/ui/refresh-button/refresh-button';

@Component({
  selector: 'app-cohort-outreach-panel',
  standalone: true,
  imports: [CommonModule, RefreshButton],
  templateUrl: './cohort-outreach-panel.html',
  styleUrl: './cohort-outreach-panel.scss',
})
export class CohortOutreachPanel implements OnInit {
  private readonly api = inject(AdminOutreachApi);
  private readonly toast = inject(ToastState);
  private readonly sessionUser = getSessionUser();
  private readonly pageSize = 20;
  private requestToken = 0;

  readonly campaign = input.required<AdminCampaignRecord>();
  readonly closed = output<void>();
  readonly outreachCreated = output<void>();
  readonly patients = signal<AdminCohortPatient[]>([]);
  readonly total = signal(0);
  readonly summary = signal<AdminOutreachSummary | null>(null);
  readonly loading = signal(false);
  readonly loadingMore = signal(false);
  readonly creating = signal(false);
  readonly hasMore = signal(false);
  readonly error = signal<string | null>(null);
  readonly selectedKeys = signal<Set<string>>(new Set());
  readonly selectablePatients = computed(() => this.patients().filter((patient) => patient.can_create_outreach));
  readonly selectedCount = computed(() => this.selectedKeys().size);
  readonly allSelectableSelected = computed(() => {
    const selectable = this.selectablePatients();
    return selectable.length > 0 && selectable.every((patient) => this.selectedKeys().has(this.key(patient)));
  });

  ngOnInit(): void {
    this.total.set(this.campaign().readiness.eligible_patient_count);
    this.load(true);
  }

  close(): void {
    if (this.creating()) return;
    this.requestToken += 1;
    this.closed.emit();
  }

  loadMore(): void {
    if (this.hasMore()) this.load(false);
  }

  retry(): void {
    this.load(this.patients().length === 0);
  }

  refresh(): void {
    this.selectedKeys.set(new Set());
    this.load(true);
  }

  togglePatient(patient: AdminCohortPatient, checked: boolean): void {
    if (!patient.can_create_outreach) return;
    this.selectedKeys.update((current) => {
      const next = new Set(current);
      if (checked) next.add(this.key(patient));
      else next.delete(this.key(patient));
      return next;
    });
  }

  toggleAll(checked: boolean): void {
    this.selectedKeys.update((current) => {
      const next = new Set(current);
      for (const patient of this.selectablePatients()) {
        if (checked) next.add(this.key(patient));
        else next.delete(this.key(patient));
      }
      return next;
    });
  }

  createOutreach(): void {
    const actorId = this.actorId();
    if (!actorId || this.creating() || !this.selectedCount()) return;
    const selected = this.selectedKeys();
    const selections: AdminOutreachSelection[] = this.patients()
      .filter((patient) => selected.has(this.key(patient)))
      .map((patient) => ({ patient_id: patient.patient_id, episode_id: patient.episode_id }));
    this.creating.set(true);
    this.error.set(null);
    this.api.createOutreachEvents(actorId, this.campaign().campaign_id, selections)
      .pipe(finalize(() => this.creating.set(false)))
      .subscribe({
        next: (response) => {
          const result = response.data;
          this.toast.success(
            `${result.created} created, ${result.already_existing} already existed, ${result.no_longer_eligible} no longer eligible.`,
          );
          this.selectedKeys.set(new Set());
          this.outreachCreated.emit();
          this.load(true);
        },
        error: (error: unknown) => {
          const message = this.errorMessage(error, 'Unable to create outreach.');
          this.error.set(message);
          this.toast.error(message);
        },
      });
  }

  selected(patient: AdminCohortPatient): boolean {
    return this.selectedKeys().has(this.key(patient));
  }

  formatLabel(value: string): string {
    return value.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  private load(reset: boolean): void {
    const actorId = this.actorId();
    if (!actorId || (!reset && this.loadingMore())) {
      if (!actorId) this.error.set('Your session has expired. Please sign in again.');
      return;
    }
    const token = ++this.requestToken;
    const skip = reset ? 0 : this.patients().length;
    this.error.set(null);
    if (reset) this.loading.set(true);
    else this.loadingMore.set(true);
    this.api.listCohortMembers(actorId, this.campaign().campaign_id, skip, this.pageSize)
      .pipe(finalize(() => {
        if (token !== this.requestToken) return;
        this.loading.set(false);
        this.loadingMore.set(false);
      }))
      .subscribe({
        next: (response) => {
          if (token !== this.requestToken) return;
          this.patients.update((current) => reset ? response.data.patients : [...current, ...response.data.patients]);
          this.total.set(response.data.count);
          this.summary.set(response.data.outreach_summary);
          this.hasMore.set(response.data.has_more);
        },
        error: (error: unknown) => {
          if (token !== this.requestToken) return;
          this.error.set(this.errorMessage(error, 'Unable to load eligible patients.'));
        },
      });
  }

  private key(patient: AdminCohortPatient): string {
    return `${patient.patient_id}:${patient.episode_id}`;
  }

  private actorId(): number {
    return Number(this.sessionUser?.user_id ?? this.sessionUser?.userId ?? 0);
  }

  private errorMessage(error: unknown, fallback: string): string {
    return (error as { error?: { message?: string } })?.error?.message ?? fallback;
  }
}