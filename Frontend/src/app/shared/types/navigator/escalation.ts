export type EscalationStatus = 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'CLOSED';

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
}

export interface EscalationQueueData {
  escalations: EscalationSummary[];
  count: number;
}