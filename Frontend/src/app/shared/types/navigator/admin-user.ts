import { ApiSuccessResponse } from './user';

export type AdminRoleName =
  | 'PATIENT'
  | 'CARE_MANAGER'
  | 'TRANSITIONAL_CARE_NURSE'
  | 'PHARMACIST'
  | 'CLINICAL_GOVERNANCE'
  | 'SYSTEM_ADMIN';

export type AdminUserStatus = 'ACTIVE' | 'INACTIVE' | 'SUSPENDED';

export interface AdminUserRecord {
  user_id: number;
  organization_id: number;
  organization_name: string | null;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  role_id: number;
  role_name: AdminRoleName;
  status: AdminUserStatus;
  created_at: string | null;
  updated_at: string | null;
}

export interface AdminRoleOption {
  role_id: number;
  role_name: AdminRoleName;
  description: string | null;
}

export interface AdminUserFilters {
  skip?: number;
  limit?: number;
  search?: string;
  role_name?: AdminRoleName | '';
  user_status?: AdminUserStatus | '';
}

export interface AdminUserCreateRequest {
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  password: string;
  role_name: AdminRoleName;
}

export interface AdminUserUpdateRequest {
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  role_name: AdminRoleName;
}

export interface AdminUserListData {
  users: AdminUserRecord[];
  count: number;
}

export interface AdminRoleListData {
  roles: AdminRoleOption[];
}

export type AdminUserResponse = ApiSuccessResponse<AdminUserRecord>;
export type AdminUserListResponse = ApiSuccessResponse<AdminUserListData>;
export type AdminRoleListResponse = ApiSuccessResponse<AdminRoleListData>;