import { CommonModule } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, finalize, of, switchMap } from 'rxjs';

import { FhirDataApi } from '../../../../api/patientfhir/fhir.data.api';
import { UserApi } from '../../../../api/navigator/user.api';
import { getSessionUser } from '../../../../api/tokenstore';
import { FhirRecord } from '../../../../shared/types/patientfhir/fhir';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

const DIRECTIONS_UNAVAILABLE = 'Directions are not available in your record.';

@Component({
  selector: 'app-patient-medicines',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './patient-medicines.html',
  styleUrl: './patient-medicines.scss',
})
export class PatientMedicines implements OnInit {
  private readonly fhirApi = inject(FhirDataApi);
  private readonly userApi = inject(UserApi);
  private readonly router = inject(Router);
  private readonly toast = inject(ToastState);

  readonly medications = signal<FhirRecord[]>([]);
  readonly loading = signal(true);
  readonly remindersOn = signal(false);

  ngOnInit(): void {
    const sessionUser = getSessionUser();
    if (!sessionUser) {
      this.loading.set(false);
      this.toast.error('Your session has expired. Please sign in again.');
      return;
    }

    this.userApi
      .getPatientOnboarding(sessionUser.userId)
      .pipe(
        switchMap((response) => {
          const fhirPatientId = response.data.profile?.external_fhir_patient_id;
          if (!fhirPatientId) {
            return of(null);
          }

          return this.fhirApi.getPatientByFhirId(fhirPatientId).pipe(
            switchMap((patientResponse) => {
              const patient = patientResponse.data;
              const resolvedId = typeof patient['id'] === 'string' ? patient['id'] : fhirPatientId;
              return this.fhirApi.getPatientActiveMedications(resolvedId);
            })
          );
        }),
        catchError(() => {
          this.toast.warning('Your medication list is temporarily unavailable.');
          return of(null);
        }),
        finalize(() => this.loading.set(false))
      )
      .subscribe((response) => this.medications.set(response?.data.medications ?? []));
  }

  medicationName(medication: FhirRecord): string {
    return this.recordText(medication, ['medication_name', 'name', 'medication'], 'Medication');
  }

  dosage(medication: FhirRecord): string {
    return this.recordText(medication, ['dosage_text', 'dosage', 'instructions'], DIRECTIONS_UNAVAILABLE);
  }

  reason(medication: FhirRecord): string | null {
    const value = this.recordText(medication, ['reason'], '');
    return value || null;
  }

  startedOn(medication: FhirRecord): string | null {
    const date = this.recordText(medication, ['start_date', 'authored_on'], '');
    if (!date) {
      return null;
    }

    const parsed = new Date(date);
    return Number.isNaN(parsed.valueOf()) ? date : new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).format(parsed);
  }

  askAboutMedicine(medication: FhirRecord): void {
    const medicineName = this.medicationName(medication);
    const dosage = this.dosage(medication);
    const navigatorPrompt = dosage === DIRECTIONS_UNAVAILABLE
      ? `Can you explain what ${medicineName} is for? My record does not include directions for it.`
      : `Can you explain what ${medicineName} is for and the directions in my record: ${dosage}`;
    this.router.navigate(['/patient/dashboard'], {
      state: {
        navigatorPrompt,
      },
    });
  }

  toggleReminders(): void {
    this.remindersOn.set(!this.remindersOn());
    this.toast.info(this.remindersOn() ? 'Medication reminders are enabled for this browser session.' : 'Medication reminders are paused.');
  }

  printList(): void {
    window.print();
  }

  private recordText(record: FhirRecord, keys: string[], fallback: string): string {
    for (const key of keys) {
      const value = record[key];
      if (typeof value === 'string' && value.trim()) {
        return value;
      }
    }
    return fallback;
  }
}