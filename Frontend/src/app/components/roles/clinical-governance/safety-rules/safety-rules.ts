import { CommonModule } from '@angular/common';
import { Component, ElementRef, ViewChild, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { heroBeaker, heroBolt, heroCheckCircle, heroClock, heroDocumentDuplicate, heroExclamationTriangle, heroFunnel, heroMagnifyingGlass, heroPlay, heroShieldCheck } from '@ng-icons/heroicons/outline';
import { finalize } from 'rxjs/operators';
import { SafetyRulesApi } from '../../../../api/navigator/safety-rules.api';
import { getSessionUser } from '../../../../api/tokenstore';
import { SafetyRule, SafetyRulesOverview, ScenarioTestResult } from '../../../../shared/types/navigator/safety-rules';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

@Component({
  selector: 'app-safety-rules',
  standalone: true,
  imports: [CommonModule, FormsModule, NgIcon],
  providers: [provideIcons({ heroBeaker, heroBolt, heroCheckCircle, heroClock, heroDocumentDuplicate, heroExclamationTriangle, heroFunnel, heroMagnifyingGlass, heroPlay, heroShieldCheck })],
  templateUrl: './safety-rules.html',
  styleUrl: './safety-rules.scss',
})
export class SafetyRules {
  private readonly api = inject(SafetyRulesApi);
  private readonly toast = inject(ToastState);
  private readonly sessionUser = getSessionUser();
  @ViewChild('scenarioInput') scenarioInput?: ElementRef<HTMLTextAreaElement>;

  readonly overview = signal<SafetyRulesOverview | null>(null);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly testing = signal(false);
  readonly error = signal<string | null>(null);
  readonly selectedRuleId = signal<number | null>(null);
  readonly searchTerm = signal('');
  readonly statusFilter = signal('ALL');
  readonly categoryFilter = signal('ALL');
  readonly testResult = signal<ScenarioTestResult | null>(null);
  scenarioText = '';
  approvalNote = '';

  ngOnInit(): void { this.loadRules(); }

  loadRules(): void {
    const userId = this.sessionUser?.user_id ?? this.sessionUser?.userId;
    if (!userId) { this.error.set('Your session has expired. Please sign in again.'); return; }
    this.loading.set(true); this.error.set(null);
    this.api.getOverview(userId).pipe(finalize(() => this.loading.set(false))).subscribe({
      next: (response) => {
        this.overview.set(response.data);
        if (!this.selectedRuleId() && response.data.rules.length) this.selectedRuleId.set(response.data.rules[0].rule_id);
      },
      error: (error: { error?: { message?: string } }) => this.error.set(error?.error?.message ?? 'Unable to load safety rules.'),
    });
  }

  get filteredRules(): SafetyRule[] {
    const search = this.searchTerm().trim().toLowerCase();
    return (this.overview()?.rules ?? []).filter((rule) =>
      (this.statusFilter() === 'ALL' || rule.status === this.statusFilter()) &&
      (this.categoryFilter() === 'ALL' || rule.category === this.categoryFilter()) &&
      (!search || `${rule.rule_name} ${rule.guardrail_name} ${rule.category}`.toLowerCase().includes(search))
    );
  }

  get selectedRule(): SafetyRule | null { return this.overview()?.rules.find((rule) => rule.rule_id === this.selectedRuleId()) ?? null; }
  get categories(): string[] { return [...new Set((this.overview()?.rules ?? []).map((rule) => rule.category))]; }

  selectRule(rule: SafetyRule): void { this.selectedRuleId.set(rule.rule_id); this.testResult.set(null); this.approvalNote = ''; }

  approveSelected(): void {
    const userId = this.sessionUser?.user_id ?? this.sessionUser?.userId; const rule = this.selectedRule;
    if (!userId || !rule || !this.approvalNote.trim()) { this.error.set('Enter an approval note before activating this rule.'); return; }
    this.saving.set(true); this.error.set(null);
    this.api.approveRule(userId, rule.rule_id, this.approvalNote).pipe(finalize(() => this.saving.set(false))).subscribe({
      next: () => { this.toast.success('Rule approved and activated.'); this.loadRules(); },
      error: (error: { error?: { message?: string } }) => this.error.set(error?.error?.message ?? 'Unable to approve this rule.'),
    });
  }

  runScenario(): void {
    const userId = this.sessionUser?.user_id ?? this.sessionUser?.userId;
    if (!userId || !this.scenarioText.trim()) { this.error.set('Enter an example patient message to test.'); return; }
    this.testing.set(true); this.error.set(null);
    this.api.testScenario(userId, this.scenarioText, this.selectedRuleId()).pipe(finalize(() => this.testing.set(false))).subscribe({
      next: (response) => this.testResult.set(response.data),
      error: (error: { error?: { message?: string } }) => this.error.set(error?.error?.message ?? 'Unable to test this scenario.'),
    });
  }

  focusScenario(): void { this.scenarioInput?.nativeElement.focus(); }
  label(value: string | null): string { return value ? value.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase()) : 'Not configured'; }
  formatDate(value: string | null): string { return value ? new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : 'Never'; }
  historyNote(event: SafetyRule['approval_history'][number]): string { return typeof event.details === 'object' && event.details?.note ? event.details.note : 'Rule status updated'; }
}
