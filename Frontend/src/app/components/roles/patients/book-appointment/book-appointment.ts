import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, OnDestroy, OnInit, Output, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Subscription, finalize } from 'rxjs';
import { AppointmentApi } from '../../../../api/navigator/appointment.api';
import { getSessionUser } from '../../../../api/tokenstore';
import {
  AppointmentType,
  AvailableAppointmentSlot,
  RoutineAppointmentRequest,
} from '../../../../shared/types/navigator/appointment';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

interface RoutineBookingForm {
  appointment_type: AppointmentType;
  appointment_date: string;
  duration_minutes: number;
  reason: string;
  location_or_channel: string;
}

@Component({
  selector: 'app-book-appointment',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './book-appointment.html',
  styleUrl: './book-appointment.scss',
})
export class BookAppointment implements OnInit, OnDestroy {
  @Input({ required: true }) patientId!: number;
  @Output() readonly closed = new EventEmitter<void>();
  @Output() readonly booked = new EventEmitter<void>();

  private readonly appointmentApi = inject(AppointmentApi);
  private readonly toast = inject(ToastState);
  private readonly sessionUser = getSessionUser();
  private slotRequest?: Subscription;

  readonly booking = signal(false);
  readonly slotsLoading = signal(false);
  readonly availableSlots = signal<AvailableAppointmentSlot[]>([]);
  readonly selectedSlot = signal<AvailableAppointmentSlot | null>(null);
  readonly bookingError = signal<string | null>(null);
  readonly slotsError = signal<string | null>(null);
  readonly today = new Date().toISOString().slice(0, 10);

  bookingForm: RoutineBookingForm = {
    appointment_type: 'NURSE_FOLLOWUP',
    appointment_date: this.today,
    duration_minutes: 30,
    reason: '',
    location_or_channel: 'Phone call',
  };

  ngOnInit(): void {
    this.loadAvailableSlots();
  }

  ngOnDestroy(): void {
    this.slotRequest?.unsubscribe();
  }

  close(): void {
    if (!this.booking()) {
      this.closed.emit();
    }
  }

  changeAppointmentDate(value: string): void {
    this.bookingForm.appointment_date = value;
    this.loadAvailableSlots();
  }

  openPicker(input: HTMLInputElement): void {
    if (typeof input.showPicker === 'function') {
      input.showPicker();
    } else {
      input.focus();
    }
  }

  changeDuration(value: number): void {
    this.bookingForm.duration_minutes = value;
    this.loadAvailableSlots();
  }

  selectSlot(slot: AvailableAppointmentSlot): void {
    this.selectedSlot.set(slot);
    this.bookingError.set(null);
  }

  bookRoutineAppointment(): void {
    const userId = this.sessionUser?.userId;
    const slot = this.selectedSlot();
    if (!userId || !slot) {
      this.bookingError.set('Select an available appointment time.');
      return;
    }

    const payload: RoutineAppointmentRequest = {
      patient_id: this.patientId,
      appointment_type: this.bookingForm.appointment_type,
      appointment_datetime: slot.start,
      end_datetime: slot.end,
      reason: this.bookingForm.reason.trim() || null,
      location_or_channel: this.bookingForm.location_or_channel || null,
    };

    this.booking.set(true);
    this.bookingError.set(null);
    this.appointmentApi.bookRoutineAppointment(userId, payload)
      .pipe(finalize(() => this.booking.set(false)))
      .subscribe({
        next: (response) => {
          this.toast.success(response.message);
          this.booked.emit();
        },
        error: (error: unknown) => {
          this.bookingError.set(this.extractErrorMessage(error));
          this.loadAvailableSlots();
        },
      });
  }

  formatSlotTime(value: string): string {
    return new Date(value).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  }

  private loadAvailableSlots(): void {
    const userId = this.sessionUser?.userId;
    if (!userId || !this.bookingForm.appointment_date) {
      this.slotsError.set('Your session has expired. Please sign in again.');
      return;
    }

    this.slotRequest?.unsubscribe();
    this.slotsLoading.set(true);
    this.slotsError.set(null);
    this.availableSlots.set([]);
    this.selectedSlot.set(null);
    this.slotRequest = this.appointmentApi.getAvailableSlots(
      userId,
      this.bookingForm.appointment_date,
      this.bookingForm.duration_minutes,
    )
      .pipe(finalize(() => this.slotsLoading.set(false)))
      .subscribe({
        next: (response) => this.availableSlots.set(response.data.slots),
        error: (error: unknown) => this.slotsError.set(this.extractErrorMessage(error)),
      });
  }

  private extractErrorMessage(error: unknown): string {
    if (typeof error !== 'object' || error === null) {
      return 'Unable to complete this request. Please try again.';
    }
    const response = error as { error?: { message?: string }; message?: string };
    return response.error?.message ?? response.message ?? 'Unable to complete this request. Please try again.';
  }
}