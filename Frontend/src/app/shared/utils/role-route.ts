const ROLE_ROUTE_BY_ID: Record<number, string> = {
  1: '/patient/dashboard',
  2: '/care-manager/dashboard',
  3: '/transitional-care-nurse/dashboard',
  4: '/pharmacist/dashboard',
  5: '/clinical-governance/dashboard',
  6: '/social-worker/dashboard',
  7: '/population-health-manager/dashboard',
  8: '/clinical-governance/dashboard',
  9: '/clinical-governance/dashboard',
};

const ROLE_ROUTE_BY_NAME: Record<string, string> = {
  PATIENT: '/patient/dashboard',
  CARE_MANAGER: '/care-manager/dashboard',
  TRANSITIONAL_CARE_NURSE: '/transitional-care-nurse/dashboard',
  PHARMACIST: '/pharmacist/dashboard',
  SCHEDULER: '/clinical-governance/dashboard',
  SOCIAL_WORKER: '/social-worker/dashboard',
  POPULATION_HEALTH_MANAGER: '/population-health-manager/dashboard',
  CLINICAL_GOVERNANCE: '/clinical-governance/dashboard',
  SYSTEM_ADMIN: '/clinical-governance/dashboard',
};

export function getDashboardRouteForRole(roleId: number, roleName?: string | null): string {
  if (ROLE_ROUTE_BY_ID[roleId]) {
    return ROLE_ROUTE_BY_ID[roleId];
  }

  if (roleName && ROLE_ROUTE_BY_NAME[roleName]) {
    return ROLE_ROUTE_BY_NAME[roleName];
  }

  return '/clinical-governance/dashboard';
}
