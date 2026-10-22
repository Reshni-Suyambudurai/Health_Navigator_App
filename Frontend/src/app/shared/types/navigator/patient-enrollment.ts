export interface ApiSuccessResponse<TData> {
  status: 'success' | string;
  message: string;
  data: TData;
}

export interface PatientEnrollmentRecord {
  enrollment_id: number;
  patient_id: number;
  first_name: string;
  last_name: string;
  organization_id: number;
  enrollment_program: string;
  enrollment_status: string;
  enrollment_date: string | null;
  last_login_at: string | null;
  episode_type: string | null;
  consent_status: string | null;
  consent_captured_at: string | null;
  captured_channel: string | null;
}

export interface PatientEnrollmentListData {
  enrollments: PatientEnrollmentRecord[];
  count: number;
}

export interface PatientEnrollmentListParams {
  patient_id?: number;
  organization_id?: number;
  status_filter?: string;
  skip?: number;
  limit?: number;
}

export interface PatientEnrollmentStatusUpdateRequest {
  enrollment_status: string;
  close_date?: string | null;
  closed_reason?: string | null;
}

export interface PatientEnrollmentStatusUpdateData {
  enrollment_id: number;
  enrollment_status: string;
  close_date: string | null;
  closed_reason: string | null;
}

export interface PatientCareEnrollment {
  enrollment_id: number;
  patient_id: number;
  organization_id: number;
  enrollment_program: string;
  enrollment_status: string;
  enrollment_date: string | null;
  close_date: string | null;
  closed_reason: string | null;
}

export interface PatientCareEpisode {
  episode_id: number;
  patient_id: number;
  enrollment_id: number;
  episode_type: string;
  trigger_type: string;
  episode_status: string;
  opened_at: string | null;
  closed_at: string | null;
  owner_staff_id: number | null;
}

export interface PatientCareStaffOption {
  staff_id: number;
  display_name: string;
  user_id: number;
}

export interface PatientCareDetailsData {
  risk_tier: string | null;
  enrollment: PatientCareEnrollment | null;
  episode: PatientCareEpisode | null;
  owner_staff: PatientCareStaffOption[];
}

export interface PatientCareDetailsUpsertRequest {
  organization_id?: number | null;
  risk_tier: string | null;
  owner_staff_id: number | null;
  enrollment_program: string;
  enrollment_status: string;
  enrollment_date: string | null;
  close_date: string | null;
  closed_reason: string | null;
  episode_type: string;
  trigger_type: string;
  episode_status: string;
  opened_at: string | null;
  closed_at: string | null;
}
