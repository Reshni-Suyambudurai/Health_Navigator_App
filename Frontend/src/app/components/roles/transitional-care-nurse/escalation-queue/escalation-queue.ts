import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';

import { EscalationApi } from '../../../../api/navigator/escalation.api';
import { getSessionUser } from '../../../../api/tokenstore';
import { EscalationActionType, EscalationDetail, EscalationStatus, EscalationSummary } from '../../../../shared/types/navigator/escalation';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

@Component({
  selector: 'app-escalation-queue',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './escalation-queue.html',
  styleUrl: './escalation-queue.scss',
})
export class EscalationQueue implements OnInit {
  private readonly escalationApi = inject(EscalationApi);
  private readonly toast = inject(ToastState);
  private readonly sessionUser = getSessionUser();

  readonly escalations = signal<EscalationSummary[]>([]);
  readonly selected = signal<EscalationDetail | null>(null);
  readonly loading = signal(true);
  readonly working = signal(false);
  readonly statusFilter = signal<string>('ACTIVE');
  readonly actionNotes = signal('');

  ngOnInit(): void {
    this.loadQueue();
  }

  loadQueue(): void {
    if (!this.sessionUser) {
      this.loading.set(false);
      return;
    }
    const filter = this.statusFilter();
    const status = filter === 'ACTIVE' ? undefined : filter;
    this.loading.set(true);
    this.escalationApi.list(this.sessionUser.userId, status)
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: ({ data }) => this.escalations.set(filter === 'ACTIVE' ? data.escalations.filter((item) => item.status !== 'RESOLVED' && item.status !== 'CLOSED') : data.escalations),
        error: (error) => this.toast.error(this.errorMessage(error, 'The escalation queue could not be loaded.')),
      });
  }

  selectEscalation(escalation: EscalationSummary): void {
    if (!this.sessionUser) return;
    this.actionNotes.set('');
    this.escalationApi.detail(this.sessionUser.userId, escalation.escalation_id).subscribe({
      next: ({ data }) => this.selected.set(data),
      error: (error) => this.toast.error(this.errorMessage(error, 'The escalation details could not be loaded.')),
    });
  }

  claim(): void { this.runCommand((id) => this.escalationApi.claim(this.sessionUser!.userId, id), 'Escalation claimed.'); }
  addAction(actionType: EscalationActionType): void { this.runCommand((id) => this.escalationApi.addAction(this.sessionUser!.userId, id, actionType, this.actionNotes()), 'Action recorded.'); }
  resolve(): void { this.runCommand((id) => this.escalationApi.resolve(this.sessionUser!.userId, id, this.actionNotes()), 'Escalation resolved.'); }

  setStatusFilter(status: string): void {
    this.statusFilter.set(status);
    this.selected.set(null);
    this.loadQueue();
  }

  formatDate(value: string): string { return new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)); }
  isSelected(id: number): boolean { return this.selected()?.escalation_id === id; }
  isActionable(status: EscalationStatus): boolean { return status !== 'RESOLVED' && status !== 'CLOSED'; }

  private runCommand(request: (id: number) => ReturnType<EscalationApi['claim']>, successMessage: string): void {
    const escalation = this.selected();
    if (!escalation || !this.sessionUser || this.working()) return;
    this.working.set(true);
    request(escalation.escalation_id).pipe(finalize(() => this.working.set(false))).subscribe({
      next: ({ data }) => {
        this.selected.set(data);
        this.actionNotes.set('');
        this.toast.success(successMessage);
        this.loadQueue();
      },
      error: (error) => this.toast.error(this.errorMessage(error, 'The escalation could not be updated.')),
    });
  }

  private errorMessage(error: unknown, fallback: string): string {
    if (typeof error !== 'object' || error === null) return fallback;
    const response = error as { error?: { message?: string }; message?: string };
    return response.error?.message ?? response.message ?? fallback;
  }
}