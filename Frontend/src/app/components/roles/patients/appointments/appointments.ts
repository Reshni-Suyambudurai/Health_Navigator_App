import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { finalize, forkJoin } from 'rxjs';
import { AppointmentApi } from '../../../../api/navigator/appointment.api';
import { UserApi } from '../../../../api/navigator/user.api';
import { getSessionUser } from '../../../../api/tokenstore';
import { PatientAppointmentRecord } from '../../../../shared/types/navigator/appointment';
import { ToastState } from '../../../../shared/ui/toast/toast-state';
import { BookAppointment } from '../book-appointment/book-appointment';

@Component({
  selector: 'app-patient-appointments',
  standalone: true,
  imports: [CommonModule, BookAppointment],
  templateUrl: './appointments.html',
  styleUrl: './appointments.scss',
})
export class PatientAppointments implements OnInit {
  private readonly appointmentApi = inject(AppointmentApi);
  private readonly userApi = inject(UserApi);
  private readonly toast = inject(ToastState);
  private readonly sessionUser = getSessionUser();

  readonly loading = signal(true);
  readonly patientId = signal<number | null>(null);
  readonly upcoming = signal<PatientAppointmentRecord[]>([]);
  readonly history = signal<PatientAppointmentRecord[]>([]);
  readonly pageError = signal<string | null>(null);
  readonly bookingModalOpen = signal(false);

  ngOnInit(): void {
    const userId = this.sessionUser?.userId;
    if (!userId) {
      this.loading.set(false);
      this.pageError.set('Your session has expired. Please sign in again.');
      return;
    }

    this.userApi.getPatientOnboarding(userId).subscribe({
        next: (response) => {
          if (response.data.onboarding_required || !response.data.profile) {
            this.pageError.set('Complete patient onboarding before booking an appointment.');
            this.loading.set(false);
            return;
          }
          this.patientId.set(response.data.profile.patient_id);
          this.loadAppointments();
        },
        error: (error: unknown) => {
          this.pageError.set(this.extractErrorMessage(error));
          this.loading.set(false);
        },
      });
  }

  openBookingModal(): void {
    this.bookingModalOpen.set(true);
  }

  closeBookingModal(): void {
    this.bookingModalOpen.set(false);
  }

  bookingCompleted(): void {
    this.bookingModalOpen.set(false);
    this.loadAppointments();
  }

  formatDateTime(value: string): string {
    return new Date(value).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
  }

  formatTime(value: string): string {
    return new Date(value).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  }

  formatType(value: string): string {
    return value.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  dueLabel(value: string): string {
    const appointment = new Date(value);
    const today = new Date();
    const appointmentDay = new Date(appointment.getFullYear(), appointment.getMonth(), appointment.getDate());
    const todayDay = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    const days = Math.round((appointmentDay.getTime() - todayDay.getTime()) / 86_400_000);

    if (days <= 0) {
      return 'Due today';
    }
    return days === 1 ? 'Due in 1 day' : `Due in ${days} days`;
  }

  private loadAppointments(): void {
    const userId = this.sessionUser?.userId;
    if (!userId) {
      return;
    }

    forkJoin({
      upcoming: this.appointmentApi.getPatientUpcoming(userId),
      history: this.appointmentApi.getPatientHistory(userId),
    })
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
      next: (response) => {
        this.upcoming.set(response.upcoming.data.appointments);
        this.history.set(response.history.data.appointments);
      },
      error: (error: unknown) => this.toast.error(this.extractErrorMessage(error)),
    });
  }

  private extractErrorMessage(error: unknown): string {
    if (typeof error !== 'object' || error === null) {
      return 'Unable to load appointments. Please try again.';
    }

    const response = error as { error?: { message?: string }; message?: string };
    return response.error?.message ?? response.message ?? 'Unable to load appointments. Please try again.';
  }
}
