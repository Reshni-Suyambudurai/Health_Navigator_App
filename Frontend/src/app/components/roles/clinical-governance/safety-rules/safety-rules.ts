import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  heroBeaker,
  heroCheckCircle,
  heroNoSymbol,
  heroPencilSquare,
  heroShieldCheck,
  heroXMark,
} from '@ng-icons/heroicons/outline';
import { finalize } from 'rxjs/operators';

import { SafetyRulesApi } from '../../../../api/navigator/safety-rules.api';
import { getSessionUser } from '../../../../api/tokenstore';
import {
  SafetyRule,
  SafetyRulesOverview,
  SafetyRuleUpdate,
} from '../../../../shared/types/navigator/safety-rules';
import { MarkdownPreview } from '../../../../shared/ui/markdown-preview/markdown-preview';
import { RefreshButton } from '../../../../shared/ui/refresh-button/refresh-button';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

type ReviewDecision = 'APPROVE' | 'REJECT';
type GovernanceView = 'PENDING' | 'EXISTING';

@Component({
  selector: 'app-safety-rules',
  standalone: true,
  imports: [CommonModule, FormsModule, NgIcon, MarkdownPreview, RefreshButton],
  providers: [provideIcons({ heroBeaker, heroCheckCircle, heroNoSymbol, heroPencilSquare, heroShieldCheck, heroXMark })],
  templateUrl: './safety-rules.html',
  styleUrl: './safety-rules.scss',
})
export class SafetyRules {
  private readonly api = inject(SafetyRulesApi);
  private readonly toast = inject(ToastState);
  private readonly sessionUser = getSessionUser();

  readonly overview = signal<SafetyRulesOverview | null>(null);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  readonly activeView = signal<GovernanceView>('PENDING');
  readonly searchTerm = signal('');
  readonly statusFilter = signal('ALL');
  readonly selectedRuleId = signal<number | null>(null);
  readonly decision = signal<ReviewDecision | null>(null);
  readonly deactivating = signal(false);
  readonly activating = signal(false);
  readonly descriptionMode = signal<'EDIT' | 'PREVIEW'>('EDIT');

  decisionReason = '';
  effectiveFrom = this.today();
  changeReason = '';
  activationForm: SafetyRuleUpdate = this.emptyUpdateForm();

