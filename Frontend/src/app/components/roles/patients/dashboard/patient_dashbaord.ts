import { CommonModule } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { UserApi } from '../../../../api/navigator/user.api';
import { getSessionUser } from '../../../../api/tokenstore';
import {
  CareTeamMember,
  PatientOnboardingState,
  PatientProfileUpdateRequest,
} from '../../../../shared/types/navigator/user';
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

@Component({
  selector: 'app-patient-dashbaord',
  standalone: true,
  imports: [CommonModule, FormsModule, AiChat],
  templateUrl: './patient_dashbaord.html',
  styleUrl: './patient_dashbaord.scss',
})
export class PatientDashbaord implements OnInit {
  private readonly userApi = inject(UserApi);
  private readonly toast = inject(ToastState);

  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly showOnboarding = signal(false);
  readonly step = signal<OnboardingStep>('profile');
  readonly state = signal<PatientOnboardingState | null>(null);
  readonly careTeam = signal<CareTeamMember[]>([]);
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
          this.loadCareTeam();
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
      this.loadCareTeam();
    }
  }

  private loadCareTeam(): void {
    this.userApi.getActiveUsersByRole('TRANSITIONAL_CARE_NURSE').subscribe({
      next: (response) => this.careTeam.set(response.data.users),
      error: () => this.toast.warning('Care team details are temporarily unavailable.'),
    });
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
