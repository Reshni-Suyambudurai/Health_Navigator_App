export interface ApiSuccessResponse<TData> {
  status: 'success' | string;
  message: string;
  data: TData;
}

export interface PatientProfileRecord {
  patient_id: number;
  user_id: number;
  external_fhir_patient_id: string | null;
  date_of_birth: string | null;
  gender: string | null;
  preferred_language: string | null;
  preferred_contact_method: string | null;
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  risk_tier: string | null;
}
