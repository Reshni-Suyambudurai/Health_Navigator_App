import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin, finalize } from 'rxjs';
import { OutreachApi } from '../../../../api/navigator/outreach.api';
import { getSessionUser } from '../../../../api/tokenstore';
import { BookAppointment } from '../book-appointment/book-appointment';
import {
  CheckinSession,
  CheckinResponse,
  PatientCheckinQuestion,
  CheckinResponseRequest,
} from '../../../../shared/types/navigator/outreach';
import { BreadcrumbItem } from '../../../../shared/ui/breadcrumb/breadcrumb';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

@Component({
  selector: 'app-patient-check-ins',
  standalone: true,
  imports: [CommonModule, FormsModule, BookAppointment, RouterLink],
  templateUrl: './patient-check-ins.html',
  styleUrl: './patient-check-ins.scss',
})
export class PatientCheckIns implements OnInit {
  private readonly api = inject(OutreachApi);
  private readonly route = inject(ActivatedRoute);
  private readonly toast = inject(ToastState);

  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly submitting = signal(false);
  readonly error = signal<string | null>(null);
  readonly sessions = signal<CheckinSession[]>([]);
  readonly selectedSession = signal<CheckinSession | null>(null);
  readonly bookingModalOpen = signal(false);
  readonly statusFilter = signal('ALL');
  readonly statusOptions = ['ALL', 'PENDING', 'IN_PROGRESS', 'COMPLETED', 'EXPIRED', 'ESCALATED', 'OVERDUE', 'ABANDONED'];
  readonly filteredSessions = computed(() => {
    const filter = this.statusFilter();
    if (filter !== 'ALL') {
      return this.sessions().filter((session) => session.session_status === filter);
    }
    return [...this.sessions()].sort(
      (left, right) => this.sessionTimestamp(right) - this.sessionTimestamp(left),
    );
  });
  readonly breadcrumbs: BreadcrumbItem[] = [
    { label: 'Patient dashboard', route: '/patient/dashboard' },
    { label: 'Check-ins' },
  ];
  readonly answers: Record<number, unknown> = {};

  ngOnInit(): void {
    this.loadSessions();
  }

