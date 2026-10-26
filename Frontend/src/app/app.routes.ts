import { Routes } from '@angular/router';
import { Login } from './components/auth/pages/login/login';
import { RoleShell } from './shared/layout/role-shell/role-shell';
import { ClinicalGovernanceDashbaord } from './components/roles/clinical-governance/dashboard/clinical_governance_dashbaord';
import { CareManagerDashbaord } from './components/roles/care-manager/dashboard/care_manager_dashbaord';
import { PopulationHealthManagerDashbaord } from './components/roles/population-health-manager/dashboard/population_health_manager_dashbaord';
import { OutreachTracker } from './components/roles/population-health-manager/outreach-tracker/outreach-tracker';
import { PatientDashbaord } from './components/roles/patients/dashboard/patient_dashbaord';
import { PatientAppointments } from './components/roles/patients/appointments/appointments';
import { PatientCareTeam } from './components/roles/patients/care-team/care-team';
import { PatientTalkToPerson } from './components/roles/patients/talk-to-person/talk-to-person';
import { PatientMedicines } from './components/roles/patients/medicines/patient-medicines';
import { TransitionalCareNurseDashbaord } from './components/roles/transitional-care-nurse/dashboard/transitional_care_nurse_dashbaord';
import { EscalationQueue } from './components/roles/transitional-care-nurse/escalation-queue/escalation-queue';
import { MyPatient } from './components/roles/transitional-care-nurse/my-patient/my-patient';
import { MyPatientDetails } from './components/roles/transitional-care-nurse/my-patient-details/my-patient-details';
import { TransitionalCareNurseAppointments } from './components/roles/transitional-care-nurse/appointments/appointments';
import { AppointmentDetails } from './components/roles/transitional-care-nurse/appointment-details/appointment-details';
import { PharmacistDashbaord } from './components/roles/pharmacist/dashboard/pharmacist_dashbaord';
import { SocialWorkerDashbaord } from './components/roles/social-worker/dashboard/social_worker_dashbaord';
import { SystemAdminDashboard } from './components/roles/system-admin/dashboard/system-admin-dashboard';
import { SystemAdminOrganization } from './components/roles/system-admin/organization/organization';
import { SystemAdminUsersRoles } from './components/roles/system-admin/users-roles/users-roles';
import { SystemAdminAuditTrail } from './components/roles/system-admin/audit-trail/audit-trail';
import { SystemAdminOutreachCampaigns } from './components/roles/system-admin/outreach-campaigns/outreach-campaigns';
import { SystemAdminOutreachWorkflows } from './components/roles/system-admin/outreach-workflows/outreach-workflows';
import { SystemAdminOutreachEvents } from './components/roles/system-admin/outreach-events/outreach-events';
import { CareManagerOutreachEvents } from './components/roles/care-manager/outreach-events/outreach-events';
import { SystemAdminCheckinTemplate } from './components/roles/system-admin/checkin-template/checkin-template';
import { ClinicalCheckinTemplateReviews } from './components/roles/clinical-governance/checkin-template-reviews/checkin-template-reviews';
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
      { path: 'clinical-governance/checkin-template-reviews', component: ClinicalCheckinTemplateReviews },
      { path: 'care-manager/dashboard', component: CareManagerDashbaord },
      { path: 'care-manager/outreach-events', component: CareManagerOutreachEvents },
      { path: 'population-health-manager/dashboard', component: PopulationHealthManagerDashbaord },
      { path: 'population-health-manager/outreach', component: OutreachTracker },
      { path: 'patient/dashboard', component: PatientDashbaord },
      { path: 'patient/appointments', component: PatientAppointments },
      { path: 'patient/care-team', component: PatientCareTeam },
      { path: 'patient/talk-to-person', component: PatientTalkToPerson },
      { path: 'patient/medicines', component: PatientMedicines },
      { path: 'transitional-care-nurse/dashboard', component: TransitionalCareNurseDashbaord },
      { path: 'transitional-care-nurse/escalation-queue', component: EscalationQueue },
      { path: 'transitional-care-nurse/my-patient', component: MyPatient },
      { path: 'transitional-care-nurse/my-patient/:patientId/details', component: MyPatientDetails },
      { path: 'transitional-care-nurse/appointments', component: TransitionalCareNurseAppointments },
      { path: 'transitional-care-nurse/appointments/:appointmentId/details', component: AppointmentDetails },
      { path: 'pharmacist/dashboard', component: PharmacistDashbaord },
      { path: 'social-worker/dashboard', component: SocialWorkerDashbaord },
      { path: 'system-admin/dashboard', component: SystemAdminDashboard },
      { path: 'system-admin/users-roles', component: SystemAdminUsersRoles },
      { path: 'system-admin/organization', component: SystemAdminOrganization },
      { path: 'system-admin/outreach-campaigns', component: SystemAdminOutreachCampaigns },
      { path: 'system-admin/outreach-campaigns/:campaignId/workflows', component: SystemAdminOutreachWorkflows },
      { path: 'system-admin/outreach-events', component: SystemAdminOutreachEvents },
      { path: 'system-admin/checkin-template', component: SystemAdminCheckinTemplate },
      { path: 'system-admin/audit-trail', component: SystemAdminAuditTrail },
    ],
  },
  { path: 'home', redirectTo: '/clinical-governance/dashboard', pathMatch: 'full' },
];
