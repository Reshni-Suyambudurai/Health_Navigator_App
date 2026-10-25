import { ApiSuccessResponse } from './user';

export type AdminCampaignType = 'POST_DISCHARGE' | 'MEDICATION_ADHERENCE' | 'APPOINTMENT_REMINDER';
export type AdminCampaignStatus = 'DRAFT' | 'ACTIVE' | 'PAUSED' | 'COMPLETED' | 'ARCHIVED';
export type EnrollmentStatus = 'ACTIVE' | 'INACTIVE' | 'COMPLETED' | 'WITHDRAWN' | 'CLOSED' | 'PAUSED';
export type EnrollmentProgram = 'TCM' | 'APCM' | 'RPM' | 'CHRONIC_CARE' | 'CARE_NAVIGATION' | 'TRANSITIONAL_CARE';
export type EpisodeType = 'POST_DISCHARGE_30_DAY' | 'MEDICATION_SUPPORT' | 'CHRONIC_CARE_FOLLOWUP' | 'APPOINTMENT_FOLLOWUP' | 'GENERAL_NAVIGATION' | 'POST_DISCHARGE' | 'CHRONIC_CARE';
export type EpisodeStatus = 'OPEN' | 'IN_PROGRESS' | 'ON_HOLD' | 'COMPLETED' | 'CLOSED';
export type WorkflowTriggerType = 'AFTER_DISCHARGE' | 'BEFORE_APPOINTMENT' | 'AFTER_EVENT';
export type WorkflowTriggerAnchor = 'DISCHARGE_DATETIME' | 'APPOINTMENT_DATETIME' | 'EVENT_DATETIME';
export type WorkflowChannel = 'SMS' | 'CALL' | 'PHONE' | 'EMAIL' | 'PORTAL';
export type OutreachActivityStatus = 'NEWLY_ELIGIBLE' | 'PENDING' | 'SENT' | 'COMPLETED' | 'FAILED';

export interface AdminCohortCriteria {
  enrollment_statuses: EnrollmentStatus[];
  enrollment_programs: EnrollmentProgram[];
  episode_types: EpisodeType[];
  episode_statuses: EpisodeStatus[];
  discharged_within_days: number;
}

export interface CampaignReadiness {
  ready: boolean;
  issues: string[];
  eligible_patient_count: number;
  workflow_count: number;
  active_workflow_count: number;
}

export interface AdminCohortPatient {
  patient_id: number;
  episode_id: number;
  external_fhir_patient_id: string | null;
  patient_name: string;
  enrollment_program: EnrollmentProgram;
  enrollment_status: EnrollmentStatus;
  enrollment_date: string | null;
  episode_type: EpisodeType;
  episode_status: EpisodeStatus;
  discharge_date: string | null;
  episode_created_at: string | null;
  outreach_status: OutreachActivityStatus;
  can_create_outreach: boolean;
  workflow_statuses: AdminWorkflowOutreachStatus[];
}

export interface AdminWorkflowOutreachStatus {
  workflow_id: number;
  workflow_name: string;
  status: OutreachActivityStatus;
  outreach_event_id: number | null;
}

export interface AdminOutreachSummary {
  cohort: number;
  eligible_for_workflow: number;
  outreach_created: number;
  newly_eligible: number;
  pending: number;
}

export interface AdminOutreachSelection {
  patient_id: number;
  episode_id: number;
}

export interface AdminCampaignRecord {
  campaign_id: number;
  organization_id: number;
  campaign_name: string;
  description: string | null;
  campaign_type: AdminCampaignType;
  cohort: AdminCohortCriteria;
  timezone: string;
  start_at: string | null;
  end_at: string | null;
  status: AdminCampaignStatus;
  auto_outreach_enabled: boolean;
  created_by: string | null;
  updated_by: string | null;
  created_at: string | null;
  updated_at: string | null;
  readiness: CampaignReadiness;
  workflows?: AdminWorkflowRecord[];
}

export interface AdminCampaignRequest {
  campaign_name: string;
  description: string | null;
  campaign_type: AdminCampaignType;
  timezone: string;
  start_at: string | null;
  end_at: string | null;
  cohort: AdminCohortCriteria;
}

export interface AdminWorkflowRecord {
  workflow_id: number;
  campaign_id: number;
  step_order: number;
  step_name: string;
  trigger_type: WorkflowTriggerType;
  trigger_anchor: WorkflowTriggerAnchor;
  trigger_offset_hours: number;
  channel: WorkflowChannel;
  template_text: string | null;
  checkin_template_id: number | null;
  escalation_on_no_response: boolean;
  max_attempts: number;
  retry_interval_minutes: number;
  is_active: boolean;
  template_name: string | null;
  configuration_status: 'READY' | 'INCOMPLETE' | 'INACTIVE';
}

export interface AdminWorkflowRequest {
  step_order: number;
  step_name: string;
  trigger_type: WorkflowTriggerType;
  trigger_anchor: WorkflowTriggerAnchor;
  trigger_offset_hours: number;
  channel: WorkflowChannel;
  template_text: string | null;
  checkin_template_id: number;
  escalation_on_no_response: boolean;
  max_attempts: number;
  retry_interval_minutes: number;
  is_active: boolean;
}

export interface AdminTemplateOption {
  checkin_template_id: number;
  template_name: string;
  template_type: string;
  version: number;
  status: 'ACTIVE';
}

export interface AdminCampaignFilters {
  skip?: number;
  limit?: number;
  status?: AdminCampaignStatus | '';
  campaign_type?: AdminCampaignType | '';
}

export type AdminCampaignListResponse = ApiSuccessResponse<{ campaigns: AdminCampaignRecord[]; count: number }>;
export type AdminCampaignResponse = ApiSuccessResponse<AdminCampaignRecord>;
export type AdminCohortMembersResponse = ApiSuccessResponse<{
  campaign_id: number;
  campaign_name: string;
  patients: AdminCohortPatient[];
  count: number;
  skip: number;
  limit: number;
  has_more: boolean;
  outreach_summary: AdminOutreachSummary;
}>;
export type AdminCreateOutreachResponse = ApiSuccessResponse<{
  requested: number;
  created: number;
  already_existing: number;
  no_longer_eligible: number;
  created_occurrences: number;
  outreach_event_ids: number[];
}>;
export type AdminWorkflowListResponse = ApiSuccessResponse<{ campaign: AdminCampaignRecord; workflows: AdminWorkflowRecord[]; count: number }>;
export type AdminWorkflowResponse = ApiSuccessResponse<AdminWorkflowRecord>;
export type AdminTemplateListResponse = ApiSuccessResponse<{ templates: AdminTemplateOption[] }>;