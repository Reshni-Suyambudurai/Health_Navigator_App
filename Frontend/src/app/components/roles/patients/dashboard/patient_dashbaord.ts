import { CommonModule } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';
import { finalize } from 'rxjs';
import { UserApi } from '../../../../api/navigator/user.api';
import { getSessionUser } from '../../../../api/tokenstore';
import {
  CareTeamMember,
  PatientOnboardingState,
} from '../../../../shared/types/navigator/user';
import { AiChat } from '../ai-chat/ai-chat';
import { PatientOnboarding } from '../onboarding/patient-onboarding';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

@Component({
  selector: 'app-patient-dashbaord',
  standalone: true,
  imports: [CommonModule, AiChat, PatientOnboarding],
  templateUrl: './patient_dashbaord.html',
  styleUrl: './patient_dashbaord.scss',
})
export class PatientDashbaord implements OnInit {
  private readonly userApi = inject(UserApi);
  private readonly toast = inject(ToastState);

  readonly loading = signal(true);
  readonly state = signal<PatientOnboardingState | null>(null);
  readonly careTeam = signal<CareTeamMember[]>([]);

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

  private applyOnboardingState(onboardingState: PatientOnboardingState): void {
    this.state.set(onboardingState);

    if (onboardingState.onboarding_required) {
      this.toast.info('Please complete your patient onboarding before continuing.');
    } else {
      this.loadCareTeam();
    }
  }

  onboardingCompleted(onboardingState: PatientOnboardingState): void {
    this.state.set(onboardingState);
    this.loadCareTeam();
  }

  private loadCareTeam(): void {
    this.userApi.getActiveUsersByRole('TRANSITIONAL_CARE_NURSE').subscribe({
      next: (response) => this.careTeam.set(response.data.users),
      error: () => this.toast.warning('Care team details are temporarily unavailable.'),
    });
  }

  private extractErrorMessage(error: unknown): string {
    if (typeof error !== 'object' || error === null) {
      return 'We could not complete this request. Please try again.';
    }

    const response = error as { error?: { message?: string }; message?: string };
    return response.error?.message ?? response.message ?? 'We could not complete this request. Please try again.';
  }
}
