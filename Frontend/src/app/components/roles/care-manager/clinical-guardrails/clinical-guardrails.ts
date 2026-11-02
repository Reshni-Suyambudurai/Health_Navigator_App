import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  heroChevronRight,
  heroPaperAirplane,
  heroPencilSquare,
  heroPlus,
  heroTrash,
  heroXMark,
} from '@ng-icons/heroicons/outline';
import { finalize } from 'rxjs/operators';

import { SafetyRulesApi } from '../../../../api/navigator/safety-rules.api';
import { getSessionUser } from '../../../../api/tokenstore';
import {
  ClinicalGuardrailCreate,
  SafetyRule,
  SafetyRulePayload,
  SafetyRulesOverview,
  SafetyRuleUpdate,
} from '../../../../shared/types/navigator/safety-rules';
import { MarkdownPreview } from '../../../../shared/ui/markdown-preview/markdown-preview';
import { RefreshButton } from '../../../../shared/ui/refresh-button/refresh-button';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

@Component({
  selector: 'app-care-manager-clinical-guardrails',
  standalone: true,
  imports: [CommonModule, FormsModule, NgIcon, MarkdownPreview, RefreshButton],
  providers: [provideIcons({ heroChevronRight, heroPaperAirplane, heroPencilSquare, heroPlus, heroTrash, heroXMark })],
  templateUrl: './clinical-guardrails.html',
  styleUrl: './clinical-guardrails.scss',
})
export class CareManagerClinicalGuardrails {
  private readonly api = inject(SafetyRulesApi);
  private readonly toast = inject(ToastState);
  private readonly sessionUser = getSessionUser();

  readonly overview = signal<SafetyRulesOverview | null>(null);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  readonly searchTerm = signal('');
  readonly approvalFilter = signal('ALL');
  readonly selectedRuleId = signal<number | null>(null);
  readonly selectedForSubmission = signal<Set<number>>(new Set());
  readonly showCreateForm = signal(false);
  readonly editingRuleId = signal<number | null>(null);
  readonly descriptionMode = signal<'EDIT' | 'PREVIEW'>('EDIT');

  createForm: ClinicalGuardrailCreate = this.emptyCreateForm();
  editForm: SafetyRuleUpdate = this.emptyUpdateForm();

