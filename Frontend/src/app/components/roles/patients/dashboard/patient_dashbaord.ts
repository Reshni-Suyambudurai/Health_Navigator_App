import { CommonModule } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { catchError, finalize, forkJoin, of, switchMap } from 'rxjs';
import { UserApi } from '../../../../api/navigator/user.api';
import { FhirDataApi } from '../../../../api/patientfhir/fhir.data.api';
import { ConversationApi } from '../../../../api/navigator/conversation.api';
import { getSessionUser } from '../../../../api/tokenstore';
import {
  CareTeamMember,
  PatientCareSnapshot,
  PatientOnboardingState,
  PatientProfileUpdateRequest,
} from '../../../../shared/types/navigator/user';
import { CareTeamRequestStatus } from '../../../../shared/types/navigator/conversation';
import { FhirRecord } from '../../../../shared/types/patientfhir/fhir';
import { AiChat } from '../ai-chat/ai-chat';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

type OnboardingStep = 'profile' | 'consent';

interface ProfileForm {
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  dateOfBirth: string;
  gender: string;
  preferredLanguage: string;
  preferredContactMethod: string;
  emergencyContactName: string;
  emergencyContactPhone: string;
}

interface CarePlanTask {
  title: string;
  detail: string;
  completed: boolean;
}

@Component({
  selector: 'app-patient-dashbaord',
  standalone: true,
  imports: [CommonModule, FormsModule, AiChat],
  templateUrl: './patient_dashbaord.html',
  styleUrl: './patient_dashbaord.scss',
})
export class PatientDashbaord implements OnInit {
  private readonly userApi = inject(UserApi);
  private readonly fhirApi = inject(FhirDataApi);
  private readonly conversationApi = inject(ConversationApi);
  private readonly toast = inject(ToastState);

  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly showOnboarding = signal(false);
  readonly step = signal<OnboardingStep>('profile');
  readonly state = signal<PatientOnboardingState | null>(null);
  readonly careSnapshot = signal<PatientCareSnapshot | null>(null);
  readonly careTeam = signal<CareTeamMember[]>([]);
  readonly careTeamRequests = signal<CareTeamRequestStatus[]>([]);
  readonly medications = signal<FhirRecord[]>([]);
  readonly activeCarePlan = signal<FhirRecord | null>(null);
  readonly carePlanLoading = signal(false);
  readonly visibleCareTeamPhoneId = signal<number | null>(null);
  readonly aiDisclosureAccepted = signal(false);
  readonly reminderAccepted = signal(false);

  readonly profileForm: ProfileForm = {
    firstName: '',
    lastName: '',
    email: '',
    phone: '',
    dateOfBirth: '',
    gender: '',
    preferredLanguage: '',
    preferredContactMethod: '',
    emergencyContactName: '',
    emergencyContactPhone: '',
  };

  get patientName(): string {
    const sessionUser = getSessionUser();
    return sessionUser ? `${sessionUser.firstName} ${sessionUser.lastName}` : 'Patient';
  }

  get profileOptions(): PatientOnboardingState['options'] {
    return this.state()?.options ?? { genders: [], contact_methods: [] };
  }

  get carePlanTitle(): string {
    return this.readRecordText(this.activeCarePlan(), ['title', 'name', 'description'], 'Your care plan');
  }

  get carePlanSubtitle(): string {
    return this.readRecordText(this.activeCarePlan(), ['status', 'intent', 'category'], 'Your current care plan');
  }

  get carePlanTasks(): CarePlanTask[] {
    const activities = this.activeCarePlan()?.['activity'] ?? this.activeCarePlan()?.['tasks'];
    if (!Array.isArray(activities)) {
      return [];
    }

    return activities.slice(0, 3).map((activity, index) => {
      const record = this.asRecord(activity);
      const detail = this.asRecord(record?.['detail']) ?? record;
      const status = this.readRecordText(detail, ['status'], 'pending').toLowerCase();

      return {
        title: this.readRecordText(detail, ['description', 'title', 'name'], `Care-plan task ${index + 1}`),
        detail: this.readRecordText(detail, ['scheduledString', 'timing', 'note'], 'Review with your care team'),
        completed: ['completed', 'done'].includes(status),
      };
    });
  }

    get carePlanProgress(): number {
      const tasks = this.carePlanTasks;
      if (tasks.length === 0) {
        return 0;
      }
      return Math.round((tasks.filter((task) => task.completed).length / tasks.length) * 100);
    }

    get latestCareTeamRequest(): CareTeamRequestStatus | null {
      return this.careTeamRequests()[0] ?? null;
    }

    get careTeamRequestLabel(): string {
      const status = this.latestCareTeamRequest?.status;
      if (!status) {
        return 'No open requests';
      }
      return status.replace('_', ' ').toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
    }

