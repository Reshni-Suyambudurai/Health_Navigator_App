import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { AdminCheckinTemplateApi } from '../../../../api/navigator/admin-checkin-template.api';
import { getSessionUser } from '../../../../api/tokenstore';
import {
  AdminCheckinQuestion,
  AdminCheckinQuestionRequest,
  AdminCheckinTemplate,
  AdminCheckinTemplateRequest,
  CheckinAnswerType,
  CheckinTemplateType,
} from '../../../../shared/types/navigator/admin-checkin-template';
import { Breadcrumb, BreadcrumbItem } from '../../../../shared/ui/breadcrumb/breadcrumb';
import { CheckinTemplatePreview } from './checkin-template-preview/checkin-template-preview';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

interface QuestionDraft {
  question_key: string;
  question_text: string;
  answer_type: CheckinAnswerType;
  optionsText: string;
  display_order: number;
  is_required: boolean;
  is_active: boolean;
}

type PendingDeletion =
  | { kind: 'template'; template: AdminCheckinTemplate }
  | { kind: 'question'; template: AdminCheckinTemplate; question: AdminCheckinQuestion };

@Component({
  selector: 'app-system-admin-checkin-template',
  standalone: true,
  imports: [CommonModule, FormsModule, Breadcrumb, CheckinTemplatePreview],
  templateUrl: './checkin-template.html',
  styleUrl: './checkin-template.scss',
})
export class SystemAdminCheckinTemplate implements OnInit {
  private readonly api = inject(AdminCheckinTemplateApi);
  private readonly toast = inject(ToastState);
  private readonly sessionUser = getSessionUser();

  readonly templates = signal<AdminCheckinTemplate[]>([]);
  readonly selected = signal<AdminCheckinTemplate | null>(null);
  readonly loading = signal(false);
  readonly detailLoading = signal(false);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  readonly templateDialog = signal<'create' | 'edit' | null>(null);
  readonly questionDialog = signal<'create' | 'edit' | null>(null);
  readonly editingQuestion = signal<AdminCheckinQuestion | null>(null);
  readonly pendingDeletion = signal<PendingDeletion | null>(null);
  readonly submissionOpen = signal(false);
  readonly activeView = signal<'questions' | 'preview'>('questions');
  readonly filteredTemplates = computed(() => {
    const query = this.search.trim().toLowerCase();
    return query
      ? this.templates().filter((template) =>
          template.template_name.toLowerCase().includes(query)
          || template.template_type.toLowerCase().includes(query),
        )
      : this.templates();
  });
  readonly breadcrumbs: BreadcrumbItem[] = [
    { label: 'System administration', route: '/system-admin/dashboard' },
    { label: 'Check-in templates' },
  ];
  readonly templateTypes: CheckinTemplateType[] = ['POST_DISCHARGE', 'CHRONIC_CARE', 'MEDICATION_FOLLOWUP'];
  readonly answerTypes: CheckinAnswerType[] = ['YES_NO', 'TEXT', 'NUMBER', 'SINGLE_CHOICE', 'MULTIPLE_CHOICE'];

  search = '';
  submissionNote = '';
  templateDraft: AdminCheckinTemplateRequest = this.emptyTemplateDraft();
  questionDraft: QuestionDraft = this.emptyQuestionDraft();

  ngOnInit(): void {
    this.loadTemplates();
  }

  refresh(): void {
    this.loadTemplates(this.selected()?.checkin_template_id);
  }

  selectTemplate(template: AdminCheckinTemplate): void {
    this.detailLoading.set(true);
    this.error.set(null);
    this.api.get(this.userId(), template.checkin_template_id)
      .pipe(finalize(() => this.detailLoading.set(false)))
      .subscribe({
        next: (response) => this.selected.set(response.data),
        error: (error) => this.showError(this.errorMessage(error, 'Unable to load the template.')),
      });
  }

  openCreateTemplate(): void {
    this.templateDraft = this.emptyTemplateDraft();
    this.error.set(null);
    this.templateDialog.set('create');
  }

  openEditTemplate(): void {
    const template = this.selected();
    if (!template?.is_editable) return;
    this.templateDraft = {
      template_name: template.template_name,
      template_type: template.template_type,
      description: template.description,
    };
    this.error.set(null);
    this.templateDialog.set('edit');
  }