  readonly categoryOptions = ['EMERGENCY', 'MEDICATION', 'SYMPTOM', 'PRIVACY', 'CLINICAL_SCOPE', 'SYMPTOM_SAFETY'];
  readonly urgencyOptions = ['ROUTINE', 'SAME_DAY', 'EMERGENCY', 'HIGH'];
  readonly actionOptions = ['SAFE_RESPOND', 'BLOCK_RESPONSE', 'ESCALATE', 'EMERGENCY_PROTOCOL', 'CREATE_ESCALATION'];
  readonly queueOptions = ['MEDICATION', 'APPOINTMENT', 'SOCIAL_SUPPORT', 'CLINICAL', 'CLINICAL_REVIEW', 'EMERGENCY'];
  readonly escalationTypeOptions = ['MEDICATION', 'APPOINTMENT', 'SOCIAL_SUPPORT', 'CLINICAL_REVIEW', 'EMERGENCY'];
  readonly priorityOptions = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];

  ngOnInit(): void {
    this.loadGuardrails();
  }

  loadGuardrails(): void {
    const userId = this.userId;
    if (!userId) {
      this.error.set('Your session has expired. Please sign in again.');
      return;
    }
    this.loading.set(true);
    this.error.set(null);
    this.api.getOverview(userId).pipe(finalize(() => this.loading.set(false))).subscribe({
      next: (response) => {
        this.overview.set(response.data);
        const selected = this.selectedRuleId();
        if (!selected || !response.data.rules.some((rule) => rule.rule_id === selected)) {
          this.selectedRuleId.set(response.data.rules[0]?.rule_id ?? null);
        }
        const eligibleIds = new Set(response.data.rules.filter((rule) => this.canEdit(rule)).map((rule) => rule.rule_id));
        this.selectedForSubmission.update((items) => new Set([...items].filter((id) => eligibleIds.has(id))));
      },
      error: (error: { error?: { message?: string } }) => this.error.set(error.error?.message ?? 'Unable to load clinical guardrails.'),
    });
  }

  get filteredRules(): SafetyRule[] {
    const search = this.searchTerm().trim().toLowerCase();
    return (this.overview()?.rules ?? []).filter((rule) =>
      (this.approvalFilter() === 'ALL' || rule.approval_status === this.approvalFilter()) &&
      (!search || `${rule.guardrail_name} ${rule.rule_name} ${rule.category}`.toLowerCase().includes(search)),
    );
  }

  get selectedRule(): SafetyRule | null {
    return this.overview()?.rules.find((rule) => rule.rule_id === this.selectedRuleId()) ?? null;
  }

  selectRule(rule: SafetyRule): void {
    this.showCreateForm.set(false);
    this.editingRuleId.set(null);
    this.selectedRuleId.set(rule.rule_id);
  }

  startCreate(): void {
    this.createForm = this.emptyCreateForm();
    this.editingRuleId.set(null);
    this.descriptionMode.set('EDIT');
    this.showCreateForm.set(true);
  }

  cancelCreate(): void {
    this.showCreateForm.set(false);
  }

  canEdit(rule: SafetyRule): boolean {
    return rule.created_by_user_id === this.userId && ['DRAFT', 'REJECTED'].includes(rule.approval_status);
  }

  toggleSubmission(ruleId: number): void {
    this.selectedForSubmission.update((current) => {
      const next = new Set(current);
      if (next.has(ruleId)) next.delete(ruleId); else next.add(ruleId);
      return next;
    });
  }

  submitSelected(): void {
    const userId = this.userId;
    const ruleIds = [...this.selectedForSubmission()];
    if (!userId || !ruleIds.length) {
      this.toast.warning('Select at least one draft or rejected rule.');
      return;
    }
    this.saving.set(true);
    this.api.submitRules(userId, ruleIds).pipe(finalize(() => this.saving.set(false))).subscribe({
      next: (response) => {
        this.toast.success(`${response.data.rule_ids.length} rule(s) submitted for review.`);
        this.selectedForSubmission.set(new Set());
        this.loadGuardrails();
      },
      error: (error: { error?: { message?: string } }) => this.showError(error, 'Unable to submit the selected rules.'),
    });
  }

  createGuardrail(): void {
    const userId = this.userId;
    if (!userId || !this.validCreateForm()) {
      this.toast.warning('Complete the guardrail and rule fields.');
      return;
    }
    this.saving.set(true);
    this.api.createGuardrail(userId, this.createForm).pipe(finalize(() => this.saving.set(false))).subscribe({
      next: () => {
        this.toast.success('Clinical guardrail saved as draft.');
        this.createForm = this.emptyCreateForm();
        this.showCreateForm.set(false);
        this.loadGuardrails();
      },
      error: (error: { error?: { message?: string } }) => this.showError(error, 'Unable to create this guardrail.'),
    });
  }

  addRuleDraft(): void {
    this.createForm.rules.push(this.emptyRule());
  }

  removeRuleDraft(index: number): void {
    if (this.createForm.rules.length > 1) this.createForm.rules.splice(index, 1);
  }

  startEdit(rule: SafetyRule): void {
    if (!this.canEdit(rule)) return;
    this.selectedRuleId.set(rule.rule_id);
    this.showCreateForm.set(false);
    this.editingRuleId.set(rule.rule_id);
    this.descriptionMode.set('EDIT');
    this.editForm = this.ruleToUpdate(rule);
  }

  cancelEdit(): void {
    this.editingRuleId.set(null);
  }

  saveEdit(): void {
    const userId = this.userId;
    const ruleId = this.editingRuleId();
    if (!userId || ruleId === null || !this.validRule(this.editForm)) {
      this.toast.warning('Complete the rule fields.');
      return;
    }
    this.saving.set(true);
    this.api.updateDraftRule(userId, ruleId, this.editForm).pipe(finalize(() => this.saving.set(false))).subscribe({
      next: () => {
        this.toast.success('Draft rule updated.');
        this.editingRuleId.set(null);
        this.loadGuardrails();
      },
      error: (error: { error?: { message?: string } }) => this.showError(error, 'Unable to update this rule.'),
    });
  }

  label(value: string | null): string {
    return value ? value.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase()) : 'Not configured';
  }

  formatDate(value: string | null): string {
    return value ? new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : 'Not set';
  }

  eventLabel(event: SafetyRule['activity_history'][number]): string {
    if (typeof event.details === 'object' && event.details) {
      return this.label(String(event.details['event_type'] ?? event.action));
    }
    return this.label(event.action);
  }

  private get userId(): number | null {
    return this.sessionUser?.user_id ?? this.sessionUser?.userId ?? null;
  }

  private validCreateForm(): boolean {
    return !!this.createForm.guardrail_name.trim() && !!this.createForm.description.trim() &&
      this.createForm.rules.length > 0 && this.createForm.rules.every((rule) => this.validRule(rule));
  }

  private validRule(rule: SafetyRulePayload): boolean {
    return !!rule.rule_name.trim();
  }

  private ruleToUpdate(rule: SafetyRule): SafetyRuleUpdate {
    return {
      guardrail_name: rule.guardrail_name,
      description: rule.description,
      rule_name: rule.rule_name,
      category: rule.category,
      urgency: rule.urgency,
      handler_role_id: rule.handler_role_id,
      action_type: rule.action_type,
      patient_response_template: rule.patient_response_template,
      target_queue_type: rule.target_queue_type,
      escalation_type: rule.escalation_type,
      escalation_priority: rule.escalation_priority,
    };
  }

  private emptyCreateForm(): ClinicalGuardrailCreate {
    return { guardrail_name: '', description: '', rules: [this.emptyRule()] };
  }

  private emptyUpdateForm(): SafetyRuleUpdate {
    return { guardrail_name: '', description: '', ...this.emptyRule() };
  }

  private emptyRule(): SafetyRulePayload {
    return {
      rule_name: '',
      category: 'SYMPTOM',
      urgency: 'ROUTINE',
      handler_role_id: null,
      action_type: 'SAFE_RESPOND',
      patient_response_template: null,
      target_queue_type: null,
      escalation_type: null,
      escalation_priority: null,
    };
  }

  private showError(error: { error?: { message?: string } }, fallback: string): void {
    const message = error.error?.message ?? fallback;
    this.error.set(message);
    this.toast.error(message);
  }
}