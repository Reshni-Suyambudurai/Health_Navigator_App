import { ApiSuccessResponse } from './user';

export type TcmTrackerScope = 'ORGANIZATION' | 'ASSIGNED_PATIENTS';
export type TcmPatientCategory =
  | 'ACTIVE'
  | 'NEEDS_ATTENTION'
  | 'APPOINTMENT_ATTENTION'
  | 'REGULAR_APPOINTMENTS'
  | 'COMPLETE';

export interface TcmCampaign {
  campaign_id: number;
  campaign_name: string;
  status: string;
}

export interface TcmCampaignList {
  scope: TcmTrackerScope;
  campaigns: TcmCampaign[];
}

export interface TcmCategoryCounts {
  active: number;
  needs_attention: number;
  appointment_attention: number;
  regular_appointments: number;
  complete: number;
}

export interface TcmSummary {
  scope: TcmTrackerScope;
  eligible_patients: number;
  active_episodes: number;
  workflow_completion_rate: number;
  overdue_activities: number;
  patient_categories: TcmCategoryCounts;
}

export interface TcmAppointmentProgress {
  eligible: number;
  booked: number;
  completed: number;
  pending_booking: number;
  pending_completion: number;
  booking_percentage: number;
  completion_percentage: number;
}

export interface TcmWorkflowProgress {
  campaign_id: number;
  campaign_name: string;
  workflow_id: number;
  workflow_name: string;
  step_order: number;
  appointment_required: boolean;
  eligible_count: number;
  checkin: {
    completed: number;
    pending: number;
    completion_percentage: number;
  };
  appointment: TcmAppointmentProgress | null;
}

export interface TcmWorkflowProgressList {
  scope: TcmTrackerScope;
  workflows: TcmWorkflowProgress[];
}

export interface TcmAppointment {
  appointment_id: number;
  appointment_type: string;
  status: string;
  staff_id: number | null;
  appointment_datetime: string;
  created_at: string;
  location_or_channel: string | null;
}

export interface TcmEscalation {
  checkin_escalation_id: number;
  type: string;
  status: string;
  reason: string;
  assigned_staff: string | null;
  assigned_at: string | null;
  action_taken: string | null;
  resolution_notes: string | null;
}

export interface TcmPatientRow {
  campaign_id: number;
  campaign_name: string;
  episode_id: number;
  patient_id: number;
  patient_name: string;
  condition: string | null;
  discharge_date: string | null;
  episode_status: string;
  category: TcmPatientCategory;
  current_workflow: string | null;
  checkin_status: string;
  appointment_status: string;
  next_due_at: string | null;
  checkin_session_id: number | null;
  appointment: TcmAppointment | null;
  escalation: TcmEscalation | null;
  completed_at: string | null;
}

export interface TcmPatientPage {
  scope: TcmTrackerScope;
  category: TcmPatientCategory;
  total: number;
  page: number;
  page_size: number;
  patients: TcmPatientRow[];
}

export interface TcmWorkflowDetail {
  workflow_id: number;
  workflow_name: string;
  step_order: number;
  eligible: boolean;
  due_at: string;
  complete: boolean;
  appointment_required: boolean;
  checkin_session_id: number | null;
  checkin_status: string | null;
  checkin_completed_at: string | null;
  appointment: TcmAppointment | null;
}

export interface TcmActivity {
  type: string;
  label: string;
  timestamp: string | null;
}

export interface TcmPatientDetail extends TcmPatientRow {
  workflows: TcmWorkflowDetail[];
  appointments: TcmAppointment[];
  escalations: TcmEscalation[];
  recent_activity: TcmActivity[];
}

export type TcmCampaignListResponse = ApiSuccessResponse<TcmCampaignList>;
export type TcmSummaryResponse = ApiSuccessResponse<TcmSummary>;
export type TcmWorkflowProgressResponse = ApiSuccessResponse<TcmWorkflowProgressList>;
export type TcmPatientPageResponse = ApiSuccessResponse<TcmPatientPage>;
export type TcmPatientDetailResponse = ApiSuccessResponse<TcmPatientDetail>;