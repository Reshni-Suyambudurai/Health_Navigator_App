export interface ApiSuccessResponse<TData> {
  status: 'success' | string;
  message: string;
  data: TData;
}

export interface OrganizationOption {
  organization_id: number;
  organization_name: string;
}

export interface OwnerStaffOption {
  staff_id: number;
  display_name: string;
  user_id: number;
}

export interface PatientIntakeMetadata {
  enrollment_programs: string[];
  enrollment_statuses: string[];
  episode_types: string[];
  trigger_types: string[];
  episode_statuses: string[];
  genders: string[];
  contact_methods: string[];
  risk_tiers: string[];
  organizations: OrganizationOption[];
  owner_staff: OwnerStaffOption[];
}

export interface PatientOnboardFromFhirRequest {
  fhir_patient_id: string;
  organization_id: number;
  enrollment_program: string;
  enrollment_status: string;
  enrollment_date?: string | null;
  created_by_user_id?: number | null;
  episode_type: string;
  trigger_type: string;
  trigger_reference?: string | null;
  episode_status: string;
  opened_at?: string | null;
  owner_staff_id?: number | null;
  first_name: string;
  last_name: string;
  email?: string | null;
  date_of_birth: string;
  gender: string;
  phone?: string | null;
  preferred_language?: string | null;
  preferred_contact_method: string;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  risk_tier: string;
  initial_password: string;
}

export interface PatientIntakeResult {
  existing_user: boolean;
  user_id: number;
  patient_id: number | null;
  enrollment_id?: number;
  episode_id?: number;
  email: string;
  status: string;
}
