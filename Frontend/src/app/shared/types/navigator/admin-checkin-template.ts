import { ApiSuccessResponse } from './user';

export type CheckinTemplateType = 'POST_DISCHARGE' | 'CHRONIC_CARE' | 'MEDICATION_FOLLOWUP';
export type CheckinTemplateStatus = 'DRAFT' | 'ACTIVE' | 'INACTIVE';
export type TemplateReviewStatus = 'PENDING' | 'APPROVED' | 'REJECTED';
export type CheckinAnswerType = 'YES_NO' | 'TEXT' | 'NUMBER' | 'SINGLE_CHOICE' | 'MULTIPLE_CHOICE';

export interface AdminCheckinQuestion {
  question_id: number;
  question_key: string;
  question_text: string;
  answer_type: CheckinAnswerType;
  options: string[] | null;
  display_order: number;
  is_required: boolean;
  is_active: boolean;
}

export interface AdminCheckinTemplate {
  checkin_template_id: number;
  template_name: string;
  template_type: CheckinTemplateType;
  description: string | null;
  version: number;
  status: CheckinTemplateStatus;
  review_status: TemplateReviewStatus | null;
  review_id: number | null;
  review_notes: string | null;
  is_editable: boolean;
  created_at: string | null;
  updated_at: string | null;
  questions?: AdminCheckinQuestion[];
}

export interface AdminCheckinTemplateRequest {
  template_name: string;
  template_type: CheckinTemplateType;
  description: string | null;
}

export interface AdminCheckinQuestionRequest {
  question_key: string;
  question_text: string;
  answer_type: CheckinAnswerType;
  options: string[] | null;
  display_order: number;
  is_required: boolean;
  is_active: boolean;
}

export interface CheckinTemplateReview {
  review_id: number;
  status: TemplateReviewStatus;
  submission_note: string | null;
  review_notes: string | null;
  submitted_by_user_id: number;
  reviewed_by_user_id: number | null;
  submitted_at: string | null;
  reviewed_at: string | null;
  template: AdminCheckinTemplate;
}

export type AdminCheckinTemplateListResponse = ApiSuccessResponse<{ templates: AdminCheckinTemplate[] }>;
export type AdminCheckinTemplateResponse = ApiSuccessResponse<AdminCheckinTemplate>;
export type AdminCheckinQuestionResponse = ApiSuccessResponse<AdminCheckinQuestion>;
export type AdminCheckinQuestionListResponse = ApiSuccessResponse<{ questions: AdminCheckinQuestion[] }>;
export type CheckinTemplateReviewResponse = ApiSuccessResponse<CheckinTemplateReview>;
export type CheckinTemplateReviewListResponse = ApiSuccessResponse<{ reviews: CheckinTemplateReview[] }>;