  closeTemplateDialog(): void {
    if (!this.saving()) this.templateDialog.set(null);
  }

  saveTemplate(): void {
    if (!this.templateDraft.template_name.trim()) {
      this.showError('Template name is required.');
      return;
    }
    const selected = this.selected();
    const request = this.templateDialog() === 'edit' && selected
      ? this.api.update(this.userId(), selected.checkin_template_id, this.templateDraft)
      : this.api.create(this.userId(), this.templateDraft);
    this.saving.set(true);
    request.pipe(finalize(() => this.saving.set(false))).subscribe({
      next: (response) => {
        this.templateDialog.set(null);
        this.selected.set(response.data);
        this.toast.success(response.message);
        this.loadTemplates(response.data.checkin_template_id);
      },
      error: (error) => this.showError(this.errorMessage(error, 'Unable to save the template.')),
    });
  }

  requestTemplateDeletion(): void {
    const template = this.selected();
    if (template?.is_editable) this.pendingDeletion.set({ kind: 'template', template });
  }

  openCreateQuestion(): void {
    const template = this.selected();
    if (!template?.is_editable) return;
    this.editingQuestion.set(null);
    this.questionDraft = this.emptyQuestionDraft((template.questions?.length ?? 0) + 1);
    this.error.set(null);
    this.questionDialog.set('create');
  }

  openEditQuestion(question: AdminCheckinQuestion): void {
    if (!this.selected()?.is_editable) return;
    this.editingQuestion.set(question);
    this.questionDraft = {
      question_key: question.question_key,
      question_text: question.question_text,
      answer_type: question.answer_type,
      optionsText: (question.options ?? []).join('\n'),
      display_order: question.display_order,
      is_required: question.is_required,
      is_active: question.is_active,
    };
    this.error.set(null);
    this.questionDialog.set('edit');
  }

  closeQuestionDialog(): void {
    if (!this.saving()) this.questionDialog.set(null);
  }

  saveQuestion(): void {
    const template = this.selected();
    if (!template || !this.questionDraft.question_key.trim() || !this.questionDraft.question_text.trim()) {
      this.showError('Question key and text are required.');
      return;
    }
    const options = this.choiceType(this.questionDraft.answer_type)
      ? this.questionDraft.optionsText.split(/\r?\n|,/).map((value) => value.trim()).filter(Boolean)
      : null;
    if (this.choiceType(this.questionDraft.answer_type) && (options?.length ?? 0) < 2) {
      this.showError('Choice questions require at least two options.');
      return;
    }
    const payload: AdminCheckinQuestionRequest = {
      question_key: this.questionDraft.question_key.trim(),
      question_text: this.questionDraft.question_text.trim(),
      answer_type: this.questionDraft.answer_type,
      options,
      display_order: this.questionDraft.display_order,
      is_required: this.questionDraft.is_required,
      is_active: this.questionDraft.is_active,
    };
    const editing = this.editingQuestion();
    const request = editing
      ? this.api.updateQuestion(this.userId(), editing.question_id, payload)
      : this.api.createQuestion(this.userId(), template.checkin_template_id, payload);
    this.saving.set(true);
    request.pipe(finalize(() => this.saving.set(false))).subscribe({
      next: (response) => {
        this.questionDialog.set(null);
        this.toast.success(response.message);
        this.selectTemplate(template);
        this.loadTemplates(template.checkin_template_id, false);
      },
      error: (error) => this.showError(this.errorMessage(error, 'Unable to save the question.')),
    });
  }

  requestQuestionDeletion(question: AdminCheckinQuestion): void {
    const template = this.selected();
    if (template?.is_editable) this.pendingDeletion.set({ kind: 'question', template, question });
  }

  cancelDeletion(): void {
    if (!this.saving()) this.pendingDeletion.set(null);
  }

