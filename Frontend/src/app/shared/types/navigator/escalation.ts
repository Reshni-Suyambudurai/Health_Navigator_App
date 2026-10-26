export type EscalationStatus = 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'CLOSED';
export type EscalationActionType = 'MESSAGE_SENT' | 'CALL_PLACED' | 'TASK_CREATED';

export interface EscalationSummary {
  escalation_id: number;
  patient_id: number;
  patient_name: string;
  escalation_type: string;
  priority: string;
  reason: string;
  status: EscalationStatus;
  created_at: string;
  resolved_at: string | null;
  assigned_to: string | null;
}

export interface EscalationAction {
  action_id: number;
  action_type: string;
  notes: string | null;
  action_at: string;
}

export interface EscalationDetail extends EscalationSummary {
  patient_summary: string | null;
  actions: EscalationAction[];
  is_assigned_to_current_nurse: boolean;
  can_claim: boolean;
  can_act: boolean;
  is_emergency: boolean;
}

export interface EscalationQueueData {
  escalations: EscalationSummary[];
  count: number;
}