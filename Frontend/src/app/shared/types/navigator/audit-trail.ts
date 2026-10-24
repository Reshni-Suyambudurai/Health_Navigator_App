import { ApiSuccessResponse } from './user';

export type AdminAuditAction = 'CREATE_USER' | 'UPDATE_USER' | 'DISABLE_USER' | 'ENABLE_USER';

export interface AdminAuditDetails {
  changed_fields?: string[];
  before?: Record<string, unknown> | null;
  after?: Record<string, unknown> | null;
  summary?: string;
}

export interface AdminAuditEntry {
  audit_id: number;
  action: AdminAuditAction;
  resource_id: number;
  actor_name: string;
  target_name: string;
  target_email: string;
  details: AdminAuditDetails | null;
  created_at: string | null;
}

export interface AdminAuditListData {
  entries: AdminAuditEntry[];
  count: number;
}

export type AdminAuditListResponse = ApiSuccessResponse<AdminAuditListData>;