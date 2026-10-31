import { ApiSuccessResponse } from './user';

export type GovernancePeriod = 'today' | 'month' | 'custom';

export interface GovernanceMetric {
  label: string;
  value: number;
  tone: 'default' | 'positive' | 'warning' | 'critical';
}

export interface GovernancePeriodRange {
  key: GovernancePeriod;
  start_date: string;
  end_date: string;
}

export interface RedFlagOutcome {
  triggered_at: string;
  rule: string;
  patient_message: string;
  urgency: string;
  action_taken: string;
  emergency_instruction_sent: string;
  care_team_notified: string;
  event_status: string;
}

export interface RulePerformance {
  rule: string;
  category: string;
  urgency: string;
  action: string;
  status: string;
  trigger_count: number;
  last_triggered_at: string | null;
}

export interface EscalationDocumentation {
  escalation_id: number;
  patient: string;
  type: string;
  priority: string;
  status: string;
  action_count: number;
  documentation_issues: string;
  created_at: string;
}

export interface GovernanceAuditEntry {
  created_at: string;
  action: string;
  resource_type: string;
  resource_id: number | null;
  actor: string;
  details: string;
}

export interface ClinicalGovernanceAnalytics {
  generated_at: string;
  period: GovernancePeriodRange;
  kpis: GovernanceMetric[];
  escalation_summary: { metrics: GovernanceMetric[] };
  red_flag_outcomes: RedFlagOutcome[];
  rule_performance: RulePerformance[];
  documentation: EscalationDocumentation[];
  audit_history: GovernanceAuditEntry[];
  detection_accuracy: {
    available: boolean;
    message: string;
  };
}

export type ClinicalGovernanceAnalyticsResponse = ApiSuccessResponse<ClinicalGovernanceAnalytics>;