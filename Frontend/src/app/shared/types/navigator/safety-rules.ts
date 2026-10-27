import { ApiSuccessResponse } from './user';

export interface SafetyRuleMatcher {
  matcher_id: number;
  rule_id: number;
  pattern: string;
  match_type: string;
  priority: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SafetyRuleApprovalEvent {
  audit_id: number;
  rule_id: number;
  action: string;
  details: { event_type?: string; note?: string; previous_status?: string; rule_name?: string } | string | null;
  created_at: string;
  actor_name: string | null;
}

export interface SafetyRule {
  rule_id: number;
  guardrail_id: number;
  guardrail_name: string;
  guardrail_markdown: string;
  rule_name: string;
  category: string;
  urgency: string;
  action_type: string;
  status: string;
  patient_response_template: string | null;
  target_queue_type: string | null;
  escalation_type: string | null;
  escalation_priority: string | null;
  created_at: string;
  updated_at: string;
  hit_count: number;
  last_hit_at: string | null;
  emergency_event_count: number;
  version: string;
  last_reviewed_at: string;
  matchers: SafetyRuleMatcher[];
  approval_history: SafetyRuleApprovalEvent[];
}

export interface SafetyRulesOverview {
  summary: { total_rules: number; active_rules: number; draft_rules: number; emergency_rules: number; hits_30_days: number };
  rules: SafetyRule[];
}

export interface ScenarioTestResult {
  matched: boolean;
  rule: SafetyRule | null;
  matcher: SafetyRuleMatcher | null;
  side_effects_created: boolean;
}

export type SafetyRulesResponse = ApiSuccessResponse<SafetyRulesOverview>;
export type ScenarioTestResponse = ApiSuccessResponse<ScenarioTestResult>;