    formatRequestMessageTime(sentAt: string): string {
      return new Intl.DateTimeFormat('en-IN', {
        hour: 'numeric',
        minute: '2-digit',
        timeZone: 'Asia/Kolkata',
        timeZoneName: 'short',
      }).format(this.parseUtcTimestamp(sentAt));
    }

    private parseUtcTimestamp(timestamp: string): Date {
      const hasTimeZone = /(?:Z|[+-]\d{2}:\d{2})$/i.test(timestamp);
      return new Date(hasTimeZone ? timestamp : `${timestamp}Z`);
    }

    toggleCareTeamPhone(member: CareTeamMember): void {
      this.visibleCareTeamPhoneId.update((visibleMemberId) =>
        visibleMemberId === member.user_id ? null : member.user_id
      );
    }

  medicationName(medication: FhirRecord): string {
    return this.readRecordText(medication, ['medication_name', 'name', 'medication', 'display'], 'Medication');
  }

  medicationInstruction(medication: FhirRecord): string {
    return this.readRecordText(medication, ['dosage', 'dosage_text', 'instructions', 'frequency'], 'Directions are not available in your record.');
  }

  ngOnInit(): void {
    const sessionUser = getSessionUser();
    if (!sessionUser) {
      this.loading.set(false);
      this.toast.error('Your session has expired. Please sign in again.');
      return;
    }

    this.userApi
      .getPatientOnboarding(sessionUser.userId)
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (response) => this.applyOnboardingState(response.data),
        error: (error: unknown) => this.toast.error(this.extractErrorMessage(error)),
      });
  }

  submitProfile(): void {
    const sessionUser = getSessionUser();
    const missingFields = this.requiredProfileFields();

    if (!sessionUser) {
      this.toast.error('Your session has expired. Please sign in again.');
      return;
    }

    if (missingFields.length > 0) {
      this.toast.warning(`Please complete: ${missingFields.join(', ')}.`);
      return;
    }

    const payload: PatientProfileUpdateRequest = {
      first_name: this.profileForm.firstName.trim(),
      last_name: this.profileForm.lastName.trim(),
      email: this.profileForm.email.trim(),
      phone: this.profileForm.phone.trim(),
      date_of_birth: this.profileForm.dateOfBirth,
      gender: this.profileForm.gender,
      preferred_language: this.profileForm.preferredLanguage.trim(),
      preferred_contact_method: this.profileForm.preferredContactMethod,
      emergency_contact_name: this.profileForm.emergencyContactName.trim(),
      emergency_contact_phone: this.profileForm.emergencyContactPhone.trim(),
    };

    this.saving.set(true);
    this.userApi
      .updatePatientProfile(sessionUser.userId, payload)
      .pipe(finalize(() => this.saving.set(false)))
      .subscribe({
        next: (response) => {
          this.state.set(response.data);
          this.step.set('consent');
          this.toast.success('Profile details saved. Please review the AI consent.');
        },
        error: (error: unknown) => this.toast.error(this.extractErrorMessage(error)),
      });
  }

  submitConsent(): void {
    const sessionUser = getSessionUser();
    if (!sessionUser) {
      this.toast.error('Your session has expired. Please sign in again.');
      return;
    }

    if (!this.aiDisclosureAccepted() || !this.reminderAccepted()) {
      this.toast.warning('Please accept both required acknowledgements to continue.');
      return;
    }

    this.saving.set(true);
    this.userApi
      .submitPatientConsent(sessionUser.userId, {
        consent_text_version: 'v1.0',
        ai_disclosure_accepted: true,
        reminders_accepted: true,
      })
      .pipe(finalize(() => this.saving.set(false)))
      .subscribe({
        next: (response) => {
          this.state.set(response.data);
          this.showOnboarding.set(false);
          this.loadCareSnapshot();
          this.loadPatientFhirData(response.data.profile?.external_fhir_patient_id);
          this.toast.success('Consent recorded. Welcome to your patient dashboard.');
        },
        error: (error: unknown) => this.toast.error(this.extractErrorMessage(error)),
      });
  }

  private applyOnboardingState(onboardingState: PatientOnboardingState): void {
    this.state.set(onboardingState);
    this.profileForm.firstName = onboardingState.user.first_name ?? '';
    this.profileForm.lastName = onboardingState.user.last_name ?? '';
    this.profileForm.email = onboardingState.user.email ?? '';
    this.profileForm.phone = onboardingState.user.phone ?? '';

    const profile = onboardingState.profile;
    this.profileForm.dateOfBirth = profile?.date_of_birth ?? '';
    this.profileForm.gender = profile?.gender ?? '';
    this.profileForm.preferredLanguage = profile?.preferred_language ?? '';
    this.profileForm.preferredContactMethod = profile?.preferred_contact_method ?? '';
    this.profileForm.emergencyContactName = profile?.emergency_contact_name ?? '';
    this.profileForm.emergencyContactPhone = profile?.emergency_contact_phone ?? '';

    if (onboardingState.onboarding_required) {
      this.showOnboarding.set(true);
      this.step.set('profile');
      const missingFields = this.requiredProfileFields();
      if (missingFields.length > 0) {
        this.toast.warning(`Please complete: ${missingFields.join(', ')}.`);
      } else {
        this.toast.info('Please verify your profile details before continuing.');
      }
    } else {
      this.loadCareSnapshot();
      this.loadPatientFhirData(onboardingState.profile?.external_fhir_patient_id);
    }
  }

  private loadCareSnapshot(): void {
    const sessionUser = getSessionUser();
    if (!sessionUser) {
      return;
    }

    this.userApi.getPatientCareSnapshot(sessionUser.userId).subscribe({
      next: (response) => {
        this.careSnapshot.set(response.data);
        this.careTeam.set(response.data.care_team);
      },
      error: () => this.toast.warning('Your care-team details are temporarily unavailable.'),
    });

    this.conversationApi.getCareTeamRequests(sessionUser.userId).subscribe({
      next: (response) => this.careTeamRequests.set(response.data.requests),
      error: () => this.careTeamRequests.set([]),
    });
  }

  private loadPatientFhirData(externalFhirPatientId: string | null | undefined): void {
    if (!externalFhirPatientId) {
      this.medications.set([]);
      this.activeCarePlan.set(null);
      return;
    }

    this.carePlanLoading.set(true);
    this.fhirApi
      .getPatientByFhirId(externalFhirPatientId)
      .pipe(
        catchError(() => of(null)),
        switchMap((patientResponse) => {
          const fhirPatient = patientResponse?.data as FhirRecord | undefined;
          const fhirPatientId = this.resolveFhirPatientId(fhirPatient, externalFhirPatientId);

          if (!fhirPatientId) {
            return of({ medications: null, carePlans: null });
          }

          return forkJoin({
            medications: this.fhirApi.getPatientActiveMedications(fhirPatientId).pipe(catchError(() => of(null))),
            carePlans: this.fhirApi.getPatientActiveCarePlans(fhirPatientId).pipe(catchError(() => of(null))),
          });
        }),
        finalize(() => this.carePlanLoading.set(false))
      )
      .subscribe(({ medications, carePlans }) => {
        this.medications.set(medications?.data.medications ?? []);
        this.activeCarePlan.set(carePlans?.data.care_plans?.[0] ?? null);
      });
  }

  private resolveFhirPatientId(fhirPatient: FhirRecord | undefined, fallbackId: string): string {
    const fhirId = fhirPatient?.['id'];
    return typeof fhirId === 'string' && fhirId.trim() ? fhirId : fallbackId;
  }

  private readRecordText(record: FhirRecord | null | undefined, keys: string[], fallback: string): string {
    if (!record) {
      return fallback;
    }

    for (const key of keys) {
      const value = this.readValue(record[key]);
      if (value) {
        return value;
      }
    }

    return fallback;
  }

  private readValue(value: unknown): string | null {
    if (typeof value === 'string' && value.trim()) {
      return value;
    }

    if (typeof value === 'number') {
      return String(value);
    }

    const record = this.asRecord(value);
    if (record) {
      for (const key of ['text', 'display', 'value', 'code']) {
        const nestedValue = this.readValue(record[key]);
        if (nestedValue) {
          return nestedValue;
        }
      }
    }

    return null;
  }

  private asRecord(value: unknown): FhirRecord | null {
    return typeof value === 'object' && value !== null && !Array.isArray(value) ? (value as FhirRecord) : null;
  }

  private requiredProfileFields(): string[] {
    const fields: Array<[string, string]> = [
      ['First name', this.profileForm.firstName],
      ['Last name', this.profileForm.lastName],
      ['Email', this.profileForm.email],
      ['Mobile number', this.profileForm.phone],
      ['Date of birth', this.profileForm.dateOfBirth],
      ['Gender', this.profileForm.gender],
      ['Preferred language', this.profileForm.preferredLanguage],
      ['Preferred contact method', this.profileForm.preferredContactMethod],
      ['Emergency contact name', this.profileForm.emergencyContactName],
      ['Emergency contact phone', this.profileForm.emergencyContactPhone],
    ];

    return fields.filter(([, value]) => !value.trim()).map(([label]) => label);
  }

  private extractErrorMessage(error: unknown): string {
    if (typeof error !== 'object' || error === null) {
      return 'We could not complete this request. Please try again.';
    }

    const response = error as { error?: { message?: string }; message?: string };
    return response.error?.message ?? response.message ?? 'We could not complete this request. Please try again.';
  }
}
