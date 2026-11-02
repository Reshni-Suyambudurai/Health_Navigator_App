import { ApiSuccessResponse } from './user';

export type RuleApprovalStatus = 'DRAFT' | 'PENDING' | 'APPROVED' | 'REJECTED';
export type RuleStatus = 'DRAFT' | 'ACTIVE' | 'INACTIVE' | 'RETIRED';

export interface GuardrailActivityEvent {
  audit_id: number;
  rule_id: number;
  action: string;
  details: Record<string, unknown> | string | null;
  created_at: string;
  actor_name: string | null;
}

export interface SafetyRule {
  rule_id: number;
  guardrail_id: number;
  guardrail_name: string;
  description: string;
  rule_name: string;
  category: string;
  urgency: string;
  handler_role_id: number | null;
  handler_role: string | null;
  action_type: string;
  status: RuleStatus;
  approval_status: RuleApprovalStatus;
  patient_response_template: string | null;
  target_queue_type: string | null;
  escalation_type: string | null;
  escalation_priority: string | null;
  created_by_user_id: number | null;
  created_by_name: string | null;
  creator_organization_id: number | null;
  approved_by_user_id: number | null;
  approved_by_name: string | null;
  approved_at: string | null;
  effective_from: string | null;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
  hit_count: number;
  last_hit_at: string | null;
  emergency_event_count: number;
  activity_history: GuardrailActivityEvent[];
}

export interface ClinicalGuardrail {
  guardrail_id: number;
  guardrail_name: string;
  description: string;
  rules: SafetyRule[];
}

export interface GuardrailHandlerRole {
  role_id: number;
  role_name: string;
}

export interface SafetyRulesOverview {
  summary: {
    total_guardrails: number;
    total_rules: number;
    active_rules: number;
    inactive_rules: number;
    pending_rules: number;
    draft_rules: number;
    rejected_rules: number;
    emergency_rules: number;
    hits_30_days: number;
  };
  guardrails: ClinicalGuardrail[];
  rules: SafetyRule[];
  handler_roles: GuardrailHandlerRole[];
}

export interface SafetyRulePayload {
  rule_name: string;
  category: string;
  urgency: string;
  handler_role_id: number | null;
  action_type: string;
  patient_response_template: string | null;
  target_queue_type: string | null;
  escalation_type: string | null;
  escalation_priority: string | null;
}

export interface SafetyRuleUpdate extends SafetyRulePayload {
  guardrail_name: string;
  description: string;
}

export interface ClinicalGuardrailCreate {
  guardrail_name: string;
  description: string;
  rules: SafetyRulePayload[];
}

export interface ScenarioTestResult {
  matched: boolean;
  rule: SafetyRule | null;
  side_effects_created: boolean;
}

export type SafetyRulesResponse = ApiSuccessResponse<SafetyRulesOverview>;
export type ScenarioTestResponse = ApiSuccessResponse<ScenarioTestResult>;
