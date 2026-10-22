import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { finalize } from 'rxjs/operators';
import { catchError, map, switchMap } from 'rxjs/operators';
import { PatientEnrollmentApi } from '../../../../api/navigator/patient-enrollment.api';
import { PatientProfileApi } from '../../../../api/navigator/patient-profile.api';
import { FhirDataApi } from '../../../../api/patientfhir/fhir.data.api';
import {
  PatientCareDetailsData,
  PatientCareDetailsUpsertRequest,
} from '../../../../shared/types/navigator/patient-enrollment';
import { PatientProfileRecord } from '../../../../shared/types/navigator/patient-profile';
import { FhirRecord } from '../../../../shared/types/patientfhir/fhir';
import { Breadcrumb, BreadcrumbItem } from '../../../../shared/ui/breadcrumb/breadcrumb';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

type NullableApiResponse = { data?: FhirRecord | { conditions?: FhirRecord[]; medications?: FhirRecord[] } } | null;

interface PatientDetailsBundle {
  fhir: NullableApiResponse;
  summary: NullableApiResponse;
  conditions: NullableApiResponse;
  medications: NullableApiResponse;
}

interface CareEditForm {
  organization_id: number | null;
  risk_tier: string;
  owner_staff_id: number | null;
  enrollment_program: string;
  enrollment_status: string;
  close_date: string;
  closed_reason: string;
  episode_type: string;
  trigger_type: string;
  episode_status: string;
}

