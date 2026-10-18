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
  episode_type: string | null;
}

export interface PatientEnrollmentListData {
  enrollments: PatientEnrollmentRecord[];
  count: number;
}

export interface PatientEnrollmentListParams {
  organization_id?: number;
  status_filter?: string;
  skip?: number;
  limit?: number;
}
