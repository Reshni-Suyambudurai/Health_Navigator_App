export interface SidebarTopic {
  label: string;
  badge?: number;
  route?: string;
}

export interface RoleSidebarConfig {
  label: string;
  route: string;
  topics: SidebarTopic[];
}

export const ROLE_SIDEBAR_CONFIG: RoleSidebarConfig[] = [
  {
    label: 'Care Manager',
    route: '/care-manager/dashboard',
    topics: [
      { label: 'Dashboard' },
      { label: 'Patient assignments' },
      { label: 'Care plans' },
      { label: 'Escalation queue' },
      { label: 'Outreach Events', route: '/care-manager/outreach-events' },
      { label: 'Reports' },
      { label: 'Activity log' },
    ],
  },
  {
    label: 'Population Health Manager',
    route: '/population-health-manager/dashboard',
    topics: [
      { label: 'Dashboard' },
      { label: 'Campaign queue' },
      { label: 'Cohort metrics' },
      { label: 'Outreach tracker', route: '/population-health-manager/outreach' },
      { label: 'Messages' },
      { label: 'Reports' },
      { label: 'Activity log' },
    ],
  },
  {
    label: 'Patient',
    route: '/patient/dashboard',
    topics: [
      { label: 'Dashboard' },
      { label: 'My medicine' },
      { label: 'Care plan' },
      { label: 'Appointments', route: '/patient/appointments' },
      { label: 'Care Team', route: '/patient/care-team' },
      { label: 'Talk to person', route: '/patient/talk-to-person' },
      { label: 'Activity log' },
    ],
  },
  {
    label: 'Transitional Care Nurse',
    route: '/transitional-care-nurse/dashboard',
    topics: [
      { label: 'Dashboard' },
      { label: 'Escalation queue' },
      { label: 'My patients', route: '/transitional-care-nurse/my-patient' },
      { label: 'Appointments', route: '/transitional-care-nurse/appointments' },
      { label: 'TCM tracker' },
      { label: 'Messages' },
      { label: 'Reports' },
      { label: 'Activity log' },
    ],
  },
  {
    label: 'Pharmacist',
    route: '/pharmacist/dashboard',
    topics: [
      { label: 'Dashboard' },
      { label: 'Medication queue' },
      { label: 'Refill follow-up' },
      { label: 'Adherence alerts' },
      { label: 'Patients' },
      { label: 'Reports' },
      { label: 'Activity log' },
    ],
  },
  {
    label: 'Social Worker',
    route: '/social-worker/dashboard',
    topics: [
      { label: 'Dashboard' },
      { label: 'Support queue' },
      { label: 'Resource referrals' },
      { label: 'Housing & transport' },
      { label: 'Messages' },
      { label: 'Reports' },
      { label: 'Activity log' },
    ],
  },
  {
    label: 'Clinical Governance',
    route: '/clinical-governance/dashboard',
    topics: [
      { label: 'Governance Overview' },
      { label: 'Safety Rules & Guardrails' },
      { label: 'Check-in Template' },
      { label: 'AI Safety Evaluations' },
      { label: 'Check-in Template Reviews', route: '/clinical-governance/checkin-template-reviews' },
      { label: 'Reports' },
      { label: 'Activity log' },
    ],
  },
  {
    label: 'System Administrator',
    route: '/system-admin/dashboard',
    topics: [
      { label: 'Dashboard', route: '/system-admin/dashboard' },
      { label: 'Organizations', route: '/system-admin/organization' },
      { label: 'Users and roles', route: '/system-admin/users-roles' },
      { label: 'Outreach Campaigns', route: '/system-admin/outreach-campaigns' },
      { label: 'Check-In template', route: '/system-admin/checkin-template' },
        { label: 'Outreach Events', route: '/system-admin/outreach-events' },
      { label: 'Audit trail', route: '/system-admin/audit-trail' }

    ],
  },
];
