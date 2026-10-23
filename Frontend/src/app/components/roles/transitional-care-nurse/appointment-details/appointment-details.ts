import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError, finalize, map, switchMap } from 'rxjs/operators';
import { AppointmentApi } from '../../../../api/navigator/appointment.api';
import { getSessionUser } from '../../../../api/tokenstore';
import { FhirDataApi } from '../../../../api/patientfhir/fhir.data.api';
import {
  AppointmentStatus,
  AvailableNurseOption,
  NurseAppointmentDetails,
} from '../../../../shared/types/navigator/appointment';
import { FhirRecord } from '../../../../shared/types/patientfhir/fhir';
import { Breadcrumb, BreadcrumbItem } from '../../../../shared/ui/breadcrumb/breadcrumb';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

interface AppointmentDetailsBundle {
  appointment: NurseAppointmentDetails;
  patient: FhirRecord | null;
  conditions: FhirRecord[];
  medications: FhirRecord[];
}

@Component({
  selector: 'app-appointment-details',
  standalone: true,
  imports: [CommonModule, Breadcrumb],
  templateUrl: './appointment-details.html',
  styleUrl: './appointment-details.scss',
})
export class AppointmentDetails implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly appointmentApi = inject(AppointmentApi);
  private readonly fhirApi = inject(FhirDataApi);
  private readonly toast = inject(ToastState);
  private readonly sessionUser = getSessionUser();

  readonly appointment = signal<NurseAppointmentDetails | null>(null);
  readonly patient = signal<FhirRecord | null>(null);
  readonly conditions = signal<FhirRecord[]>([]);
  readonly medications = signal<FhirRecord[]>([]);
  readonly conditionStatusFilter = signal('active');
  readonly medicationStatusFilter = signal('active');
  readonly filteredConditions = computed(() =>
    this.filterByStatus(this.conditions(), 'clinical_status', this.conditionStatusFilter()),
  );
  readonly filteredMedications = computed(() =>
    this.filterByStatus(this.medications(), 'status', this.medicationStatusFilter()),
  );
  readonly conditionStatusOptions = computed(() =>
    this.statusOptions(this.conditions(), 'clinical_status'),
  );
  readonly medicationStatusOptions = computed(() =>
    this.statusOptions(this.medications(), 'status'),
  );
  readonly appointmentStatuses: AppointmentStatus[] = [
    'REQUESTED',
    'SCHEDULED',
    'CONFIRMED',
    'COMPLETED',
    'CANCELLED',
    'NO_SHOW',
    'RESCHEDULED',
  ];
  readonly selectedAppointmentStatus = signal<AppointmentStatus>('REQUESTED');
  readonly selectedNurseId = signal<number | null>(null);
  readonly availableNurses = signal<AvailableNurseOption[]>([]);
  readonly loadingNurses = signal(false);
  readonly updatingAppointment = signal(false);
  readonly appointmentActionError = signal<string | null>(null);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly clinicalWarning = signal<string | null>(null);
  readonly breadcrumbs: BreadcrumbItem[] = [
    { label: 'Appointments', route: '/transitional-care-nurse/appointments' },
    { label: 'Appointment Details' },
  ];

  ngOnInit(): void {
    const appointmentId = Number(this.route.snapshot.paramMap.get('appointmentId'));
    const userId = this.sessionUser?.user_id ?? this.sessionUser?.userId;

    if (!Number.isInteger(appointmentId) || appointmentId <= 0) {
      this.error.set('Invalid appointment selected.');
      return;
    }
    if (!userId) {
      this.error.set('Your session has expired. Please sign in again.');
      return;
    }

    this.loadDetails(userId, appointmentId);
  }

  get patientName(): string {
    const patient = this.patient();
    if (!patient) {
      return this.appointment()?.patient_name ?? 'Patient';
    }
    return [patient['first_name'], patient['last_name']]
      .filter((value) => typeof value === 'string' && value.trim())
      .join(' ') || this.appointment()?.patient_name || 'Patient';
  }

  patientValue(key: string): string {
    return this.formatValue(this.patient()?.[key]);
  }

  recordValue(record: FhirRecord, key: string): string {
    return this.formatValue(record[key]);
  }

  formatDateTime(value: string): string {
    return new Date(value).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
  }

  formatLabel(value: string): string {
    return value
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  statusClass(status: AppointmentStatus | unknown): string {
    const value = String(status ?? '').toUpperCase();
    const appointmentClasses: Record<string, string> = {
      REQUESTED: 'status-requested',
      SCHEDULED: 'status-scheduled',
      CONFIRMED: 'status-confirmed',
      COMPLETED: 'status-completed',
      CANCELLED: 'status-cancelled',
      NO_SHOW: 'status-no-show',
      RESCHEDULED: 'status-rescheduled',
    };
    if (appointmentClasses[value]) {
      return appointmentClasses[value];
    }
    if (value === 'ACTIVE') {
      return 'status-confirmed';
    }
    if (['INACTIVE', 'DISCONTINUED', 'CRITICAL'].includes(value)) {
      return 'status-cancelled';
    }
    return 'status-requested';
  }

  selectAppointmentStatus(value: string): void {
    const status = this.appointmentStatuses.find((option) => option === value);
    if (status) {
      this.selectedAppointmentStatus.set(status);
    }
    this.appointmentActionError.set(null);
  }

  selectNurse(value: string): void {
    const staffId = Number(value);
    this.selectedNurseId.set(Number.isInteger(staffId) && staffId > 0 ? staffId : null);
    this.appointmentActionError.set(null);
  }

  updateAppointmentStatus(): void {
    const appointment = this.appointment();
    const userId = this.sessionUser?.user_id ?? this.sessionUser?.userId;
    if (!appointment || !userId) {
      return;
    }

    this.updatingAppointment.set(true);
    this.appointmentActionError.set(null);
    this.appointmentApi.updateNurseAppointment(userId, appointment.appointment_id, {
      status: this.selectedAppointmentStatus(),
      staff_id: null,
    })
      .pipe(finalize(() => this.updatingAppointment.set(false)))
      .subscribe({
        next: (response) => {
          this.appointment.update((current) => current
            ? { ...current, status: response.data.status, staff_id: response.data.staff_id }
            : current);
          this.toast.success('Appointment status updated successfully.');
        },
        error: (error: { error?: { message?: string } }) => {
          this.appointmentActionError.set(
            error?.error?.message ?? 'Unable to update the appointment.',
          );
        },
      });
  }

  escalateAppointment(): void {
    const appointment = this.appointment();
    const userId = this.sessionUser?.user_id ?? this.sessionUser?.userId;
    const staffId = this.selectedNurseId();
    if (!appointment || !userId || !staffId) {
      this.appointmentActionError.set('Select an available nurse before escalating.');
      return;
    }

    this.updatingAppointment.set(true);
    this.appointmentActionError.set(null);
    this.appointmentApi.updateNurseAppointment(userId, appointment.appointment_id, {
      status: 'RESCHEDULED',
      staff_id: staffId,
    })
      .pipe(finalize(() => this.updatingAppointment.set(false)))
      .subscribe({
        next: () => {
          this.toast.success('Appointment escalated to the selected nurse.');
          void this.router.navigate(['/transitional-care-nurse/appointments']);
        },
        error: (error: { error?: { message?: string } }) => {
          this.appointmentActionError.set(
            error?.error?.message ?? 'Unable to escalate the appointment.',
          );
        },
      });
  }

  private loadDetails(userId: number, appointmentId: number): void {
    this.loading.set(true);
    this.error.set(null);
    this.clinicalWarning.set(null);

    this.appointmentApi
      .getNurseAppointmentDetails(userId, appointmentId)
      .pipe(
        switchMap((response) => {
          const appointment = response.data;
          this.appointment.set(appointment);
          this.selectedAppointmentStatus.set(appointment.status);
          this.loadAvailableNurses(userId, appointment.appointment_id);
          if (!appointment.external_fhir_patient_id) {
            this.clinicalWarning.set('This patient is not linked to a FHIR record.');
            return of(this.emptyBundle(appointment));
          }

          return this.fhirApi.getPatientByFhirId(appointment.external_fhir_patient_id).pipe(
            switchMap((patientResponse) => {
              const patient = patientResponse.data;
              const monsterPatientId = patient['id'];
              if (typeof monsterPatientId !== 'string' || !monsterPatientId.trim()) {
                this.clinicalWarning.set('The linked FHIR patient record has no clinical identifier.');
                return of({ ...this.emptyBundle(appointment), patient });
              }

              return forkJoin({
                conditions: this.fhirApi.getPatientConditions(monsterPatientId).pipe(
                  map((result) => result.data.conditions),
                  catchError(() => of([])),
                ),
                medications: this.fhirApi.getPatientMedications(monsterPatientId).pipe(
                  map((result) => result.data.medications),
                  catchError(() => of([])),
                ),
              }).pipe(
                map((clinical) => ({ appointment, patient, ...clinical })),
              );
            }),
            catchError(() => {
              this.clinicalWarning.set('Patient clinical details could not be loaded.');
              return of(this.emptyBundle(appointment));
            }),
          );
        }),
        finalize(() => this.loading.set(false)),
      )
      .subscribe({
        next: (bundle: AppointmentDetailsBundle) => {
          this.patient.set(bundle.patient);
          this.conditions.set(bundle.conditions);
          this.medications.set(bundle.medications);
        },
        error: (error: { error?: { message?: string } }) => {
          this.error.set(error?.error?.message ?? 'Unable to load appointment details.');
        },
      });
  }

  private loadAvailableNurses(userId: number, appointmentId: number): void {
    this.loadingNurses.set(true);
    this.appointmentApi.getReassignmentOptions(userId, appointmentId)
      .pipe(finalize(() => this.loadingNurses.set(false)))
      .subscribe({
        next: (response) => this.availableNurses.set(response.data.staff),
        error: () => this.availableNurses.set([]),
      });
  }

  private emptyBundle(appointment: NurseAppointmentDetails): AppointmentDetailsBundle {
    return { appointment, patient: null, conditions: [], medications: [] };
  }

  private formatValue(value: unknown): string {
    if (value === null || value === undefined || value === '') {
      return 'Not available';
    }
    if (Array.isArray(value) || typeof value === 'object') {
      return JSON.stringify(value);
    }
    return String(value);
  }

  private filterByStatus(
    records: FhirRecord[],
    statusField: string,
    selectedStatus: string,
  ): FhirRecord[] {
    if (selectedStatus === 'all') {
      return records;
    }
    return records.filter(
      (record) => String(record[statusField] ?? '').toLowerCase() === selectedStatus,
    );
  }

  private statusOptions(records: FhirRecord[], statusField: string): string[] {
    return Array.from(
      new Set(
        records
          .map((record) => String(record[statusField] ?? '').trim().toLowerCase())
          .filter(Boolean),
      ),
    ).sort();
  }
}