@Component({
  selector: 'app-my-patient-details',
  imports: [CommonModule, FormsModule, Breadcrumb],
  templateUrl: './my-patient-details.html',
  styleUrl: './my-patient-details.scss',
})
export class MyPatientDetails implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly enrollmentApi = inject(PatientEnrollmentApi);
  private readonly profileApi = inject(PatientProfileApi);
  private readonly fhirApi = inject(FhirDataApi);
  private readonly toast = inject(ToastState);

  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly profile = signal<PatientProfileRecord | null>(null);
  readonly fhirDetails = signal<FhirRecord | null>(null);
  readonly patientContextSummary = signal<FhirRecord | null>(null);
  readonly conditions = signal<FhirRecord[]>([]);
  readonly medications = signal<FhirRecord[]>([]);
  readonly patientId = signal<number | null>(null);
  readonly careDetails = signal<PatientCareDetailsData | null>(null);
  readonly editCareOpen = signal(false);
  readonly closeCareFieldsOpen = signal(false);
  readonly savingCare = signal(false);
  readonly careForm = signal<CareEditForm | null>(null);
  readonly riskTierOptions = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL', 'UNKNOWN'];
  readonly enrollmentProgramOptions = ['TCM', 'APCM', 'RPM', 'CHRONIC_CARE', 'CARE_NAVIGATION', 'TRANSITIONAL_CARE'];
  readonly enrollmentStatusOptions = ['ACTIVE', 'PAUSED', 'COMPLETED', 'INACTIVE', 'WITHDRAWN'];
  readonly episodeTypeOptions = [
    'POST_DISCHARGE_30_DAY',
    'MEDICATION_SUPPORT',
    'CHRONIC_CARE_FOLLOWUP',
    'APPOINTMENT_FOLLOWUP',
    'GENERAL_NAVIGATION',
    'POST_DISCHARGE',
    'CHRONIC_CARE',
  ];
  readonly triggerTypeOptions = [
    'DISCHARGE',
    'PATIENT_REQUEST',
    'MEDICATION_CONCERN',
    'SCHEDULED_OUTREACH',
    'STAFF_REFERRAL',
    'FHIR_ENCOUNTER',
    'FHIR_OBSERVATION',
    'MANUAL',
    'CAMPAIGN',
  ];
  readonly episodeStatusOptions = ['OPEN', 'IN_PROGRESS', 'ON_HOLD', 'COMPLETED', 'CLOSED'];
  readonly breadcrumbs: BreadcrumbItem[] = [
    { label: 'My Patients', route: '/transitional-care-nurse/my-patient' },
    { label: 'Patient Details' },
  ];

  ngOnInit(): void {
    const patientIdParam = this.route.snapshot.paramMap.get('patientId');
    const patientId = Number(patientIdParam);

    if (!patientIdParam || Number.isNaN(patientId) || patientId <= 0) {
      this.error.set('Invalid patient selected.');
      return;
    }

    this.patientId.set(patientId);
    this.loadEnrollment(patientId);
    this.loadPatientDetails(patientId);
  }

  openEditCareDialog(): void {
    const details = this.careDetails();
    const enrollment = details?.enrollment;
    const episode = details?.episode;

    this.careForm.set({
      organization_id: enrollment?.organization_id ?? null,
      risk_tier: details?.risk_tier ?? '',
      owner_staff_id: episode?.owner_staff_id ?? null,
      enrollment_program: enrollment?.enrollment_program ?? '',
      enrollment_status: enrollment?.enrollment_status ?? '',
      close_date: this.dateInputValue(enrollment?.close_date),
      closed_reason: enrollment?.closed_reason ?? '',
      episode_type: episode?.episode_type ?? '',
      trigger_type: episode?.trigger_type ?? '',
      episode_status: episode?.episode_status ?? '',
    });
    this.closeCareFieldsOpen.set(false);
    this.editCareOpen.set(true);
  }

  openCloseCareFields(): void {
    const form = this.careForm();
    if (form && !form.close_date) {
      this.updateCareForm('close_date', this.todayAsInputValue());
    }
    this.closeCareFieldsOpen.set(true);
  }

  closeEditCareDialog(): void {
    if (!this.savingCare()) {
      this.editCareOpen.set(false);
    }
  }

  updateCareForm(field: keyof CareEditForm, value: string | number | null): void {
    this.careForm.update((form) => (form ? { ...form, [field]: value } as CareEditForm : form));
  }

  saveCareDetails(): void {
    const patientId = this.patientId();
    const form = this.careForm();

    if (!patientId || !form) {
      return;
    }

    if (this.closeCareFieldsOpen() && !form.closed_reason.trim()) {
      this.toast.warning('Enter a reason before closing care.');
      return;
    }

    if (
      !form.risk_tier ||
      !form.enrollment_program ||
      !form.enrollment_status ||
      !form.episode_type ||
      !form.trigger_type ||
      !form.episode_status
    ) {
      this.toast.warning('Select a value for every care detail field before saving.');
      return;
    }

    this.savingCare.set(true);
    this.enrollmentApi
      .upsertCareDetails(patientId, this.toCareDetailsPayload(form))
      .pipe(finalize(() => this.savingCare.set(false)))
      .subscribe({
        next: (response) => {
          this.careDetails.set(response.data);
          this.editCareOpen.set(false);
          this.toast.success('Care details saved successfully.');
        },
        error: (error: { error?: { message?: string } }) => {
          this.toast.error(error?.error?.message ?? 'Unable to save care details.');
        },
      });
  }

  get fhirEntries(): Array<[string, unknown]> {
    const data = this.fhirDetails();
    return data ? Object.entries(data) : [];
  }

  get summaryEntries(): Array<[string, unknown]> {
    const data = this.patientContextSummary();
    return data ? Object.entries(data) : [];
  }

  get patientName(): string {
    const data = this.fhirDetails();
    if (!data) {
      return 'Patient';
    }

    const firstName = data['first_name'] ?? data['given_name'];
    const lastName = data['last_name'] ?? data['family_name'];
    const combinedName = [firstName, lastName].filter((value) => typeof value === 'string' && value.trim()).join(' ');

    if (combinedName) {
      return combinedName;
    }

    const name = data['name'];
    if (typeof name === 'string' && name.trim()) {
      return name;
    }

    if (Array.isArray(name) && name.length > 0) {
      const firstNameEntry = name[0];
      if (typeof firstNameEntry === 'string') {
        return firstNameEntry;
      }

      if (typeof firstNameEntry === 'object' && firstNameEntry !== null) {
        const nameRecord = firstNameEntry as Record<string, unknown>;
        const given = Array.isArray(nameRecord['given']) ? nameRecord['given'].join(' ') : nameRecord['given'];
        const family = nameRecord['family'];
        return [given, family].filter((value) => typeof value === 'string' && value.trim()).join(' ') || 'Patient';
      }
    }

    return 'Patient';
  }

  get hasClinicalData(): boolean {
    return this.conditions().length > 0 || this.medications().length > 0;
  }

  get conditionColumns(): string[] {
    return this.tableColumns(this.conditions());
  }

  get medicationColumns(): string[] {
    return this.tableColumns(this.medications());
  }

  previewEntries(record: FhirRecord, limit = 8): Array<[string, string]> {
    return Object.entries(record)
      .filter(([key]) => !this.isIdentifierField(key))
      .slice(0, limit)
      .map(([key, value]) => [key, this.formatValue(value)]);
  }

  statusClass(value: unknown): string {
    const status = String(value ?? '').toLowerCase().replace(/\s+/g, '_');

    if (['active', 'stable', 'resolved', 'completed', 'normal', 'current'].includes(status)) {
      return 'status-positive';
    }

    if (['critical', 'high', 'severe', 'urgent', 'danger'].includes(status)) {
      return 'status-critical';
    }

    if (['inactive', 'discontinued', 'cancelled', 'abnormal', 'low'].includes(status)) {
      return 'status-negative';
    }

    if (['pending', 'in_progress', 'unknown', 'on_hold'].includes(status)) {
      return 'status-warning';
    }

    return '';
  }

  recordValue(record: FhirRecord, key: string): string {
    return this.formatValue(record[key]);
  }

  private tableColumns(records: FhirRecord[]): string[] {
    return Array.from(
      new Set(records.flatMap((record) => Object.keys(record).filter((key) => !this.isIdentifierField(key))))
    ).slice(0, 8);
  }

  private isIdentifierField(key: string): boolean {
    const normalizedKey = key.toLowerCase();
    return normalizedKey === 'id' || normalizedKey.endsWith('_id') || normalizedKey === 'patientid';
  }

  formatValue(value: unknown): string {
    if (value === null || value === undefined || value === '') {
      return 'N/A';
    }

    if (Array.isArray(value) || typeof value === 'object') {
      try {
        return JSON.stringify(value);
      } catch {
        return String(value);
      }
    }

    return String(value);
  }

  private loadPatientDetails(patientId: number): void {
    this.loading.set(true);
    this.error.set(null);
    this.patientContextSummary.set(null);
    this.conditions.set([]);
    this.medications.set([]);

    this.profileApi
      .getPatientProfile(patientId)
      .pipe(
        switchMap((profileResponse) => {
          const profile = profileResponse.data;
          this.profile.set(profile);

          if (!profile.external_fhir_patient_id) {
            return of<PatientDetailsBundle>({
              fhir: null,
              summary: null,
              conditions: null,
              medications: null,
            });
          }

          return this.fhirApi.getPatientByFhirId(profile.external_fhir_patient_id).pipe(
            catchError(() => {
              this.toast.warning('FHIR details could not be loaded.');
              return of(null);
            }),
            switchMap((patientResponse) => {
              const fhirPatientData = patientResponse?.data as FhirRecord | null;
              const fhirPatientId = this.resolveFhirPatientId(
                fhirPatientData,
                profile.external_fhir_patient_id
              );

              if (!fhirPatientId) {
                return of<PatientDetailsBundle>({
                  fhir: patientResponse,
                  summary: null,
                  conditions: null,
                  medications: null,
                });
              }

              return forkJoin({
                fhir: of(patientResponse),
                summary: this.fhirApi.getPatientContextSummary(fhirPatientId).pipe(catchError(() => of(null))),
                conditions: this.fhirApi.getPatientConditions(fhirPatientId).pipe(catchError(() => of(null))),
                medications: this.fhirApi.getPatientMedications(fhirPatientId).pipe(catchError(() => of(null))),
              }).pipe(map((bundle): PatientDetailsBundle => bundle));
            })
          );
        })
      )
      .subscribe({
        next: (result: PatientDetailsBundle) => {
          this.fhirDetails.set(result.fhir?.data ?? null);
          this.patientContextSummary.set((result.summary?.data as FhirRecord | undefined) ?? null);

          const conditionsData = (result.conditions?.data as { conditions?: FhirRecord[] } | undefined) ?? {};
          const medicationsData = (result.medications?.data as { medications?: FhirRecord[] } | undefined) ?? {};

          this.conditions.set(conditionsData.conditions ?? []);
          this.medications.set(medicationsData.medications ?? []);

          if (this.fhirDetails() && !this.patientContextSummary()) {
            this.toast.info('Patient context summary is unavailable at the moment.');
          }

          this.loading.set(false);
        },
        error: (error: { error?: { message?: string } }) => {
          this.loading.set(false);
          this.error.set(error?.error?.message ?? 'Unable to load patient details right now.');
        },
      });
  }

  private loadEnrollment(patientId: number): void {
    this.enrollmentApi.getCareDetails(patientId).subscribe({
      next: (response) => {
        this.careDetails.set(response.data);
      },
      error: () => {
        this.toast.warning('Care details could not be loaded. You can still create them.');
        this.careDetails.set({ risk_tier: null, enrollment: null, episode: null, owner_staff: [] });
      },
    });
  }

  private toCareDetailsPayload(form: CareEditForm): PatientCareDetailsUpsertRequest {
    const closingCare = this.closeCareFieldsOpen();
    const closeDate = closingCare
      ? form.close_date || this.todayAsInputValue()
      : this.careDetails()?.enrollment?.close_date ?? null;
    const closeDateInput = closeDate ?? '';

    return {
      organization_id: form.organization_id,
      risk_tier: form.risk_tier || null,
      owner_staff_id: form.owner_staff_id,
      enrollment_program: form.enrollment_program,
      enrollment_status: closingCare ? 'CLOSED' : form.enrollment_status,
      enrollment_date: this.careDetails()?.enrollment?.enrollment_date ?? null,
      close_date: closingCare ? this.dateTimeValue(closeDateInput) : closeDate,
      closed_reason: form.closed_reason.trim() || null,
      episode_type: form.episode_type,
      trigger_type: form.trigger_type,
      episode_status: closingCare ? 'CLOSED' : form.episode_status,
      opened_at: this.careDetails()?.episode?.opened_at ?? null,
      closed_at: this.dateTimeValue(
        closingCare ? closeDateInput : this.dateInputValue(this.careDetails()?.episode?.closed_at)
      ),
    };
  }

  private todayAsInputValue(): string {
    return new Date().toISOString().slice(0, 10);
  }

  private dateInputValue(value: string | null | undefined): string {
    return value ? value.slice(0, 10) : '';
  }

  private dateTimeValue(value: string): string | null {
    return value ? `${value}T00:00:00` : null;
  }

  private resolveFhirPatientId(fhirData: FhirRecord | null, fallbackId: string | null): string {
    const id = fhirData?.['id'];

    if (typeof id === 'string' && id.trim()) {
      return id;
    }

    return fallbackId?.trim() ?? '';
  }
}
