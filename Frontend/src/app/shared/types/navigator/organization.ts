import { ApiSuccessResponse } from './user';

export type OrganizationStatus = 'ACTIVE' | 'INACTIVE';
export type OrganizationType = 'HOSPITAL' | 'CLINIC' | 'HEALTHCARE_GROUP' | 'PHARMACY' | 'HEALTH_PLAN';

export interface OrganizationContact {
  user_id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
}

export interface OrganizationRecord {
  organization_id: number;
  organization_name: string;
  organization_type: OrganizationType;
  npi_number: string | null;
  address: string | null;
  phone: string | null;
  status: OrganizationStatus;
  created_at: string | null;
  updated_at: string | null;
  user_count: number;
  contact: OrganizationContact;
}

export interface OrganizationUpdateRequest {
  organization_name: string;
  organization_type: OrganizationType;
  npi_number: string | null;
  address: string | null;
  phone: string | null;
  status: OrganizationStatus;
  contact_first_name: string;
  contact_last_name: string;
  contact_email: string;
  contact_phone: string | null;
}

export type OrganizationResponse = ApiSuccessResponse<OrganizationRecord>;