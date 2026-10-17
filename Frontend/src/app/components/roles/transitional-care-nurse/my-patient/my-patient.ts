import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Component, OnInit, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { finalize } from 'rxjs';
import { getSessionUser } from '../../../../api/tokenstore';
import { FhirDataApi } from '../../../../api/patientfhir/fhir.data.api';
import { PatientEnrollmentApi } from '../../../../api/navigator/patient-enrollment.api';
import { PatientEnrollmentRecord } from '../../../../shared/types/navigator/patient-enrollment';
import {
  PatientIntakeMetadata,
  PatientOnboardFromFhirRequest,
} from '../../../../shared/types/navigator/patient-intake';
import { PatientIntakeApi } from '../../../../api/navigator/patient-intake.api';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

interface FhirPatientRow {
  id: string;
  fhir_patient_id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  phone: string;
  email: string;
}

@Component({
  imports: [CommonModule, FormsModule],
  selector: 'app-my-patient',
  styleUrl: './my-patient.scss',
  templateUrl: './my-patient.html',
})
export class MyPatient implements OnInit {
  private readonly enrollmentApi = inject(PatientEnrollmentApi);
  private readonly fhirApi = inject(FhirDataApi);
  private readonly intakeApi = inject(PatientIntakeApi);
  private readonly toast = inject(ToastState);
  private readonly router = inject(Router);
  private readonly sessionUser = getSessionUser();

  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly enrollments = signal<PatientEnrollmentRecord[]>([]);

  readonly metadataLoading = signal(false);
  readonly metadataError = signal<string | null>(null);
  readonly intakeMetadata = signal<PatientIntakeMetadata | null>(null);

  readonly searchFhirId = signal('');
  readonly searching = signal(false);
  readonly searchError = signal<string | null>(null);
  readonly searchedPatient = signal<FhirPatientRow | null>(null);

  readonly modalOpen = signal(false);
  readonly submitLoading = signal(false);
  readonly actionMessage = signal<string | null>(null);

  form: PatientOnboardFromFhirRequest = this.buildDefaultForm();

  ngOnInit(): void {
    this.loadEnrollments();
  }

  reload(): void {
    this.loadEnrollments();
  }

  onSearchEnter(event: Event): void {
    event.preventDefault();
    this.searchByFhirId();
  }

  searchByFhirId(): void {
    const value = this.searchFhirId().trim();
    if (!value) {
      this.searchError.set('Enter a FHIR patient ID.');
      this.searchedPatient.set(null);
      return;
    }

    this.searching.set(true);
    this.searchError.set(null);
    this.searchedPatient.set(null);
    this.actionMessage.set(null);

    this.loadMetadataIfNeeded();

    this.fhirApi
      .getPatientByFhirId(value)
      .pipe(finalize(() => this.searching.set(false)))
      .subscribe({
        next: (response) => {
          const raw = response.data as Record<string, unknown>;
          const row: FhirPatientRow = {
            id: String(raw['id'] ?? ''),
            fhir_patient_id: String(raw['fhir_patient_id'] ?? value),
            first_name: String(raw['first_name'] ?? ''),
            last_name: String(raw['last_name'] ?? ''),
            date_of_birth: this.toDateInput(raw['date_of_birth']),
            gender: String(raw['gender'] ?? 'UNKNOWN'),
            phone: String(raw['phone'] ?? ''),
            email: String(raw['email'] ?? ''),
          };
          this.searchedPatient.set(row);
        },
        error: () => {
          this.searchError.set('No patient found for the provided FHIR patient ID.');
        },
      });
  }

