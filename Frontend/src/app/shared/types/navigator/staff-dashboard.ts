import { ApiSuccessResponse } from './user';

export type StaffDashboardPeriod = 'TODAY' | 'THIS_MONTH';

export interface StaffEscalationRow {
  patient: string;
  patient_id: number;
  type: string;
  priority: string;
  status: string;
  reason: string;
  assigned_at: string;
}

export interface StaffCheckinEscalationRow {
  patient: string;
  patient_id: number;
  type: string;
  status: string;
  reason: string;
  response: string;
  trigger_source: string;
  assigned_at: string;
}

export interface StaffAppointmentRow {
  patient: string;
  type: string;
  status: string;
  date_time: string;
  location_or_channel: string;
}

export interface StaffDashboardAnalytics {
  period: StaffDashboardPeriod;
  from_date: string | null;
  to_date: string | null;
  period_start: string;
  period_end: string;
  role: 'PHARMACIST' | 'SOCIAL_WORKER';
  patients_escalated: number;
  emergency_escalations: number;
  routine_escalations: number;
  checkin_emergency_escalations: number;
  checkin_routine_escalations: number;
  appointments_count: number;
  details: {
    assigned_escalations: StaffEscalationRow[];
    checkin_escalations: StaffCheckinEscalationRow[];
    appointments: StaffAppointmentRow[];
    recent_emergency_escalations: StaffEscalationRow[];
    recent_emergency_checkins: StaffCheckinEscalationRow[];
  };
}

export type StaffDashboardAnalyticsResponse = ApiSuccessResponse<StaffDashboardAnalytics>;
