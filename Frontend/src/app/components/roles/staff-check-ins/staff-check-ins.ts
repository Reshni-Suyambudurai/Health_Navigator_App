import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';

import { OutreachApi } from '../../../api/navigator/outreach.api';
import { getSessionUser } from '../../../api/tokenstore';
import { StaffCheckinWork } from '../../../shared/types/navigator/outreach';
import { ToastState } from '../../../shared/ui/toast/toast-state';

@Component({
  selector: 'app-staff-check-ins',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './staff-check-ins.html',
  styleUrl: './staff-check-ins.scss',
})
export class StaffCheckIns implements OnInit {
  private readonly api = inject(OutreachApi);
  private readonly toast = inject(ToastState);
  private readonly user = getSessionUser();

  readonly checkins = signal<StaffCheckinWork[]>([]);
  readonly selected = signal<StaffCheckinWork | null>(null);
  readonly loading = signal(true);
  readonly working = signal(false);
  readonly showCompleted = signal(true);
  readonly showEmergency = signal(true);
  readonly showRoutine = signal(true);
  actionTaken = '';
  resolutionNotes = '';

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    if (!this.user) {
      this.loading.set(false);
      return;
    }
    this.loading.set(true);
    this.api.listAssignedCheckins(this.user.userId)
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: ({ data }) => {
          this.checkins.set(data.checkins);
          const currentId = this.selected()?.assignment.assignment_id;
          if (currentId) {
            this.selected.set(data.checkins.find((item) => item.assignment.assignment_id === currentId) ?? null);
          }
        },
        error: (error) => this.toast.error(this.errorMessage(error, 'Unable to load assigned check-ins.')),
      });
  }

  visibleCheckins(): StaffCheckinWork[] {
    const statusFiltered = this.showCompleted()
      ? this.checkins()
      : this.checkins().filter((item) => item.assignment.assignment_status !== 'COMPLETED');
    return statusFiltered.filter((item) => (
      item.escalation.escalation_type === 'EMERGENCY'
        ? this.showEmergency()
        : this.showRoutine()
    ));
  }

  select(item: StaffCheckinWork): void {
    this.selected.set(item);
    this.actionTaken = item.assignment.action_taken ?? '';
    this.resolutionNotes = item.assignment.resolution_notes ?? '';
  }

  startReview(): void {
    const item = this.selected();
    if (!item || !this.user || this.working()) return;
    this.working.set(true);
    this.api.startCheckinReview(this.user.userId, item.assignment.assignment_id)
      .pipe(finalize(() => this.working.set(false)))
      .subscribe({
        next: ({ data }) => {
          this.replace(data);
          this.toast.success('Check-in review started.');
        },
        error: (error) => this.toast.error(this.errorMessage(error, 'Unable to start this review.')),
      });
  }

  resolve(): void {
    const item = this.selected();
    if (!item || !this.user || this.working()) return;
    if (!this.actionTaken.trim() || !this.resolutionNotes.trim()) {
      this.toast.error('Document the action taken and resolution notes.');
      return;
    }
    this.working.set(true);
    this.api.resolveCheckin(
      this.user.userId,
      item.assignment.assignment_id,
      this.actionTaken.trim(),
      this.resolutionNotes.trim(),
    ).pipe(finalize(() => this.working.set(false))).subscribe({
      next: ({ data }) => {
        this.replace(data);
        this.toast.success('Check-in resolved.');
      },
      error: (error) => this.toast.error(this.errorMessage(error, 'Unable to resolve this check-in.')),
    });
  }

  answer(item: StaffCheckinWork['responses'][number]): string {
    if (item.answer_text) return item.answer_text;
    if (Array.isArray(item.answer_value)) return item.answer_value.join(', ');
    return String(item.answer_value ?? 'No answer');
  }

  formatDate(value: string | null): string {
    return value
      ? new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
      : 'Not available';
  }

  formatLabel(value: string): string {
    return value
      .replaceAll('_', ' ')
      .toLowerCase()
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  private replace(updated: StaffCheckinWork): void {
    this.selected.set(updated);
    this.checkins.update((items) => items.map((item) => (
      item.assignment.assignment_id === updated.assignment.assignment_id ? updated : item
    )));
  }

  private errorMessage(error: unknown, fallback: string): string {
    const value = error as { error?: { message?: string; detail?: string }; message?: string };
    return value?.error?.message ?? value?.error?.detail ?? value?.message ?? fallback;
  }
}