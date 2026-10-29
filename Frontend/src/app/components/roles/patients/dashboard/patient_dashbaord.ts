import { CommonModule } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';
import { catchError, finalize, forkJoin, of, switchMap } from 'rxjs';
import { UserApi } from '../../../../api/navigator/user.api';
import { FhirDataApi } from '../../../../api/patientfhir/fhir.data.api';
import { ConversationApi } from '../../../../api/navigator/conversation.api';
import { OutreachApi } from '../../../../api/navigator/outreach.api';
import { getSessionUser } from '../../../../api/tokenstore';
import {
  CareTeamMember,
  PatientCareSnapshot,
  PatientOnboardingState,
} from '../../../../shared/types/navigator/user';
import { CareTeamRequestStatus } from '../../../../shared/types/navigator/conversation';
import { FhirRecord } from '../../../../shared/types/patientfhir/fhir';
import { AiChat } from '../ai-chat/ai-chat';
import { PatientOnboarding } from '../onboarding/patient-onboarding';
import { ToastState } from '../../../../shared/ui/toast/toast-state';
import { CheckinSession } from '../../../../shared/types/navigator/outreach';

interface CarePlanTask {
  title: string;
  detail: string;
  completed: boolean;
}

@Component({
  selector: 'app-patient-dashbaord',
  standalone: true,
  imports: [CommonModule, AiChat, PatientOnboarding],
  templateUrl: './patient_dashbaord.html',
  styleUrl: './patient_dashbaord.scss',
})
export class PatientDashbaord implements OnInit {
  private readonly userApi = inject(UserApi);
  private readonly fhirApi = inject(FhirDataApi);
  private readonly conversationApi = inject(ConversationApi);
  private readonly outreachApi = inject(OutreachApi);
  private readonly toast = inject(ToastState);

  readonly loading = signal(true);
  readonly state = signal<PatientOnboardingState | null>(null);
  readonly careSnapshot = signal<PatientCareSnapshot | null>(null);
  readonly careTeam = signal<CareTeamMember[]>([]);
  readonly careTeamRequests = signal<CareTeamRequestStatus[]>([]);
  readonly medications = signal<FhirRecord[]>([]);
  readonly activeCarePlan = signal<FhirRecord | null>(null);
  readonly carePlanLoading = signal(false);
  readonly visibleCareTeamPhoneId = signal<number | null>(null);
  readonly pendingCheckins = signal<CheckinSession[]>([]);

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

    this.outreachApi.listSessions(sessionUser.userId).subscribe({
      next: (response) => this.pendingCheckins.set(response.data.sessions.filter((session) => ['PENDING', 'IN_PROGRESS', 'OVERDUE'].includes(session.session_status))),
      error: () => this.pendingCheckins.set([]),
    });
  }

  onboardingCompleted(onboardingState: PatientOnboardingState): void {
    this.state.set(onboardingState);
    this.loadCareSnapshot();
    this.loadPatientFhirData(onboardingState.profile?.external_fhir_patient_id);
  }

  private applyOnboardingState(onboardingState: PatientOnboardingState): void {
    this.state.set(onboardingState);

    if (onboardingState.onboarding_required) {
      this.toast.info('Please complete your patient onboarding before continuing.');
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

  private extractErrorMessage(error: unknown): string {
    if (typeof error !== 'object' || error === null) {
      return 'We could not complete this request. Please try again.';
    }

    const response = error as { error?: { message?: string }; message?: string };
    return response.error?.message ?? response.message ?? 'We could not complete this request. Please try again.';
  }
}