  openIntakeModal(): void {
    const patient = this.searchedPatient();
    const metadata = this.intakeMetadata();

    if (!patient || !metadata) {
      return;
    }

    this.form = {
      ...this.buildDefaultForm(),
      fhir_patient_id: patient.fhir_patient_id,
      first_name: patient.first_name,
      last_name: patient.last_name,
      date_of_birth: patient.date_of_birth,
      gender: this.pickOrFallback(metadata.genders, patient.gender, 'UNKNOWN'),
      phone: patient.phone || null,
      email: patient.email || null,
      organization_id: metadata.organizations[0]?.organization_id ?? 0,
      enrollment_program: metadata.enrollment_programs[0] ?? 'CARE_NAVIGATION',
      enrollment_status: metadata.enrollment_statuses[0] ?? 'ACTIVE',
      episode_type: metadata.episode_types[0] ?? 'POST_DISCHARGE',
      trigger_type: metadata.trigger_types[0] ?? 'MANUAL',
      episode_status: metadata.episode_statuses[0] ?? 'OPEN',
      preferred_contact_method: metadata.contact_methods[0] ?? 'SMS',
      risk_tier: metadata.risk_tiers[0] ?? 'UNKNOWN',
      owner_staff_id: metadata.owner_staff[0]?.staff_id ?? null,
    };

    this.modalOpen.set(true);
  }

  closeIntakeModal(): void {
    this.modalOpen.set(false);
  }

  openEnrollmentDetails(patientId: number): void {
    this.router.navigate(['/transitional-care-nurse/my-patient', patientId, 'details']);
  }

  submitIntake(): void {
    if (!this.intakeMetadata()) {
      return;
    }

    this.submitLoading.set(true);
    this.actionMessage.set(null);

    this.intakeApi
      .onboardFromFhir(this.form)
      .pipe(finalize(() => this.submitLoading.set(false)))
      .subscribe({
        next: (response) => {
          this.toast.success(response.message);
          this.actionMessage.set(response.message);
          this.closeIntakeModal();
          this.loadEnrollments();
        },
        error: (error: { error?: { message?: string } }) => {
          const message = error?.error?.message ?? 'Unable to create intake record right now.';
          this.toast.error(message);
          this.actionMessage.set(message);
        },
      });
  }

  private loadMetadata(): void {
    this.metadataLoading.set(true);
    this.metadataError.set(null);

    this.intakeApi
      .getMetadata()
      .pipe(finalize(() => this.metadataLoading.set(false)))
      .subscribe({
        next: (response) => this.intakeMetadata.set(response.data),
        error: () => this.metadataError.set('Unable to load intake dropdown values.'),
      });
  }

  private loadMetadataIfNeeded(): void {
    if (this.intakeMetadata() || this.metadataLoading()) {
      return;
    }

    this.loadMetadata();
  }

  private loadEnrollments(): void {
    this.loading.set(true);
    this.error.set(null);

    this.enrollmentApi
      .getEnrollments({ limit: 500 })
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (response) => this.enrollments.set(response.data.enrollments ?? []),
        error: () => this.error.set('Unable to load enrolled patients right now.'),
      });
  }

  private toDateInput(value: unknown): string {
    if (!value) {
      return '';
    }

    const text = String(value);
    return text.length >= 10 ? text.slice(0, 10) : text;
  }

  private pickOrFallback(options: string[], value: string, fallback: string): string {
    if (options.includes(value)) {
      return value;
    }

    if (options.includes(fallback)) {
      return fallback;
    }

    return options[0] ?? fallback;
  }

  private buildDefaultForm(): PatientOnboardFromFhirRequest {
    return {
      fhir_patient_id: '',
      organization_id: 0,
      enrollment_program: 'CARE_NAVIGATION',
      enrollment_status: 'ACTIVE',
      enrollment_date: null,
      created_by_user_id: this.sessionUser?.userId ?? null,
      episode_type: 'POST_DISCHARGE',
      trigger_type: 'MANUAL',
      trigger_reference: null,
      episode_status: 'OPEN',
      opened_at: null,
      owner_staff_id: null,
      first_name: '',
      last_name: '',
      email: null,
      date_of_birth: '',
      gender: 'UNKNOWN',
      phone: null,
      preferred_language: 'en-US',
      preferred_contact_method: 'SMS',
      emergency_contact_name: null,
      emergency_contact_phone: null,
      risk_tier: 'UNKNOWN',
      initial_password: 'Test@1234',
    };
  }
}
