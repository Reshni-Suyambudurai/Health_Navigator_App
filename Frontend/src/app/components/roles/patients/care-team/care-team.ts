import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { UserApi } from '../../../../api/navigator/user.api';
import { CareTeamMember } from '../../../../shared/types/navigator/user';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

@Component({
  selector: 'app-patient-care-team',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './care-team.html',
  styleUrl: './care-team.scss',
})
export class PatientCareTeam implements OnInit {
  private readonly userApi = inject(UserApi);
  private readonly toast = inject(ToastState);

  readonly careTeam = signal<CareTeamMember[]>([]);
  readonly loadingCareTeam = signal(false);

  ngOnInit(): void {
    this.loadCareTeam();
  }

  private loadCareTeam(): void {
    this.loadingCareTeam.set(true);
    this.userApi.getActiveUsersByRole('TRANSITIONAL_CARE_NURSE').subscribe({
      next: (response) => {
        this.careTeam.set(response.data.users);
        this.loadingCareTeam.set(false);
      },
      error: () => {
        this.loadingCareTeam.set(false);
        this.toast.warning('Care team details are temporarily unavailable.');
      },
    });
  }
}