  confirmDeletion(): void {
    const pending = this.pendingDeletion();
    if (!pending) return;
    const request = pending.kind === 'template'
      ? this.api.delete(this.userId(), pending.template.checkin_template_id)
      : this.api.deleteQuestion(this.userId(), pending.question.question_id);
    this.saving.set(true);
    request
      .pipe(finalize(() => this.saving.set(false)))
      .subscribe({
        next: (response) => {
          this.pendingDeletion.set(null);
          this.toast.success(response.message);
          if (pending.kind === 'template') {
            this.selected.set(null);
            this.loadTemplates();
          } else {
            this.selectTemplate(pending.template);
          }
        },
        error: (error) => this.showError(this.errorMessage(error, `Unable to delete the ${pending.kind}.`)),
      });
  }

  moveQuestion(index: number, direction: -1 | 1): void {
    const template = this.selected();
    const questions = [...(template?.questions ?? [])].sort((a, b) => a.display_order - b.display_order);
    const target = index + direction;
    if (!template?.is_editable || target < 0 || target >= questions.length) return;
    [questions[index], questions[target]] = [questions[target], questions[index]];
    this.saving.set(true);
    this.api.reorder(this.userId(), template.checkin_template_id, questions.map((question) => question.question_id))
      .pipe(finalize(() => this.saving.set(false)))
      .subscribe({
        next: (response) => {
          this.selected.set({ ...template, questions: response.data.questions });
          this.toast.success(response.message);
        },
        error: (error) => this.showError(this.errorMessage(error, 'Unable to reorder questions.')),
      });
  }

  openSubmission(): void {
    this.submissionNote = '';
    this.error.set(null);
    this.submissionOpen.set(true);
  }

  submitReview(): void {
    const template = this.selected();
    if (!template) return;
    this.saving.set(true);
    this.api.submitReview(this.userId(), template.checkin_template_id, this.submissionNote.trim() || null)
      .pipe(finalize(() => this.saving.set(false)))
      .subscribe({
        next: (response) => {
          this.submissionOpen.set(false);
          this.toast.success(response.message);
          this.loadTemplates(template.checkin_template_id);
        },
        error: (error) => this.showError(this.errorMessage(error, 'Unable to submit the template.')),
      });
  }

  createVersion(): void {
    const template = this.selected();
    if (!template || template.review_status !== 'APPROVED') return;
    this.saving.set(true);
    this.api.createVersion(this.userId(), template.checkin_template_id)
      .pipe(finalize(() => this.saving.set(false)))
      .subscribe({
        next: (response) => {
          this.toast.success(response.message);
          this.loadTemplates(response.data.checkin_template_id);
        },
        error: (error) => this.showError(this.errorMessage(error, 'Unable to create a new version.')),
      });
  }

  choiceType(type: CheckinAnswerType): boolean {
    return type === 'SINGLE_CHOICE' || type === 'MULTIPLE_CHOICE';
  }

  label(value: string): string {
    return value.toLowerCase().replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  private loadTemplates(selectedId?: number, loadDetail = true): void {
    this.loading.set(true);
    this.api.list(this.userId()).pipe(finalize(() => this.loading.set(false))).subscribe({
      next: (response) => {
        this.templates.set(response.data.templates);
        const id = selectedId ?? this.selected()?.checkin_template_id;
        const next = response.data.templates.find((template) => template.checkin_template_id === id)
          ?? response.data.templates[0]
          ?? null;
        if (loadDetail && next) this.selectTemplate(next);
        else if (!next) this.selected.set(null);
      },
      error: (error) => this.showError(this.errorMessage(error, 'Unable to load check-in templates.')),
    });
  }

  private emptyTemplateDraft(): AdminCheckinTemplateRequest {
    return { template_name: '', template_type: 'POST_DISCHARGE', description: null };
  }

  private emptyQuestionDraft(displayOrder = 1): QuestionDraft {
    return {
      question_key: '',
      question_text: '',
      answer_type: 'YES_NO',
      optionsText: '',
      display_order: displayOrder,
      is_required: true,
      is_active: true,
    };
  }

  private userId(): number {
    return Number(this.sessionUser?.user_id ?? this.sessionUser?.userId ?? 0);
  }

  private showError(message: string): void {
    this.error.set(message);
    this.toast.error(message);
  }

  private errorMessage(error: unknown, fallback: string): string {
    return (error as { error?: { message?: string } })?.error?.message ?? fallback;
  }
}
