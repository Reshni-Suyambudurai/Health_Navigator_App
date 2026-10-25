import { ApiSuccessResponse } from './user';

export type CampaignStatus = 'DRAFT' | 'ACTIVE' | 'PAUSED' | 'COMPLETED' | 'ARCHIVED';
export type EventStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
export type DeliveryStatus = 'PENDING' | 'SENT' | 'DELIVERED' | 'FAILED' | 'RESPONDED';
export type FollowUpStatus = 'OPEN' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';

export interface OutreachCampaign {
  campaign_id: number;
  organization_id: number;
  campaign_name: string;
  campaign_type: string;
  target_cohort_definition: Record<string, unknown> | null;
  timezone: string;
  start_at: string | null;
  end_at: string | null;
  status: CampaignStatus;
  created_at: string;
}

export interface CampaignRequest {
  organization_id: number;
  campaign_name: string;
  campaign_type: string;
  timezone: string;
  status: CampaignStatus;
}

export interface OutreachWorkflow {
  workflow_id: number;
  campaign_id: number;
  step_order: number;
  step_name: string;
  trigger_type: string;
  trigger_anchor: string;
  trigger_offset_hours: number;
  channel: string;
  template_text: string | null;
  checkin_template_id: number | null;
  escalation_on_no_response: boolean;
  max_attempts: number;
  retry_interval_minutes: number;
  is_active: boolean;
}

export interface WorkflowRequest {
  step_order: number;
  step_name: string;
  trigger_type: string;
  trigger_anchor: string;
  trigger_offset_hours: number;
  channel: string;
  template_text: string | null;
  checkin_template_id: number | null;
  escalation_on_no_response: boolean;
  max_attempts: number;
  retry_interval_minutes: number;
  is_active: boolean;
}

export interface CheckinTemplate {
  checkin_template_id: number;
  organization_id: number;
  template_name: string;
  template_type: string;
  description: string | null;
  version: number;
  status: 'DRAFT' | 'ACTIVE' | 'INACTIVE';
  created_at: string;
}

export interface CheckinTemplateRequest {
  organization_id: number;
  template_name: string;
  template_type: string;
  description: string | null;
  version: number;
  status: 'DRAFT' | 'ACTIVE' | 'INACTIVE';
}

export interface CheckinQuestion {
  question_id: number;
  checkin_template_id: number;
  question_key: string;
  question_text: string;
  answer_type: string;
  options: unknown;
  display_order: number;
  is_required: boolean;
  is_active: boolean;
}

export interface CheckinQuestionRequest {
  question_key: string;
  question_text: string;
  answer_type: string;
  options: string[] | null;
  display_order: number;
  is_required: boolean;
  is_active: boolean;
}

export interface OutreachEvent {
  outreach_event_id: number;
  patient_id: number;
  campaign_id: number;
  workflow_id: number;
  appointment_id: number | null;
  channel: string;
  event_type: string;
  event_status: EventStatus;
  delivery_status: DeliveryStatus;
  scheduled_at: string;
  attempt_count: number;
  last_error: string | null;
}

export interface OutreachEventSummary extends OutreachEvent {
  patient_name: string;
  campaign_name: string;
  workflow_name: string;
  episode_id: number | null;
  last_activity_at: string | null;
}

export interface OutreachEventDetail extends OutreachEventSummary {
  delivery: {
    sent_at: string | null;
    responded_at: string | null;
    completed_at: string | null;
    attempt_count: number;
    last_error: string | null;
  };
  checkin_responses: {
    response_id: number;
    question_id: number;
    question_text: string;
    answer_text: string | null;
    answer_value: unknown;
    response_source: string;
    answered_at: string;
  }[];
  appointment: {
    appointment_id: number;
    appointment_type: string;
    appointment_datetime: string;
    end_datetime: string;
    status: string;
    location_or_channel: string | null;
    reason: string | null;
  } | null;
  follow_up_tasks: {
    follow_up_task_id: number;
    task_type: string;
    title: string;
    description: string | null;
    assigned_to_staff_id: number | null;
    due_at: string | null;
    priority: string;
    status: string;
  }[];
}

export interface OutreachEventFilters {
  campaign_id?: number;
  workflow_id?: number;
  campaign_name?: string;
  workflow_name?: string;
  event_status?: EventStatus;
  delivery_status?: DeliveryStatus;
  scheduled_from?: string;
  scheduled_to?: string;
  patient_search?: string;
  skip?: number;
  limit?: number;
}

export interface OutreachEventFilterOptions {
  campaigns: { campaign_id: number; campaign_name: string }[];
  workflows: { workflow_id: number; campaign_id: number; workflow_name: string }[];
}

export interface OutreachEventListData {
  events: OutreachEventSummary[];
  count: number;
  has_more: boolean;
}

export interface CheckinResponse {
  response_id: number;
  question_id: number;
  answer_text: string | null;
  answer_value: unknown;
  response_source: string;
  answered_at: string;
}

export interface CheckinSession {
  checkin_session_id: number;
  patient_id: number;
  outreach_event_id: number;
  checkin_template_id: number;
  session_status: string;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  responses: CheckinResponse[];
}

export interface AppointmentAction {
  appointment_action_id: number;
  appointment_id: number;
  action_taken: string;
  outcome: string | null;
  resolution_status: string;
  follow_up_required: boolean;
  follow_up_due_at: string | null;
  created_at: string;
}

export interface AppointmentActionRequest {
  contact_datetime: string | null;
  contact_method: string | null;
  action_taken: string;
  outcome: string | null;
  action_notes: string | null;
  resolution_status: string;
  follow_up_required: boolean;
  follow_up_notes: string | null;
  follow_up_due_at: string | null;
}

export interface FollowUpTask {
  follow_up_task_id: number;
  patient_id: number;
  appointment_id: number | null;
  task_type: string;
  title: string;
  description: string | null;
  assigned_to_staff_id: number | null;
  due_at: string | null;
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: FollowUpStatus;
  completion_notes: string | null;
}

export type CampaignListResponse = ApiSuccessResponse<{ campaigns: OutreachCampaign[]; count: number }>;
export type WorkflowListResponse = ApiSuccessResponse<{ workflows: OutreachWorkflow[]; count: number }>;
export type TemplateListResponse = ApiSuccessResponse<{ templates: CheckinTemplate[]; count: number }>;
export type QuestionListResponse = ApiSuccessResponse<{ questions: CheckinQuestion[]; count: number }>;
export type EventListResponse = ApiSuccessResponse<{ events: OutreachEvent[]; count: number }>;
export type ProtectedOutreachEventListResponse = ApiSuccessResponse<OutreachEventListData>;
export type ProtectedOutreachEventDetailResponse = ApiSuccessResponse<OutreachEventDetail>;
export type SessionListResponse = ApiSuccessResponse<{ sessions: CheckinSession[]; count: number }>;
export type AppointmentActionListResponse = ApiSuccessResponse<{ actions: AppointmentAction[]; count: number }>;
export type FollowUpTaskListResponse = ApiSuccessResponse<{ tasks: FollowUpTask[]; count: number }>;