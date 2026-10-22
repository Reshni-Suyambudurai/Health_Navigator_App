export type ConversationSafetyCategory = 'emergency' | 'medication_review' | null;

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
}

export interface SendConversationMessageData {
  thread_id: number;
  patient_message: ConversationMessage;
  assistant_message: ConversationMessage;
}