import { ApiSuccessResponse } from './user';

export type CareManagerSectionKey =
  | 'dashboard'
  | 'caseload'
  | 'appointments'
  | 'outreach'
  | 'escalations'
  | 'follow_up'
  | 'program_performance';

export interface CareManagerMetric {
  label: string;
  value: string | number;
  tone: 'default' | 'positive' | 'warning' | 'critical';
}

export type CareManagerRow = Record<string, string | number | null>;

export interface CareManagerSection {
  metrics: CareManagerMetric[];
  rows: CareManagerRow[];
  detail_groups?: Record<string, CareManagerRow[]>;
}

export interface CareManagerAnalytics {
  generated_at: string;
  dashboard: CareManagerSection;
  caseload: CareManagerSection;
  appointments: CareManagerSection;
  outreach: CareManagerSection;
  escalations: CareManagerSection;
  follow_up: CareManagerSection;
  program_performance: CareManagerSection;
}

export type CareManagerAnalyticsResponse = ApiSuccessResponse<CareManagerAnalytics>;
