import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { UserApi } from '../../../../api/navigator/user.api';
import { getSessionUser } from '../../../../api/tokenstore';
import {
  PatientOnboardingState,
  PatientProfileUpdateRequest,
} from '../../../../shared/types/navigator/user';
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
  selector: 'app-patient-onboarding',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './patient-onboarding.html',
  styleUrl: './patient-onboarding.scss',
})
export class PatientOnboarding {
  private readonly userApi = inject(UserApi);
  private readonly toast = inject(ToastState);

  @Input({ required: true }) onboardingState!: PatientOnboardingState;
  @Output() completed = new EventEmitter<PatientOnboardingState>();

  readonly saving = signal(false);
  readonly step = signal<OnboardingStep>('profile');
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

  ngOnChanges(): void {
    const state = this.onboardingState;
    if (!state) {
      return;
    }

    this.profileForm.firstName = state.user.first_name ?? '';
    this.profileForm.lastName = state.user.last_name ?? '';
    this.profileForm.email = state.user.email ?? '';
    this.profileForm.phone = state.user.phone ?? '';

    const profile = state.profile;
    this.profileForm.dateOfBirth = profile?.date_of_birth ?? '';
    this.profileForm.gender = profile?.gender ?? '';
    this.profileForm.preferredLanguage = profile?.preferred_language ?? '';
    this.profileForm.preferredContactMethod = profile?.preferred_contact_method ?? '';
    this.profileForm.emergencyContactName = profile?.emergency_contact_name ?? '';
    this.profileForm.emergencyContactPhone = profile?.emergency_contact_phone ?? '';
  }

  get patientName(): string {
    const sessionUser = getSessionUser();
    return sessionUser ? `${sessionUser.firstName} ${sessionUser.lastName}` : 'Patient';
  }

  get profileOptions(): PatientOnboardingState['options'] {
    return this.onboardingState?.options ?? { genders: [], contact_methods: [] };
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
          this.onboardingState = response.data;
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
          this.completed.emit(response.data);
          this.toast.success('Consent recorded. Welcome to your patient dashboard.');
        },
        error: (error: unknown) => this.toast.error(this.extractErrorMessage(error)),
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
