import { Routes } from '@angular/router';
import { Login } from './components/auth/pages/login/login';
import { RoleShell } from './shared/layout/role-shell/role-shell';
import { ClinicalGovernanceDashbaord } from './components/roles/clinical-governance/dashboard/clinical_governance_dashbaord';
import { CareManagerDashbaord } from './components/roles/care-manager/dashboard/care_manager_dashbaord';
import { PopulationHealthManagerDashbaord } from './components/roles/population-health-manager/dashboard/population_health_manager_dashbaord';
import { PatientDashbaord } from './components/roles/patients/dashboard/patient_dashbaord';
import { PatientAppointments } from './components/roles/patients/appointments/appointments';
import { PatientCareTeam } from './components/roles/patients/care-team/care-team';
import { PatientTalkToPerson } from './components/roles/patients/talk-to-person/talk-to-person';
import { TransitionalCareNurseDashbaord } from './components/roles/transitional-care-nurse/dashboard/transitional_care_nurse_dashbaord';
import { MyPatient } from './components/roles/transitional-care-nurse/my-patient/my-patient';
import { MyPatientDetails } from './components/roles/transitional-care-nurse/my-patient-details/my-patient-details';
import { TransitionalCareNurseAppointments } from './components/roles/transitional-care-nurse/appointments/appointments';
import { AppointmentDetails } from './components/roles/transitional-care-nurse/appointment-details/appointment-details';
import { PharmacistDashbaord } from './components/roles/pharmacist/dashboard/pharmacist_dashbaord';
import { SocialWorkerDashbaord } from './components/roles/social-worker/dashboard/social_worker_dashbaord';
import { SystemAdminDashboard } from './components/roles/system-admin/dashboard/system-admin-dashboard';
import { authGuard } from './guards/guards/auth.guard';
import { roleAccessGuard } from './guards/guards/role-access.guard';

export const routes: Routes = [
  { path: '', redirectTo: '/login', pathMatch: 'full' },
  { path: 'login', component: Login },
  {
    path: '',
    component: RoleShell,
    canActivate: [authGuard],
    canActivateChild: [roleAccessGuard],
    children: [
      { path: '', redirectTo: 'clinical-governance/dashboard', pathMatch: 'full' },
      { path: 'clinical-governance/dashboard', component: ClinicalGovernanceDashbaord },
      { path: 'care-manager/dashboard', component: CareManagerDashbaord },
      { path: 'population-health-manager/dashboard', component: PopulationHealthManagerDashbaord },
      { path: 'patient/dashboard', component: PatientDashbaord },
      { path: 'patient/appointments', component: PatientAppointments },
      { path: 'patient/care-team', component: PatientCareTeam },
      { path: 'patient/talk-to-person', component: PatientTalkToPerson },
      { path: 'transitional-care-nurse/dashboard', component: TransitionalCareNurseDashbaord },
      { path: 'transitional-care-nurse/my-patient', component: MyPatient },
      { path: 'transitional-care-nurse/my-patient/:patientId/details', component: MyPatientDetails },
      { path: 'transitional-care-nurse/appointments', component: TransitionalCareNurseAppointments },
      { path: 'transitional-care-nurse/appointments/:appointmentId/details', component: AppointmentDetails },
      { path: 'pharmacist/dashboard', component: PharmacistDashbaord },
      { path: 'social-worker/dashboard', component: SocialWorkerDashbaord },
      { path: 'system-admin/dashboard', component: SystemAdminDashboard },
    ],
  },
  { path: 'home', redirectTo: '/clinical-governance/dashboard', pathMatch: 'full' },
];
