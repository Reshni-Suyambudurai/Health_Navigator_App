import { ApiSuccessResponse } from './navigator/user';

export type NotificationType =
  | 'GENERAL'
  | 'ESCALATION'
  | 'APPOINTMENT_REMINDER'
  | 'OUTREACH_UPDATE'
  | 'FOLLOW_UP'
  | 'SYSTEM_ALERT';
export type NotificationPriority = 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT';
export type NotificationStatus = 'UNREAD' | 'READ' | 'ARCHIVED';

export interface NotificationRecord {
  notification_id: number;
  organization_id: number | null;
  sender_user_id: number;
  sender_name: string;
  recipient_user_id: number;
  title: string | null;
  message: string;
  notification_type: NotificationType;
  priority: NotificationPriority;
  status: NotificationStatus;
  created_at: string | null;
  read_at: string | null;
}

export interface NotificationCreateRequest {
  recipient_user_id: number;
  title: string | null;
  message: string;
  notification_type: NotificationType;
  priority: NotificationPriority;
}

export type NotificationListResponse = ApiSuccessResponse<{
  notifications: NotificationRecord[];
  count: number;
  unread_count: number;
}>;
export type NotificationResponse = ApiSuccessResponse<NotificationRecord>;
export type NotificationUnreadCountResponse = ApiSuccessResponse<{ unread_count: number }>;