  loadSessions(): void {
    const user = getSessionUser();
    if (!user) {
      this.loading.set(false);
      this.error.set('Your session has expired. Please sign in again.');
      return;
    }

    this.loading.set(true);
    this.api.listSessions(user.userId)
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (response) => {
          this.sessions.set(response.data.sessions);
          const requestedId = Number(this.route.snapshot.paramMap.get('sessionId'));
          const requested = requestedId
            ? response.data.sessions.find((session) => session.checkin_session_id === requestedId)
            : null;
          if (requested) {
            this.selectSession(requested);
          }
          const current = this.selectedSession();
          if (current) {
            const refreshed = response.data.sessions.find(
              (session) => session.checkin_session_id === current.checkin_session_id,
            );
            if (refreshed) {
              this.selectSession(refreshed);
            }
          }
        },
        error: (error: unknown) => this.error.set(this.errorMessage(error)),
      });
  }

  selectSession(session: CheckinSession): void {
    this.selectedSession.set(session);
    Object.keys(this.answers).forEach((key) => delete this.answers[Number(key)]);
    for (const response of session.responses) {
      this.answers[response.question_id] = response.answer_value ?? response.answer_text ?? '';
    }
  }

  closeSession(): void {
    this.bookingModalOpen.set(false);
    this.selectedSession.set(null);
    Object.keys(this.answers).forEach((key) => delete this.answers[Number(key)]);
  }

  isOpen(session: CheckinSession): boolean {
    return ['PENDING', 'IN_PROGRESS'].includes(session.session_status) && !this.isExpired(session);
  }

  canBookAppointment(session: CheckinSession): boolean {
    return session.appointment_required
      && session.appointment_id === null
      && ['PENDING', 'IN_PROGRESS'].includes(session.session_status)
      && !this.isExpired(session);
  }

  openAppointmentBooking(session: CheckinSession | null = this.selectedSession()): void {
    if (session && this.canBookAppointment(session)) {
      if (this.selectedSession()?.checkin_session_id !== session.checkin_session_id) {
        this.selectSession(session);
      }
      this.bookingModalOpen.set(true);
    }
  }

  closeAppointmentBooking(): void {
    this.bookingModalOpen.set(false);
  }

  appointmentBooked(): void {
    this.bookingModalOpen.set(false);
    this.loadSessions();
  }

  isExpired(session: CheckinSession): boolean {
    return ['OVERDUE', 'EXPIRED'].includes(session.session_status)
      || (!!session.expires_at && new Date(session.expires_at).getTime() <= Date.now());
  }

  isMultipleChoice(answerType: string): boolean {
    return answerType === 'MULTIPLE_CHOICE' || answerType === 'MULTI_CHOICE';
  }

  progress(session: CheckinSession): string {
    const required = session.questions.filter((question) => question.is_required);
    const answered = required.filter((question) => this.hasAnswer(session, question)).length;
    return `${answered} of ${required.length} required answered`;
  }

  hasAnswer(session: CheckinSession, question: PatientCheckinQuestion): boolean {
    const existing = session.responses.find((response) => response.question_id === question.question_id);
    const value = this.answers[question.question_id] ?? existing?.answer_value ?? existing?.answer_text;
    return Array.isArray(value) ? value.length > 0 : value !== null && value !== undefined && String(value).trim().length > 0;
  }

  isOptionSelected(questionId: number, option: string): boolean {
    return this.multipleChoiceAnswer(questionId).includes(option);
  }

  toggleOption(questionId: number, option: string): void {
    const selected = this.multipleChoiceAnswer(questionId);
    this.answers[questionId] = selected.includes(option)
      ? selected.filter((item) => item !== option)
      : [...selected, option];
  }

  submit(): void {
    const session = this.selectedSession();
    if (!session || !this.isOpen(session)) return;

    const missing = session.questions.some((question) => question.is_required && !this.hasAnswer(session, question));
    if (missing) {
      this.error.set('Please answer all required questions before submitting.');
      return;
    }

    const user = getSessionUser();
    if (!user) {
      this.error.set('Your session has expired. Please sign in again.');
      return;
    }
    const responses = session.questions
      .filter((question) => this.hasAnswer(session, question))
      .map((question) => this.responsePayload(question));
    this.submitting.set(true);
    this.error.set(null);
    this.api.submitCheckin(session.checkin_session_id, { responses }, user.userId)
      .pipe(finalize(() => this.submitting.set(false)))
      .subscribe({
        next: (response) => {
          const updatedSession = { ...session, ...response.data };
          this.selectedSession.set(updatedSession);
          this.sessions.update((items) => items.map((item) => (
            item.checkin_session_id === updatedSession.checkin_session_id ? updatedSession : item
          )));
          this.toast.success('Your check-in has been submitted.');
        },
        error: (error: unknown) => this.error.set(this.errorMessage(error)),
      });
  }

  saveDraft(): void {
    const session = this.selectedSession();
    if (!session || !this.isOpen(session)) return;
    this.persistAnswers('Your check-in draft has been saved.', false);
  }

  private persistAnswers(successMessage: string, closeAfterSave: boolean): void {
    const session = this.selectedSession();
    const user = getSessionUser();
    if (!session || !user || !this.isOpen(session)) return;

    const requests = session.questions
      .filter((question) => this.hasAnswer(session, question))
      .map((question) => this.api.recordCheckinResponse(
        session.checkin_session_id,
        this.responsePayload(question),
        user.userId,
      ));
    if (!requests.length) {
      this.error.set('Answer at least one question before saving a draft.');
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    forkJoin(requests)
      .pipe(finalize(() => this.saving.set(false)))
      .subscribe({
        next: (responses) => {
          this.updateSessionResponses(responses.map((response) => response.data));
          this.toast.success(successMessage);
          if (closeAfterSave) this.closeSession();
        },
        error: (error: unknown) => this.error.set(this.errorMessage(error)),
      });
  }

  private updateSessionResponses(responses: CheckinResponse[]): void {
    const session = this.selectedSession();
    if (!session) return;
    const updatedByQuestion = new Map(responses.map((response) => [response.question_id, response]));
    const mergedResponses = session.responses.map((response) => updatedByQuestion.get(response.question_id) ?? response);
    for (const response of responses) {
      if (!session.responses.some((existing) => existing.question_id === response.question_id)) {
        mergedResponses.push(response);
      }
    }
    const updatedSession = {
      ...session,
      responses: mergedResponses,
      session_status: session.session_status === 'PENDING' ? 'IN_PROGRESS' : session.session_status,
      updated_at: new Date().toISOString(),
    };
    this.selectedSession.set(updatedSession);
    this.sessions.update((items) => items.map((item) => (
      item.checkin_session_id === updatedSession.checkin_session_id ? updatedSession : item
    )));
  }

  formatDate(value: string | null): string {
    if (!value) return 'No expiry configured';
    return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
  }

  formatDateTime(value: string | null): string {
    if (!value) return 'Not available';
    return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
  }

  formatLabel(value: string): string {
    return value
      .replaceAll('_', ' ')
      .toLowerCase()
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  private sessionTimestamp(session: CheckinSession): number {
    return new Date(session.scheduled_at || session.created_at).getTime();
  }

  private responsePayload(question: PatientCheckinQuestion): CheckinResponseRequest {
    const value = this.answers[question.question_id];
    return {
      question_id: question.question_id,
      answer_text: question.answer_type === 'TEXT' ? String(value ?? '') : null,
      answer_value: question.answer_type === 'TEXT' ? null : value,
      response_source: 'PATIENT_REPORTED',
    };
  }

  private multipleChoiceAnswer(questionId: number): string[] {
    const value = this.answers[questionId];
    return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
  }

  private errorMessage(error: unknown): string {
    const detail = (error as { error?: { detail?: string } })?.error?.detail;
    return detail || 'Unable to load your check-ins.';
  }
}
