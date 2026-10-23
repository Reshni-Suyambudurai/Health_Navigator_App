export type ConversationSafetyCategory = 'emergency' | 'medication' | 'symptom' | 'clinical_scope' | null;

export interface ConversationMessage {
  message_id: number;
  sender: 'patient' | 'assistant';
  text: string;
  sent_at: string;
  safety_category: ConversationSafetyCategory;
  escalation_id: number | null;
  is_guardrail_override: boolean;
  source_labels?: string[];
}

export interface ConversationHistoryData {
  messages: ConversationMessage[];
  emergency_chat_paused: boolean;
}

export interface SendConversationMessageData {
  thread_id: number;
  patient_message: ConversationMessage;
  assistant_message: ConversationMessage;
  emergency_chat_paused: boolean;
}

export interface CareTeamRequestStatus {
  escalation_id: number;
  reason: string;
  status: 'OPEN' | 'ASSIGNED' | 'IN_PROGRESS' | 'RESOLVED' | 'CLOSED';
  created_at: string;
  resolved_at: string | null;
}