  readonly categoryOptions = ['EMERGENCY', 'MEDICATION', 'SYMPTOM', 'PRIVACY', 'CLINICAL_SCOPE', 'SYMPTOM_SAFETY'];
  readonly urgencyOptions = ['ROUTINE', 'SAME_DAY', 'EMERGENCY', 'HIGH'];
  readonly actionOptions = ['SAFE_RESPOND', 'BLOCK_RESPONSE', 'ESCALATE', 'EMERGENCY_PROTOCOL', 'CREATE_ESCALATION'];
  readonly queueOptions = ['MEDICATION', 'APPOINTMENT', 'SOCIAL_SUPPORT', 'CLINICAL', 'CLINICAL_REVIEW', 'EMERGENCY'];
  readonly escalationTypeOptions = ['MEDICATION', 'APPOINTMENT', 'SOCIAL_SUPPORT', 'CLINICAL_REVIEW', 'EMERGENCY'];
  readonly priorityOptions = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];

  ngOnInit(): void {
    this.loadRules();
  }

  loadRules(): void {
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
        const visible = this.visibleRules;
        if (!visible.some((rule) => rule.rule_id === this.selectedRuleId())) {
          this.selectedRuleId.set(visible[0]?.rule_id ?? null);
        }
      },
      error: (error: { error?: { message?: string } }) => this.error.set(error.error?.message ?? 'Unable to load clinical guardrails.'),
    });
  }

  get pendingRules(): SafetyRule[] {
    return (this.overview()?.rules ?? []).filter((rule) => rule.approval_status === 'PENDING');
  }

  get existingRules(): SafetyRule[] {
    return (this.overview()?.rules ?? []).filter((rule) => rule.approval_status !== 'PENDING');
  }

  get visibleRules(): SafetyRule[] {
    const source = this.activeView() === 'PENDING' ? this.pendingRules : this.existingRules;
    const search = this.searchTerm().trim().toLowerCase();
    return source.filter((rule) =>
      (this.statusFilter() === 'ALL' || rule.status === this.statusFilter() || rule.approval_status === this.statusFilter()) &&
      (!search || `${rule.guardrail_name} ${rule.rule_name} ${rule.category} ${rule.created_by_name ?? ''}`.toLowerCase().includes(search)),
    );
  }

  get selectedRule(): SafetyRule | null {
    return this.overview()?.rules.find((rule) => rule.rule_id === this.selectedRuleId()) ?? null;
  }

  switchView(view: GovernanceView): void {
    this.activeView.set(view);
    this.statusFilter.set('ALL');
    this.selectedRuleId.set(this.visibleRules[0]?.rule_id ?? null);
  }

  selectRule(rule: SafetyRule): void {
    this.selectedRuleId.set(rule.rule_id);
  }

  openDecision(decision: ReviewDecision): void {
    this.decisionReason = '';
    this.effectiveFrom = this.today();
    this.decision.set(decision);
  }

  submitDecision(): void {
    const userId = this.userId;
    const rule = this.selectedRule;
    const decision = this.decision();
    if (!userId || !rule || !decision || !this.decisionReason.trim()) {
      this.toast.warning('A review reason is required.');
      return;
    }
    if (decision === 'APPROVE' && !this.effectiveFrom) {
      this.toast.warning('Select an effective date.');
      return;
    }
    this.saving.set(true);
    const request = decision === 'APPROVE'
      ? this.api.approveRule(userId, rule.rule_id, this.decisionReason, this.effectiveFrom)
      : this.api.rejectRule(userId, rule.rule_id, this.decisionReason);
    request.pipe(finalize(() => this.saving.set(false))).subscribe({
      next: () => {
        this.toast.success(decision === 'APPROVE' ? 'Rule approved and activated.' : 'Rule rejected with feedback.');
        this.decision.set(null);
        this.loadRules();
      },
      error: (error: { error?: { message?: string } }) => this.showError(error, 'Unable to record this review decision.'),
    });
  }

  openDeactivate(): void {
    this.changeReason = '';
    this.deactivating.set(true);
  }

  submitDeactivation(): void {
    const userId = this.userId;
    const rule = this.selectedRule;
    if (!userId || !rule || !this.changeReason.trim()) {
      this.toast.warning('A deactivation reason is required.');
      return;
    }
    this.saving.set(true);
    this.api.deactivateRule(userId, rule.rule_id, this.changeReason).pipe(finalize(() => this.saving.set(false))).subscribe({
      next: () => {
        this.toast.success('Rule deactivated.');
        this.deactivating.set(false);
        this.loadRules();
      },
      error: (error: { error?: { message?: string } }) => this.showError(error, 'Unable to deactivate this rule.'),
    });
  }

  openActivation(rule: SafetyRule): void {
    this.activationForm = this.ruleToUpdate(rule);
    this.changeReason = '';
    this.effectiveFrom = this.today();
    this.descriptionMode.set('EDIT');
    this.activating.set(true);
  }

  submitActivation(): void {
    const userId = this.userId;
    const rule = this.selectedRule;
    if (!userId || !rule || !this.changeReason.trim() || !this.effectiveFrom || !this.validRule(this.activationForm)) {
      this.toast.warning('Complete the rule, reason, and effective date fields.');
      return;
    }
    this.saving.set(true);
    this.api.activateRule(userId, rule.rule_id, this.activationForm, this.changeReason, this.effectiveFrom).pipe(finalize(() => this.saving.set(false))).subscribe({
      next: () => {
        this.toast.success('Inactive rule updated and activated.');
        this.activating.set(false);
        this.loadRules();
      },
      error: (error: { error?: { message?: string } }) => this.showError(error, 'Unable to activate this rule.'),
    });
  }

  label(value: string | null): string {
    return value ? value.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase()) : 'Not configured';
  }

  formatDate(value: string | null): string {
    return value ? new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : 'Not set';
  }

  eventLabel(event: SafetyRule['activity_history'][number]): string {
    if (typeof event.details === 'object' && event.details) return this.label(String(event.details['event_type'] ?? event.action));
    return this.label(event.action);
  }

  eventReason(event: SafetyRule['activity_history'][number]): string | null {
    if (typeof event.details === 'object' && event.details && typeof event.details['reason'] === 'string') return event.details['reason'];
    return null;
  }

  private get userId(): number | null {
    return this.sessionUser?.user_id ?? this.sessionUser?.userId ?? null;
  }

  private validRule(rule: SafetyRuleUpdate): boolean {
    return !!rule.guardrail_name.trim() && !!rule.description.trim() && !!rule.rule_name.trim();
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

  private emptyUpdateForm(): SafetyRuleUpdate {
    return {
      guardrail_name: '', description: '', rule_name: '', category: 'SYMPTOM', urgency: 'ROUTINE',
      handler_role_id: null, action_type: 'SAFE_RESPOND', patient_response_template: null,
      target_queue_type: null, escalation_type: null, escalation_priority: null,
    };
  }

  private today(): string {
    const now = new Date();
    return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
  }

  private showError(error: { error?: { message?: string } }, fallback: string): void {
    const message = error.error?.message ?? fallback;
    this.error.set(message);
    this.toast.error(message);
  }
}