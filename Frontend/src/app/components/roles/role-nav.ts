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
      { label: 'Messages' },
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
      { label: 'Outreach tracker' },
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
      { label: 'Appointments' },
      { label: 'Care Team' },
      { label: 'Talk to person' },
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
      { label: 'Guardrail rules' },
      { label: 'Safety alerts' },
      { label: 'Rule compliance' },
      { label: 'Incidents' },
      {label : 'Audit trail'},
      { label: 'Reports' },
      { label: 'Activity log' },
    ],
  },
];
