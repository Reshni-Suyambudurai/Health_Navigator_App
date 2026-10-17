import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError, map, switchMap } from 'rxjs/operators';
import { PatientProfileApi } from '../../../../api/navigator/patient-profile.api';
import { FhirDataApi } from '../../../../api/patientfhir/fhir.data.api';
import { PatientProfileRecord } from '../../../../shared/types/navigator/patient-profile';
import { FhirRecord } from '../../../../shared/types/patientfhir/fhir';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

type NullableApiResponse = { data?: FhirRecord | { conditions?: FhirRecord[]; medications?: FhirRecord[] } } | null;

interface PatientDetailsBundle {
  fhir: NullableApiResponse;
  summary: NullableApiResponse;
  conditions: NullableApiResponse;
  medications: NullableApiResponse;
}

@Component({
  selector: 'app-my-patient-details',
  imports: [CommonModule, RouterLink],
  templateUrl: './my-patient-details.html',
  styleUrl: './my-patient-details.scss',
})
export class MyPatientDetails implements OnInit {
  private readonly route = inject(ActivatedRoute);
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

  ngOnInit(): void {
    const patientIdParam = this.route.snapshot.paramMap.get('patientId');
    const patientId = Number(patientIdParam);

    if (!patientIdParam || Number.isNaN(patientId) || patientId <= 0) {
      this.error.set('Invalid patient selected.');
      return;
    }

    this.loadPatientDetails(patientId);
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

  private resolveFhirPatientId(fhirData: FhirRecord | null, fallbackId: string | null): string {
    const id = fhirData?.['id'];

    if (typeof id === 'string' && id.trim()) {
      return id;
    }

    return fallbackId?.trim() ?? '';
  }
}
